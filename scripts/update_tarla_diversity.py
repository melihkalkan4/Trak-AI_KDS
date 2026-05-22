"""
TRAK-AI KDS — Tarla Diversification
====================================
Updates the 5 EVRENLI tarlalar to a realistic mix:
    3 sunflower + 2 wheat
    distinct coordinates (1-2km apart so Sentinel-2 10m gives different pixels)
    crop-specific season metadata

Operates on the `tarla` table (underlying the `tarlalar` view).
Idempotent: re-running just re-applies the same UPDATE.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "trakai.db"


UPDATED_TARLALAR = [
    {
        "id": 1,
        "name": "Kendi tarlam - Vize merkez",
        "evrenli_id": "EVR_01",
        "crop_type": "sunflower",
        "season_start_month": 4,
        "season_end_month": 10,
        "active_season_year": 2026,
        "soil_type": "tinli",
        "lat": 41.045, "lon": 27.205,
        "area_da": 12.5,
    },
    {
        "id": 2,
        "name": "Komsu - Kuzey (Bugday)",
        "evrenli_id": "EVR_02",
        "crop_type": "wheat",
        "season_start_month": 10,
        "season_end_month": 6,
        "active_season_year": 2026,
        "soil_type": "killi",
        "lat": 41.052, "lon": 27.218,   # ~1.6 km NE of EVR_01
        "area_da": 18.0,
    },
    {
        "id": 3,
        "name": "Komsu - Guney",
        "evrenli_id": "EVR_03",
        "crop_type": "sunflower",
        "season_start_month": 4,
        "season_end_month": 10,
        "active_season_year": 2026,
        "soil_type": "tinli",
        "lat": 41.038, "lon": 27.192,   # ~1.5 km SW
        "area_da": 15.0,
    },
    {
        "id": 4,
        "name": "Komsu - Dogu (Bugday)",
        "evrenli_id": "EVR_04",
        "crop_type": "wheat",
        "season_start_month": 10,
        "season_end_month": 6,
        "active_season_year": 2026,
        "soil_type": "kumlu-tinli",
        "lat": 41.057, "lon": 27.225,   # ~2 km NE
        "area_da": 10.0,
    },
    {
        "id": 5,
        "name": "Komsu - Bati",
        "evrenli_id": "EVR_05",
        "crop_type": "sunflower",
        "season_start_month": 4,
        "season_end_month": 10,
        "active_season_year": 2026,
        "soil_type": "killi",
        "lat": 41.032, "lon": 27.184,   # ~2.3 km SW
        "area_da": 7.5,
    },
]


SCHEMA_ADDITIONS_SQL = [
    "ALTER TABLE tarla ADD COLUMN season_start_month INTEGER",
    "ALTER TABLE tarla ADD COLUMN season_end_month INTEGER",
    "ALTER TABLE tarla ADD COLUMN active_season_year INTEGER",
    "ALTER TABLE tarla ADD COLUMN soil_type TEXT",
]


def _safe_add_columns(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    for sql in SCHEMA_ADDITIONS_SQL:
        try:
            cur.execute(sql)
            print(f"  [schema] {sql}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                continue
            raise
    con.commit()


# Rebuild the tarlalar view so dashboard sees crop-aware columns.
REBUILD_VIEW_SQL = """
DROP VIEW IF EXISTS tarlalar;
CREATE VIEW tarlalar AS
SELECT
    id,
    name        AS isim,
    evrenli_id  AS research_code,
    lat,
    lon,
    lat         AS konum_lat,
    lon         AS konum_lon,
    crop_type   AS aktif_urun,
    area_da,
    area_da     AS alan_dekar,
    soil_type   AS toprak_tipi,
    'Kirklareli' AS il,
    'Vize'      AS ilce,
    CASE WHEN id = 1 THEN 'self' ELSE 'neighbor' END AS sahip,
    CASE
        WHEN crop_type = 'wheat' THEN
            (active_season_year - 1) || '-10-15'
        ELSE
            active_season_year || '-04-15'
    END         AS ekim_tarihi,
    NULL        AS toprak_kil,
    NULL        AS toprak_kum,
    NULL        AS toprak_ph,
    created_at
FROM tarla;
"""


def update_all() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        _safe_add_columns(con)
        con.executescript(REBUILD_VIEW_SQL)
        cur = con.cursor()
        updated = 0
        for t in UPDATED_TARLALAR:
            cur.execute(
                """
                UPDATE tarla SET
                    name = ?,
                    crop_type = ?,
                    season_start_month = ?,
                    season_end_month = ?,
                    active_season_year = ?,
                    soil_type = ?,
                    lat = ?,
                    lon = ?,
                    area_da = ?
                WHERE id = ?
                """,
                (t["name"], t["crop_type"], t["season_start_month"],
                 t["season_end_month"], t["active_season_year"],
                 t["soil_type"], t["lat"], t["lon"], t["area_da"], t["id"]),
            )
            if cur.rowcount > 0:
                updated += 1
            print(f"  OK  Tarla {t['id']}: {t['name']} ({t['crop_type']}) "
                  f"@ ({t['lat']}, {t['lon']})")
        con.commit()
        return updated
    finally:
        con.close()


def verify():
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT id, name, evrenli_id, crop_type, lat, lon, area_da, "
            "       season_start_month, season_end_month, soil_type "
            "FROM tarla ORDER BY id"
        )
        print("\n[verify] tarla rows:")
        for r in cur.fetchall():
            print(f"  [{r[0]}] {r[2]:<7} {r[3]:<9} ({r[4]:.4f}, {r[5]:.4f}) "
                  f"{r[6]:>5.1f}da soil={r[9]} season={r[7]}->{r[8]} | {r[1]}")
    finally:
        con.close()


def main() -> int:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DB missing at {DB_PATH}. Run scripts/init_database.py first."
        )
    print(f"[update_tarla_diversity] DB: {DB_PATH}")
    n = update_all()
    print(f"\n[done] {n} tarla rows updated")
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
