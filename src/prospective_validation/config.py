"""
Central configuration for the Forward-Looking Operational Validation (FLOV) module.

Single source of truth for:
    - Pilot site coordinates (PLACEHOLDERS — to be replaced with real coords in Phase 6)
    - Filesystem paths (all via pathlib.Path for Windows compatibility)
    - Frozen feature schema (must match models/cp2/feature_names.json EXACTLY)
    - Validation time-windows
    - Champion artefact locations

This module is read-only. Do NOT mutate constants at runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Repository layout (resolved from this file's location)
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT: Final[Path] = _THIS_FILE.parents[2]   # …/Trak-AI_KDS
SRC_DIR: Final[Path] = PROJECT_ROOT / "src"
CP2_DIR: Final[Path] = SRC_DIR / "cp2_model"

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"
PROSPECTIVE_DIR: Final[Path] = DATA_DIR / "prospective"
HISTORICAL_CLIMATOLOGY_DIR: Final[Path] = DATA_DIR / "historical" / "climatology"
CACHE_DIR: Final[Path] = DATA_DIR / "cache" / "api"

REPORTS_DIR: Final[Path] = PROJECT_ROOT / "reports" / "prospective"
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"
DOCS_DIR: Final[Path] = PROJECT_ROOT / "docs"

KEYS_DIR: Final[Path] = PROJECT_ROOT / "keys"
GEE_SERVICE_ACCOUNT_KEY: Final[Path] = KEYS_DIR / "trak-ai-kds-d3e5e5b6e168.json"

# Master historical feature matrix (used by climatology builder)
MASTER_FEATURE_MATRIX: Final[Path] = PROCESSED_DIR / "master_feature_matrix_2017_2024.csv"

# ---------------------------------------------------------------------------
# Champion artefacts (FROZEN — do not modify)
# ---------------------------------------------------------------------------
# Per user decision: hybrid champion
#   - LSTM        → NDVI t+7 residual-delta prediction
#   - XGBoost     → end-of-season yield
# Both trained on 2017-2024, sunflower only for now.
LSTM_CHAMPION_PATH: Final[Path] = CP2_DIR / "model_lstm_sunflower.keras"
XGB_CHAMPION_PATH: Final[Path] = CP2_DIR / "model_xgb_sunflower.pkl"
SCALER_PATH: Final[Path] = CP2_DIR / "scaler_sunflower.pkl"
YIELD_XGB_PATH: Final[Path] = CP2_DIR / "yield_xgb_sunflower.pkl"
YIELD_SCALER_PATH: Final[Path] = CP2_DIR / "yield_scaler_sunflower.pkl"
FEATURE_NAMES_PATH: Final[Path] = CP2_DIR / "feature_names.json"
XGB_FEATURE_NAMES_PATH: Final[Path] = CP2_DIR / "xgb_feature_names_sunflower.json"

# ---------------------------------------------------------------------------
# Frozen feature contract (17 features, T=30 input window)
# Loaded once at import-time from the same JSON the training pipeline uses,
# so drift is impossible without an explicit edit to feature_names.json.
# ---------------------------------------------------------------------------
with FEATURE_NAMES_PATH.open("r", encoding="utf-8") as _fh:
    FEATURE_NAMES: Final[list[str]] = json.load(_fh)

assert len(FEATURE_NAMES) == 17, (
    f"Frozen contract violated: expected 17 features, got {len(FEATURE_NAMES)}"
)
NDVI_FEATURE: Final[str] = "NDVI_int"
NDVI_INDEX: Final[int] = FEATURE_NAMES.index(NDVI_FEATURE)
INPUT_WINDOW: Final[int] = 30          # T — frozen
FORECAST_HORIZON_DAYS: Final[int] = 7  # t+7
DELTA_SCALE: Final[float] = 0.30       # matches ScaleDelta in train_models_cp2.py

# ---------------------------------------------------------------------------
# Pilot sites — Vize/Evrenli (PLACEHOLDERS, replace before Phase 6)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Site:
    id: str
    name: str
    lat: float
    lon: float
    owner: str
    area_da: float        # decares (1 da = 1000 m²)

    @property
    def area_ha(self) -> float:
        return self.area_da / 10.0

    @property
    def subpixel_risk(self) -> bool:
        """30-m inward buffer + 10-m S2 pixel purity ⇒ < 5 ha is risky."""
        return self.area_ha < 5.0


EVRENLI_SITES: Final[tuple[Site, ...]] = (
    # NOTE: coordinates spread ~1-2 km apart so Sentinel-2 (10 m) returns
    # genuinely different pixels per site.  Crop mix mirrors Trakya reality:
    # 3 sunflower + 2 wheat fields.
    Site("EVR_01", "Kendi tarlam — Vize merkez",   41.045, 27.205, "self",       12.5),
    Site("EVR_02", "Komşu — Kuzey (Buğday)",       41.052, 27.218, "neighbor_1", 18.0),
    Site("EVR_03", "Komşu — Güney",                41.038, 27.192, "neighbor_2", 15.0),
    Site("EVR_04", "Komşu — Doğu (Buğday)",        41.057, 27.225, "neighbor_3", 10.0),
    Site("EVR_05", "Komşu — Batı",                 41.032, 27.184, "neighbor_4",  7.5),
)

# MVP site (single-site end-to-end before scaling)
MVP_SITE_ID: Final[str] = "EVR_01"

# S2 pixel-purity buffer (metres, inward from parcel boundary)
PIXEL_PURITY_BUFFER_M: Final[float] = 30.0

# ---------------------------------------------------------------------------
# Sunflower phenology (Trakya / NW Türkiye, day-of-year ranges)
# Drawn from agro_calendar.py + 2017-2024 NDVI peak DOY (≈150 in climatology).
# Used by the validator for per-stage metric breakdown.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PhenologyStage:
    name: str
    doy_start: int
    doy_end: int           # inclusive


SUNFLOWER_PHENOLOGY: Final[tuple[PhenologyStage, ...]] = (
    PhenologyStage("pre_season",   1,   104),  # winter / pre-emergence
    PhenologyStage("emergence",    105, 130),  # mid-Apr to mid-May
    PhenologyStage("vegetative",   131, 170),  # mid-May to mid-Jun
    PhenologyStage("flowering",    171, 200),  # mid-Jun to mid-Jul
    PhenologyStage("grain_fill",   201, 240),  # mid-Jul to late-Aug
    PhenologyStage("maturity",     241, 280),  # late-Aug to early-Oct
    PhenologyStage("post_harvest", 281, 366),  # rest of year
)


def stage_for_doy(doy: int) -> str:
    for s in SUNFLOWER_PHENOLOGY:
        if s.doy_start <= doy <= s.doy_end:
            return s.name
    return "unknown"

# ---------------------------------------------------------------------------
# Validation periods
# ---------------------------------------------------------------------------
VALIDATION_2025_START: Final[date] = date(2025, 1, 1)
VALIDATION_2026_START: Final[date] = date(2026, 4, 1)
VALIDATION_2026_END:   Final[date] = date(2026, 10, 31)
TRAINING_WINDOW_YEARS: Final[tuple[int, int]] = (2017, 2024)

# ---------------------------------------------------------------------------
# CDS API (new beta endpoint per user spec)
# ---------------------------------------------------------------------------
CDS_API_URL: Final[str] = "https://cds-beta.climate.copernicus.eu/api"

# ---------------------------------------------------------------------------
# Logging / caching policy
# ---------------------------------------------------------------------------
LOG_FILE: Final[Path] = LOGS_DIR / "flov.log"
AUDIT_FILE: Final[Path] = LOGS_DIR / "api_audit.jsonl"
INTEGRITY_LEDGER: Final[Path] = LOGS_DIR / "model_integrity.jsonl"
LOG_ROTATION: Final[str] = "100 MB"
LOG_RETENTION: Final[str] = "90 days"


def ensure_runtime_dirs() -> None:
    """Idempotently create every directory the runtime writes to."""
    for d in (
        PROSPECTIVE_DIR,
        PROSPECTIVE_DIR / "2025",
        PROSPECTIVE_DIR / "2026",
        HISTORICAL_CLIMATOLOGY_DIR,
        CACHE_DIR,
        REPORTS_DIR,
        FIGURES_DIR,
        LOGS_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
