"""
TRAK-AI KDS — SQLite Veritabanı Katmanı (offline-first)
========================================================
Tarlalar (EVR_xx kodlu), rover ölçümleri, model tahminleri, hava geçmişi.
DB dosyası: data/trakaia.db

Tasarım ilkeleri:
    * DB tek doğru kaynak ("source of truth").
    * Hiç bir mock üretici çalıştırılmaz — tablolar yalnızca gerçek ölçüm/
      tahmin/hava verisi alır. İlk init'te yalnızca EVR_xx tarlaları
      seed edilir (prospective_validation.config.EVRENLI_SITES'tan).
    * Çevrim dışı: weather_service, FLOV ve rover modülleri DB'ye INSERT yapar;
      dashboard sadece DB'den OKUR. İnternet/Open-Meteo erişimi kaybolsa bile
      en son kayıtlar görüntülenebilir.
    * Şema sürümü `db_meta.schema_version` üzerinden takip edilir; eski
      şema tespit edilirse DB yedeklenip yeniden yaratılır.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# DB path migrated to the new bootstrap layout (scripts/init_database.py).
# Old `trakaia.db` is intentionally untouched as a backup.
DB_PATH = PROJECT_ROOT / "data" / "trakai.db"

# Şema sürümü — değiştirildiğinde init_db() eski DB'yi yedekler.
SCHEMA_VERSION = "3"

# ─────────────────────────────────────────────────────────────────────────────
# Şema
# ─────────────────────────────────────────────────────────────────────────────

_CREATE_TARLALAR = """
CREATE TABLE IF NOT EXISTS tarlalar (
    id            INTEGER PRIMARY KEY,
    research_code TEXT UNIQUE,
    isim          TEXT NOT NULL,
    il            TEXT,
    ilce          TEXT,
    konum_lat     REAL NOT NULL,
    konum_lon     REAL NOT NULL,
    alan_dekar    REAL,
    toprak_tipi   TEXT,
    toprak_kil    REAL,
    toprak_kum    REAL,
    toprak_ph     REAL,
    aktif_urun    TEXT,
    ekim_tarihi   TEXT,
    sahip         TEXT,
    notlar        TEXT,
    created_at    TEXT
)
"""

_CREATE_ROVER = """
CREATE TABLE IF NOT EXISTS rover_olcumler (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id         INTEGER REFERENCES tarlalar(id),
    timestamp        TEXT NOT NULL,
    waypoint_id      INTEGER,
    waypoint_label   TEXT,
    gps_lat          REAL,
    gps_lon          REAL,
    nem_1_pct        REAL,
    nem_2_pct        REAL,
    hava_temp_c      REAL,
    hava_nem_pct     REAL,
    bbch_sinif       TEXT,
    bbch_guven       REAL,
    hastalik         TEXT,
    hastalik_guven   REAL,
    engel_on_cm      INTEGER,
    ndvi_tahmini     REAL,
    verim_tahmini    REAL,
    anomali_sayisi   INTEGER DEFAULT 0,
    anomaliler       TEXT,
    kds_tavsiye      TEXT,
    image_path       TEXT,
    camera_sinif     TEXT,
    camera_guven     REAL
)
"""

_CREATE_TAHMINLER = """
CREATE TABLE IF NOT EXISTS tarla_tahminler (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id                INTEGER REFERENCES tarlalar(id),
    timestamp               TEXT NOT NULL,
    urun                    TEXT,
    ndvi_mevcut             REAL,
    ndvi_tahmin_7gun        REAL,
    ndvi_delta              REAL,
    saglik_durumu           TEXT,
    verim_tahmini_kg_dekar  REAL,
    verim_guven_alt         REAL,
    verim_guven_ust         REAL,
    verim_risk              TEXT,
    fenolojik_evre          TEXT,
    bbch_aralik             TEXT,
    kritik_donem            INTEGER DEFAULT 0,
    sulama_aciliyet         TEXT,
    sulama_miktar           REAL,
    gubre_zamani            INTEGER DEFAULT 0,
    gubre_tip               TEXT,
    ekim_skoru              INTEGER,
    ekim_kategori           TEXT,
    hava_sicaklik           REAL,
    hava_nem                REAL,
    hava_yagis_7gun         REAL,
    hava_uyarilar           TEXT,
    kaynak                  TEXT
)
"""

_CREATE_HAVA = """
CREATE TABLE IF NOT EXISTS hava_kayitlari (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id            INTEGER REFERENCES tarlalar(id),
    timestamp           TEXT NOT NULL,
    tarih               TEXT NOT NULL,
    konum_lat           REAL,
    konum_lon           REAL,
    hava_temp_c         REAL,
    hava_nem_pct        REAL,
    toprak_temp_c       REAL,
    toprak_nem_pct      REAL,
    yagis_mm            REAL,
    ruzgar_kmh          REAL,
    temp_max            REAL,
    temp_min            REAL,
    yagis_gunluk_mm     REAL,
    et0_mm              REAL,
    yagis_olasilik      INTEGER,
    gdd_kumulatif       REAL,
    don_riski           INTEGER DEFAULT 0,
    sicak_stres         INTEGER DEFAULT 0,
    kaynak              TEXT,
    UNIQUE(tarla_id, tarih)
)
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS db_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
)
"""

_CREATE_HAVA_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_hava_tarla_tarih "
    "ON hava_kayitlari(tarla_id, tarih)"
)
_CREATE_ROVER_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_rover_tarla_ts "
    "ON rover_olcumler(tarla_id, timestamp)"
)


# ─────────────────────────────────────────────────────────────────────────────
# Fenoloji / GDD yardımcıları (fiziksel modeller — mock değil)
# Rover-vs-model karşılaştırması için Trakya'ya kalibre profil eğrileri.
# ─────────────────────────────────────────────────────────────────────────────

def _wheat_season(scan_date: date, clay_pct: float = 31.0) -> dict:
    """Trakya buğday mevsim profili (model beklentisi)."""
    clay_bonus = (clay_pct - 31.0) * 0.18
    m, y = scan_date.month, scan_date.year
    if y == 2025:
        if m == 10:
            return dict(nem_c=34 + clay_bonus, nem_s=5, temp_c=12, temp_s=3,
                        bb=(0, 9), ndvi=0.20)
        return dict(nem_c=37 + clay_bonus, nem_s=5, temp_c=8, temp_s=4,
                    bb=(5, 19), ndvi=0.27)
    if m == 1:
        return dict(nem_c=41 + clay_bonus, nem_s=5, temp_c=2, temp_s=4,
                    bb=(15, 25), ndvi=0.35)
    if m == 2:
        return dict(nem_c=39 + clay_bonus, nem_s=5, temp_c=4, temp_s=4,
                    bb=(20, 29), ndvi=0.43)
    if m == 3:
        return dict(nem_c=31 + clay_bonus, nem_s=5, temp_c=11, temp_s=4,
                    bb=(25, 35), ndvi=0.51)
    if m == 4:
        return dict(nem_c=26 + clay_bonus, nem_s=4, temp_c=17, temp_s=5,
                    bb=(35, 55), ndvi=0.63)
    if m == 5:
        return dict(nem_c=22 + clay_bonus, nem_s=4, temp_c=22, temp_s=5,
                    bb=(50, 69), ndvi=0.69)
    return dict(nem_c=30 + clay_bonus, nem_s=5, temp_c=15, temp_s=4,
                bb=(0, 9), ndvi=0.30)


def _sunflower_season(days_since_planting: int, scan_date: date) -> dict:
    """Trakya ayçiçeği büyüme-bazlı profil (model beklentisi)."""
    temp_c = 17.0 + (scan_date.day / 31.0) * 5.0 + (scan_date.month - 4) * 4.0
    if days_since_planting < 7:
        return dict(nem_c=33, nem_s=5, temp_c=temp_c, temp_s=3,
                    bb=(0, 5), ndvi=0.12)
    if days_since_planting < 14:
        return dict(nem_c=29, nem_s=4, temp_c=temp_c, temp_s=3,
                    bb=(5, 10), ndvi=0.19)
    if days_since_planting < 21:
        return dict(nem_c=26, nem_s=4, temp_c=temp_c, temp_s=3,
                    bb=(10, 14), ndvi=0.27)
    return dict(nem_c=24, nem_s=4, temp_c=temp_c + 1, temp_s=3,
                bb=(14, 19), ndvi=0.34)


def calculate_gdd(temp_max: float, temp_min: float, base: float = 10.0) -> float:
    """Growing Degree Days: max(0, (Tmax + Tmin)/2 - base)."""
    return max(0.0, (temp_max + temp_min) / 2.0 - base)


# ─────────────────────────────────────────────────────────────────────────────
# Bağlantı + init
# ─────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _backup_old_db() -> Optional[Path]:
    if not DB_PATH.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.with_suffix(f".bak_{ts}")
    shutil.copy2(DB_PATH, backup)
    return backup


def _needs_reset(conn: sqlite3.Connection) -> bool:
    """Eski şemayı (research_code yok) ya da farklı SCHEMA_VERSION'ı algıla."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tarlalar)").fetchall()]
    if cols and "research_code" not in cols:
        return True
    try:
        row = conn.execute(
            "SELECT value FROM db_meta WHERE key='schema_version'"
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    return (row[0] if row else None) != SCHEMA_VERSION


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_TARLALAR)
    conn.execute(_CREATE_ROVER)
    conn.execute(_CREATE_TAHMINLER)
    conn.execute(_CREATE_HAVA)
    conn.execute(_CREATE_META)
    conn.execute(_CREATE_HAVA_INDEX)
    conn.execute(_CREATE_ROVER_INDEX)
    conn.commit()


