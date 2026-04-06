"""
═══════════════════════════════════════════════════════════════════════════════
TRAK-AI KDS — WP2: Data Preprocessing & Feature Engineering
═══════════════════════════════════════════════════════════════════════════════
This module takes the master_feature_matrix CSV produced by WP1 and applies:
  1. Anomaly cleaning (EVI outliers, SSR rescaling)
  2. Agronomic feature derivation (GDD, drought index, NDVI trend, etc.)
  3. Crop-specific season filtering (Wheat: Oct-Jul, Sunflower: Apr-Oct)
  4. Sliding window + 7-day forecast horizon -> X, y arrays
  5. MinMaxScaler fit & persist (for inverse transform at inference)

Outputs (saved to BASE_DIR):
  - X_wheat.npy, y_wheat.npy
  - X_sunflower.npy, y_sunflower.npy
  - X_xgb_wheat.npy, X_xgb_sunflower.npy   (flattened for XGBoost)
  - scaler_wheat.pkl, scaler_sunflower.pkl
  - feature_names.json
  - soil_metadata.json

Author  : TRAK-AI Team
Python  : 3.9+
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler

# -- Directory Structure --
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
CSV_PATH = os.path.join(
    PROJECT_ROOT, "data", "processed", "master_feature_matrix_2017_2024.csv"
)

# -- Constants --
WINDOW_SIZE = 30
FORECAST_HORIZON = 7
TARGET_COLUMN = "NDVI_int"

WHEAT_MONTHS = [10, 11, 12, 1, 2, 3, 4, 5, 6, 7]
SUNFLOWER_MONTHS = [4, 5, 6, 7, 8, 9, 10]
GDD_BASE_GENERAL = 5.0


def load_and_clean(csv_path: str) -> tuple:
    print("=" * 60)
    print("STEP 1: Data Loading & Anomaly Cleaning")
    print("=" * 60)

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"   Raw data: {df.shape[0]} rows, {df.shape[1]} columns")

    evi_mask = df["EVI"].notna() & (df["EVI"].abs() > 1.0)
    n_evi_outliers = evi_mask.sum()
    df.loc[evi_mask, "EVI"] = np.nan
    print(f"   [OK] EVI outliers: {n_evi_outliers} measurements set to NaN (|EVI| > 1)")

    df["EVI_int"] = df["EVI"].interpolate(method="linear").bfill().ffill()
    print("   [OK] EVI_int re-interpolated after outlier removal")

    df["ssr_sum"] = df["ssr_sum"] / 1e6
    print(f"   [OK] ssr_sum: J/m2 -> MJ/m2 (range: {df['ssr_sum'].min():.1f} - {df['ssr_sum'].max():.1f})")

    df["evaporation_mm"] = df["e_sum"].abs() * 1000
    print(f"   [OK] evaporation_mm derived (range: {df['evaporation_mm'].min():.2f} - {df['evaporation_mm'].max():.2f} mm)")

    soil_cols = [c for c in df.columns if any(s in c for s in ["clay_", "sand_", "phh2o_"])]
    soil_metadata = {c: df[c].iloc[0] for c in soil_cols}
    df = df.drop(columns=soil_cols)
    print(f"   [OK] {len(soil_cols)} constant soil columns removed (saved as metadata)")

    drop_cols = ["EVI", "NDVI", "NDWI", "e_sum"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    print("   [OK] Raw spectral indices and e_sum dropped")
    print(f"   -> Cleaned data: {df.shape[0]} rows, {df.shape[1]} columns")

    return df, soil_metadata


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("STEP 2: Feature Engineering")
    print("=" * 60)

    t_mean_daily = (df["t2m_max"] + df["t2m_min"]) / 2
    df["GDD"] = np.maximum(0, t_mean_daily - GDD_BASE_GENERAL)
    print(f"   [OK] GDD (base={GDD_BASE_GENERAL}C): mean={df['GDD'].mean():.2f}")

    df["year"] = df["date"].dt.year
    df["GDD_cum"] = df.groupby("year")["GDD"].cumsum()
    df = df.drop(columns=["year"])
    print(f"   [OK] GDD_cum (annual cumulative): max={df['GDD_cum'].max():.0f}")

    df["precip_evap_diff"] = df["tp_sum"] - df["evaporation_mm"]
    df["drought_index_7d"] = df["precip_evap_diff"].rolling(window=7, min_periods=1).sum()
    print("   [OK] drought_index_7d: negative = drought tendency")

    df["NDVI_trend_7d"] = df["NDVI_int"] - df["NDVI_int"].shift(7)
    df["NDVI_trend_7d"] = df["NDVI_trend_7d"].bfill()
    print("   [OK] NDVI_trend_7d: positive = growth, negative = stress/harvest")

    df["temp_amplitude"] = df["t2m_max"] - df["t2m_min"]
    print(f"   [OK] temp_amplitude: mean={df['temp_amplitude'].mean():.2f}C")

    df["dew_depression"] = df["t2m_mean"] - df["d2m_mean"]
    print("   [OK] dew_depression: high = dry air, low = humid")

    doy = df["date"].dt.dayofyear
    df["sin_doy"] = np.sin(2 * np.pi * doy / 365.25)
    df["cos_doy"] = np.cos(2 * np.pi * doy / 365.25)
    print("   [OK] sin_doy, cos_doy: seasonal signal encoded")

    df = df.drop(columns=["precip_evap_diff", "d2m_mean"])

    print(f"   -> Enriched data: {df.shape[0]} rows, {df.shape[1]} columns")
    return df


def get_model_features() -> list:
    return [
        "t2m_mean", "t2m_max", "t2m_min", "tp_sum", "ssr_sum",
        "GDD", "GDD_cum", "evaporation_mm", "drought_index_7d",
        "temp_amplitude", "dew_depression",
        "NDVI_int", "EVI_int", "NDWI_int",
        "NDVI_trend_7d", "sin_doy", "cos_doy",
    ]


def filter_by_crop(df: pd.DataFrame, crop_type: str) -> pd.DataFrame:
    month = df["date"].dt.month
    if crop_type == "Wheat":
        mask = month.isin(WHEAT_MONTHS)
    elif crop_type == "Sunflower":
        mask = month.isin(SUNFLOWER_MONTHS)
    else:
        raise ValueError(f"Unknown crop type: {crop_type}")
    return df[mask].reset_index(drop=True)


def create_sliding_windows(data, window, horizon, target_idx):
    X, y = [], []
    for i in range(len(data) - window - horizon + 1):
        X.append(data[i : i + window, :])
        y.append(data[i + window + horizon - 1, target_idx])
    return np.array(X), np.array(y)


def create_xgboost_features(X_3d, feature_names):
    records = []
    for i in range(X_3d.shape[0]):
        w = X_3d[i]
        row = {}
        for j, fn in enumerate(feature_names):
            col = w[:, j]
            row[f"{fn}_last"] = col[-1]
            row[f"{fn}_mean"] = col.mean()
            row[f"{fn}_min"] = col.min()
            row[f"{fn}_max"] = col.max()
            row[f"{fn}_trend"] = col[-1] - col[0]
        records.append(row)
    return pd.DataFrame(records)


def main():
    print("\n" + "=" * 60)
    print("  TRAK-AI KDS — WP2 Data Preprocessing Pipeline")
    print("=" * 60 + "\n")

    df, soil_meta = load_and_clean(CSV_PATH)
    df = engineer_features(df)

    features = get_model_features()
    target_idx = features.index(TARGET_COLUMN)

    print(f"\nModel feature set ({len(features)} features):")
    for i, f in enumerate(features):
        marker = " <-- TARGET" if f == TARGET_COLUMN else ""
        print(f"   [{i:2d}] {f}{marker}")

    with open(os.path.join(BASE_DIR, "feature_names.json"), "w") as f:
        json.dump(features, f, indent=2)

    with open(os.path.join(BASE_DIR, "soil_metadata.json"), "w") as f:
        json.dump(soil_meta, f, indent=2)

    crops = {
        "Wheat":     {"label": "Wheat",     "prefix": "wheat"},
        "Sunflower": {"label": "Sunflower", "prefix": "sunflower"},
    }

    for crop_key, info in crops.items():
        print(f"\n{'─' * 60}")
        print(f"  Processing: {info['label']}")
        print(f"{'─' * 60}")

        df_season = filter_by_crop(df, crop_key)
        print(f"   Season days: {len(df_season)}")

        df_model = df_season[features].copy()
        nan_count = df_model.isnull().sum().sum()
        if nan_count > 0:
            print(f"   [WARN] {nan_count} NaN values found, applying ffill + bfill...")
            df_model = df_model.ffill().bfill()

        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled = scaler.fit_transform(df_model.values)
        print("   [OK] MinMaxScaler fitted (range: 0-1)")

        scaler_path = os.path.join(BASE_DIR, f"scaler_{info['prefix']}.pkl")
        joblib.dump(scaler, scaler_path)
        print(f"   [SAVED] Scaler: {os.path.basename(scaler_path)}")

        X, y = create_sliding_windows(scaled, WINDOW_SIZE, FORECAST_HORIZON, target_idx)
        print(f"   [OK] Window: {WINDOW_SIZE} days, Horizon: {FORECAST_HORIZON} days")
        print(f"   -> X shape: {X.shape}  (samples, timesteps, features)")
        print(f"   -> y shape: {y.shape}  (samples,)")
        print(f"   -> y range: [{y.min():.4f}, {y.max():.4f}], mean: {y.mean():.4f}")

        X_xgb = create_xgboost_features(X, features)
        print(f"   [OK] XGBoost features: {X_xgb.shape}  (samples, flattened_features)")

        np.save(os.path.join(BASE_DIR, f"X_{info['prefix']}.npy"), X)
        np.save(os.path.join(BASE_DIR, f"y_{info['prefix']}.npy"), y)
        np.save(os.path.join(BASE_DIR, f"X_xgb_{info['prefix']}.npy"), X_xgb.values)

        with open(os.path.join(BASE_DIR, f"xgb_feature_names_{info['prefix']}.json"), "w") as f:
            json.dump(list(X_xgb.columns), f)

        print(f"   [SAVED] X_{info['prefix']}.npy, y_{info['prefix']}.npy")

    print(f"\n{'=' * 60}")
    print("  WP2 DATA PREPROCESSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"   Window size      : {WINDOW_SIZE} days")
    print(f"   Forecast horizon : {FORECAST_HORIZON} days")
    print(f"   Feature count    : {len(features)}")
    print(f"   Target           : {TARGET_COLUMN} (t+{FORECAST_HORIZON})")
    print(f"   Output directory : {BASE_DIR}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()