"""
XGBoost Verim Tahmin Modeli Eğitimi
=====================================
TÜİK verim verisi + 17 yıllık özellik → her mahsul için ayrı XGBoost modeli.
LOO-CV ile değerlendirme, SHAP analizi, model kaydetme.
Çalıştırmak için: python src/cp2_model/train_yield_model.py
"""
import json
import sys
import os
from pathlib import Path
from math import sqrt

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

_this_dir = Path(__file__).parent
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

XGB_PARAMS = {
    "n_estimators": 100,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 2.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
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


def train_crop(crop: str, feat_df: pd.DataFrame, yield_df: pd.DataFrame) -> dict:
    merged = feat_df[feat_df["crop"] == crop].merge(
        yield_df[yield_df["crop"] == crop][["year", "yield_kg_dekar"]],
        on="year"
    ).dropna().sort_values("year").reset_index(drop=True)

    if len(merged) < 4:
        print(f"[UYARI] {crop}: yeterli veri yok ({len(merged)} satır)")
        return {}

    X = merged[FEATURE_NAMES].values.astype(float)
    y = merged["yield_kg_dekar"].values.astype(float)
    years = merged["year"].values

    print(f"\n{'='*50}")
    print(f"  {crop} — {len(merged)} yıl LOO-CV")
    print(f"{'='*50}")

    # LOO-CV
    loo = LeaveOneOut()
    y_pred_loo = []
    y_true_loo = []

    for train_idx, test_idx in loo.split(X):
        scaler_fold = StandardScaler().fit(X[train_idx])
        X_tr = scaler_fold.transform(X[train_idx])
        X_te = scaler_fold.transform(X[test_idx])
        m = XGBRegressor(**XGB_PARAMS)
        m.fit(X_tr, y[train_idx])
        pred = m.predict(X_te)[0]
        y_pred_loo.append(pred)
        y_true_loo.append(y[test_idx][0])
        test_year = years[test_idx[0]]
        print(f"  LOO fold yıl={test_year}: gerçek={y[test_idx[0]]:.0f}, tahmin={pred:.0f}, hata={abs(pred-y[test_idx[0]]):.0f}")

    y_pred_arr = np.array(y_pred_loo)
    y_true_arr = np.array(y_true_loo)

    r2   = r2_score(y_true_arr, y_pred_arr)
    mae  = mean_absolute_error(y_true_arr, y_pred_arr)
    rmse = sqrt(mean_squared_error(y_true_arr, y_pred_arr))
    mape = float(np.mean(np.abs((y_true_arr - y_pred_arr) / y_true_arr) * 100))

    print(f"\n  LOO-CV Metrikler:")
    print(f"  R²   = {r2:.4f}")
    print(f"  MAE  = {mae:.2f} kg/dekar")
    print(f"  RMSE = {rmse:.2f} kg/dekar")
    print(f"  MAPE = {mape:.2f}%")

    # Final model — tüm veriyle
    final_scaler = StandardScaler().fit(X)
    X_scaled = final_scaler.transform(X)
    final_model = XGBRegressor(**XGB_PARAMS)
    final_model.fit(X_scaled, y)

    # SHAP analizi
    try:
        import shap
        explainer = shap.TreeExplainer(final_model)
        try:
            shap_values = explainer.shap_values(X_scaled, check_additivity=False)
        except TypeError:
            shap_values = explainer.shap_values(X_scaled)
        mean_shap = dict(zip(FEATURE_NAMES, np.abs(shap_values).mean(axis=0).tolist()))
        sorted_shap = sorted(mean_shap.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  SHAP Top-5 Özellik:")
        for fname, fval in sorted_shap[:5]:
            print(f"    {fname:<25} {fval:.4f}")
        shap_data = {
            "feature_names": FEATURE_NAMES,
            "mean_shap": mean_shap,
            "shap_values": shap_values.tolist(),
            "years": years.tolist(),
        }
    except Exception as e:
        print(f"  [SHAP HATASI] {e}")
        shap_data = {"feature_names": FEATURE_NAMES, "mean_shap": {}, "shap_values": [], "years": years.tolist()}

    # Kaydet
    crop_key = crop.lower()
    model_path  = _this_dir / f"yield_xgb_{crop_key}.pkl"
    scaler_path = _this_dir / f"yield_scaler_{crop_key}.pkl"
    shap_path   = _this_dir / f"yield_shap_{crop_key}.json"
    meta_path   = _this_dir / f"yield_meta_{crop_key}.json"

    joblib.dump(final_model, model_path)
    joblib.dump(final_scaler, scaler_path)
    with open(shap_path, "w", encoding="utf-8") as f:
        json.dump(shap_data, f, ensure_ascii=False)

    trakya_median = float(np.median(y))
    meta = {
        "crop": crop,
        "n_samples": int(len(merged)),
        "feature_names": FEATURE_NAMES,
        "metrics": {"r2": round(r2, 4), "mae": round(mae, 2), "rmse": round(rmse, 2), "mape": round(mape, 2)},
        "trakya_median_yield": trakya_median,
        "confidence_interval_half_width": round(rmse * 1.5, 1),
        "years": years.tolist(),
        "yields": y.tolist(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n  Kaydedildi: {model_path.name}, {scaler_path.name}, {shap_path.name}, {meta_path.name}")
    return meta


def main():
    project_root = _this_dir.parent.parent
    feat_path  = project_root / "data" / "yield" / "yield_feature_matrix.csv"
    yield_path = project_root / "data" / "yield" / "trakya_yield_2017_2024.csv"

    if not feat_path.exists():
        print(f"[HATA] Özellik matrisi bulunamadı: {feat_path}")
        print("Önce çalıştır: python build_yield_features.py")
        sys.exit(1)
    if not yield_path.exists():
        print(f"[HATA] Verim verisi bulunamadı: {yield_path}")
        print("Önce çalıştır: python collect_yield_data.py")
        sys.exit(1)

    feat_df  = pd.read_csv(feat_path)
    yield_df = pd.read_csv(yield_path)

    results = {}
    for crop in ["Wheat", "Sunflower"]:
        results[crop] = train_crop(crop, feat_df, yield_df)

    print("\n" + "="*50)
    print("  EĞİTİM TAMAMLANDI")
    print("="*50)
    for crop, meta in results.items():
        if meta:
            m = meta["metrics"]
            print(f"  {crop:<12} R²={m['r2']:.3f}  MAE={m['mae']:.1f}  RMSE={m['rmse']:.1f}  MAPE={m['mape']:.1f}%")


if __name__ == "__main__":
    main()
