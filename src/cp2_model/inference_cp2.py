"""
===============================================================================
TRAK-AI KDS  -  WP2: Inference & RAG-LLM Context Generator
===============================================================================
Hybrid model selection: best architecture per crop.
Uses registered custom layers — simple tf.keras.models.load_model().

Run:  python inference_cp2.py
===============================================================================
"""

import os, sys, json, logging, numpy as np, pandas as pd, joblib

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf

# sys.path: cp2_model/ ve src/ her iki modülden de erişilebilsin
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # src/cp2_model/
_SRC_DIR = os.path.dirname(BASE_DIR)                    # src/
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Hava servisi (src/ altında — isteğe bağlı)
try:
    from weather_service import get_current_weather, get_7day_forecast, get_weather_alerts
    _WEATHER_AVAILABLE = True
except ImportError:
    _WEATHER_AVAILABLE = False

# Custom layer kaydı — model yüklemeden önce yapılmalı
try:
    from train_models_cp2 import SelfAttention, ExtractLastNDVI, ScaleDelta, _ndvi_idx
except ImportError as _e:
    logging.getLogger("trak-ai.inference").warning("Custom layer import failed: %s", _e)
    def _ndvi_idx():
        return -1

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("trak-ai.inference")

PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
CSV_PATH = os.path.join(
    PROJECT_ROOT, "data", "processed", "master_feature_matrix_2017_2024.csv"
)
FIELD_SUMMARY_DAYS = 15

# Hybrid config: best model per crop (ordered by priority)
CROP_CONFIG = {
    "Wheat": dict(
        model_files=[
            "model_convlstm_wheat.keras",
            "model_lstm_wheat.keras",
            "model_attention_lstm_wheat.keras",
        ],
        scaler="scaler_wheat.pkl",
        test_data="X_wheat.npy",
        label="Wheat",
        best_arch="Conv-LSTM (residual delta)",
    ),
    "Sunflower": dict(
        model_files=[
            "model_lstm_sunflower.keras",
            "model_attention_lstm_sunflower.keras",
            "model_convlstm_sunflower.keras",
        ],
        scaler="scaler_sunflower.pkl",
        test_data="X_sunflower.npy",
        label="Sunflower",
        best_arch="LSTM (residual delta)",
    ),
}


def classify_ndvi(v):
    if v < 0.15:
        return dict(status="CRITICAL",
                    desc="Very weak or damaged vegetation",
                    action="Immediate field inspection required")
    if v < 0.25:
        return dict(status="LOW",
                    desc="Stress indicators present",
                    action="Investigate drought, disease, or nutrient deficiency")
    if v < 0.40:
        return dict(status="MODERATE",
                    desc="Below-average health",
                    action="Monitor closely, consider irrigation or fertilization")
    if v < 0.55:
        return dict(status="FAIR",
                    desc="Acceptable vegetation health",
                    action="Continue standard management")
    if v < 0.70:
        return dict(status="GOOD",
                    desc="Healthy vegetation cover",
                    action="Maintain current practices")
    return dict(status="EXCELLENT",
                desc="Dense and vigorous vegetation",
                action="Optimal conditions")


def classify_trend(current, predicted):
    delta = predicted - current
    pct = (delta / max(abs(current), 0.01)) * 100
    if delta < -0.08:
        return dict(trend="DECLINING", delta=round(delta, 4),
                    pct_change=round(pct, 1),
                    alert="Significant decline expected in 7 days")
    if delta < -0.03:
        return dict(trend="SLIGHT_DECLINE", delta=round(delta, 4),
                    pct_change=round(pct, 1),
                    alert="Minor decline expected, monitor conditions")
    if delta > 0.05:
        return dict(trend="GROWING", delta=round(delta, 4),
                    pct_change=round(pct, 1),
                    alert="Healthy growth trajectory")
    return dict(trend="STABLE", delta=round(delta, 4),
                pct_change=round(pct, 1),
                alert="Stable conditions expected")


def get_field_summary(csv_path=CSV_PATH):
    if not os.path.exists(csv_path):
        return "Field data unavailable."
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return "Field data read error."
    needed = ["tp_sum", "t2m_max", "t2m_min", "ssr_sum"]
    if any(c not in df.columns for c in needed):
        return "Incomplete field data."
    last = df.tail(FIELD_SUMMARY_DAYS)
    return (
        f"Last {FIELD_SUMMARY_DAYS} Days: "
        f"Precip={last['tp_sum'].sum():.1f}mm, "
        f"Max Temp={last['t2m_max'].mean():.1f}C, "
        f"Min Temp={last['t2m_min'].mean():.1f}C, "
        f"Solar Rad={last['ssr_sum'].mean():.0f} J/m2."
    )


