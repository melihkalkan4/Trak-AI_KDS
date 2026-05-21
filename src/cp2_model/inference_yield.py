"""
XGBoost Verim Tahmini — Çıkarım Modülü
========================================
Eğitilmiş XGBoost modelini kullanarak güncel sezon özelliklerinden
yıllık mahsul verimi tahmin eder.
Kullanım: from inference_yield import predict_yield
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

_this_dir = Path(__file__).parent
_project_root = _this_dir.parent.parent

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

_GROWING_WINDOWS = {
    "Wheat": {
        "full_start_month": 10, "full_end_month": 7, "year_wrap": True,
        "critical_start": 2,    "critical_end": 5,
        "gdd_base": 0.0,        "heat_stress_thr": 32.0,
    },
    "Sunflower": {
        "full_start_month": 4,  "full_end_month": 10, "year_wrap": False,
        "critical_start": 6,    "critical_end": 8,
        "gdd_base": 8.0,        "heat_stress_thr": 35.0,
    },
}


def _get_latest_harvest_year(crop: str) -> int:
    """En son tam büyüme sezonu olan hasat yılını döndür."""
    current = datetime.now()
    if crop == "Wheat":
        # Hasat Temmuz — eğer Ağustos+ isek bu yılki hasat tamamdır
        return current.year if current.month >= 8 else current.year - 1
    else:
        # Sunflower hasat Ekim — Kasım+ isek bu yılki tamamdır
        return current.year if current.month >= 11 else current.year - 1


def _compute_season_features(df: pd.DataFrame, crop: str, harvest_year: int) -> dict:
    """
    master_feature_matrix DataFrame'inden tek bir büyüme sezonu için
    17 özellik hesaplar.
    """
    cfg = _GROWING_WINDOWS[crop]

    if cfg["year_wrap"]:
        start = pd.Timestamp(harvest_year - 1, cfg["full_start_month"], 1)
        end   = pd.Timestamp(harvest_year,     cfg["full_end_month"],   31, 23, 59, 59)
        cs    = pd.Timestamp(harvest_year,     cfg["critical_start"],   1)
        ce    = pd.Timestamp(harvest_year,     cfg["critical_end"],     30, 23, 59, 59)
    else:
        start = pd.Timestamp(harvest_year, cfg["full_start_month"], 1)
        end   = pd.Timestamp(harvest_year, cfg["full_end_month"],   31, 23, 59, 59)
        cs    = pd.Timestamp(harvest_year, cfg["critical_start"],   1)
        ce    = pd.Timestamp(harvest_year, cfg["critical_end"],     30, 23, 59, 59)

    df_full = df[(df["date"] >= start) & (df["date"] <= end)]
    df_crit = df[(df["date"] >= cs) & (df["date"] <= ce)]

    if df_full.empty:
        return {}

    base     = cfg["gdd_base"]
    heat_thr = cfg["heat_stress_thr"]

    rolling7 = df_full["tp_sum"].rolling(7, min_periods=1).sum()

    return {
        "ndvi_peak":           float(df_full["NDVI_int"].max()),
        "ndvi_mean_grow":      float(df_full["NDVI_int"].mean()),
        "ndvi_sum":            float(df_full["NDVI_int"].sum()),
        "gdd_total":           float(df_full["t2m_mean"].apply(lambda t: max(0, t - base)).sum()),
        "gdd_critical":        float(df_crit["t2m_mean"].apply(lambda t: max(0, t - base)).sum()) if not df_crit.empty else 0.0,
        "precip_total":        float(df_full["tp_sum"].sum()),
        "precip_grow":         float(df_crit["tp_sum"].sum()) if not df_crit.empty else 0.0,
        "drought_days":        int((rolling7 < 1.0).sum()),
        "heat_stress_days":    int((df_full["t2m_max"] > heat_thr).sum()),
        "frost_days":          int((df_full["t2m_min"] < 0.0).sum()),
        "temp_mean_grow":      float(df_full["t2m_mean"].mean()),
        "temp_amplitude_mean": float((df_full["t2m_max"] - df_full["t2m_min"]).mean()),
        "evi_peak":            float(df_full["EVI_int"].max()),
        "ndwi_min":            float(df_full["NDWI_int"].min()),
        "radiation_total":     float(df_full["ssr_sum"].sum() / 1_000_000.0),
        "soil_clay":           float(df_full[["clay_0-5cm", "clay_5-15cm", "clay_15-30cm"]].iloc[0].mean()),
        "soil_ph":             float(df_full[["phh2o_0-5cm", "phh2o_5-15cm", "phh2o_15-30cm"]].iloc[0].mean()),
    }


def _extract_latest_features(crop: str) -> tuple[dict, int, str | None]:
    """
    master_feature_matrix'ten en son tam hasat yılı özelliklerini çıkarır.
    Returns: (features_dict, harvest_year, warning_str_or_None)
    """
    data_path = _project_root / "data" / "processed" / "master_feature_matrix_2017_2024.csv"
    if not data_path.exists():
        return {}, 0, f"Veri bulunamadı: {data_path}"

    df = pd.read_csv(data_path, parse_dates=["date"])
    max_data_year = df["date"].dt.year.max()

    harvest_year = _get_latest_harvest_year(crop)

    # Veri sınırının dışındaysa en son mevcut yıla ine
    uyari = None
    if harvest_year > max_data_year:
        harvest_year = max_data_year
        uyari = (
            f"Güncel sezon verisi mevcut değil — {max_data_year} sezonu kullanıldı "
            f"({datetime.now().year} tahmini için)"
        )

    feats = _compute_season_features(df, crop, harvest_year)
    return feats, harvest_year, uyari


def predict_yield(crop_type: str, current_year_features: dict = None) -> dict:
    """
    XGBoost modeli ile yıllık mahsul verimini tahmin eder.

    Args:
        crop_type: "Wheat" veya "Sunflower"
        current_year_features: 17-özellik dict (None ise master_feature_matrix'ten otomatik)

    Returns:
        dict: tahmin sonuçları
    """
    import joblib

    crop_key = crop_type.lower()
    model_path  = _this_dir / f"yield_xgb_{crop_key}.pkl"
    scaler_path = _this_dir / f"yield_scaler_{crop_key}.pkl"
    meta_path   = _this_dir / f"yield_meta_{crop_key}.json"
    shap_path   = _this_dir / f"yield_shap_{crop_key}.json"

    if not model_path.exists():
        return {
            "hata": f"Model bulunamadı: {model_path.name}. Önce train_yield_model.py çalıştırın.",
            "tahmini_verim_kg_dekar": None,
        }

    model  = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    # Özellik vektörü hazırla
    uyari = None
    veri_yili = 0

    if current_year_features is not None:
        feats = current_year_features
        veri_yili = datetime.now().year
    else:
        feats, veri_yili, uyari = _extract_latest_features(crop_type)

    if not feats:
        return {
            "hata": "Özellikler çıkarılamadı.",
            "tahmini_verim_kg_dekar": None,
        }

    X = np.array([[feats.get(f, 0.0) for f in FEATURE_NAMES]])
    X_scaled = scaler.transform(X)
    pred = float(model.predict(X_scaled)[0])

    # Güven aralığı
    hw = meta["confidence_interval_half_width"]
    ci = {"alt": round(pred - hw, 1), "ust": round(pred + hw, 1)}

    # Trakya karşılaştırması
    trakya_ort = meta["trakya_median_yield"]
    pct_comp   = round((pred / trakya_ort - 1.0) * 100.0, 1)

    # Risk seviyesi
    if pct_comp < -10:
        risk = "YÜKSEK RİSK"
    elif pct_comp < 5:
        risk = "NORMAL"
    else:
        risk = "OLUMLU"

    # Trend
    if pct_comp >= 8:
        trend = "ORTANIN ÜSTÜ"
    elif pct_comp <= -8:
        trend = "ORTANIN ALTI"
    else:
        trend = "ORTA"

    # SHAP top-3
    en_etkili = []
    if shap_path.exists():
        try:
            with open(shap_path, encoding="utf-8") as f:
                shap_data = json.load(f)
            mean_shap = shap_data.get("mean_shap", {})
            shap_sorted = sorted(mean_shap.items(), key=lambda x: x[1], reverse=True)[:3]

            shap_vals_list = shap_data.get("shap_values", [])
            # Most recent sample SHAP values (last row)
            last_shap = shap_vals_list[-1] if shap_vals_list else []

            fn_list = shap_data.get("feature_names", FEATURE_NAMES)
            fn_idx  = {fn: i for i, fn in enumerate(fn_list)}

            for fname, mean_val in shap_sorted:
                yon = "pozitif"
                if last_shap and fname in fn_idx:
                    yon = "pozitif" if last_shap[fn_idx[fname]] >= 0 else "negatif"
                en_etkili.append({"ozellik": fname, "etki": round(mean_val, 4), "yon": yon})
        except Exception:
            pass

    return {
        "tahmini_verim_kg_dekar": round(pred, 1),
        "trakya_ortalama": trakya_ort,
        "yuzde_karsilastirma": pct_comp,
        "guven_araligi": ci,
        "en_etkili_faktorler": en_etkili,
        "risk_analizi": risk,
        "trend": trend,
        "model_metrikleri": meta["metrics"],
        "veri_yili": veri_yili,
        "uyari": uyari,
    }


if __name__ == "__main__":
    print("=" * 55)
    print("  TRAK-AI KDS — XGBoost Verim Tahmini Testi")
    print("=" * 55)

    for crop in ["Wheat", "Sunflower"]:
        crop_tr = "Buğday" if crop == "Wheat" else "Ayçiçeği"
        result  = predict_yield(crop)

        if result.get("hata"):
            print(f"\n{crop_tr}: HATA — {result['hata']}")
            continue

        print(f"\n{crop_tr}:")
        print(f"  Tahmini verim    : {result['tahmini_verim_kg_dekar']:.1f} kg/dekar")
        print(f"  Trakya ortalaması: {result['trakya_ortalama']:.0f} kg/dekar")
        print(f"  Karşılaştırma    : %{result['yuzde_karsilastirma']:+.1f}")
        print(f"  Güven aralığı    : {result['guven_araligi']['alt']:.0f}–{result['guven_araligi']['ust']:.0f} kg/dekar")
        print(f"  Risk             : {result['risk_analizi']}")
        print(f"  Trend            : {result['trend']}")
        m = result["model_metrikleri"]
        print(f"  Model metrikleri : R²={m['r2']:.3f}, MAE={m['mae']:.1f}, RMSE={m['rmse']:.1f}, MAPE={m['mape']:.1f}%")
        if result.get("uyari"):
            print(f"  UYARI            : {result['uyari']}")
        if result["en_etkili_faktorler"]:
            print(f"  Top-3 SHAP faktör:")
            for f in result["en_etkili_faktorler"]:
                print(f"    {f['ozellik']:<25} etki={f['etki']:.4f} ({f['yon']})")
