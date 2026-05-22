"""
TRAK-AI KDS — DB Bootstrapper
==============================
Creates `data/trakai.db` from scratch with the production schema:
    tarla, sensor_reading, ndvi_prediction, yield_prediction, active_alert

Also seeds the 5 EVRENLI pilot sites.

Idempotent: re-running is safe (uses CREATE TABLE IF NOT EXISTS + INSERT OR
IGNORE for the seed rows).

CLI:
    python scripts/init_database.py            # create+seed
    python scripts/init_database.py --reset    # drop tables first
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("init_database")


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH   = REPO_ROOT / "data" / "trakai.db"

INITIAL_TARLALAR = [
    {"id": 1, "name": "Kendi tarlam - Vize merkez", "evrenli_id": "EVR_01",
     "lat": 41.045, "lon": 27.205, "area_da": 12.5},
    {"id": 2, "name": "Komsu tarla - Kuzey",        "evrenli_id": "EVR_02",
     "lat": 41.048, "lon": 27.210, "area_da":  8.0},
    {"id": 3, "name": "Komsu tarla - Guney",        "evrenli_id": "EVR_03",
     "lat": 41.043, "lon": 27.198, "area_da": 15.0},
    {"id": 4, "name": "Komsu tarla - Dogu",         "evrenli_id": "EVR_04",
     "lat": 41.050, "lon": 27.215, "area_da": 10.0},
    {"id": 5, "name": "Komsu tarla - Bati",         "evrenli_id": "EVR_05",
     "lat": 41.040, "lon": 27.200, "area_da":  7.5},
]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tarla (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    evrenli_id  TEXT    UNIQUE,
    lat         REAL,
    lon         REAL,
    crop_type   TEXT    DEFAULT 'sunflower',
    area_da     REAL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensor_reading (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id        INTEGER NOT NULL,
    timestamp       DATETIME NOT NULL,
    temperature     REAL,
    humidity        REAL,
    soil_moisture   REAL,
    ndvi            REAL,
    evi             REAL,
    ndwi            REAL,
    precipitation   REAL,
    gdd             REAL,
    drought_index   REAL,
    data_source     TEXT    DEFAULT 'esp32',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tarla_id) REFERENCES tarla(id),
    UNIQUE(tarla_id, timestamp, data_source)
);

CREATE INDEX IF NOT EXISTS idx_sensor_tarla_time
    ON sensor_reading(tarla_id, timestamp);

CREATE TABLE IF NOT EXISTS ndvi_prediction (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id                INTEGER NOT NULL,
    prediction_date         DATE    NOT NULL,
    target_date             DATE    NOT NULL,
    predicted_ndvi          REAL,
    last_observed_ndvi      REAL,
    residual_delta          REAL,
    climatology_ndvi        REAL,
    anomaly_vs_climatology  REAL,
    model_hash              TEXT,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tarla_id) REFERENCES tarla(id),
    UNIQUE(tarla_id, prediction_date, target_date)
);

CREATE TABLE IF NOT EXISTS yield_prediction (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id                    INTEGER NOT NULL,
    season_year                 INTEGER NOT NULL,
    predicted_yield_kg_da       REAL,
    confidence_low              REAL,
    confidence_high             REAL,
    shap_top_features           TEXT,
    veri_yili                   INTEGER,
    model_hash                  TEXT,
    created_at                  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tarla_id, season_year)
);

CREATE TABLE IF NOT EXISTS active_alert (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id        INTEGER,
    alert_type      TEXT,
    severity        TEXT,
    message_tr      TEXT,
    message_en      TEXT,
    action_tr       TEXT,
    triggered_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged    BOOLEAN DEFAULT 0,
    resolved        BOOLEAN DEFAULT 0,
    source          TEXT
);

-- Dashboard-side legacy table: accepts live LSTM button writes and
-- keeps backwards compatibility with the previous schema's column shape.
CREATE TABLE IF NOT EXISTS tarla_tahminler (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    tarla_id                 INTEGER NOT NULL,
    timestamp                DATETIME NOT NULL,
    urun                     TEXT,
    ndvi_mevcut              REAL,
    ndvi_tahmin_7gun         REAL,
    ndvi_delta               REAL,
    saglik_durumu            TEXT,
    verim_tahmini_kg_dekar   REAL,
    verim_guven_alt          REAL,
    verim_guven_ust          REAL,
    verim_risk               TEXT,
    fenolojik_evre           TEXT,
    bbch_aralik              TEXT,
    kritik_donem             TEXT,
    sulama_aciliyet          TEXT,
    sulama_miktar            REAL,
    gubre_zamani             TEXT,
    gubre_tip                TEXT,
    ekim_skoru               REAL,
    ekim_kategori            TEXT,
    hava_sicaklik            REAL,
    hava_nem                 REAL,
    hava_yagis_7gun          REAL,
    hava_uyarilar            TEXT,
    kaynak                   TEXT,
    FOREIGN KEY (tarla_id) REFERENCES tarla(id)
);

CREATE INDEX IF NOT EXISTS idx_tahmin_tarla_ts
    ON tarla_tahminler(tarla_id, timestamp DESC);

-- Lightweight schema version marker for the existing database.py's
-- _needs_reset() probe.
CREATE TABLE IF NOT EXISTS db_meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
INSERT OR REPLACE INTO db_meta (key, value) VALUES ('schema_version', '3');
"""