def predict(crop_type, live_data=None, field_summary=None):
    """
    7-day NDVI forecast with health classification.

    Parameters
    ----------
    crop_type    : 'Wheat' or 'Sunflower'
    live_data    : numpy array (1, 30, 17). None = test mode.
    field_summary: pre-computed string. None = auto-compute.

    Returns
    -------
    dict with: crop, model_used, architecture, current_ndvi, predicted_ndvi,
               health, trend, data_source, field_summary, llm_context
    """
    if crop_type not in CROP_CONFIG:
        raise ValueError(
            f"Unknown crop: '{crop_type}'. Valid: {list(CROP_CONFIG.keys())}"
        )

    cfg = CROP_CONFIG[crop_type]

    # Load best available model (priority order)
    model, model_file = None, None
    for mf in cfg["model_files"]:
        path = os.path.join(BASE_DIR, mf)
        if os.path.exists(path):
            try:
                model = tf.keras.models.load_model(path)
                model_file = mf
                break
            except Exception as e:
                logger.warning("Could not load %s: %s", mf, e)

    if model is None:
        raise FileNotFoundError(f"No model found for {crop_type}")

    # Load scaler and feature info
    scaler = joblib.load(os.path.join(BASE_DIR, cfg["scaler"]))
    ndvi_idx = _ndvi_idx()

    # Prepare input
    if live_data is not None:
        inp, source = live_data, "live_sensor_data"
    else:
        X = np.load(os.path.join(BASE_DIR, cfg["test_data"]))
        inp, source = X[-1:], "test_data_last_window"
        logger.warning("No live data — using last training window (test mode)")

    # Predict and inverse scale
    raw = float(model.predict(inp, verbose=0)[0][0])
    pred_scaled = float(np.clip(raw, 0, 1))

    ndvi_min = scaler.data_min_[ndvi_idx]
    ndvi_range = scaler.data_range_[ndvi_idx]
    pred_real = float(np.clip(pred_scaled * ndvi_range + ndvi_min, -1, 1))
    current_real = float(inp[0, -1, ndvi_idx] * ndvi_range + ndvi_min)

    # Classify
    health = classify_ndvi(pred_real)
    trend = classify_trend(current_real, pred_real)

    if field_summary is None:
        field_summary = get_field_summary()

    # LLM context for WP4 RAG pipeline
    llm_context = (
        f"TRAK-AI KDS 7-Day Forecast for {cfg['label']}:\n"
        f"- Model: {cfg['best_arch']}\n"
        f"- Current NDVI: {current_real:.4f}\n"
        f"- Predicted NDVI (t+7): {pred_real:.4f}\n"
        f"- Health Status: {health['status']} — {health['desc']}\n"
        f"- Trend: {trend['trend']} ({trend['delta']:+.4f}, "
        f"{trend['pct_change']:+.1f}%)\n"
        f"- Alert: {trend['alert']}\n"
        f"- Recommended Action: {health['action']}\n"
        f"- {field_summary}"
    )

    # Hava verisi (isteğe bağlı — başarısız olursa None)
    weather_current, weather_forecast, weather_alerts = None, None, None
    if _WEATHER_AVAILABLE:
        try:
            weather_current = get_current_weather()
            weather_forecast = get_7day_forecast()
            weather_alerts = get_weather_alerts(weather_forecast) if weather_forecast else []
        except Exception as e:
            logger.warning("Hava servisi alınamadı: %s", e)

    return dict(
        crop=cfg["label"],
        model_used=model_file,
        architecture=cfg["best_arch"],
        current_ndvi=round(current_real, 4),
        predicted_ndvi=round(pred_real, 4),
        health=health,
        trend=trend,
        data_source=source,
        field_summary=field_summary,
        llm_context=llm_context,
        weather_current=weather_current,
        weather_forecast=weather_forecast,
        weather_alerts=weather_alerts,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  TRAK-AI KDS — Inference (Hybrid Model Selection)")
    print("=" * 60)

    summary = get_field_summary()

    for crop in CROP_CONFIG:
        print(f"\n{'─' * 60}")
        try:
            r = predict(crop, field_summary=summary)
            print(f"  Crop           : {r['crop']}")
            print(f"  Architecture   : {r['architecture']}")
            print(f"  Model File     : {r['model_used']}")
            print(f"  Current NDVI   : {r['current_ndvi']:.4f}")
            print(f"  Predicted NDVI : {r['predicted_ndvi']:.4f} (t+7)")
            print(f"  Health         : {r['health']['status']} — "
                  f"{r['health']['desc']}")
            print(f"  Trend          : {r['trend']['trend']} "
                  f"({r['trend']['delta']:+.4f}, "
                  f"{r['trend']['pct_change']:+.1f}%)")
            print(f"  Alert          : {r['trend']['alert']}")
            print(f"  Action         : {r['health']['action']}")
            print(f"  Data Source    : {r['data_source']}")
            print(f"\n  LLM Context:")
            for line in r["llm_context"].split("\n"):
                print(f"    {line}")
        except Exception as e:
            logger.error("[%s] %s", crop, e)

    print(f"\n{'=' * 60}")
    print("  Inference complete. Ready for RAG-LLM (WP4).")


# ─────────────────────────────────────────────────────────────────────
# ÇP-2.5 v2 — Verim Tahmin Köprüsü (NDVI → kg/da)
# ─────────────────────────────────────────────────────────────────────
"""Mevcut ``predict()`` ile yan yana koşar, dokunmaz.

Public API:
    predict_yield_kg_da(crop_type, ndvi_predicted=None, il=None,
                        ilce_id=None, feature_context=None,
                        current_date=None) -> dict

Bundle önceliği:  champion_{crop}.pkl → layer_c → layer_b → layer_a
"""
import pickle as _pickle

_CP25_MODELS_DIR = os.path.join(PROJECT_ROOT, "models", "cp25")
_CP25_BUNDLE_CACHE: dict = {}


def _load_cp25_champion(crop_short: str):
    if crop_short in _CP25_BUNDLE_CACHE:
        return _CP25_BUNDLE_CACHE[crop_short]
    for fname in (f"champion_{crop_short}.pkl",
                  f"layer_c_{crop_short}.pkl",
                  f"layer_b_{crop_short}.pkl",
                  f"layer_a_{crop_short}.pkl"):
        p = os.path.join(_CP25_MODELS_DIR, fname)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                bundle = _pickle.load(fh)
            _CP25_BUNDLE_CACHE[crop_short] = bundle
            logger.info("[cp25] loaded %s for %s", fname, crop_short)
            return bundle
    raise FileNotFoundError(
        f"ÇP-2.5 v2 bundle yok ({crop_short}). "
        "`python src/cp25/12_final_synthesis.py` çalıştırın.")


def _cp25_lookup_22yr_mean(il, crop_short, ilce_id=None):
    """22-yıl TÜİK ortalaması: ilçe varsa exact, yoksa il ortalaması."""
    try:
        crop_full = "bugday" if crop_short == "bugday" else "aycicegi_yaglik"
        il_df = pd.read_csv(os.path.join(PROJECT_ROOT, "data", "external",
                                          "tuik", "ilce_yield_stats.csv"))
        # Önce ilçe spesifik
        if ilce_id is not None:
            row = il_df[(il_df["ilce_id"] == int(ilce_id)) &
                         (il_df["crop"] == crop_full)]
            if not row.empty:
                return float(row["mean_kg_da"].iloc[0])
        # Sonra il-genel
        if il:
            row = il_df[(il_df["il"] == il) & (il_df["crop"] == crop_full)]
            if not row.empty:
                return float(row["mean_kg_da"].mean())
        # Fallback: tüm Trakya ortalaması
        crop_all = il_df[il_df["crop"] == crop_full]
        return float(crop_all["mean_kg_da"].mean()) if not crop_all.empty else None
    except Exception:
        return None


def _cp25_interpret_sapma(d):
    if d > 15:  return "Beklenenin üstünde verim — verimli sezon"
    if d > 5:   return "Hafifçe ortalamanın üstünde"
    if d > -5:  return "Ortalama yakınında"
    if d > -15: return "Hafif düşüş — risk izlenmeli"
    if d > -25: return "Belirgin düşüş — sulama/girdi gözden geçirilmeli"
    return "Kritik düşüş — kuraklık veya stres sinyali"


def _cp25_fallback_perm_imp(crop_short):
    try:
        for layer in ("C", "B", "A"):
            p = os.path.join(PROJECT_ROOT, "reports", "cp25",
                              f"08_perm_importance_{layer}_{crop_short}.csv")
            if os.path.exists(p):
                df = pd.read_csv(p)
                return [(str(r["feature"]), float(r["imp_mean"]))
                        for _, r in df.head(3).iterrows()]
    except Exception:
        pass
    return []


def _cp25_build_default_context(crop, ndvi):
    """Eksik feature'lar için varsayılan değerler (climatology proxy)."""
    return {
        # Climate
        "gdd_cum_season": 1800, "gdd_flowering": 350,
        "vernalization_days": 60 if crop == "bugday" else 0,
        "tp_season_sum": 350, "tp_winter_sum": 200 if crop == "bugday" else 0,
        "tp_flowering": 30, "tp_grain_fill": 25,
        "aridity_index": 0.5, "heat_stress_days": 10,
        "t2m_flowering_mean": 18, "t2m_flowering_max": 25, "tdiff_mean": 12,
        "ssr_flowering_sum": 5500, "ssr_season_sum": 35000,
        # NDVI
        "ndvi_max": float(ndvi) if ndvi else 0.6,
        "ndvi_mean_season": float(ndvi) * 0.7 if ndvi else 0.4,
        "ndvi_integral": float(ndvi) * 80 if ndvi else 40,
        "ndvi_flowering": float(ndvi) if ndvi else 0.55,
        "ndvi_grain_fill": float(ndvi) * 0.8 if ndvi else 0.45,
        "ndvi_spring_slope": 0.005, "greenness_days": 80,
        # Soil (Trakya ortalaması)
        "clay_0-5cm": 30.0, "sand_0-5cm": 31.6, "silt_0-5cm": 38.4,
        "phh2o_0-5cm": 6.92, "soc_0-5cm": 4.28, "awc_0-5cm": 0.215,
    }


def predict_yield_kg_da(crop_type: str,
                         ndvi_predicted: float = None,
                         il: str = None,
                         ilce_id: int = None,
                         feature_context=None,
                         current_date=None) -> dict:
    """ÇP-2 NDVI t+7 → ÇP-2.5 v2 verim tahmini (kg/dekar + PI + sapma).

    Args:
        crop_type: 'Wheat'/'Sunflower' (ÇP-2 contract) ya da 'bugday'/'aycicegi_yaglik'.
        ndvi_predicted: ÇP-2 ``predict()`` çıktısından NDVI t+7.
        il: 'Edirne'/'Kırklareli'/'Tekirdağ'.
        ilce_id: TÜİK ilçe id (per-ilçe bias correction için).
        feature_context: dict — sezonluk climate+NDVI+soil features.
            None ise climatology proxy ile doldurulur.
        current_date: Tahmin anı (sezon ilerleme % hesabı).

    Returns:
        {yield_kg_da, yield_kg_da_lower, yield_kg_da_upper,
         lokal_22yil_ortalama, sapma_pct, sapma_yorum,
         top_3_features, champion_model, layer, model_version}
    """
    ct = crop_type.lower()
    crop_short = "bugday" if ct.startswith(("w", "b")) else "aycicegi"
    bundle = _load_cp25_champion(crop_short)

    if feature_context is None or isinstance(feature_context, dict) and not feature_context:
        feature_context = _cp25_build_default_context(crop_short, ndvi_predicted)
    elif hasattr(feature_context, "iloc"):
        feature_context = feature_context.iloc[0].to_dict()

    if ndvi_predicted is not None:
        feature_context.setdefault("ndvi_max", float(ndvi_predicted))

    feats = bundle["feature_cols"]
    X_row = {f: float(feature_context.get(f, 0.0)) for f in feats}
    X_df = pd.DataFrame([X_row], columns=feats)
    if bundle.get("scaler") is not None:
        X_use = bundle["scaler"].transform(X_df)
    else:
        X_use = X_df.values

    try:
        yhat = float(bundle["model"].predict(X_use)[0])
    except Exception as exc:
        # Model array shape mismatch fallback — flatten + retry
        logger.warning("[cp25] predict fallback: %s", exc)
        yhat = float(bundle["model"].predict(X_df.values)[0])

    bias = bundle.get("per_il_bias_correction_kg_da", {}).get(il, 0.0)
    yhat_corr = yhat + float(bias)

    rmse = float(bundle["metrics_loyo"]["rmse_kg_da"])
    half = 1.96 * rmse
    pi_lower, pi_upper = yhat_corr - half, yhat_corr + half

    stats_mean = _cp25_lookup_22yr_mean(il, crop_short, ilce_id=ilce_id)
    sapma_pct = (((yhat_corr - stats_mean) / stats_mean) * 100
                 if stats_mean else None)
    yorum = _cp25_interpret_sapma(sapma_pct or 0)

    shap_imp = bundle.get("feature_importance_shap")
    top3 = ([(k, float(v)) for k, v in list(shap_imp.items())[:3]]
            if shap_imp else _cp25_fallback_perm_imp(crop_short))

    return {
        "yield_kg_da":           round(yhat_corr, 1),
        "yield_kg_da_lower":     round(pi_lower, 1),
        "yield_kg_da_upper":     round(pi_upper, 1),
        "lokal_22yil_ortalama":  stats_mean,
        "sapma_pct":             round(sapma_pct, 1) if sapma_pct is not None else None,
        "sapma_yorum":           yorum,
        "top_3_features":        top3,
        "champion_model":        bundle["champion_name"],
        "layer":                 bundle["model_version"].split("layer")[-1].upper()
                                  if "layer" in bundle["model_version"] else "?",
        "model_version":         bundle["model_version"],
    }


__all__ = ["predict", "get_field_summary", "predict_yield_kg_da"]