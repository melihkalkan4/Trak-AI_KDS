"""
Ground-truth NDVI loader for validation.

The validator compares ``predicted_ndvi`` (issued at prediction_date, valid
for target_date) against the cloud-free Sentinel-2 NDVI at or near
target_date.  We deliberately do NOT interpolate the actuals — only real
overpasses count as ground truth.

Two source modes are supported:

  1. ``from_unified_features(parquet)`` — for prospective sites, where the
     unified parquet preserves daily ``NDVI_int`` (interpolated).  We use
     ``NDVI_int`` here, accepting that interpolated days are weaker
     ground truth.  *Phase 4.5 todo:* keep the raw S2 cache and re-use it
     to mask interpolated days out of metric calculations.

  2. ``from_master_matrix()`` — for the 2017-2024 training period, the
     master CSV exposes both raw ``NDVI`` (NaN on cloudy days) and
     ``NDVI_int``.  We expose both; the validator defaults to raw ``NDVI``
     joined with a tolerance window.

  3. ``from_sentinel2_fetch(site, start, end)`` — direct GEE pull,
     bypassing the feature builder.  Used when only S2 is wanted (e.g.
     ERA5 not yet fetched).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config
from .fetchers import fetch_sentinel2_daily
from .logging_setup import logger


def from_unified_features(parquet_path: Path) -> pd.DataFrame:
    """Return DataFrame[date, actual_ndvi] from a unified-features parquet."""
    if not parquet_path.exists():
        raise FileNotFoundError(parquet_path)
    df = pd.read_parquet(parquet_path)
    df["date"] = pd.to_datetime(df["date"])
    out = df[["date", "NDVI_int"]].rename(columns={"NDVI_int": "actual_ndvi"})
    out["source"] = "unified_features_NDVI_int"
    return out.reset_index(drop=True)


def from_master_matrix(
    *,
    use_raw: bool = True,
    path: Path = config.MASTER_FEATURE_MATRIX,
) -> pd.DataFrame:
    """
    Read the 2017-2024 master CSV and return one of:
        DataFrame[date, actual_ndvi]   (raw, NaN-tolerant — use_raw=True)
        DataFrame[date, actual_ndvi]   (NDVI_int interpolated — use_raw=False)

    The raw form is the gold standard for validation metrics: only days
    with real cloud-free Sentinel-2 overpasses contribute.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, parse_dates=["date"])
    col = "NDVI" if use_raw else "NDVI_int"
    if col not in df.columns:
        raise RuntimeError(f"Column {col!r} not in {path.name}")
    out = df[["date", col]].rename(columns={col: "actual_ndvi"}).copy()
    out["source"] = "master_NDVI_raw" if use_raw else "master_NDVI_int"
    if use_raw:
        n_valid = int(out["actual_ndvi"].notna().sum())
        logger.info("[actuals] master raw NDVI: {} cloud-free days of {} total",
                    n_valid, len(out))
    return out.reset_index(drop=True)


def from_sentinel2_fetch(
    site: config.Site,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Direct S2 ground-truth from GEE (cloud-free overpasses only)."""
    df = fetch_sentinel2_daily(site, start_date, end_date)
    if df.empty:
        return pd.DataFrame(columns=["date", "actual_ndvi", "source"])
    out = df[["date", "NDVI"]].rename(columns={"NDVI": "actual_ndvi"})
    out["source"] = "s2_gee_raw"
    return out.reset_index(drop=True)


__all__ = ["from_unified_features", "from_master_matrix", "from_sentinel2_fetch"]
