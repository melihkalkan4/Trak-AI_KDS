"""
DOY-mean NDVI climatology from the 2017-2024 master feature matrix.

Why this exists
---------------
The Keras champion's residual head adds its delta to *last observed NDVI*,
not to a DOY baseline.  But for narrative/anomaly reporting (and for SCRAG
prompt context — see thesis Section 3.9), it is useful to express each
prediction as a deviation from the historical seasonal mean.

We build the climatology **only once**, lock its bytes via SHA-256, and
treat it as an additional frozen artefact downstream.

Source
------
``data/processed/master_feature_matrix_2017_2024.csv``

We use the raw cloud-masked ``NDVI`` column (NaN-tolerant), not ``NDVI_int``,
to avoid interpolation contamination of the DOY mean.  Cloud-gap NaNs are
simply excluded from each DOY bucket.

Output
------
``data/historical/climatology/sunflower_doy_climatology.parquet`` with
columns:

    doy            int   1..366
    ndvi_mean      float DOY-mean across all available years
    ndvi_std       float
    ndvi_count     int   how many year-day samples contributed
    ndvi_smooth    float 7-day centred rolling mean of ndvi_mean (gap-fill)

Note: the master matrix is currently single-site (the training site).
When real Evrenli coordinates land in Phase 6, rebuild per-site climatology
by re-running this module against per-site Sentinel-2 history.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config, integrity
from .logging_setup import logger


CLIMATOLOGY_PATH = (
    config.HISTORICAL_CLIMATOLOGY_DIR / "sunflower_doy_climatology.parquet"
)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def _load_master_matrix() -> pd.DataFrame:
    p = config.MASTER_FEATURE_MATRIX
    if not p.exists():
        raise FileNotFoundError(
            f"Master feature matrix missing: {p}\n"
            "The climatology builder cannot proceed without it."
        )
    df = pd.read_csv(p, parse_dates=["date"])
    if "NDVI" not in df.columns:
        raise RuntimeError(
            f"Expected column 'NDVI' in {p.name}, found: {list(df.columns)[:30]}"
        )
    return df


def build_climatology(
    *,
    src_df: Optional[pd.DataFrame] = None,
    smoothing_window_days: int = 7,
    out_path: Path = CLIMATOLOGY_PATH,
) -> pd.DataFrame:
    """
    Build, lock, and return the DOY climatology dataframe.

    Idempotent: if ``out_path`` already exists we re-hash and return it.
    To force a rebuild, delete the file (and its integrity ledger row).
    """
    config.ensure_runtime_dirs()

    if out_path.exists():
        logger.info("[climatology] existing artefact found at {} — verifying", out_path)
        integrity.ensure_unchanged(out_path, role="sunflower_doy_climatology")
        return pd.read_parquet(out_path)

    df = src_df if src_df is not None else _load_master_matrix()
    train_start, train_end = config.TRAINING_WINDOW_YEARS
    mask = (df["date"].dt.year >= train_start) & (df["date"].dt.year <= train_end)
    df = df.loc[mask, ["date", "NDVI"]].copy()
    df["doy"] = df["date"].dt.dayofyear

    # Drop NaN NDVI (cloud gaps) for unbiased DOY means
    df_valid = df.dropna(subset=["NDVI"])

    agg = (
        df_valid.groupby("doy")["NDVI"]
        .agg(ndvi_mean="mean", ndvi_std="std", ndvi_count="count")
        .reindex(range(1, 367))     # ensure all 366 DOYs present
    )
    agg["ndvi_count"] = agg["ndvi_count"].fillna(0).astype(int)

    # Centred rolling smoother (NaN-tolerant) — fills small gaps & damps noise
    agg["ndvi_smooth"] = (
        agg["ndvi_mean"]
        .rolling(window=smoothing_window_days, center=True, min_periods=1)
        .mean()
    )
    # Wrap-around fill: leap-day DOY 366 often has count=0; mirror DOY 365
    if pd.isna(agg.loc[366, "ndvi_smooth"]):
        agg.loc[366, "ndvi_smooth"] = agg.loc[365, "ndvi_smooth"]

    out = agg.reset_index().rename(columns={"index": "doy"})

    # Metadata column for traceability
    out["src_rows"] = len(df_valid)
    out["src_year_start"] = train_start
    out["src_year_end"] = train_end
    out["smoothing_window_days"] = smoothing_window_days

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)

    # Lock + record hash
    sha = integrity.ensure_unchanged(out_path, role="sunflower_doy_climatology")
    integrity.mark_readonly_best_effort(out_path)
    logger.info(
        "[climatology] built {} rows={} sha256={}…",
        out_path.name, len(out), sha[:16],
    )
    return out


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Climatology:
    table: pd.DataFrame    # indexed by doy

    def value_at(self, doy: int, *, smoothed: bool = True) -> float:
        col = "ndvi_smooth" if smoothed else "ndvi_mean"
        return float(self.table.at[int(doy), col])

    def anomaly(self, predicted_ndvi: float, doy: int) -> float:
        """predicted − DOY mean (positive = above seasonal norm)."""
        return predicted_ndvi - self.value_at(doy, smoothed=True)


def load_climatology(path: Path = CLIMATOLOGY_PATH) -> Climatology:
    if not path.exists():
        raise FileNotFoundError(
            f"Climatology artefact missing: {path}\n"
            "Run scripts/build_climatology.py first."
        )
    integrity.ensure_unchanged(path, role="sunflower_doy_climatology")
    df = pd.read_parquet(path).set_index("doy")
    return Climatology(table=df)


# Convenience hash for callers that want the digest without touching ledger
def climatology_sha256(path: Path = CLIMATOLOGY_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "build_climatology",
    "load_climatology",
    "Climatology",
    "CLIMATOLOGY_PATH",
    "climatology_sha256",
]
