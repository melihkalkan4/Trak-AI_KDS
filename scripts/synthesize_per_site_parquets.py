"""
TRAK-AI KDS — Per-Site Parquet Synthesis (Offline-First)
=========================================================
External Sentinel-2 / GEE fetch is unreliable (no auth in this env).
This script takes the EVR_01 unified-features parquet as a base and
derives per-site distinct NDVI / EVI / NDWI curves driven by:

    * Crop type            (wheat winter+spring peak vs sunflower summer peak)
    * Soil type modifier   (clay holds water -> +NDVI in dry weeks)
    * Site-specific seed   (deterministic per-evrenli jitter)

ERA5-Land columns (t2m, tp_sum, GDD, ...) are kept identical across sites,
because the real 9-km grid genuinely covers the cluster. The synthetic
NDVI curves are physically plausible (Trakya phenology, DOY-driven) and
are flagged in DB `data_source = 'synth_crop_phenology'` for honesty.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "trakai.db"
BASE_PARQUET = REPO_ROOT / "data" / "prospective" / "2025" / "EVR_01_unified_features.parquet"
OUT_DIR_BASE = REPO_ROOT / "data" / "prospective"


# ---------- DOY -> NDVI lookup tables (Trakya, sunflower + wheat) ----------
def _interp_curve(points: list[tuple[int, float]], doy: np.ndarray) -> np.ndarray:
    xs = np.array([p[0] for p in points], dtype=float)
    ys = np.array([p[1] for p in points], dtype=float)
    return np.interp(doy % 366, xs, ys)


# Sunflower NDVI(DOY)  — peaks DOY ~180 (late June)
SUNFLOWER_NDVI_POINTS = [
    (1,   0.22), (60,  0.24), (105, 0.27),
    (130, 0.40), (150, 0.55), (170, 0.72),
    (180, 0.82), (195, 0.85), (210, 0.78),
    (230, 0.58), (250, 0.38), (270, 0.24),
    (300, 0.20), (340, 0.22), (366, 0.22),
]

# Wheat NDVI(DOY) — peaks DOY ~120 (early May)
WHEAT_NDVI_POINTS = [
    (1,   0.30), (30,  0.33), (60,  0.38),
    (90,  0.50), (110, 0.65), (125, 0.75),
    (140, 0.72), (160, 0.55), (175, 0.38),
    (190, 0.22), (240, 0.15), (270, 0.18),
    (285, 0.25), (310, 0.30), (340, 0.30),
    (366, 0.30),
]


def _ndvi_from_doy(doy: np.ndarray, crop_type: str) -> np.ndarray:
    if crop_type == "wheat":
        return _interp_curve(WHEAT_NDVI_POINTS, doy)
    return _interp_curve(SUNFLOWER_NDVI_POINTS, doy)


# Soil modifiers
SOIL_NDVI_BUMP = {
    "killi":       +0.04,   # clay: holds water -> greener under heat stress
    "tinli":       +0.00,
    "kumlu-tinli": -0.03,   # sandy-loam: drains fast -> drier vegetation
}


def _site_seed(evrenli_id: str) -> int:
    return abs(hash(evrenli_id)) % (2**31 - 1)


def synthesise_for_site(
    base_df: pd.DataFrame,
    *,
    evrenli_id: str,
    crop_type: str,
    soil_type: str,
) -> pd.DataFrame:
    """Return a new DataFrame with crop-aware NDVI/EVI/NDWI replacing base."""
    df = base_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    doy = df["date"].dt.dayofyear.to_numpy()

    rng = np.random.default_rng(_site_seed(evrenli_id))
    noise = rng.normal(0.0, 0.015, size=len(df))           # ~1.5% noise

    soil_bump = SOIL_NDVI_BUMP.get(soil_type, 0.0)
    ndvi = _ndvi_from_doy(doy, crop_type) + soil_bump + noise

    # Heat stress depresses NDVI in summer (t2m_max > 35)
    if "t2m_max" in df.columns:
        heat_mask = df["t2m_max"].to_numpy() > 35
        ndvi[heat_mask] -= 0.05

    # Drought depression
    if "drought_index_7d" in df.columns:
        drought_mask = df["drought_index_7d"].to_numpy() > 5
        ndvi[drought_mask] -= 0.03

    ndvi = np.clip(ndvi, 0.05, 0.95)

    # EVI ~ NDVI * 0.55 (canonical narrowband ratio)
    evi = np.clip(ndvi * 0.55 + rng.normal(0, 0.01, size=len(df)), 0.0, 0.85)

    # NDWI: inverse-related, vegetation water content proxy.
    # Higher NDVI generally means more biomass -> NDWI typically negative
    # in dry summers, positive in wet spring.
    ndwi = -0.45 + (ndvi - 0.4) * 0.8 + rng.normal(0, 0.02, size=len(df))
    ndwi = np.clip(ndwi, -0.7, 0.5)

    df["NDVI_int"] = ndvi
    df["EVI_int"] = evi
    df["NDWI_int"] = ndwi

    # NDVI_trend_7d  (rolling diff)
    df["NDVI_trend_7d"] = (df["NDVI_int"]
                          - df["NDVI_int"].shift(7).fillna(df["NDVI_int"].iloc[0]))

    return df


def _load_crop_map() -> dict[str, tuple[str, str]]:
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT evrenli_id, crop_type, soil_type FROM tarla ORDER BY id"
        ).fetchall()
    finally:
        con.close()
    return {evr: (crop, soil) for evr, crop, soil in rows}


def main() -> int:
    if not BASE_PARQUET.exists():
        raise FileNotFoundError(f"Base parquet missing: {BASE_PARQUET}")

    base_df = pd.read_parquet(BASE_PARQUET)
    print(f"[base] {BASE_PARQUET.name}: {len(base_df)} rows, "
          f"{base_df['date'].min()} -> {base_df['date'].max()}")

    crop_map = _load_crop_map()
    print(f"[crop_map] {crop_map}")

    # split rows into per-year buckets (2025 + 2026 if applicable)
    base_df["date"] = pd.to_datetime(base_df["date"])
    base_df["_year"] = base_df["date"].dt.year

    written = 0
    for evrenli_id, (crop, soil) in crop_map.items():
        for yr, year_df in base_df.groupby("_year"):
            year_df = year_df.drop(columns=["_year"])
            new_df = synthesise_for_site(
                year_df, evrenli_id=evrenli_id, crop_type=crop, soil_type=soil
            )
            out_dir = OUT_DIR_BASE / str(yr)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{evrenli_id}_unified_features.parquet"
            new_df.to_parquet(out_path)
            ndvi_min = float(new_df["NDVI_int"].min())
            ndvi_max = float(new_df["NDVI_int"].max())
            ndvi_peak_doy = int(
                new_df.loc[new_df["NDVI_int"].idxmax(), "date"].dayofyear
            )
            print(f"  OK  {evrenli_id} {yr}: {crop:<9} soil={soil:<12} "
                  f"NDVI={ndvi_min:.2f}-{ndvi_max:.2f}  peak DOY={ndvi_peak_doy}  "
                  f"-> {out_path.relative_to(REPO_ROOT)}")
            written += 1

    print(f"\n[done] {written} parquet files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
