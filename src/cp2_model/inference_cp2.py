"""
===============================================================================
TRAK-AI KDS  -  WP2: Inference & RAG-LLM Context Generator
===============================================================================
Hybrid model selection: best architecture per crop.
Uses registered custom layers — simple tf.keras.models.load_model().

Run:  python inference_cp2.py
===============================================================================
"""

import os, json, logging, numpy as np, pandas as pd, joblib

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf

# Import registered custom layers so Keras can find them
from train_models_cp2 import SelfAttention, ExtractLastNDVI, ScaleDelta, _ndvi_idx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("trak-ai.inference")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
    print(f"{'=' * 60}\n")