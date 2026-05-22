"""
TRAK-AI KDS — Forward-Looking Operational Validation (FLOV)
============================================================
Frozen-model prospective validation for the sunflower NDVI champion (LSTM)
and the yield champion (XGBoost), trained on 2017-2024 and evaluated on
2025-now (true out-of-sample) data.

Public surface (Phase 1):
    config             — sites, paths, feature schema, validation periods
    logging_setup      — Loguru with 100 MB rotating files
    integrity          — SHA-256 model/file hashing + integrity ledger
    audit              — JSONL audit trail for every API call
    cache              — Hash-based response cache (never re-download)
    model_loader       — FrozenChampion (LSTM + XGBoost) load with hash check
    climatology        — DOY-mean baseline from master_feature_matrix_2017_2024

NEVER mutate or retrain the champion artefacts from this package.
"""

__all__ = [
    "config",
    "logging_setup",
    "integrity",
    "audit",
    "cache",
    "model_loader",
    "climatology",
]

__version__ = "0.1.0-phase1"
