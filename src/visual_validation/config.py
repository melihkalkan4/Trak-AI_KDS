"""
Central configuration for the Multi-Modal Visual Validation module.

Single source of truth for:
    - Paths to all 3 modality artefacts
    - Harmonized 4-class taxonomy + per-modality mappings
    - MQTT broker / topics
    - Consensus thresholds + weights
    - Planet API stub paths (real key wired once Education tier lands)
    - Integration anchors into src/prospective_validation/

All read-only — DO NOT mutate at runtime.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT: Final[Path] = _THIS_FILE.parents[2]
SRC_DIR:      Final[Path] = PROJECT_ROOT / "src"

DATA_DIR:     Final[Path] = PROJECT_ROOT / "data"
VISUAL_DIR:   Final[Path] = DATA_DIR / "visual"

PLANETSCOPE_DIR:           Final[Path] = VISUAL_DIR / "planetscope"
FIELD_PHOTOS_DIR:          Final[Path] = VISUAL_DIR / "field_photos"
CONSENSUS_PREDICTIONS_DIR: Final[Path] = VISUAL_DIR / "consensus_predictions"
GROUND_TRUTH_DIR:          Final[Path] = VISUAL_DIR / "ground_truth_observations"

MODELS_VISUAL_DIR:     Final[Path] = PROJECT_ROOT / "models" / "visual"
REPORTS_VISUAL_DIR:    Final[Path] = PROJECT_ROOT / "reports" / "visual"
LOGS_DIR:              Final[Path] = PROJECT_ROOT / "logs"


# ---------------------------------------------------------------------------
# Frozen-artefact anchors (shared with prospective_validation)
# ---------------------------------------------------------------------------
# Existing YOLOv8 classifier — FROZEN, never retrained here.
# Confirmed file location (different from spec; spec was wrong):
YOLOV8_MODEL_PATH: Final[Path] = PROJECT_ROOT / "models" / "crop_health_best.pt"

# New ResNet50 — to be trained on Colab once Planet key arrives.
SATELLITE_CNN_PATH: Final[Path] = MODELS_VISUAL_DIR / "satellite_cnn_resnet50.pt"
SATELLITE_CNN_METRICS_PATH: Final[Path] = MODELS_VISUAL_DIR / "satellite_cnn_metrics.json"

# Pull through the FLOV anchors so we don't fork them
_PV_DIR = SRC_DIR / "prospective_validation"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
try:
    from prospective_validation import config as _flov  # noqa: E402
    EVRENLI_SITES = _flov.EVRENLI_SITES
    MVP_SITE_ID:   Final[str] = _flov.MVP_SITE_ID
    Site          = _flov.Site
    SUNFLOWER_PHENOLOGY = _flov.SUNFLOWER_PHENOLOGY
    stage_for_doy = _flov.stage_for_doy
    FLOV_CONFIG_OK = True
except Exception:                                             # pragma: no cover
    FLOV_CONFIG_OK = False
    EVRENLI_SITES = ()  # type: ignore[assignment]
    MVP_SITE_ID = "EVR_01"
    Site = None  # type: ignore[assignment]
    SUNFLOWER_PHENOLOGY = ()  # type: ignore[assignment]
    def stage_for_doy(doy: int) -> str:  # type: ignore[no-redef]
        return "unknown"


# ---------------------------------------------------------------------------
# Harmonized 4-class taxonomy
# ---------------------------------------------------------------------------
# This is the canonical schema every modality must map *into* before the
# consensus engine sees its output.  We keep it tiny on purpose — anything
# wider than 4 classes collapses interrater agreement (Cohen/Fleiss κ).
HARMONIZED_LABELS: Final[tuple[str, ...]] = (
    "healthy",
    "mild_stress",
    "severe_stress",
    "disease",
)
HARMONIZED_INDEX: Final[dict[str, int]] = {l: i for i, l in enumerate(HARMONIZED_LABELS)}


# ----- Modality 2 (Field vision / YOLOv8) -----
# Source class names: confirmed from src/image_classifier.py:42-80
YOLOV8_CLASS_NAMES: Final[tuple[str, ...]] = (
    "hastalik_mildiyo",    # 0
    "hastalik_pas",        # 1
    "saglikli_aycicegi",   # 2
    "saglikli_bugday",     # 3
    "stres_besin",         # 4
    "stres_kuraklik",      # 5
)

YOLOV8_TO_HARMONIZED: Final[dict[str, str]] = {
    "saglikli_aycicegi":  "healthy",
    "saglikli_bugday":    "healthy",
    "stres_besin":        "mild_stress",
    "stres_kuraklik":     "severe_stress",
    "hastalik_pas":       "disease",
    "hastalik_mildiyo":   "disease",
}

# ----- Modality 1 (Satellite ResNet50) -----
# 3-class output (no disease — satellite cannot detect leaf-scale disease)
SATELLITE_CLASS_NAMES: Final[tuple[str, ...]] = (
    "healthy", "mild_stress", "severe_stress",
)
SATELLITE_TO_HARMONIZED: Final[dict[str, str]] = {
    "healthy":       "healthy",
    "mild_stress":   "mild_stress",
    "severe_stress": "severe_stress",
}

# ----- Modality 3 (Feature predictor — z-score thresholds) -----
# Z-score is computed against the DOY climatology baseline built by FLOV.
# These thresholds match the alert engine's anomaly thresholds (0.05/0.10/0.20
# NDVI units), translated into z-units assuming σ_NDVI(doy) ≈ 0.07 (median
# across DOYs in the 2017-2024 climatology parquet).
FEATURE_Z_HEALTHY_MAX:        Final[float] = -1.0
FEATURE_Z_MILD_STRESS_MAX:    Final[float] = -2.0


def feature_zscore_to_class(z: float) -> str:
    """Convert NDVI anomaly z-score (vs DOY climatology) → harmonized label."""
    if z is None or z != z:                  # NaN guard
        return "healthy"
    if z >= FEATURE_Z_HEALTHY_MAX:
        return "healthy"
    if z >= FEATURE_Z_MILD_STRESS_MAX:
        return "mild_stress"
    return "severe_stress"


# ---------------------------------------------------------------------------
# Consensus engine knobs
# ---------------------------------------------------------------------------
# Default modality weights — Field (direct observation) gets the highest
# vote because it's the only modality that can see disease.  Once Planet
# arrives and the satellite CNN is well-trained, weights can be re-tuned.
MODALITY_WEIGHTS: Final[dict[str, float]] = {
    "satellite": 0.30,
    "field":     0.40,
    "features":  0.30,
}

# Decision flags
CONSENSUS_FLAGS: Final[dict[str, str]] = {
    "HIGH_CONF_OK":     "All 3 modalities agree on healthy",
    "HIGH_CONF_ALERT":  "All 3 modalities agree on severe issue",
    "EARLY_WARNING":    "Features detect anomaly before satellite/field visible",
    "INVESTIGATE":      "Field detects disease not yet visible from satellite",
    "SATELLITE_FALSE":  "Satellite stress flag not confirmed by field/sensors",
    "EQUIPMENT_FAIL":   "Sensor data anomalous, satellite/field both healthy",
    "PARTIAL_AGREEMENT":"2/3 modalities agree",
    "NO_CONSENSUS":     "All 3 modalities disagree",
}

# Confidence buckets reported alongside the consensus class
CONSENSUS_CONFIDENCE_BUCKETS: Final[tuple[str, ...]] = ("HIGH", "MEDIUM", "LOW")


# ---------------------------------------------------------------------------
# MQTT (existing TRAK-AI broker — DO NOT change topic without warning)
# ---------------------------------------------------------------------------
# Confirmed from src/mqtt_orchestrator.py:77-78
MQTT_BROKER:       Final[str] = os.environ.get("TRAKAI_MQTT_BROKER", "localhost")
MQTT_PORT:         Final[int] = int(os.environ.get("TRAKAI_MQTT_PORT", "1883"))
MQTT_TOPIC_ROVER:  Final[str] = "trakaia/rover/data"          # subscribe: image + sensors
MQTT_TOPIC_FIELD_PREDICTION: Final[str] = "trakaia/visual/field"   # publish:   YOLOv8 result
MQTT_TOPIC_CONSENSUS:        Final[str] = "trakaia/visual/consensus"  # publish: 3-way result


# ---------------------------------------------------------------------------
# Planet API (stub while Education tier application is pending)
# ---------------------------------------------------------------------------
PLANET_API_KEY: Final[str] = os.environ.get("PLANET_API_KEY", "")
PLANET_API_KEY_AVAILABLE: Final[bool] = bool(PLANET_API_KEY)
PLANET_BASE_URL: Final[str] = "https://api.planet.com/data/v1"
# Until the key is live we substitute Sentinel-2 RGB chips through the
# existing FLOV S2 fetcher (see api_clients/sentinel2_imagery.py).
SATELLITE_STAND_IN_SOURCE: Final[str] = "sentinel2_rgb"      # vs "planet_psbsd"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
CONSENSUS_LOG: Final[Path] = LOGS_DIR / "visual_consensus.jsonl"


def ensure_dirs() -> None:
    """Idempotently create every writable directory."""
    for d in (
        VISUAL_DIR, PLANETSCOPE_DIR, FIELD_PHOTOS_DIR,
        CONSENSUS_PREDICTIONS_DIR, GROUND_TRUTH_DIR,
        MODELS_VISUAL_DIR, REPORTS_VISUAL_DIR, LOGS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


__all__ = [
    "PROJECT_ROOT", "VISUAL_DIR",
    "PLANETSCOPE_DIR", "FIELD_PHOTOS_DIR",
    "CONSENSUS_PREDICTIONS_DIR", "GROUND_TRUTH_DIR",
    "MODELS_VISUAL_DIR", "REPORTS_VISUAL_DIR", "LOGS_DIR",
    "YOLOV8_MODEL_PATH", "SATELLITE_CNN_PATH", "SATELLITE_CNN_METRICS_PATH",
    "EVRENLI_SITES", "MVP_SITE_ID", "Site",
    "SUNFLOWER_PHENOLOGY", "stage_for_doy",
    "HARMONIZED_LABELS", "HARMONIZED_INDEX",
    "YOLOV8_CLASS_NAMES", "YOLOV8_TO_HARMONIZED",
    "SATELLITE_CLASS_NAMES", "SATELLITE_TO_HARMONIZED",
    "feature_zscore_to_class",
    "FEATURE_Z_HEALTHY_MAX", "FEATURE_Z_MILD_STRESS_MAX",
    "MODALITY_WEIGHTS", "CONSENSUS_FLAGS",
    "CONSENSUS_CONFIDENCE_BUCKETS",
    "MQTT_BROKER", "MQTT_PORT",
    "MQTT_TOPIC_ROVER", "MQTT_TOPIC_FIELD_PREDICTION",
    "MQTT_TOPIC_CONSENSUS",
    "PLANET_API_KEY", "PLANET_API_KEY_AVAILABLE",
    "PLANET_BASE_URL", "SATELLITE_STAND_IN_SOURCE",
    "CONSENSUS_LOG",
    "ensure_dirs",
]
