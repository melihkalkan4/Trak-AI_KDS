"""
TRAK-AI KDS — Live (on-demand) tarla predictor
================================================
Thin façade around `prospective_validation.frozen_model_predictor.FrozenPredictor`
that the dashboard can call from a button click without knowing FLOV internals.

Behavior
--------
1. Resolve the active tarla's `research_code` (EVR_xx).
2. Find the latest 17-feature parquet for the matching year.
3. Run walk-forward NDVI prediction with the frozen LSTM.
4. Persist the last 7 prediction rows to `tarla_tahminler` via the existing DB
   helper (`add_tahmin`), tagged with `kaynak="frozen_lstm_live"`.
5. Return a compact summary dict suitable for direct st.metric / st.dataframe.

This file does NOT duplicate FLOV math — it just wires it.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

_HERE = Path(__file__).resolve().parent
SRC = _HERE.parent
PROJECT_ROOT = SRC.parent
for _p in (str(SRC), str(PROJECT_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

logger = logging.getLogger("trakai.live_predictor")


# ─────────────────────────────────────────────────────────────────────────────
# Internal cached singletons
# ─────────────────────────────────────────────────────────────────────────────

_CHAMPION = None
_CLIM = None


def _get_predictor():
    """Lazy load the frozen champion + climatology only once per process."""
    global _CHAMPION, _CLIM
    if _CHAMPION is None:
        from prospective_validation.model_loader import load_frozen_champion
        from prospective_validation.frozen_model_predictor import FrozenPredictor
        from prospective_validation import climatology as clim_mod
        from prospective_validation import config as flov_config

        _CHAMPION = load_frozen_champion()
        try:
            _CLIM = clim_mod.load_climatology()
        except Exception as exc:                                       # noqa: BLE001
            logger.warning("Climatology not available: %s", exc)
            _CLIM = None
        return FrozenPredictor(champion=_CHAMPION, climatology=_CLIM)

    from prospective_validation.frozen_model_predictor import FrozenPredictor
    return FrozenPredictor(champion=_CHAMPION, climatology=_CLIM)


def _find_features_parquet(research_code: str,
                           year: Optional[int] = None) -> Optional[Path]:
    """Find the most recent unified-features parquet for a site.

    Searches in this priority order:
      1. The requested year if given.
      2. The highest year directory under data/prospective/.
    """
    base = PROJECT_ROOT / "data" / "prospective"
    if not base.exists():
        return None
    candidates: list[tuple[int, Path]] = []
    for y_dir in base.iterdir():
        if not (y_dir.is_dir() and y_dir.name.isdigit()):
            continue
        p = y_dir / f"{research_code}_unified_features.parquet"
        if p.exists():
            candidates.append((int(y_dir.name), p))
    if not candidates:
        return None
    if year is not None:
        for y, p in candidates:
            if y == year:
                return p
    # latest
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def predict_for_tarla(tarla_id: int,
                      year: Optional[int] = None,
                      window: int = 30,
                      persist: bool = True) -> dict:
    """Run the frozen LSTM on the tarla's latest features.

    Returns
    -------
    dict
        {
          "ok": bool,
          "tarla_id": int,
          "research_code": str | None,
          "features_path": str | None,
          "n_predictions": int,
          "last_row": dict | None,   # most recent prediction
          "all": pd.DataFrame | None,
          "error": str | None,
        }
    """
    result: dict = {
        "ok": False, "tarla_id": tarla_id, "research_code": None,
        "features_path": None, "n_predictions": 0,
        "last_row": None, "all": None, "error": None,
    }
    try:
        from database import get_tarla, add_tahmin
    except Exception as exc:                                           # noqa: BLE001
        result["error"] = f"db import failed: {exc}"
        return result

    tarla = get_tarla(tarla_id)
    if not tarla:
        result["error"] = f"tarla_id={tarla_id} not found"
        return result
    rcode = tarla.get("research_code")
    result["research_code"] = rcode
    if not rcode:
        result["error"] = "tarla has no research_code (FLOV bridge missing)"
        return result

    p = _find_features_parquet(rcode, year)
    if p is None:
        result["error"] = f"no features parquet found for {rcode}"
        return result
    result["features_path"] = str(p)

    df = pd.read_parquet(p)
    if len(df) < window:
        result["error"] = (
            f"need at least {window} rows, got {len(df)} in {p.name}"
        )
        return result

    try:
        predictor = _get_predictor()
    except Exception as exc:                                           # noqa: BLE001
        result["error"] = f"frozen champion load failed: {exc}"
        return result

    try:
        preds = predictor.predict_ndvi_series(df, verify_integrity=True)
    except Exception as exc:                                           # noqa: BLE001
        result["error"] = f"prediction failed: {exc}"
        return result

    if preds.empty:
        result["error"] = "predictor returned empty frame"
        return result

    last = preds.iloc[-1]
    result["ok"] = True
    result["n_predictions"] = int(len(preds))
    result["all"] = preds
    result["last_row"] = {
        "prediction_date": str(last.get("prediction_date").date())
            if pd.notna(last.get("prediction_date")) else None,
        "target_date": str(last.get("target_date").date())
            if pd.notna(last.get("target_date")) else None,
        "predicted_ndvi": float(last.get("predicted_ndvi", float("nan"))),
        "last_observed_ndvi": float(last.get("last_observed_ndvi", float("nan"))),
        "residual_delta": float(last.get("residual_delta", float("nan"))),
        "climatology_ndvi": (
            float(last.get("climatology_ndvi"))
            if pd.notna(last.get("climatology_ndvi")) else None
        ),
        "anomaly_vs_climatology": (
            float(last.get("anomaly_vs_climatology"))
            if pd.notna(last.get("anomaly_vs_climatology")) else None
        ),
    }

    if persist:
        # Save just the most recent prediction so dashboard "son tahmin"
        # cards remain fast. Multiple horizons would inflate the table.
        try:
            ndvi_pred = result["last_row"]["predicted_ndvi"]
            ndvi_now  = result["last_row"]["last_observed_ndvi"]
            add_tahmin(tarla_id, {
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "urun": tarla.get("aktif_urun"),
                "ndvi_mevcut": ndvi_now,
                "ndvi_tahmin_7gun": ndvi_pred,
                "ndvi_delta": result["last_row"]["residual_delta"],
                "saglik_durumu": _ndvi_health_label(ndvi_pred),
                "kaynak": "frozen_lstm_live",
            })
        except Exception as exc:                                       # noqa: BLE001
            logger.warning("add_tahmin persist failed: %s", exc)

    return result


def _ndvi_health_label(ndvi: float) -> str:
    if ndvi is None or pd.isna(ndvi):
        return "BILINMIYOR"
    if ndvi < 0.30:  return "ZAYIF"
    if ndvi < 0.50:  return "ORTA"
    if ndvi < 0.70:  return "IYI"
    return "MUKEMMEL"


__all__ = ["predict_for_tarla"]
