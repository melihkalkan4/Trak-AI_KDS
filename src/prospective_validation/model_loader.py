"""
Frozen champion loader.

Hybrid champion (per user decision):
    * LSTM      → 7-day NDVI residual-delta prediction (sunflower)
    * XGBoost   → end-of-season yield prediction (sunflower)

Loading is one-shot.  The returned ``FrozenChampion`` exposes ``predict_ndvi``
and ``predict_yield`` but no ``train``, ``fit``, or weight-mutation method.
Every load re-verifies the SHA-256 of every frozen artefact against the
integrity ledger.

Read-only enforcement
---------------------
Keras / XGBoost have no public 'read-only' flag for in-memory models.  Our
guarantees are therefore:
    1. The Keras model's ``trainable`` is set to False (also recursively).
    2. We never expose a ``.fit()`` shortcut.
    3. The on-disk artefact's hash is re-verified on every load.
    4. ``verify_runtime_integrity()`` re-hashes the on-disk file at any
       point (cheap, used as a paranoid check around long-running jobs).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

# Quiet TF before import
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from .logging_setup import logger, configure_logging
from . import config, integrity


# ---------------------------------------------------------------------------
# Custom-layer registration — MUST run before any tf.keras.models.load_model
# ---------------------------------------------------------------------------
def _register_custom_layers() -> None:
    """Import train_models_cp2 so @register_keras_serializable runs."""
    cp2_str = str(config.CP2_DIR)
    if cp2_str not in sys.path:
        sys.path.insert(0, cp2_str)
    # The import below registers SelfAttention, ExtractLastNDVI, ScaleDelta
    # via @register_keras_serializable side-effects.
    import importlib
    importlib.import_module("train_models_cp2")


@dataclass
class FrozenChampion:
    """In-memory view of the immutable champion artefacts."""

    lstm: Any
    xgb_yield: Any
    scaler: Any                       # MinMaxScaler for 17-feature window
    yield_scaler: Any | None
    feature_names: list[str]
    xgb_feature_names: list[str]
    ndvi_index: int
    delta_scale: float
    artefact_hashes: dict[str, str] = field(default_factory=dict)

    # -- public API ---------------------------------------------------------

    def predict_ndvi_window(self, window_scaled: np.ndarray) -> dict[str, float]:
        """
        Run the LSTM on a single scaled (T, F) window.

        The Keras model embeds residual + scale + add(last_ndvi), so the raw
        output is *scaled* absolute NDVI at t+7.  We inverse-transform back
        to the native NDVI scale for caller convenience.

        Parameters
        ----------
        window_scaled : np.ndarray of shape (30, 17), already MinMax-scaled

        Returns
        -------
        dict
            predicted_ndvi_scaled  — raw model output (clipped to [0, 1])
            predicted_ndvi         — inverse-scaled absolute NDVI
            last_ndvi              — input window's last NDVI (native scale)
            residual_delta         — predicted - last_ndvi (native scale)
        """
        if window_scaled.shape != (config.INPUT_WINDOW, len(self.feature_names)):
            raise ValueError(
                f"Expected window shape ({config.INPUT_WINDOW},"
                f" {len(self.feature_names)}); got {window_scaled.shape}"
            )
        inp = window_scaled.reshape(1, *window_scaled.shape).astype("float32")
        raw = float(self.lstm.predict(inp, verbose=0)[0][0])
        pred_scaled = float(np.clip(raw, 0.0, 1.0))

        ndvi_min = float(self.scaler.data_min_[self.ndvi_index])
        ndvi_range = float(self.scaler.data_range_[self.ndvi_index])
        pred_native = float(np.clip(pred_scaled * ndvi_range + ndvi_min, -1.0, 1.0))
        last_native = float(window_scaled[-1, self.ndvi_index] * ndvi_range + ndvi_min)

        return {
            "predicted_ndvi_scaled": pred_scaled,
            "predicted_ndvi": pred_native,
            "last_ndvi": last_native,
            "residual_delta": pred_native - last_native,
        }

    def predict_yield(self, season_features_2d: np.ndarray) -> float:
        """End-of-season yield (XGBoost). Caller is responsible for matching
        the XGB feature order in :attr:`xgb_feature_names`."""
        if season_features_2d.ndim != 2:
            raise ValueError("season_features_2d must be 2-D (n_samples, n_feat)")
        return float(self.xgb_yield.predict(season_features_2d)[0])

    def verify_runtime_integrity(self) -> None:
        """Re-hash every frozen file on disk; raise on any drift."""
        for role, path in (
            ("lstm_champion_sunflower", config.LSTM_CHAMPION_PATH),
            ("xgb_yield_sunflower",     config.XGB_CHAMPION_PATH),
            ("scaler_sunflower",        config.SCALER_PATH),
            ("yield_xgb_sunflower",     config.YIELD_XGB_PATH),
            ("yield_scaler_sunflower",  config.YIELD_SCALER_PATH),
            ("feature_names",           config.FEATURE_NAMES_PATH),
            ("xgb_feature_names_sunf",  config.XGB_FEATURE_NAMES_PATH),
        ):
            if path.exists():
                integrity.ensure_unchanged(path, role=role)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
def _require(path: Path, role: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Frozen artefact missing for role={role}: {path}")


def load_frozen_champion() -> FrozenChampion:
    """Load + hash-verify the hybrid sunflower champion. Idempotent."""
    configure_logging()

    # 1. Verify presence
    _require(config.LSTM_CHAMPION_PATH, "lstm_champion_sunflower")
    _require(config.XGB_CHAMPION_PATH,  "xgb_yield_sunflower")   # main NDVI XGB (kept for reference)
    _require(config.SCALER_PATH,        "scaler_sunflower")
    _require(config.FEATURE_NAMES_PATH, "feature_names")

    # 2. Verify hashes (ledger-backed first-sight or strict re-check)
    hashes = {
        "lstm_champion_sunflower": integrity.ensure_unchanged(
            config.LSTM_CHAMPION_PATH, role="lstm_champion_sunflower"),
        "xgb_yield_sunflower": integrity.ensure_unchanged(
            config.XGB_CHAMPION_PATH, role="xgb_yield_sunflower"),
        "scaler_sunflower": integrity.ensure_unchanged(
            config.SCALER_PATH, role="scaler_sunflower"),
        "feature_names": integrity.ensure_unchanged(
            config.FEATURE_NAMES_PATH, role="feature_names"),
    }
    if config.YIELD_XGB_PATH.exists():
        hashes["yield_xgb_sunflower"] = integrity.ensure_unchanged(
            config.YIELD_XGB_PATH, role="yield_xgb_sunflower")
    if config.YIELD_SCALER_PATH.exists():
        hashes["yield_scaler_sunflower"] = integrity.ensure_unchanged(
            config.YIELD_SCALER_PATH, role="yield_scaler_sunflower")
    if config.XGB_FEATURE_NAMES_PATH.exists():
        hashes["xgb_feature_names_sunf"] = integrity.ensure_unchanged(
            config.XGB_FEATURE_NAMES_PATH, role="xgb_feature_names_sunf")

    # 3. Register custom layers, then load Keras model
    logger.info("Registering CP2 custom layers (SelfAttention, ExtractLastNDVI, ScaleDelta) …")
    _register_custom_layers()

    import tensorflow as tf  # noqa: WPS433 (intentional late import)
    logger.info("Loading frozen LSTM champion: {}", config.LSTM_CHAMPION_PATH.name)
    lstm = tf.keras.models.load_model(str(config.LSTM_CHAMPION_PATH))
    lstm.trainable = False
    for layer in lstm.layers:
        layer.trainable = False

    # 4. Load scalers / XGB
    scaler = joblib.load(config.SCALER_PATH)
    yield_xgb = joblib.load(config.YIELD_XGB_PATH) if config.YIELD_XGB_PATH.exists() else None
    yield_scaler = joblib.load(config.YIELD_SCALER_PATH) if config.YIELD_SCALER_PATH.exists() else None

    # 5. Feature schemas
    feature_names = json.loads(config.FEATURE_NAMES_PATH.read_text(encoding="utf-8"))
    if config.XGB_FEATURE_NAMES_PATH.exists():
        xgb_feature_names = json.loads(
            config.XGB_FEATURE_NAMES_PATH.read_text(encoding="utf-8"))
    else:
        xgb_feature_names = []

    # 6. Sanity: feature contract unchanged
    if feature_names != config.FEATURE_NAMES:
        raise RuntimeError(
            "Feature contract drift: config.FEATURE_NAMES (cached at import) "
            "differs from on-disk feature_names.json."
        )

    champ = FrozenChampion(
        lstm=lstm,
        xgb_yield=yield_xgb,
        scaler=scaler,
        yield_scaler=yield_scaler,
        feature_names=feature_names,
        xgb_feature_names=xgb_feature_names,
        ndvi_index=feature_names.index(config.NDVI_FEATURE),
        delta_scale=config.DELTA_SCALE,
        artefact_hashes=hashes,
    )
    logger.info("Frozen champion loaded. LSTM sha256={} (truncated)",
                hashes["lstm_champion_sunflower"][:16])
    return champ


__all__ = ["FrozenChampion", "load_frozen_champion"]
