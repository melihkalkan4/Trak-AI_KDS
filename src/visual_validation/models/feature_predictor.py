"""
Modality 3: Multi-modal feature predictor (numerical, no vision).

Thin adapter on top of `prospective_validation.FrozenPredictor` and the
DOY climatology so its NDVI anomaly output becomes a harmonized class
that the consensus engine can compare against the visual modalities.

Mapping:
    z = anomaly_vs_climatology(doy) / σ_NDVI(doy)
    z >= -1   → healthy
    -2 <= z < -1 → mild_stress
    z < -2    → severe_stress
    (disease  : never produced — only the field modality can see disease)

The wrapper preserves the FrozenPredictor's hash audit so the same
SHA-256 contract from FLOV applies here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .. import config


logger = logging.getLogger("trakai.visual.features")


@dataclass
class FeaturePrediction:
    site_id: str
    target_date: str               # ISO date
    predicted_ndvi: float
    last_observed_ndvi: float
    climatology_ndvi: float
    climatology_std: float
    anomaly: float                 # predicted − climatology_mean
    z_score: float                 # anomaly / climatology_std
    harmonized_class: str
    confidence: float              # |z| → bounded confidence (sigmoid-ish)
    model_sha256: str
    source: str = "lstm+xgb (FLOV champion)"
    timestamp_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class MultiModalFeaturePredictor:
    """
    Adapter that turns the FLOV LSTM's NDVI anomaly into a harmonized class.

    Constructed lazily so importing this module on a CPU-only dev box
    doesn't pay the TensorFlow import tax until inference is requested.
    """

    def __init__(self):
        self._predictor = None       # FrozenPredictor
        self._clim_table = None      # DataFrame indexed by doy
        self._model_sha256 = ""

    # -------------------------------------------------------------------
    def _ensure_loaded(self):
        if self._predictor is not None:
            return
        # Late import — keeps TF off the import path for unrelated code
        from prospective_validation.frozen_model_predictor import make_predictor
        self._predictor = make_predictor(load_climatology=True)
        self._model_sha256 = self._predictor.champion.artefact_hashes[
            "lstm_champion_sunflower"
        ]
        clim = self._predictor.climatology.table.copy()
        # Expect columns: doy, ndvi_mean, ndvi_std, ndvi_count (raw + smoothed)
        if "doy" in clim.columns:
            self._clim_table = clim.set_index("doy")
        else:
            self._clim_table = clim
        logger.info("MultiModalFeaturePredictor ready; lstm_sha256=%s",
                    self._model_sha256[:16])

    # -------------------------------------------------------------------
    @staticmethod
    def _confidence_from_z(z: float) -> float:
        """Map |z| → (0,1) via 1 − 2·Φ(−|z|).  z=0→0, z=1→0.683, z=2→0.954."""
        from math import erf, sqrt
        if z is None or z != z:
            return 0.0
        return float(erf(abs(z) / sqrt(2.0)))

    # -------------------------------------------------------------------
    def predict(
        self,
        site_id: str,
        target_date: date,
        features_df: Optional[pd.DataFrame] = None,
    ) -> Optional[FeaturePrediction]:
        """
        Predict the harmonized class for one (site, date).

        If `features_df` is None, we load the prospective unified-features
        parquet for the site/year automatically.  This is the path the
        consensus engine uses in production.
        """
        self._ensure_loaded()

        # Locate features
        if features_df is None:
            from prospective_validation import config as _flov
            parquet = (_flov.PROSPECTIVE_DIR / str(target_date.year)
                       / f"{site_id}_unified_features.parquet")
            if not parquet.exists():
                logger.warning("[features] unified parquet missing: %s", parquet)
                return None
            features_df = pd.read_parquet(parquet)

        # Need at least a 30-day window ending at target_date − horizon
        from prospective_validation import config as _flov
        horizon = _flov.FORECAST_HORIZON_DAYS
        feats = features_df.copy()
        feats["date"] = pd.to_datetime(feats["date"])

        target = pd.Timestamp(target_date)
        prediction_date = target - pd.Timedelta(days=horizon)
        sub = feats[feats["date"] <= prediction_date]
        if len(sub) < _flov.INPUT_WINDOW:
            logger.warning(
                "[features] %s @ %s — only %d days available (need %d)",
                site_id, target_date, len(sub), _flov.INPUT_WINDOW,
            )
            return None

        # Run the FLOV predictor on the sub-frame; pick the row whose
        # target_date matches.
        preds = self._predictor.predict_ndvi_series(sub)
        if preds.empty:
            return None
        row = preds[preds["target_date"] == target]
        if row.empty:
            row = preds.tail(1)
        row = row.iloc[0]

        # Climatology lookup
        doy = int(target.dayofyear)
        if self._clim_table is not None and doy in self._clim_table.index:
            clim_mean = float(self._clim_table.loc[doy, "ndvi_mean"])
            clim_std = float(self._clim_table.loc[doy, "ndvi_std"])
        else:
            clim_mean = float(row.get("climatology_ndvi", np.nan))
            clim_std = float("nan")

        if not np.isfinite(clim_std) or clim_std <= 1e-6:
            # Conservative fallback — keeps the harmonization stable
            clim_std = 0.07

        predicted = float(row["predicted_ndvi"])
        anomaly = predicted - clim_mean
        z = anomaly / clim_std
        harmonized = config.feature_zscore_to_class(z)
        conf = self._confidence_from_z(z)

        return FeaturePrediction(
            site_id=site_id,
            target_date=target_date.isoformat(),
            predicted_ndvi=predicted,
            last_observed_ndvi=float(row.get("last_observed_ndvi", np.nan)),
            climatology_ndvi=clim_mean,
            climatology_std=clim_std,
            anomaly=float(anomaly),
            z_score=float(z),
            harmonized_class=harmonized,
            confidence=conf,
            model_sha256=self._model_sha256,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    # -------------------------------------------------------------------
    def predict_from_flov_row(self, row: pd.Series, site_id: str) -> FeaturePrediction:
        """
        Build a harmonized prediction directly from a FrozenPredictor
        output row (skips re-running the LSTM).  Useful for batch consensus
        runs over a whole season.
        """
        self._ensure_loaded()
        target = pd.Timestamp(row["target_date"])
        doy = int(target.dayofyear)
        if self._clim_table is not None and doy in self._clim_table.index:
            clim_std = float(self._clim_table.loc[doy, "ndvi_std"])
        else:
            clim_std = float("nan")
        if not np.isfinite(clim_std) or clim_std <= 1e-6:
            clim_std = 0.07
        predicted = float(row["predicted_ndvi"])
        clim_mean = float(row["climatology_ndvi"])
        anomaly = predicted - clim_mean
        z = anomaly / clim_std
        return FeaturePrediction(
            site_id=site_id,
            target_date=target.date().isoformat(),
            predicted_ndvi=predicted,
            last_observed_ndvi=float(row.get("last_observed_ndvi", float("nan"))),
            climatology_ndvi=clim_mean,
            climatology_std=clim_std,
            anomaly=float(anomaly),
            z_score=float(z),
            harmonized_class=config.feature_zscore_to_class(z),
            confidence=self._confidence_from_z(z),
            model_sha256=self._model_sha256,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )


__all__ = ["MultiModalFeaturePredictor", "FeaturePrediction"]
