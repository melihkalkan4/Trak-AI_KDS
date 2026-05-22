"""
Frozen-model walk-forward inference.

Phase 3 of FLOV.  Given a daily 17-feature DataFrame (the output of
:mod:`feature_builder.build_unified_features`), produce one prediction
record per valid 30-day window:

    prediction_date         — last day of the input window (= "today" then)
    target_date             — prediction_date + 7d
    predicted_ndvi          — model output, inverse-scaled to native NDVI
    last_observed_ndvi      — NDVI on prediction_date (also inverse-scaled)
    residual_delta          — predicted - last_observed (the model's "delta")
    predicted_ndvi_scaled   — raw [0,1] output, for auditability
    climatology_ndvi        — DOY-mean from 2017-2024 (narrative layer)
    anomaly_vs_climatology  — predicted - climatology  (positive = above norm)

The frozen artefact is re-hashed before each batch (`verify_integrity=True`,
default).  Yield prediction is delegated to the existing
:mod:`cp2_model.inference_yield` module after the same integrity gate.

NEVER call ``.fit`` or mutate weights from this module.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from . import climatology as clim_mod
from . import config, integrity
from .logging_setup import logger
from .model_loader import FrozenChampion, load_frozen_champion


@dataclass
class FrozenPredictor:
    """Stateful wrapper around a loaded :class:`FrozenChampion`."""

    champion: FrozenChampion
    climatology: Optional[clim_mod.Climatology] = None

    # ------------------------------------------------------------------ API

    def predict_ndvi_series(
        self,
        features_df: pd.DataFrame,
        *,
        window: int = config.INPUT_WINDOW,
        horizon: int = config.FORECAST_HORIZON_DAYS,
        verify_integrity: bool = True,
    ) -> pd.DataFrame:
        """
        Walk-forward NDVI inference over a daily feature frame.

        Parameters
        ----------
        features_df : DataFrame
            Must contain a ``date`` column plus the 17 columns named in
            :data:`config.FEATURE_NAMES`.  Daily rows, ascending date.
            NaNs are tolerated and forward/back-filled per the frozen
            training convention.
        window : int
            Input sequence length (default 30; FROZEN value).
        horizon : int
            Forecast horizon in days (default 7; FROZEN value).
        verify_integrity : bool
            Re-hash all frozen artefacts on disk before predicting.

        Returns
        -------
        DataFrame with one row per (window-end) date, columns listed in the
        module docstring.  Empty if ``len(features_df) < window``.
        """
        if verify_integrity:
            self.champion.verify_runtime_integrity()

        if "date" not in features_df.columns:
            raise ValueError("features_df must contain a 'date' column")
        missing = [c for c in config.FEATURE_NAMES if c not in features_df.columns]
        if missing:
            raise ValueError(f"features_df missing required columns: {missing}")

        df = features_df.sort_values("date").reset_index(drop=True).copy()
        df["date"] = pd.to_datetime(df["date"])
        n = len(df)
        if n < window:
            logger.warning(
                "[predictor] only {} rows; need >= {} for a single window",
                n, window,
            )
            return pd.DataFrame(columns=[
                "prediction_date", "target_date",
                "predicted_ndvi", "last_observed_ndvi", "residual_delta",
                "predicted_ndvi_scaled",
                "climatology_ndvi", "anomaly_vs_climatology",
            ])

        # Mirror preprocessing_cp2.main: ffill + bfill on the 17 features
        # BEFORE the (frozen) MinMaxScaler.transform.
        feats = df[config.FEATURE_NAMES].copy()
        nan_count = int(feats.isna().sum().sum())
        if nan_count:
            logger.warning(
                "[predictor] {} NaN cells in 17-feature frame; applying "
                "ffill + bfill (matches training pipeline)",
                nan_count,
            )
            feats = feats.ffill().bfill()

        # Frozen scaler.transform — same MinMax bounds as the training fit
        scaled = self.champion.scaler.transform(feats.values).astype("float32")

        # Walk forward.  i is the index of the *first day AFTER* the window;
        # last_observed = df.iloc[i-1].
        records: list[dict] = []
        for i in range(window, n):
            window_scaled = scaled[i - window : i]
            prediction_date = df["date"].iloc[i - 1]
            target_date = prediction_date + pd.Timedelta(days=horizon)

            out = self.champion.predict_ndvi_window(window_scaled)

            rec = {
                "prediction_date": prediction_date,
                "target_date": target_date,
                "predicted_ndvi": out["predicted_ndvi"],
                "last_observed_ndvi": out["last_ndvi"],
                "residual_delta": out["residual_delta"],
                "predicted_ndvi_scaled": out["predicted_ndvi_scaled"],
            }
            if self.climatology is not None:
                doy = int(target_date.dayofyear)
                clim_value = self.climatology.value_at(doy)
                rec["climatology_ndvi"] = clim_value
                rec["anomaly_vs_climatology"] = out["predicted_ndvi"] - clim_value
            else:
                rec["climatology_ndvi"] = np.nan
                rec["anomaly_vs_climatology"] = np.nan
            records.append(rec)

        result = pd.DataFrame(records)
        logger.info(
            "[predictor] produced {} predictions ({} → {})",
            len(result),
            result["prediction_date"].iloc[0].date() if len(result) else "—",
            result["prediction_date"].iloc[-1].date() if len(result) else "—",
        )
        return result

    # ------------------------------------------------------------------ yield

    def predict_yield(
        self,
        crop: str = "Sunflower",
        current_year_features: Optional[dict] = None,
        *,
        verify_integrity: bool = True,
    ) -> dict:
        """
        Delegate to :func:`cp2_model.inference_yield.predict_yield` after
        re-hashing the yield model artefacts.

        Returns the same dict that ``inference_yield.predict_yield`` returns.
        """
        if verify_integrity:
            for role, path in (
                ("yield_xgb_sunflower",    config.YIELD_XGB_PATH),
                ("yield_scaler_sunflower", config.YIELD_SCALER_PATH),
            ):
                if path.exists():
                    integrity.ensure_unchanged(path, role=role)

        cp2 = str(config.CP2_DIR)
        if cp2 not in sys.path:
            sys.path.insert(0, cp2)
        import importlib
        iy = importlib.import_module("inference_yield")
        return iy.predict_yield(crop, current_year_features=current_year_features)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_predictor(load_climatology: bool = True) -> FrozenPredictor:
    """Convenience: load champion + climatology in one call."""
    champion = load_frozen_champion()
    clim = clim_mod.load_climatology() if load_climatology else None
    return FrozenPredictor(champion=champion, climatology=clim)


__all__ = ["FrozenPredictor", "make_predictor"]
