"""
===============================================================================
TRAK-AI KDS  -  WP2: Model Evaluation & Explainability
===============================================================================
Loads all 8 models, computes metrics, generates plots and SHAP analysis.
Uses registered custom layers from train_models_cp2 — simple load_model().

Run:  python evaluate_cp2.py
===============================================================================
"""

import os, json, numpy as np, pandas as pd, joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Import registered custom layers so Keras can find them during load
from train_models_cp2 import SelfAttention, ExtractLastNDVI, ScaleDelta, _ndvi_idx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
PLOTS_DIR = os.path.join(PROJECT_ROOT, "docs", "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)
TEST_RATIO = 0.2


def load_all(prefix):
    """Load data, all models, and scaler for one crop."""
    X = np.load(os.path.join(BASE_DIR, f"X_{prefix}.npy"))
    y = np.load(os.path.join(BASE_DIR, f"y_{prefix}.npy"))
    X_xgb = np.load(os.path.join(BASE_DIR, f"X_xgb_{prefix}.npy"))
    scaler = joblib.load(os.path.join(BASE_DIR, f"scaler_{prefix}.pkl"))

    ndvi_idx = _ndvi_idx()
    s = int(len(X) * (1 - TEST_RATIO))

    data = dict(
        X_val=X[s:], y_val=y[s:], X_xgb_val=X_xgb[s:],
        X_train_xgb=X_xgb[:s],
        last_ndvi_val=X[s:, -1, ndvi_idx],
        ndvi_idx=ndvi_idx,
    )

    # Keras models — simple load, no hacks needed
    keras_files = [
        ("Attention-LSTM", f"model_attention_lstm_{prefix}.keras"),
        ("Conv-LSTM",      f"model_convlstm_{prefix}.keras"),
        ("LSTM",           f"model_lstm_{prefix}.keras"),
    ]
    models = {}
    for name, fname in keras_files:
        path = os.path.join(BASE_DIR, fname)
        if os.path.exists(path):
            try:
                models[name] = tf.keras.models.load_model(path)
                print(f"   [OK] {name}")
            except Exception as e:
                print(f"   [WARN] {name}: {e}")

    # XGBoost
    xgb_path = os.path.join(BASE_DIR, f"model_xgb_{prefix}.pkl")
    if os.path.exists(xgb_path):
        models["XGBoost"] = joblib.load(xgb_path)
        print(f"   [OK] XGBoost")

    return data, models, scaler


def compute_metrics(y_true, y_pred, scaler, ndvi_idx):
    """Metrics in both scaled (0-1) and real NDVI space."""
    y_pred = np.clip(y_pred, 0, 1)
    mse  = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)

    ndvi_min   = scaler.data_min_[ndvi_idx]
    ndvi_range = scaler.data_range_[ndvi_idx]
    yt_real = y_true * ndvi_range + ndvi_min
    yp_real = y_pred * ndvi_range + ndvi_min

    return {
        "R2":            round(r2, 4),
        "RMSE (NDVI)":   round(np.sqrt(mean_squared_error(yt_real, yp_real)), 4),
        "MAE (NDVI)":    round(mean_absolute_error(yt_real, yp_real), 4),
        "RMSE (scaled)": round(rmse, 6),
        "MAE (scaled)":  round(mae, 6),
        "MSE (scaled)":  round(mse, 6),
    }


def get_predictions(models, data):
    """Get predictions from all models. XGBoost predicts delta."""
    preds = {}
    for name, model in models.items():
        if name == "XGBoost":
            delta = model.predict(data["X_xgb_val"])
            yp = data["last_ndvi_val"] + delta
        else:
            yp = model.predict(data["X_val"], verbose=0).flatten()
        preds[name] = np.clip(yp, 0, 1)
    return preds


