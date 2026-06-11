"""
Sentinel-2 NDVI Otomatik Çekim → ndvi_kayitlari tablosu

Tüm aktif tarlalar için son 30 günlük Sentinel-2 NDVI verisini çeker
ve ndvi_kayitlari tablosuna UPSERT eder.

Kullanım:
    python scripts/fetch_sentinel2_ndvi.py
    python scripts/fetch_sentinel2_ndvi.py --site EVR_01
    python scripts/fetch_sentinel2_ndvi.py --days 60
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows console UTF-8 — alt katman audit modülleri için
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")        # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")        # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass

THIS_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
SRC_DIR     = PROJECT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from database import get_connection, init_db                 # noqa: E402

LOGS_DIR = PROJECT_DIR / "logs"
AUDIT_LOG = LOGS_DIR / "api_audit.jsonl"

logger = logging.getLogger("trakai.s2_ndvi")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


def _ensure_ndvi_table() -> None:
    """ndvi_kayitlari tablosunu garanti et."""
    with get_connection() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS ndvi_kayitlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarla_id INTEGER REFERENCES tarla(id),
                tarih DATE NOT NULL,
                ndvi REAL,
                evi REAL,
                ndwi REAL,
                kaynak TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tarla_id, tarih, kaynak)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_ndvi_tarla_tarih "
                  "ON ndvi_kayitlari(tarla_id, tarih)")
        c.commit()


def _audit(payload: dict) -> None:
    """API audit log'a satır ekle."""
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            payload["timestamp"] = datetime.now().isoformat()
            f.write(json.dumps(payload, default=str, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("Audit log yazılamadı: %s", e)


def _upsert_ndvi(tarla_id: int, df, kaynak: str) -> int:
    """DataFrame → ndvi_kayitlari UPSERT. Döndürür: eklenen satır sayısı."""
    if df is None or len(df) == 0:
        return 0
    n = 0
    with get_connection() as c:
        for _, row in df.iterrows():
            tarih = row["date"]
            if hasattr(tarih, "date"):
                tarih = tarih.date()
            ndvi = float(row.get("NDVI", 0)) if "NDVI" in row else None
            evi  = float(row.get("EVI", 0))  if "EVI" in row  else None
            ndwi = float(row.get("NDWI", 0)) if "NDWI" in row else None
            try:
                c.execute("""
                    INSERT INTO ndvi_kayitlari (tarla_id, tarih, ndvi, evi, ndwi, kaynak)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tarla_id, tarih, kaynak) DO UPDATE SET
                        ndvi = excluded.ndvi,
                        evi  = excluded.evi,
                        ndwi = excluded.ndwi
                """, (tarla_id, tarih.isoformat(), ndvi, evi, ndwi, kaynak))
                n += 1
            except Exception as e:
                logger.warning("UPSERT hata tarla=%s tarih=%s: %s",
                               tarla_id, tarih, e)
        c.commit()
    return n


def fetch_for_site(site_id: str, days: int = 30) -> dict:
    """Tek site için NDVI çek + DB'ye yaz."""
    try:
        from prospective_validation import config as pv_config
        from prospective_validation.fetchers.sentinel2 import fetch_sentinel2_daily
    except Exception as e:
        logger.error("Sentinel-2 modülleri import edilemedi: %s", e)
        return {"ok": False, "site": site_id, "error": str(e)}

    # Site config — EVRENLI_SITES tuple içinden bul
    site = None
    try:
        for s in pv_config.EVRENLI_SITES:
            if s.id == site_id:
                site = s
                break
        if site is None:
            return {"ok": False, "site": site_id,
                    "error": f"Site {site_id} EVRENLI_SITES'de yok"}
    except Exception as e:
        logger.error("Site config bulunamadı: %s", e)
        return {"ok": False, "site": site_id, "error": str(e)}

    # Tarla DB ID
    with get_connection() as c:
        row = c.execute(
            "SELECT id FROM tarla WHERE evrenli_id = ?", (site_id,)
        ).fetchone()
    if not row:
        return {"ok": False, "site": site_id, "error": "Tarla DB'de yok"}
    tarla_id = int(row["id"])

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    logger.info("[s2] %s: %s -> %s (%d gün)", site_id, start_date, end_date, days)

    try:
        df = fetch_sentinel2_daily(site, start_date, end_date)
    except Exception as e:
        logger.error("[s2] fetch HATA %s: %s", site_id, e)
        _audit({"endpoint": "s2_gee", "site": site_id, "status": "ERROR",
                "error": str(e)})
        return {"ok": False, "site": site_id, "error": str(e)}

    rows_count = len(df) if df is not None else 0
    n_written = _upsert_ndvi(tarla_id, df, kaynak="sentinel2_gee")

    _audit({"endpoint": "s2_gee", "site": site_id, "status": "OK",
            "rows_fetched": rows_count, "rows_written": n_written,
            "start": str(start_date), "end": str(end_date)})

    logger.info("[s2] %s: %d satır alındı, %d yazıldı",
                site_id, rows_count, n_written)

    return {"ok": True, "site": site_id, "tarla_id": tarla_id,
            "rows_fetched": rows_count, "rows_written": n_written,
            "start": str(start_date), "end": str(end_date)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Sentinel-2 NDVI otomatik çekim")
    ap.add_argument("--site", default=None,
                    help="Sadece bu site için (default: hepsi)")
    ap.add_argument("--days", type=int, default=30,
                    help="Son N gün (default 30)")
    args = ap.parse_args()

    init_db()
    _ensure_ndvi_table()

    # Site listesi
    if args.site:
        sites = [args.site]
    else:
        with get_connection() as c:
            rows = c.execute(
                "SELECT evrenli_id FROM tarla WHERE evrenli_id IS NOT NULL "
                "ORDER BY id"
            ).fetchall()
        sites = [r["evrenli_id"] for r in rows]

    logger.info("=" * 50)
    logger.info("Sentinel-2 NDVI çekim: %d site, %d gün", len(sites), args.days)
    logger.info("=" * 50)

    results = []
    for s in sites:
        results.append(fetch_for_site(s, args.days))

    print()
    print("=" * 50)
    ok_count = sum(1 for r in results if r["ok"])
    total_rows = sum(r.get("rows_written", 0) for r in results)
    print(f"TAMAMLANDI: {ok_count}/{len(results)} site OK, "
          f"{total_rows} NDVI satırı yazıldı")
    print("=" * 50)

    # Site bazlı detay
    for r in results:
        if r["ok"]:
            print(f"  {r['site']:<10s} OK  {r.get('rows_written', 0):3d} satır "
                  f"({r.get('start')} -> {r.get('end')})")
        else:
            print(f"  {r['site']:<10s} HATA: {r.get('error', '?')[:80]}")


if __name__ == "__main__":
    main()
