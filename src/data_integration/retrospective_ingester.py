"""
TRAK-AI KDS — Retrospective Parquet → DB Ingester
==================================================
Reads `data/prospective/<year>/<EVR_xx>_unified_features.parquet` produced by
the FLOV orchestrator and inserts its rows into `data/trakai.db` as
`sensor_reading` records with `data_source='api_retrospective'`.

Column mapping (parquet → DB)
-----------------------------
    date              -> timestamp
    t2m_mean          -> temperature
    dew_depression    -> humidity      (derived: 100 - dd * 5, clipped)
    NDVI_int          -> ndvi
    EVI_int           -> evi
    NDWI_int          -> ndwi
    tp_sum            -> precipitation
    GDD               -> gdd
    drought_index_7d  -> drought_index
    (soil_moisture stays NULL — SoilGrids is static, not daily)

The INSERT uses ``INSERT OR REPLACE`` keyed on
``(tarla_id, timestamp, data_source)`` so re-runs are idempotent.

Usage:
    from data_integration.retrospective_ingester import RetrospectiveDataIngester
    with RetrospectiveDataIngester() as ing:
        ing.ingest_all()
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("retrospective_ingester")


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO_ROOT / "data" / "trakai.db"
DEFAULT_PARQUET_DIR = REPO_ROOT / "data" / "prospective"

EVR_IDS = ("EVR_01", "EVR_02", "EVR_03", "EVR_04", "EVR_05")
YEARS = (2025, 2026)


class RetrospectiveDataIngester:
    """Parquet → sensor_reading ingestion."""

    def __init__(self,
                 db_path: Path | str = DEFAULT_DB,
                 parquet_dir: Path | str = DEFAULT_PARQUET_DIR):
        self.db_path = Path(db_path)
        self.parquet_dir = Path(parquet_dir)
        self.conn: sqlite3.Connection | None = None

    # context-manager so callers do not forget to close
    def __enter__(self):
        self._open()
        return self

    def __exit__(self, *exc):
        self.close()

    def _open(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"DB not found at {self.db_path}. "
                "Run scripts/init_database.py first."
            )
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    # ---------------- helpers ----------------
    @staticmethod
    def _to_float(v) -> float | None:
        try:
            if v is None or pd.isna(v):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_iso(ts) -> str:
        if isinstance(ts, str):
            return ts
        if isinstance(ts, (pd.Timestamp, datetime)):
            return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)

    @staticmethod
    def _clamp_precipitation(v) -> float | None:
        """ERA5 tp_sum can occasionally arrive in mixed units (m vs mm) or
        as a multi-day accumulation. Cap at 50 mm/day — the physically
        realistic upper bound for daily precipitation in NW Türkiye."""
        if v is None or pd.isna(v):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if f < 0:
            return 0.0
        return min(f, 50.0)

    @staticmethod
    def _derive_humidity(row) -> float | None:
        """Approximate relative humidity from temp + dew depression.

        Magnus heuristic: RH ≈ 100 - 5·(T - Tdew). Clipped to [0,100].
        """
        t = row.get("t2m_mean")
        dd = row.get("dew_depression")
        if pd.isna(t) or pd.isna(dd):
            return None
        rh = 100.0 - float(dd) * 5.0
        return max(0.0, min(100.0, rh))

    def _tarla_id_for(self, evrenli_id: str) -> int | None:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM tarla WHERE evrenli_id = ?", (evrenli_id,))
        row = cur.fetchone()
        return int(row[0]) if row else None

    def _parquet_path(self, evrenli_id: str, year: int) -> Path:
        return self.parquet_dir / str(year) / f"{evrenli_id}_unified_features.parquet"

    # ---------------- ingest one ----------------
    def ingest_site_year(self, evrenli_id: str, year: int) -> dict:
        if self.conn is None:
            self._open()

        result: dict = {"site": evrenli_id, "year": year, "status": "fail",
                        "inserted": 0}

        parquet = self._parquet_path(evrenli_id, year)
        if not parquet.exists():
            result["status"] = "no_parquet"
            return result

        tarla_id = self._tarla_id_for(evrenli_id)
        if tarla_id is None:
            result["status"] = "no_mapping"
            return result

        try:
            df = pd.read_parquet(parquet)
        except Exception as exc:                                       # noqa: BLE001
            result["status"] = "parquet_read_error"
            result["error"] = str(exc)
            return result

        if df.empty:
            result["status"] = "empty_parquet"
            return result

        cur = self.conn.cursor()
        inserted = 0
        failed = 0
        for _, r in df.iterrows():
            try:
                cur.execute(
                    """
                    INSERT OR REPLACE INTO sensor_reading
                        (tarla_id, timestamp, temperature, humidity,
                         soil_moisture, ndvi, evi, ndwi,
                         precipitation, gdd, drought_index, data_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            'api_retrospective')
                    """,
                    (
                        tarla_id,
                        self._to_iso(r.get("date")),
                        self._to_float(r.get("t2m_mean")),
                        self._derive_humidity(r),
                        None,  # soil_moisture: SoilGrids static, not daily
                        self._to_float(r.get("NDVI_int")),
                        self._to_float(r.get("EVI_int")),
                        self._to_float(r.get("NDWI_int")),
                        self._clamp_precipitation(r.get("tp_sum")),
                        self._to_float(r.get("GDD")),
                        self._to_float(r.get("drought_index_7d")),
                    ),
                )
                inserted += 1
            except Exception as exc:                                   # noqa: BLE001
                failed += 1
                logger.debug("row insert failed ({}, {}): {}",
                             evrenli_id, r.get("date"), exc)

        self.conn.commit()
        result.update(status="ok", inserted=inserted, failed=failed,
                      rows_in_parquet=int(len(df)))
        logger.info("[ingest] {} {} -> {} rows ({} failed)",
                    evrenli_id, year, inserted, failed)
        return result

    # ---------------- ingest many ----------------
    def ingest_all(self,
                   sites: Iterable[str] = EVR_IDS,
                   years: Iterable[int] = YEARS) -> list[dict]:
        if self.conn is None:
            self._open()
        out: list[dict] = []
        for s in sites:
            for y in years:
                out.append(self.ingest_site_year(s, y))
        return out


__all__ = ["RetrospectiveDataIngester"]