def plot_predictions(y_true, preds, crop, scaler, ndvi_idx):
    """Actual vs predicted plot for each model."""
    ndvi_min   = scaler.data_min_[ndvi_idx]
    ndvi_range = scaler.data_range_[ndvi_idx]
    y_real = y_true * ndvi_range + ndvi_min

    colors = {
        "Attention-LSTM": "#534AB7",
        "Conv-LSTM":      "#D85A30",
        "LSTM":           "#1D9E75",
        "XGBoost":        "#BA7517",
    }

    n = len(preds)
    fig, axes = plt.subplots(n, 1, figsize=(14, 3.5 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, (name, yp) in zip(axes, preds.items()):
        yp_real = yp * ndvi_range + ndvi_min
        ax.plot(y_real, color="black", lw=1.2, alpha=0.7, label="Actual")
        ax.plot(yp_real, color=colors.get(name, "blue"), lw=1.2,
                alpha=0.85, label=name)
        ax.fill_between(range(len(y_real)), y_real, yp_real,
                        alpha=0.12, color="red")
        ax.set_ylabel("NDVI")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)
        ax.set_title(f"{crop} — {name} (7-day forecast)", fontweight="bold")

    axes[-1].set_xlabel("Validation Sample Index")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"{crop.lower()}_prediction_vs_actual.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"   [SAVED] {path}")


def plot_shap(model, X_val, prefix, crop):
    """SHAP feature importance for XGBoost."""
    try:
        import shap
    except ImportError:
        print("   [SKIP] SHAP not installed")
        return

    feat_path = os.path.join(BASE_DIR, f"xgb_feature_names_{prefix}.json")
    if not os.path.exists(feat_path):
        return

    with open(feat_path) as f:
        names = json.load(f)

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X_val[:200])
    plt.figure(figsize=(12, 8))
    shap.summary_plot(sv, X_val[:200], feature_names=names,
                      max_display=20, show=False)
    plt.title(f"{crop} — XGBoost SHAP Feature Importance", fontweight="bold")
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, f"{crop.lower()}_xgb_shap_summary.png")
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"   [SAVED] {path}")


def main():
    print("=" * 60)
    print("  TRAK-AI KDS — WP2 Model Evaluation")
    print("=" * 60)

    crops = [
        dict(label="Wheat",     prefix="wheat"),
        dict(label="Sunflower", prefix="sunflower"),
    ]
    all_metrics = []

    for crop in crops:
        lbl, pfx = crop["label"], crop["prefix"]
        print(f"\n{'─' * 60}")
        print(f"  Evaluating: {lbl}")
        print(f"{'─' * 60}")

        data, models, scaler = load_all(pfx)

        # Naive baseline
        naive_r2 = r2_score(data["y_val"], data["last_ndvi_val"])
        print(f"   Naive baseline R2: {naive_r2:.4f}")

        # Predictions and metrics
        preds = get_predictions(models, data)

        for name, yp in preds.items():
            m = compute_metrics(data["y_val"], yp, scaler, data["ndvi_idx"])
            m["Crop"]  = lbl
            m["Model"] = name
            all_metrics.append(m)

            beat = "BEATS" if m["R2"] > naive_r2 else "below"
            print(f"   {name:<20} R2={m['R2']:.4f}  "
                  f"RMSE(NDVI)={m['RMSE (NDVI)']:.4f}  "
                  f"MAE(NDVI)={m['MAE (NDVI)']:.4f}  [{beat} naive]")

        # Plots
        plot_predictions(data["y_val"], preds, lbl, scaler, data["ndvi_idx"])

        if "XGBoost" in models:
            plot_shap(models["XGBoost"], data["X_xgb_val"], pfx, lbl)

    # Save comparison table
    df = pd.DataFrame(all_metrics)
    cols = ["Crop", "Model", "R2", "RMSE (NDVI)", "MAE (NDVI)",
            "RMSE (scaled)", "MAE (scaled)", "MSE (scaled)"]
    df = df[cols]
    csv_path = os.path.join(PLOTS_DIR, "model_comparison_table.csv")
    df.to_csv(csv_path, index=False)

    print(f"\n{'=' * 60}")
    print("  EVALUATION COMPLETE")
    print(f"{'=' * 60}")
    print(df.to_string(index=False))
    print(f"\n   Plots: {PLOTS_DIR}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()