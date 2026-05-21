"""
Yıllık Verim Özellik Matrisi
==============================
master_feature_matrix_2017_2024.csv üzerinden her mahsul/yıl için
17 agronomik özellik hesaplar.
Çıktı: data/yield/yield_feature_matrix.csv
"""
import numpy as np
import pandas as pd
from pathlib import Path

GROWING_WINDOWS = {
    "Wheat": {
        "full_start_month": 10,
        "full_end_month": 7,
        "year_wrap": True,
        "critical_start": 2,
        "critical_end": 5,
        "gdd_base": 0.0,
        "heat_stress_thr": 32.0,
    },
    "Sunflower": {
        "full_start_month": 4,
        "full_end_month": 10,
        "year_wrap": False,
        "critical_start": 6,
        "critical_end": 8,
        "gdd_base": 8.0,
        "heat_stress_thr": 35.0,
    },
}

FEATURE_NAMES = [
    "ndvi_peak", "ndvi_mean_grow", "ndvi_sum",
    "gdd_total", "gdd_critical",
    "precip_total", "precip_grow",
    "drought_days", "heat_stress_days", "frost_days",
    "temp_mean_grow", "temp_amplitude_mean",
    "evi_peak", "ndwi_min",
    "radiation_total",
    "soil_clay", "soil_ph",
]


def _get_season_df(df: pd.DataFrame, crop: str, harvest_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (full_season_df, critical_period_df).
    For Wheat: Oct(harvest_year-1) – Jul(harvest_year), year_wrap=True
    For Sunflower: Apr – Oct of harvest_year, year_wrap=False
    Clamps to available data range — no error if season extends beyond data.
    """
    cfg = GROWING_WINDOWS[crop]

    if cfg["year_wrap"]:
        start = pd.Timestamp(harvest_year - 1, cfg["full_start_month"], 1)
        end   = pd.Timestamp(harvest_year,     cfg["full_end_month"],   31, 23, 59, 59)
        crit_start = pd.Timestamp(harvest_year, cfg["critical_start"], 1)
        crit_end   = pd.Timestamp(harvest_year, cfg["critical_end"],   30, 23, 59, 59)
    else:
        start = pd.Timestamp(harvest_year, cfg["full_start_month"], 1)
        end   = pd.Timestamp(harvest_year, cfg["full_end_month"],   31, 23, 59, 59)
        crit_start = pd.Timestamp(harvest_year, cfg["critical_start"], 1)
        crit_end   = pd.Timestamp(harvest_year, cfg["critical_end"],   30, 23, 59, 59)

    full_df  = df[(df["date"] >= start) & (df["date"] <= end)].copy()
    crit_df  = df[(df["date"] >= crit_start) & (df["date"] <= crit_end)].copy()
    return full_df, crit_df


def compute_features(df_full: pd.DataFrame, df_crit: pd.DataFrame, crop: str) -> dict:
    """Compute 17 annual features from season DataFrames."""
    if df_full.empty:
        return {f: np.nan for f in FEATURE_NAMES}

    cfg = GROWING_WINDOWS[crop]
    base = cfg["gdd_base"]
    heat_thr = cfg["heat_stress_thr"]

    # NDVI features
    ndvi_peak      = df_full["NDVI_int"].max()
    ndvi_mean_grow = df_full["NDVI_int"].mean()
    ndvi_sum       = df_full["NDVI_int"].sum()

    # GDD
    gdd_total    = df_full["t2m_mean"].apply(lambda t: max(0, t - base)).sum()
    gdd_critical = df_crit["t2m_mean"].apply(lambda t: max(0, t - base)).sum() if not df_crit.empty else 0.0

    # Precipitation
    precip_total = df_full["tp_sum"].sum()
    precip_grow  = df_crit["tp_sum"].sum() if not df_crit.empty else 0.0

    # Drought days (rolling 7-day precip < 1 mm)
    rolling7 = df_full["tp_sum"].rolling(7, min_periods=1).sum()
    drought_days = int((rolling7 < 1.0).sum())

    # Stress days
    heat_stress_days = int((df_full["t2m_max"] > heat_thr).sum())
    frost_days       = int((df_full["t2m_min"] < 0.0).sum())

    # Temperature
    temp_mean_grow       = df_full["t2m_mean"].mean()
    temp_amplitude_mean  = (df_full["t2m_max"] - df_full["t2m_min"]).mean()

    # Spectral indices
    evi_peak = df_full["EVI_int"].max()
    ndwi_min = df_full["NDWI_int"].min()

    # Radiation (J/m² → MJ/m²)
    radiation_total = df_full["ssr_sum"].sum() / 1_000_000.0

    # Static soil (constant across all rows)
    soil_clay = df_full[["clay_0-5cm", "clay_5-15cm", "clay_15-30cm"]].iloc[0].mean()
    soil_ph   = df_full[["phh2o_0-5cm", "phh2o_5-15cm", "phh2o_15-30cm"]].iloc[0].mean()

    return {
        "ndvi_peak": ndvi_peak,
        "ndvi_mean_grow": ndvi_mean_grow,
        "ndvi_sum": ndvi_sum,
        "gdd_total": gdd_total,
        "gdd_critical": gdd_critical,
        "precip_total": precip_total,
        "precip_grow": precip_grow,
        "drought_days": drought_days,
        "heat_stress_days": heat_stress_days,
        "frost_days": frost_days,
        "temp_mean_grow": temp_mean_grow,
        "temp_amplitude_mean": temp_amplitude_mean,
        "evi_peak": evi_peak,
        "ndwi_min": ndwi_min,
        "radiation_total": radiation_total,
        "soil_clay": soil_clay,
        "soil_ph": soil_ph,
    }


def build_and_save():
    project_root = Path(__file__).parent.parent.parent
    data_path = project_root / "data" / "processed" / "master_feature_matrix_2017_2024.csv"
    out_dir   = project_root / "data" / "yield"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path  = out_dir / "yield_feature_matrix.csv"

    df = pd.read_csv(data_path, parse_dates=["date"])

    rows = []
    for crop in ["Wheat", "Sunflower"]:
        for harvest_year in range(2017, 2025):
            df_full, df_crit = _get_season_df(df, crop, harvest_year)
            feats = compute_features(df_full, df_crit, crop)
            row = {"year": harvest_year, "crop": crop}
            row.update(feats)
            rows.append(row)
            print(f"  {crop} {harvest_year}: {len(df_full)} gün, ndvi_peak={feats['ndvi_peak']:.4f}")

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False, float_format="%.4f")

    print(f"\nKaydedildi: {out_path}")
    print(f"Şekil: {out_df.shape}")
    return out_df


if __name__ == "__main__":
    build_and_save()
