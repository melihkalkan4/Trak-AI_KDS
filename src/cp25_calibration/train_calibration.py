"""ÇP-2.5 — NDVI→Verim kalibrasyon modeli eğitimi.

3 model yarıştırır (Ridge, GBR, RF), LOOCV (Leave-One-Out CV) ile
out-of-sample tahminleri toplar, en düşük RMSE'li modeli şampiyon seçer,
SHAP analizi yapar, final modeli tüm veride yeniden eğitir ve serileştirir.

Akademik kurallar
-----------------
* Örneklem küçük (n=21 buğday, n=24 ayçiçeği) → ``LeaveOneOut`` zorunlu.
* ``il`` kategorik feature **one-hot** (3 dummy) — Vize centroid proxy
  feature'larıyla aynı satıra eklenir.  Bu, il-arası sistematik ofseti
  öğrenmek için tek mekanizmadır (feature'lar 3 il için aynı olduğundan).
* Ridge alpha grid: {0.1, 1.0, 10.0, 100.0} — küçük örneklemde shrinkage
  agresif.  GBR/RF default-civarı, max_depth=3 (overfitting önlemi).
* Onurlu başarı kriterleri (Kern et al. 2018 referansı):
    * buğday  : R² ≥ 0.45  ve  MAE ≤ 55 kg/da
    * ayçiçeği: R² ≥ 0.45  ve  MAE ≤ 35 kg/da
* SHAP yalnız tree-based modellerde (GBR/RF) hesaplanır.

Çıktılar
--------
* ``models/cp25_calibration_{crop}.pkl``       (champion bundle)
* ``reports/cp25_calibration_{crop}_shap.png``
* ``reports/cp25_calibration_metrics.json``    (her crop için tüm modeller)
* ``reports/cp25_loocv_predictions_{crop}.csv``
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import (mean_absolute_error, mean_absolute_percentage_error,
                             mean_squared_error, r2_score)
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

logger = logging.getLogger("trakai.cp25.train")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR     = PROJECT_ROOT / "data" / "processed"
MODELS_DIR   = PROJECT_ROOT / "models"
REPORTS_DIR  = PROJECT_ROOT / "reports"

FEATURE_COLS_BASE = [
    "ndvi_max", "ndvi_mean", "ndvi_integral",
    "ndvi_flowering", "ndvi_grain_fill", "greenness_days",
    "gdd_cum_season", "tp_season_sum",
    "ndwi_min_flowering", "t2m_max_flowering_mean",
]
IL_DUMMY_COLS = ["il_Edirne", "il_Kirklareli", "il_Tekirdag"]

# Honest success thresholds (Kern et al. 2018 + Trakya-specific calibration)
SUCCESS = {
    "bugday":          {"r2": 0.45, "mae_kg_da": 55.0},
    "aycicegi_yaglik": {"r2": 0.45, "mae_kg_da": 35.0},
}


# ----------------------------------------------------------------------------
@dataclass
class ModelResult:
    name: str
    metrics: dict
    loocv_preds: np.ndarray = field(default_factory=lambda: np.array([]))
    feature_importance: Optional[dict] = None


def _onehot_il(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot ``il`` into 3 stable columns (consistent ordering)."""
    mapping = {"Edirne": "il_Edirne",
               "Kırklareli": "il_Kirklareli",
               "Tekirdağ": "il_Tekirdag"}
    out = df.copy()
    for col in IL_DUMMY_COLS:
        out[col] = 0
    for src_il, dst_col in mapping.items():
        out.loc[out["il"] == src_il, dst_col] = 1
    return out