# Backwards-compat views over the new schema so the existing dashboard
# (which queries `tarlalar`, `rover_olcumler`, `tarla_tahminler`,
# `hava_kayitlari`) keeps working without code changes.
VIEW_SQL = """
DROP VIEW IF EXISTS tarlalar;
CREATE VIEW tarlalar AS
SELECT
    id,
    name                  AS isim,
    name,
    evrenli_id            AS research_code,
    evrenli_id,
    lat,
    lon,
    lat                   AS konum_lat,
    lon                   AS konum_lon,
    crop_type             AS aktif_urun,
    crop_type,
    area_da,
    area_da               AS alan_dekar,
    soil_type             AS toprak_tipi,
    soil_type,
    season_start_month,
    season_end_month,
    active_season_year,
    'Kirklareli'          AS il,
    'Vize'                AS ilce,
    'self'                AS sahip,
    NULL                  AS ekim_tarihi,
    NULL                  AS toprak_kil,
    NULL                  AS toprak_kum,
    NULL                  AS toprak_ph,
    created_at
FROM tarla;

DROP VIEW IF EXISTS rover_olcumler;
CREATE VIEW rover_olcumler AS
SELECT
    id,
    tarla_id,
    timestamp,
    -- physical names (so dashboard direct readers work)
    temperature,
    humidity,
    soil_moisture,
    ndvi,
    precipitation,
    -- legacy aliases (kept for backward-compat with older dashboard code)
    temperature   AS hava_temp_c,
    humidity      AS hava_nem_pct,
    soil_moisture AS nem_1_pct,
    soil_moisture AS nem_2_pct,
    ndvi          AS ndvi_tahmini,
    evi,
    ndwi,
    precipitation AS yagis_mm,
    gdd,
    drought_index,
    data_source   AS kaynak,
    created_at,
    NULL          AS waypoint_label,
    NULL          AS waypoint_id,
    NULL          AS gps_lat,
    NULL          AS gps_lon,
    NULL          AS bbch_sinif,
    NULL          AS bbch_guven,
    NULL          AS hastalik,
    NULL          AS hastalik_guven,
    NULL          AS engel_on_cm,
    NULL          AS verim_tahmini,
    0             AS anomali_sayisi,
    NULL          AS anomaliler,
    NULL          AS kds_tavsiye,
    NULL          AS image_path,
    NULL          AS camera_sinif,
    NULL          AS camera_guven
FROM sensor_reading;

-- tarla_tahminler is intentionally a REAL TABLE (not a view) so the
-- live predictor's add_tahmin() can INSERT into it. ndvi_prediction
-- remains the canonical schema-modelled history; tarla_tahminler
-- accumulates dashboard-button-triggered live predictions.
-- (Created separately in CREATE TABLE block above.)

DROP VIEW IF EXISTS hava_kayitlari;
CREATE VIEW hava_kayitlari AS
SELECT
    id,
    tarla_id,
    timestamp,
    timestamp        AS tarih,
    -- physical names (so dashboard direct readers work)
    temperature,
    humidity,
    precipitation,
    -- legacy aliases
    temperature      AS sicaklik_c,
    humidity         AS nem_pct,
    precipitation    AS yagis_mm,
    gdd,
    drought_index,
    data_source      AS kaynak
FROM sensor_reading;
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def reset_tables(con: sqlite3.Connection) -> None:
    logger.warning("--reset: dropping all tables and views")
    cur = con.cursor()
    # tarla_tahminler may exist as a view (legacy) OR a table (new); try both.
    for v in ("tarlalar", "rover_olcumler", "hava_kayitlari",
              "tarla_tahminler"):
        cur.execute(f"DROP VIEW IF EXISTS {v};")
    for t in ("active_alert", "yield_prediction", "ndvi_prediction",
              "tarla_tahminler", "db_meta", "sensor_reading", "tarla"):
        cur.execute(f"DROP TABLE IF EXISTS {t};")
    con.commit()


def create_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_SQL)
    con.executescript(VIEW_SQL)
    con.commit()
    logger.info("[schema] tables + compat views created")


def seed_tarlalar(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    inserted = 0
    for t in INITIAL_TARLALAR:
        cur.execute("""
            INSERT OR IGNORE INTO tarla
                (id, name, evrenli_id, lat, lon, crop_type, area_da)
            VALUES (?, ?, ?, ?, ?, 'sunflower', ?)
        """, (t["id"], t["name"], t["evrenli_id"],
              t["lat"], t["lon"], t["area_da"]))
        if cur.rowcount > 0:
            inserted += 1
    con.commit()
    logger.info("[seed] {} new tarla rows inserted (total kept idempotent)",
                inserted)
    return inserted


def verify(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM tarla")
    n = cur.fetchone()[0]
    logger.info("[verify] tarla rows = {}", n)
    cur.execute("SELECT id, name, evrenli_id FROM tarla ORDER BY id")
    for r in cur.fetchall():
        logger.info("  [{}] {} ({})", r[0], r[1], r[2])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true",
                        help="Drop existing tables before creating")
    args = parser.parse_args()

    logger.info("DB path: {}", DB_PATH)
    con = _connect()
    try:
        if args.reset:
            reset_tables(con)
        create_schema(con)
        seed_tarlalar(con)
        verify(con)
    finally:
        con.close()
    logger.info("[done] init_database OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