def _seed_research_sites(conn: sqlite3.Connection) -> int:
    """EVRENLI_SITES'tan 5 araştırma tarlasını ekle. İdempotent."""
    try:
        from prospective_validation.config import EVRENLI_SITES  # type: ignore
    except Exception as exc:                                       # noqa: BLE001
        print(f"[DB] UYARI: EVRENLI_SITES yüklenemedi: {exc}")
        return 0

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    n_added = 0
    for i, site in enumerate(EVRENLI_SITES, start=1):
        exists = conn.execute(
            "SELECT id FROM tarlalar WHERE research_code = ?", (site.id,)
        ).fetchone()
        if exists:
            continue
        # FLOV pipeline aşağı yukarı tek ürün (ayçiçeği) varsayar.
        conn.execute(
            """INSERT INTO tarlalar
               (id, research_code, isim, il, ilce,
                konum_lat, konum_lon, alan_dekar,
                aktif_urun, sahip, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                i,
                site.id,
                site.name,
                "Kırklareli",
                "Vize",
                float(site.lat),
                float(site.lon),
                float(site.area_da),
                "Ayçiçeği",
                site.owner,
                now,
            ),
        )
        n_added += 1
    if n_added:
        conn.commit()
    return n_added


def init_db() -> None:
    """Ensure the production schema exists at DB_PATH (data/trakai.db).

    After the v3 bootstrap refactor the canonical schema lives in
    `scripts/init_database.py` (tables: tarla, sensor_reading,
    ndvi_prediction, yield_prediction, active_alert, tarla_tahminler,
    db_meta + compat views: tarlalar, rover_olcumler, hava_kayitlari).

    This function is a thin idempotent wrapper around that bootstrap so
    `streamlit run src/dashboard.py` can be invoked on a fresh checkout
    without manually running the script first.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Detect fresh DB: if `tarla` table does not exist yet, run the bootstrap.
    needs_bootstrap = True
    if DB_PATH.exists():
        try:
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='tarla'"
                ).fetchone()
                needs_bootstrap = row is None
        except sqlite3.DatabaseError:
            needs_bootstrap = True

    if needs_bootstrap:
        # Defer to scripts/init_database.py (single source of truth)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "trakai_bootstrap",
            PROJECT_ROOT / "scripts" / "init_database.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            con = mod._connect()
            try:
                mod.create_schema(con)
                mod.seed_tarlalar(con)
            finally:
                con.close()
            print(f"[DB] Bootstrap çalıştırıldı: {DB_PATH}")
        else:
            print(f"[DB] HATA: scripts/init_database.py bulunamadı — boş DB.")
            return

    print(f"[DB] Hazır: {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# Tarla sorguları
# ─────────────────────────────────────────────────────────────────────────────

def get_tarlalar() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tarlalar ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_tarla(tarla_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tarlalar WHERE id = ?", (tarla_id,)
        ).fetchone()
        return dict(row) if row else None


def get_tarla_by_research_code(code: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tarlalar WHERE research_code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None


def upsert_tarla(data: dict) -> int:
    """Tarla ekle veya güncelle. `research_code` veya `id` benzersiz anahtardır."""
    keys = ("research_code", "isim", "il", "ilce", "konum_lat", "konum_lon",
            "alan_dekar", "toprak_tipi", "toprak_kil", "toprak_kum",
            "toprak_ph", "aktif_urun", "ekim_tarihi", "sahip", "notlar")
    payload = {k: data.get(k) for k in keys}
    payload["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        existing = None
        if data.get("id"):
            existing = conn.execute(
                "SELECT id FROM tarlalar WHERE id = ?", (data["id"],)
            ).fetchone()
        elif payload.get("research_code"):
            existing = conn.execute(
                "SELECT id FROM tarlalar WHERE research_code = ?",
                (payload["research_code"],),
            ).fetchone()
        if existing:
            set_clause = ", ".join(f"{k} = :{k}" for k in payload)
            payload["id"] = existing[0]
            conn.execute(f"UPDATE tarlalar SET {set_clause} WHERE id = :id", payload)
            conn.commit()
            return int(existing[0])
        cols = ", ".join(payload.keys())
        phs = ", ".join(f":{k}" for k in payload)
        cur = conn.execute(f"INSERT INTO tarlalar ({cols}) VALUES ({phs})", payload)
        conn.commit()
        return int(cur.lastrowid)


# ─────────────────────────────────────────────────────────────────────────────
# Rover
# ─────────────────────────────────────────────────────────────────────────────

_ROVER_COLS = {
    "tarla_id", "timestamp", "waypoint_id", "waypoint_label",
    "gps_lat", "gps_lon", "nem_1_pct", "nem_2_pct", "hava_temp_c",
    "hava_nem_pct", "bbch_sinif", "bbch_guven", "hastalik", "hastalik_guven",
    "engel_on_cm", "ndvi_tahmini", "verim_tahmini", "anomali_sayisi",
    "anomaliler", "kds_tavsiye", "image_path", "camera_sinif", "camera_guven",
}


def add_rover_olcum(tarla_id: int, data: dict) -> int:
    payload = {"tarla_id": tarla_id, **data}
    payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    filtered = {k: v for k, v in payload.items() if k in _ROVER_COLS}
    cols = ", ".join(filtered.keys())
    phs = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO rover_olcumler ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
        return int(cur.lastrowid)


def get_rover_olcumler(tarla_id: int, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rover_olcumler WHERE tarla_id=? "
            "ORDER BY timestamp DESC LIMIT ?",
            (tarla_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_rover_olcumler_asc(tarla_id: int, limit: int = 5000) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rover_olcumler WHERE tarla_id=? "
            "ORDER BY timestamp ASC LIMIT ?",
            (tarla_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Tahminler
# ─────────────────────────────────────────────────────────────────────────────

_TAHMIN_COLS = {
    "tarla_id", "timestamp", "urun", "ndvi_mevcut", "ndvi_tahmin_7gun",
    "ndvi_delta", "saglik_durumu", "verim_tahmini_kg_dekar", "verim_guven_alt",
    "verim_guven_ust", "verim_risk", "fenolojik_evre", "bbch_aralik",
    "kritik_donem", "sulama_aciliyet", "sulama_miktar", "gubre_zamani",
    "gubre_tip", "ekim_skoru", "ekim_kategori", "hava_sicaklik", "hava_nem",
    "hava_yagis_7gun", "hava_uyarilar", "kaynak",
}


def add_tahmin(tarla_id: int, data: dict) -> int:
    payload = {"tarla_id": tarla_id, **data}
    payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    filtered = {k: v for k, v in payload.items() if k in _TAHMIN_COLS}
    cols = ", ".join(filtered.keys())
    phs = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        cur = conn.execute(
            f"INSERT INTO tarla_tahminler ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
        return int(cur.lastrowid)


def get_son_tahmin(tarla_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tarla_tahminler WHERE tarla_id=? "
            "ORDER BY timestamp DESC LIMIT 1",
            (tarla_id,),
        ).fetchone()
        return dict(row) if row else None


def get_tarla_ozet(tarla_id: int) -> dict:
    tarla = get_tarla(tarla_id) or {}
    tahmin = get_son_tahmin(tarla_id) or {}
    olc = get_rover_olcumler(tarla_id, limit=1)
    return {"tarla": tarla, "tahmin": tahmin, "son_rover": olc[0] if olc else {}}


# ─────────────────────────────────────────────────────────────────────────────
# Hava (offline-first önbellek)
# ─────────────────────────────────────────────────────────────────────────────

_HAVA_COLS = {
    "tarla_id", "timestamp", "tarih", "konum_lat", "konum_lon",
    "hava_temp_c", "hava_nem_pct", "toprak_temp_c", "toprak_nem_pct",
    "yagis_mm", "ruzgar_kmh", "temp_max", "temp_min", "yagis_gunluk_mm",
    "et0_mm", "yagis_olasilik", "gdd_kumulatif", "don_riski", "sicak_stres",
    "kaynak",
}


def save_weather_snapshot(tarla_id: int, data: dict) -> bool:
    """Tek günlük hava verisi yaz. (tarla_id, tarih) çiftinde varsa atla."""
    payload = {"tarla_id": tarla_id, **data}
    payload.setdefault("tarih", date.today().isoformat())
    payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    filtered = {k: v for k, v in payload.items() if k in _HAVA_COLS}
    cols = ", ".join(filtered.keys())
    phs = ", ".join(f":{k}" for k in filtered)
    with get_connection() as conn:
        conn.execute(
            f"INSERT OR IGNORE INTO hava_kayitlari ({cols}) VALUES ({phs})", filtered
        )
        conn.commit()
    return True


def upsert_weather_snapshot(tarla_id: int, data: dict) -> bool:
    """Aynı (tarla_id, tarih) varsa üzerine yaz."""
    payload = {"tarla_id": tarla_id, **data}
    payload.setdefault("tarih", date.today().isoformat())
    payload.setdefault("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    filtered = {k: v for k, v in payload.items() if k in _HAVA_COLS}
    cols = ", ".join(filtered.keys())
    phs = ", ".join(f":{k}" for k in filtered)
    set_clause = ", ".join(f"{k}=excluded.{k}" for k in filtered if k not in
                           ("tarla_id", "tarih"))
    with get_connection() as conn:
        conn.execute(
            f"INSERT INTO hava_kayitlari ({cols}) VALUES ({phs}) "
            f"ON CONFLICT(tarla_id, tarih) DO UPDATE SET {set_clause}",
            filtered,
        )
        conn.commit()
    return True


def bulk_upsert_weather(rows: Iterable[dict]) -> int:
    n = 0
    for r in rows:
        if "tarla_id" not in r:
            continue
        upsert_weather_snapshot(r["tarla_id"], r)
        n += 1
    return n


def get_weather_history(tarla_id: int, days: int = 30) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM hava_kayitlari WHERE tarla_id=? "
            "ORDER BY tarih DESC LIMIT ?",
            (tarla_id, days),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_weather_by_date_range(tarla_id: int, start_date: str,
                              end_date: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM hava_kayitlari "
            "WHERE tarla_id=? AND tarih BETWEEN ? AND ? "
            "ORDER BY tarih ASC",
            (tarla_id, start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_weather(tarla_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM hava_kayitlari WHERE tarla_id=? "
            "ORDER BY tarih DESC LIMIT 1",
            (tarla_id,),
        ).fetchone()
        return dict(row) if row else None


def get_weather_stats(tarla_id: int, days: int = 30) -> dict:
    """Aggregate ``hava_kayitlari`` view rows for the past ``days`` days.

    The view (see ``scripts/init_database.py``) exposes both physical
    (``temperature``, ``precipitation``, ...) and Turkish-alias
    (``sicaklik_c``, ``yagis_mm``, ...) column names; we read by physical
    name and derive min/max + frost/heat-day counts from the daily mean
    temperature since the source ``sensor_reading`` schema has no separate
    daily min/max columns.
    """
    h = get_weather_history(tarla_id, days)
    if not h:
        return {}
    temps = [r["temperature"] for r in h if r.get("temperature") is not None]
    yagis = [r["precipitation"] for r in h if r.get("precipitation") is not None]
    gdds  = [r["gdd"] for r in h if r.get("gdd") is not None]
    don_gun   = sum(1 for t in temps if t < 0.0)
    sicak_gun = sum(1 for t in temps if t > 32.0)
    return {
        "gun_sayisi":   len(h),
        "avg_temp":     round(sum(temps) / len(temps), 1) if temps else None,
        "max_temp":     round(max(temps), 1) if temps else None,
        "min_temp":     round(min(temps), 1) if temps else None,
        "toplam_yagis": round(sum(yagis), 1) if yagis else 0.0,
        "yagisli_gun":  sum(1 for y in yagis if y > 0.5),
        "don_gun":      don_gun,
        "sicak_gun":    sicak_gun,
        "son_gdd_kum":  round(sum(gdds), 1) if gdds else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    # Force UTF-8 stdout on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if "--reset" in sys.argv and DB_PATH.exists():
        backup = _backup_old_db()
        DB_PATH.unlink()
        print(f"[DB] DB silindi -> yedek: {backup.name if backup else '-'}")
    init_db()
    for t in get_tarlalar():
        rc = t.get('research_code') or '-'
        print(f"  [{t['id']}] {rc:<8} {t['isim']}"
              f"  ({t['konum_lat']:.4f}, {t['konum_lon']:.4f})"
              f"  {t.get('alan_dekar', 0):.1f} da")
