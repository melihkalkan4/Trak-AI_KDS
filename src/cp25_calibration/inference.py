"""ÇP-2.5 — Public inference API.

``predict_yield_kg_da(...)``: NDVI tahmin serisi + iklim context → kg/dekar
verim tahmini + güven bandı + TÜİK karşılaştırma + Türkçe yorum.

Mevcut ``src/cp2_model/inference_cp2.py``'a dokunmaz — ayrı modüldür.
Dashboard ve RAG katmanı bu API'yi kullanır.
"""

from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("trakai.cp25.infer")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR   = PROJECT_ROOT / "models"
EXT_DIR      = PROJECT_ROOT / "data" / "external" / "tuik"

# Province name normalisation (Turkish display vs DB key vs one-hot)
_IL_DISPLAY = {"Edirne": "Edirne", "Kırklareli": "Kırklareli", "Tekirdağ": "Tekirdağ"}
_IL_DUMMY = {"Edirne": "il_Edirne", "Kırklareli": "il_Kirklareli", "Tekirdağ": "il_Tekirdag"}

_CROP_SHORT = {"bugday": "bugday", "aycicegi_yaglik": "aycicegi"}


# ---------------------------------------------------------------------------
def _load_bundle(crop: str):
    short = _CROP_SHORT[crop]
    p = MODELS_DIR / f"cp25_calibration_{short}.pkl"
    if not p.exists():
        raise FileNotFoundError(
            f"Bundle missing: {p}.  Run "
            "`python src/cp25_calibration/train_calibration.py` first.")
    with p.open("rb") as fh:
        return pickle.load(fh)


def _stats_for(il: str, crop: str) -> dict:
    """Return TÜİK 22-yıl mean/std/cv for (il, crop)."""
    df = pd.read_csv(EXT_DIR / "yield_stats_summary.csv")
    row = df[(df["il"] == il) & (df["crop"] == crop)]
    if row.empty:
        return {"mean_kg_da": None, "std_kg_da": None, "cv_pct": None}
    r = row.iloc[0]
    return {
        "mean_kg_da": float(r["mean_kg_da"]),
        "std_kg_da":  float(r["std_kg_da"]),
        "cv_pct":     float(r["cv_pct"]),
        "min_kg_da":  float(r["min_kg_da"]),
        "min_yil":    int(r["min_yil"]),
        "max_kg_da":  float(r["max_kg_da"]),
        "max_yil":    int(r["max_yil"]),
        "n_years":    int(r["n_years"]),
    }


def _season_progress_pct(crop: str, current_date: pd.Timestamp) -> float:
    """0–100% completion of the current growing season."""
    y = int(current_date.year)
    if crop == "bugday":
        start = pd.Timestamp(y - 1, 10, 1)
        end   = pd.Timestamp(y, 7, 15)
    else:  # aycicegi_yaglik
        start = pd.Timestamp(y, 4, 1)
        end   = pd.Timestamp(y, 9, 30)
    total = (end - start).days
    elapsed = (current_date - start).days
    return float(max(0.0, min(100.0, 100.0 * elapsed / total)))


def _interpret(deviation_pct: float, crop: str) -> str:
    """Plain-Turkish sapma yorumu (uses TÜİK 22-yıl ortalamasına oran)."""
    a = abs(deviation_pct)
    if deviation_pct > 15:
        return "Beklenenin üstünde — verimli sezon"
    if deviation_pct > 5:
        return "Hafifçe ortalamanın üstünde"
    if deviation_pct > -5:
        return "Ortalama yakınında"
    if deviation_pct > -15:
        return "Hafif düşüş — risk izlenmeli"
    if deviation_pct > -25:
        return "Belirgin düşüş — sulama/girdi gözden geçirilmeli"
    return "Kritik düşüş — kuraklık veya stres sinyali"


# ---------------------------------------------------------------------------
def _extract_features_from_ndvi_series(
        predicted_ndvi_series: pd.DataFrame,
        feature_context: pd.DataFrame,
        crop: str,
        current_date: pd.Timestamp,
        ) -> dict:
    """Compute the 10 seasonal features from caller inputs."""
    # Lazy import to avoid cycles in older test setups
    from .build_calibration_set import (
        SEASON_WINDOWS, extract_seasonal_features)

    # Stitch the two frames into a single MFM-shaped DataFrame for the
    # current season window.
    ctx = feature_context.copy()
    if "date" in ctx.columns:
        ctx["date"] = pd.to_datetime(ctx["date"])
    # If caller passed a fresh NDVI series, prefer it over ctx NDVI
    if predicted_ndvi_series is not None and not predicted_ndvi_series.empty:
        s = predicted_ndvi_series.copy()
        date_col = "target_date" if "target_date" in s.columns else "date"
        s["date"] = pd.to_datetime(s[date_col])
        s["NDVI_int"] = s.get("predicted_ndvi", s.get("NDVI_int"))
        ctx = ctx.merge(s[["date", "NDVI_int"]], on="date", how="left",
                        suffixes=("", "_pred"))
        ctx["NDVI_int"] = ctx["NDVI_int_pred"].fillna(ctx["NDVI_int"])
        ctx = ctx.drop(columns=[c for c in ctx.columns if c.endswith("_pred")])

    feats = extract_seasonal_features(
        ctx.sort_values("date").reset_index(drop=True),
        year=int(current_date.year),
        window=SEASON_WINDOWS[crop],
        crop=crop,
    )
    return feats or {}