def _prepare_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Build the standardised feature matrix X and label vector y."""
    df = _onehot_il(df)
    cols = FEATURE_COLS_BASE + IL_DUMMY_COLS
    X = df[cols].astype(float)
    # Defensive: median-impute on the rare cell that came out as NaN
    X = X.fillna(X.median(numeric_only=True))
    y = df["yield_kg_da"].astype(float).values
    return X, y, cols


def _loocv_metrics(model_factory, X: pd.DataFrame, y: np.ndarray,
                   *, with_scaler: bool) -> tuple[np.ndarray, dict]:
    """Run LOOCV and return (preds, metrics).  Re-fits a fresh model+scaler
    each fold so no information leaks across folds.
    """
    preds = np.zeros_like(y, dtype=float)
    loo = LeaveOneOut()
    for tr_idx, te_idx in loo.split(X):
        X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
        y_tr = y[tr_idx]
        if with_scaler:
            scaler = StandardScaler().fit(X_tr)
            X_tr_s = scaler.transform(X_tr)
            X_te_s = scaler.transform(X_te)
        else:
            X_tr_s, X_te_s = X_tr.values, X_te.values
        m = model_factory()
        m.fit(X_tr_s, y_tr)
        preds[te_idx] = m.predict(X_te_s)

    metrics = {
        "r2":   float(r2_score(y, preds)),
        "mae_kg_da":  float(mean_absolute_error(y, preds)),
        "rmse_kg_da": float(np.sqrt(mean_squared_error(y, preds))),
        "mape_pct":   float(mean_absolute_percentage_error(y, preds) * 100),
        "n_samples":  int(len(y)),
        "mean_y":     float(np.mean(y)),
        "std_y":      float(np.std(y, ddof=1)),
    }
    return preds, metrics


# ----------------------------------------------------------------------------
def _ridge_with_grid(X: pd.DataFrame, y: np.ndarray) -> ModelResult:
    """Ridge with alpha grid search (best alpha by LOOCV RMSE)."""
    best = None
    grid = [0.1, 1.0, 10.0, 100.0]
    for alpha in grid:
        preds, metrics = _loocv_metrics(lambda a=alpha: Ridge(alpha=a),
                                        X, y, with_scaler=True)
        cand = ModelResult(name=f"Ridge(alpha={alpha})",
                           metrics={**metrics, "alpha": alpha},
                           loocv_preds=preds)
        if best is None or cand.metrics["rmse_kg_da"] < best.metrics["rmse_kg_da"]:
            best = cand
    assert best is not None
    return best


def _gbr() -> ModelResult:
    def _f():
        return GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42)
    # GBR doesn't need scaling — but we keep parity for fair comparison.
    return _run_named("GradientBoostingRegressor", _f, with_scaler=False)


def _rf() -> ModelResult:
    def _f():
        return RandomForestRegressor(
            n_estimators=300, max_depth=5, random_state=42, n_jobs=-1)
    return _run_named("RandomForestRegressor", _f, with_scaler=False)


def _run_named(name: str, factory, *, with_scaler: bool):
    # Closed-over X, y are set by the caller via partial-style binding below
    raise NotImplementedError  # placeholder; we'll bind X,y manually


# We can't use closure easily; rewrite cleanly:
def _gbr_with_loocv(X, y) -> ModelResult:
    def _f():
        return GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42)
    preds, metrics = _loocv_metrics(_f, X, y, with_scaler=False)
    return ModelResult(name="GradientBoostingRegressor", metrics=metrics, loocv_preds=preds)


def _rf_with_loocv(X, y) -> ModelResult:
    def _f():
        return RandomForestRegressor(
            n_estimators=300, max_depth=5, random_state=42, n_jobs=-1)
    preds, metrics = _loocv_metrics(_f, X, y, with_scaler=False)
    return ModelResult(name="RandomForestRegressor", metrics=metrics, loocv_preds=preds)


# ----------------------------------------------------------------------------
def _choose_champion(results: list[ModelResult]) -> ModelResult:
    """Pick the model with the lowest LOOCV RMSE."""
    return min(results, key=lambda r: r.metrics["rmse_kg_da"])


def _fit_final(champion_name: str, X: pd.DataFrame, y: np.ndarray):
    """Re-fit the champion on ALL data and return (model, scaler)."""
    if champion_name.startswith("Ridge"):
        alpha = float(champion_name.split("alpha=")[1].rstrip(")"))
        scaler = StandardScaler().fit(X)
        model = Ridge(alpha=alpha).fit(scaler.transform(X), y)
        return model, scaler
    if champion_name == "GradientBoostingRegressor":
        return (GradientBoostingRegressor(n_estimators=200, max_depth=3,
                                          learning_rate=0.05, random_state=42)
                .fit(X.values, y), None)
    if champion_name == "RandomForestRegressor":
        return (RandomForestRegressor(n_estimators=300, max_depth=5,
                                      random_state=42, n_jobs=-1)
                .fit(X.values, y), None)
    raise ValueError(f"Unknown champion: {champion_name}")


def _shap_plot(model, X: pd.DataFrame, out_path: Path) -> Optional[dict]:
    """SHAP summary plot for tree-based models.  Returns importance dict."""
    if not hasattr(model, "estimators_") and not hasattr(model, "tree_"):
        logger.info("skipping SHAP: %s is not tree-based", type(model).__name__)
        return None
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X.values)
        plt.figure(figsize=(8, 5))
        shap.summary_plot(shap_values, X, show=False, plot_size=None)
        plt.tight_layout()
        plt.savefig(out_path, dpi=120)
        plt.close()
        mean_abs = np.abs(shap_values).mean(axis=0)
        return dict(sorted(
            zip(X.columns, mean_abs.tolist()), key=lambda kv: -kv[1]))
    except Exception as exc:                                       # noqa: BLE001
        logger.warning("SHAP failed: %s", exc)
        return None


# ----------------------------------------------------------------------------
def train_one_crop(crop_short: str, crop_full: str) -> dict:
    df_path = DATA_DIR / f"calibration_train_set_{crop_short}.csv"
    df = pd.read_csv(df_path)
    logger.info("[%s] loaded %s n=%d", crop_short, df_path.name, len(df))

    X, y, cols = _prepare_xy(df)

    # ---- Train all candidates ----
    results: list[ModelResult] = [
        _ridge_with_grid(X, y),
        _gbr_with_loocv(X, y),
        _rf_with_loocv(X, y),
    ]
    for r in results:
        logger.info("[%s] %s  R²=%+.3f  MAE=%5.1f  RMSE=%5.1f  MAPE=%4.1f%%",
                    crop_short, r.name,
                    r.metrics["r2"], r.metrics["mae_kg_da"],
                    r.metrics["rmse_kg_da"], r.metrics["mape_pct"])

    champion = _choose_champion(results)
    logger.info("[%s] CHAMPION → %s", crop_short, champion.name)

    # ---- Honest success check ----
    thr = SUCCESS[crop_full]
    success = (champion.metrics["r2"] >= thr["r2"] and
               champion.metrics["mae_kg_da"] <= thr["mae_kg_da"])
    logger.info("[%s] success criteria (R²≥%.2f & MAE≤%.0f): %s",
                crop_short, thr["r2"], thr["mae_kg_da"],
                "PASS" if success else "FAIL — limitations apply")

    # ---- Final fit on all data ----
    final_model, scaler = _fit_final(champion.name, X, y)

    # ---- SHAP (tree models) ----
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    shap_path = REPORTS_DIR / f"cp25_calibration_{crop_short}_shap.png"
    feature_importance = _shap_plot(final_model, X, shap_path)

    # ---- Serialise champion bundle ----
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "model": final_model,
        "scaler": scaler,
        "feature_cols": cols,
        "champion_name": champion.name,
        "metrics_loocv": champion.metrics,
        "metrics_all_candidates": [
            {"name": r.name, "metrics": r.metrics} for r in results],
        "success_criteria": thr,
        "success": success,
        "feature_importance_shap": feature_importance,
        "crop": crop_full,
        "n_samples": len(y),
        "train_years": sorted(df["year"].unique().tolist()),
        "iller": sorted(df["il"].unique().tolist()),
        "train_date_utc": datetime.now(timezone.utc).isoformat(),
        "model_version": "cp25-v1.0",
        "limitations": [
            "Features derived from a single centroid (Vize, Kırklareli ilçesi). "
            "Per-province feature variation is artificially zero — only `il` "
            "one-hot dummies absorb between-province systematic offset.",
            "Sample size n=21 (bugday) / n=24 (aycicegi) — LOOCV used. "
            "External-test only on 2025 (n=3 per crop, held out).",
            "Pre-2017 TÜİK rows excluded (no MFM coverage).",
        ],
    }
    bundle_path = MODELS_DIR / f"cp25_calibration_{crop_short}.pkl"
    with bundle_path.open("wb") as fh:
        pickle.dump(bundle, fh)
    logger.info("[%s] bundle saved → %s", crop_short, bundle_path.name)

    # ---- LOOCV predictions CSV (truth vs predicted) ----
    pred_df = df.copy()
    pred_df["yield_pred_loocv"] = champion.loocv_preds
    pred_df["abs_error"] = (pred_df["yield_kg_da"] - pred_df["yield_pred_loocv"]).abs()
    pred_df.to_csv(REPORTS_DIR / f"cp25_loocv_predictions_{crop_short}.csv",
                   index=False)

    # ---- Per-il bias correction (computed from training residuals) ----
    bias_table = (pred_df.groupby("il")
                  .apply(lambda g: (g["yield_kg_da"] - g["yield_pred_loocv"]).mean())
                  .to_dict())
    bundle["per_il_bias_correction_kg_da"] = bias_table
    with bundle_path.open("wb") as fh:
        pickle.dump(bundle, fh)

    return {
        "crop":          crop_short,
        "champion":      champion.name,
        "metrics":       champion.metrics,
        "all_candidates":[{"name": r.name, **r.metrics} for r in results],
        "success":       success,
        "bias_correction": bias_table,
        "feature_importance_shap": feature_importance,
    }


def main() -> None:
    summary = {}
    for crop_short, crop_full in (("bugday", "bugday"),
                                   ("aycicegi", "aycicegi_yaglik")):
        summary[crop_short] = train_one_crop(crop_short, crop_full)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_DIR / "cp25_calibration_metrics.json"
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    logger.info("aggregate metrics → %s", out_json)


if __name__ == "__main__":
    main()
