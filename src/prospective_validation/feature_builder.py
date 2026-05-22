"""
Build the 17-feature daily matrix for a given site + date range.

Zero-drift policy
-----------------
We do NOT re-implement any feature derivation.  After fetching raw S2 +
ERA5 + Soil we assemble a DataFrame whose **column schema matches**
``data/processed/master_feature_matrix_2017_2024.csv`` exactly, write it
to a temporary CSV, and call the FROZEN training-time functions
``preprocessing_cp2.load_and_clean`` and ``preprocessing_cp2.engineer_features``.

Any future drift between the prospective and training pipelines is now
structurally impossible without an explicit edit to ``preprocessing_cp2.py``
— which would invalidate the frozen-model rationale altogether.

Outputs
-------
A pandas DataFrame with columns:

    date  +  the 17 features listed in :data:`config.FEATURE_NAMES`

The frame may contain NaNs in early rows for trailing windows
(NDVI_trend_7d) — preprocessing_cp2 fills these with ffill/bfill during
sliding-window construction.  We surface them so the caller can apply the
exact same fill at scaling time.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config
from .fetchers import (
    fetch_era5_daily,
    fetch_sentinel2_daily,
    fetch_soilgrids_static,
)
from .logging_setup import logger


# Column order of the raw master matrix, as produced by main_etl_pipeline.py
# (preprocessing_cp2 is robust to ordering, but we mirror it for clarity).
_RAW_MASTER_COLUMNS = [
    "date",
    "t2m_mean", "t2m_min", "t2m_max", "d2m_mean",
    "tp_sum", "ssr_sum", "e_sum",
    "clay_0-5cm", "clay_5-15cm", "clay_15-30cm",
    "sand_0-5cm", "sand_5-15cm", "sand_15-30cm",
    "phh2o_0-5cm", "phh2o_5-15cm", "phh2o_15-30cm",
    "NDVI", "EVI", "NDWI",
    "NDVI_int", "EVI_int", "NDWI_int",
]


def _assemble_raw_master(
    df_era5: pd.DataFrame,
    df_s2: pd.DataFrame,
    soil: dict,
) -> pd.DataFrame:
    """
    Build the per-day master matrix matching the training-era CSV schema.

    Steps mirror :mod:`cp1_etl.main_etl_pipeline`:
        1. ERA5 daily frame is the skeleton (one row per day).
        2. Broadcast static soil dict columns.
        3. Left-join S2 indices on ``date`` (NaN on cloudy days).
        4. Linear-interpolate NDVI/EVI/NDWI into *_int columns;
           bfill+ffill the edges.
    """
    if df_era5.empty:
        raise RuntimeError("ERA5 frame is empty; cannot build master matrix")

    df = df_era5.copy()
    df["date"] = pd.to_datetime(df["date"])

    for col, value in soil.items():
        df[col] = value

    df_s2 = df_s2.copy()
    if not df_s2.empty:
        df_s2["date"] = pd.to_datetime(df_s2["date"])
    df = df.merge(df_s2, on="date", how="left")

    for col in ("NDVI", "EVI", "NDWI"):
        if col not in df.columns:
            df[col] = float("nan")
        df[f"{col}_int"] = df[col].interpolate(method="linear")
        df[f"{col}_int"] = df[f"{col}_int"].bfill().ffill()

    missing = [c for c in _RAW_MASTER_COLUMNS if c not in df.columns]
    if missing:
        raise RuntimeError(
            f"Raw master matrix missing columns: {missing}.  Likely cause: "
            f"ERA5 fetcher returned unexpected schema."
        )
    df = df[_RAW_MASTER_COLUMNS]
    df = df.sort_values("date").reset_index(drop=True)
    return df


@contextlib.contextmanager
def _suppress_stdout():
    """preprocessing_cp2 prints verbosely; mute it during our internal use."""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old_stdout


def _apply_frozen_preprocessing(raw_master: pd.DataFrame) -> pd.DataFrame:
    """Write a temp CSV, run preprocessing_cp2 over it, return 17-feature frame."""
    cp2 = str(config.CP2_DIR)
    if cp2 not in sys.path:
        sys.path.insert(0, cp2)
    import importlib
    pp = importlib.import_module("preprocessing_cp2")

    with tempfile.TemporaryDirectory(prefix="flov_pp_") as tmp:
        tmp_csv = Path(tmp) / "raw_master_prospective.csv"
        raw_master.to_csv(tmp_csv, index=False)
        with _suppress_stdout():
            df_clean, _soil_meta = pp.load_and_clean(str(tmp_csv))
            df_eng = pp.engineer_features(df_clean)

    cols = ["date"] + list(config.FEATURE_NAMES)
    missing = [c for c in cols if c not in df_eng.columns]
    if missing:
        raise RuntimeError(
            f"Frozen preprocessing produced unexpected schema, missing: {missing}"
        )
    return df_eng[cols].reset_index(drop=True)


def build_unified_features(
    site: config.Site,
    start_date: date,
    end_date: date,
    *,
    force_refresh: bool = False,
    save: bool = True,
) -> pd.DataFrame:
    """
    End-to-end: fetch -> assemble -> frozen preprocessing -> 17-feature frame.

    Parameters
    ----------
    site         : Site to fetch for
    start_date   : inclusive
    end_date     : inclusive
    force_refresh: if True, bypass all caches (S2 + ERA5 + Soil)
    save         : if True, write parquet to
                   data/prospective/<year>/<site_id>_unified_features.parquet
                   (year derived from start_date).

    Returns
    -------
    DataFrame with columns: date + the 17 frozen features
    """
    config.ensure_runtime_dirs()
    logger.info("[features] building unified features for {} {}→{}",
                site.id, start_date, end_date)

    soil = fetch_soilgrids_static(site, force=force_refresh)
    if not soil:
        raise RuntimeError(f"SoilGrids returned empty for {site.id}")

    df_era5 = fetch_era5_daily(site, start_date, end_date, force=force_refresh)
    if df_era5.empty:
        raise RuntimeError(f"ERA5 returned empty for {site.id} {start_date}→{end_date}")

    df_s2 = fetch_sentinel2_daily(site, start_date, end_date, force=force_refresh)

    raw_master = _assemble_raw_master(df_era5, df_s2, soil)
    df_features = _apply_frozen_preprocessing(raw_master)

    if save:
        year = start_date.year
        out_dir = config.PROSPECTIVE_DIR / str(year)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{site.id}_unified_features.parquet"
        df_features.to_parquet(out_path, index=False)
        logger.info("[features] wrote {} ({} rows × {} cols)",
                    out_path, len(df_features), df_features.shape[1])
    return df_features


__all__ = ["build_unified_features"]