# ---------------------------------------------------------------------------
def predict_yield_kg_da(
        predicted_ndvi_series: Optional[pd.DataFrame],
        feature_context: pd.DataFrame,
        il: Literal["Edirne", "Kırklareli", "Tekirdağ"],
        crop: Literal["bugday", "aycicegi_yaglik"],
        current_date: pd.Timestamp,
        ) -> dict:
    """ÇP-2 NDVI tahminini somut verim tahminine (kg/dekar) çevirir.

    Args:
        predicted_ndvi_series: ÇP-2 ``predict_ndvi_series`` çıktısı
            (kolonlar: ``target_date``, ``predicted_ndvi``). Optional —
            None ise ``feature_context``'teki ``NDVI_int`` kullanılır.
        feature_context: 1 yıllık MFM-şekilli DataFrame; ``date``,
            ``NDVI_int``, ``NDWI_int``, ``t2m_max``, ``t2m_min``,
            ``tp_sum`` kolonları gerekli.
        il: Trakya ili (Edirne / Kırklareli / Tekirdağ).
        crop: 'bugday' veya 'aycicegi_yaglik'.
        current_date: Tahmin anı (sezon ilerleme % hesabı için).

    Returns:
        Açıklayıcı sözlük (bkz. modül docstring).
    """
    bundle = _load_bundle(crop)
    model  = bundle["model"]
    scaler = bundle.get("scaler")
    cols   = bundle["feature_cols"]

    # 1) Build feature vector
    feats = _extract_features_from_ndvi_series(
        predicted_ndvi_series, feature_context, crop, current_date)
    if not feats:
        raise ValueError(
            "Yetersiz feature: feature_context sezonun en az 30 gününü "
            "kapsamalı.")

    # 2) One-hot il + assemble row
    base = ["ndvi_max", "ndvi_mean", "ndvi_integral",
            "ndvi_flowering", "ndvi_grain_fill", "greenness_days",
            "gdd_cum_season", "tp_season_sum",
            "ndwi_min_flowering", "t2m_max_flowering_mean"]
    row = {c: float(feats.get(c, np.nan)) for c in base}
    for k in ("il_Edirne", "il_Kirklareli", "il_Tekirdag"):
        row[k] = 0.0
    row[_IL_DUMMY[il]] = 1.0
    X = pd.DataFrame([row], columns=cols).astype(float)
    # Median impute on any nan from incomplete season (mid-season inference)
    X = X.fillna(0.0)

    # 3) Predict (with optional scaler)
    if scaler is not None:
        yhat = float(model.predict(scaler.transform(X))[0])
    else:
        yhat = float(model.predict(X.values)[0])

    # 4) Apply per-il bias correction (mean residual on train set)
    bias = bundle.get("per_il_bias_correction_kg_da", {}).get(il, 0.0)
    yhat_corrected = yhat + float(bias)

    # 5) 95% CI (±1.96 × RMSE_LOOCV — Gaussian approx, small-n caveat)
    rmse = float(bundle["metrics_loocv"]["rmse_kg_da"])
    half = 1.96 * rmse
    lower = yhat_corrected - half
    upper = yhat_corrected + half

    # 6) Local 22-year stats + deviation
    stats = _stats_for(il, crop)
    deviation_pct = (((yhat_corrected - stats["mean_kg_da"]) /
                       stats["mean_kg_da"]) * 100
                     if stats["mean_kg_da"] else None)

    # 7) Confidence (0-1): scaled by season completeness × model quality
    season_pct = _season_progress_pct(crop, current_date)
    model_r2   = float(bundle["metrics_loocv"]["r2"])
    quality    = max(0.0, model_r2)            # negative R² → 0 quality
    completeness = season_pct / 100.0
    confidence = round(0.5 * quality + 0.5 * completeness, 3)

    return {
        "yield_kg_da":         round(yhat_corrected, 1),
        "yield_kg_da_lower":   round(lower, 1),
        "yield_kg_da_upper":   round(upper, 1),
        "yield_kg_da_raw":     round(yhat, 1),
        "per_il_bias_applied": round(float(bias), 1),
        "lokal_22yil_ortalama": stats["mean_kg_da"],
        "lokal_22yil_std":      stats["std_kg_da"],
        "lokal_22yil_min":      stats["min_kg_da"],
        "lokal_22yil_max":      stats["max_kg_da"],
        "sapma_pct":            round(deviation_pct, 1) if deviation_pct is not None else None,
        "sapma_yorum":          _interpret(deviation_pct or 0, crop),
        "confidence":           confidence,
        "features_used":        {k: round(v, 4) for k, v in row.items()
                                 if k not in _IL_DUMMY.values()},
        "sezon_tamamlanma_pct": round(season_pct, 1),
        "il":                   il,
        "crop":                 crop,
        "model_version":        bundle.get("model_version", "cp25-v1.0"),
        "champion_model":       bundle["champion_name"],
        "metrics_loocv":        bundle["metrics_loocv"],
        "limitations":          bundle.get("limitations", []),
    }


__all__ = ["predict_yield_kg_da"]
