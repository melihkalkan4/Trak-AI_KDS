"""
Phase 1 end-to-end health check for the FLOV module.

What this verifies (in order, stopping at first hard failure):

    [1] Module imports cleanly
    [2] Runtime directories exist / can be created
    [3] Frozen artefacts present (LSTM, XGBoost, scaler, feature_names)
    [4] SHA-256 ledger first-sight (or re-verification) for every artefact
    [5] FrozenChampion loads (custom layers register, Keras + XGB inflate)
    [6] Climatology artefact present (builds it if missing) and re-hashes
    [7] DOY lookup smoke test
    [8] OPTIONAL  — GEE auth via service-account key (skipped if absent)
    [9] OPTIONAL  — CDS rc-file present (warns, does not fail)
    [10] Test prediction on the last training-window sample (sanity only —
         NOT a validation metric; just confirms forward pass works)

Exit code 0 ⇒ Phase 1 green.  Non-zero ⇒ see logs/flov.log for trace.
"""

from __future__ import annotations

import io
import sys
import traceback
from pathlib import Path

# Force UTF-8 stdout on Windows so progress prints survive cp1254 default.
try:
    sys.stdout.reconfigure(encoding="utf-8")          # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")          # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(_project_root() / "src"))

    # ------------------------------------------------------------------ [1]
    print("\n=== Phase 1 health check — TRAK-AI FLOV ===\n")
    print("[1] Importing prospective_validation ...")
    from prospective_validation import (
        config, logging_setup, integrity, audit, cache,
        model_loader, climatology,
    )

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    # ------------------------------------------------------------------ [2]
    print("[2] Ensuring runtime directories ...")
    config.ensure_runtime_dirs()
    for d in (config.LOGS_DIR, config.CACHE_DIR, config.HISTORICAL_CLIMATOLOGY_DIR,
              config.PROSPECTIVE_DIR, config.REPORTS_DIR):
        assert d.exists(), f"Directory not created: {d}"
    print("    OK")

    # ------------------------------------------------------------------ [3]
    print("[3] Verifying frozen artefacts on disk ...")
    required = {
        "LSTM champion (sunflower)":  config.LSTM_CHAMPION_PATH,
        "XGBoost (sunflower, NDVI)":  config.XGB_CHAMPION_PATH,
        "Scaler (sunflower)":         config.SCALER_PATH,
        "feature_names.json":         config.FEATURE_NAMES_PATH,
    }
    optional = {
        "yield_xgb (sunflower)":      config.YIELD_XGB_PATH,
        "yield_scaler (sunflower)":   config.YIELD_SCALER_PATH,
        "xgb_feature_names (sunf)":   config.XGB_FEATURE_NAMES_PATH,
    }
    for label, path in required.items():
        if not path.exists():
            logger.error("[health] MISSING required artefact: {} ({})", label, path)
            return 11
        print(f"    OK   {label:32s} ->{path.name}")
    for label, path in optional.items():
        marker = "OK  " if path.exists() else "WARN"
        print(f"    {marker} {label:32s} ->{path.name if path.exists() else '(absent)'}")

    # ------------------------------------------------------------------ [4]
    print("[4] Hashing artefacts (ledger first-sight or re-verify) ...")
    for role, path in (
        ("lstm_champion_sunflower", config.LSTM_CHAMPION_PATH),
        ("xgb_yield_sunflower",     config.XGB_CHAMPION_PATH),
        ("scaler_sunflower",        config.SCALER_PATH),
        ("feature_names",           config.FEATURE_NAMES_PATH),
    ):
        sha = integrity.ensure_unchanged(path, role=role)
        print(f"    {role:32s} sha256={sha[:16]}...")
    for role, path in (
        ("yield_xgb_sunflower",     config.YIELD_XGB_PATH),
        ("yield_scaler_sunflower",  config.YIELD_SCALER_PATH),
        ("xgb_feature_names_sunf",  config.XGB_FEATURE_NAMES_PATH),
    ):
        if path.exists():
            sha = integrity.ensure_unchanged(path, role=role)
            print(f"    {role:32s} sha256={sha[:16]}...")

    # ------------------------------------------------------------------ [5]
    print("[5] Loading FrozenChampion (this imports TensorFlow — may be slow) ...")
    champion = model_loader.load_frozen_champion()
    print(f"    LSTM layers       : {len(champion.lstm.layers)}")
    print(f"    LSTM trainable    : {champion.lstm.trainable}")
    print(f"    NDVI index        : {champion.ndvi_index}")
    print(f"    XGB yield loaded  : {champion.xgb_yield is not None}")
    print(f"    Feature names ok  : {champion.feature_names == config.FEATURE_NAMES}")

    # ------------------------------------------------------------------ [6]
    print("[6] Climatology ...")
    if not climatology.CLIMATOLOGY_PATH.exists():
        if not config.MASTER_FEATURE_MATRIX.exists():
            logger.error("[health] cannot build climatology — master matrix missing: {}",
                         config.MASTER_FEATURE_MATRIX)
            return 12
        print("    building from master_feature_matrix_2017_2024.csv ...")
        climatology.build_climatology()
    clim = climatology.load_climatology()
    print(f"    climatology rows  : {len(clim.table)}")
    print(f"    sha256            : "
          f"{integrity.read_ledger().get('sunflower_doy_climatology', {}).get('sha256', '???')[:16]}...")

    # ------------------------------------------------------------------ [7]
    print("[7] DOY lookup smoke test ...")
    for d in (1, 60, 150, 200, 250, 350):
        v = clim.value_at(d)
        print(f"    DOY {d:>3d} ->climatology NDVI {v:.4f}")

    # ------------------------------------------------------------------ [8]
    print("[8] GEE service-account key ...")
    if config.GEE_SERVICE_ACCOUNT_KEY.exists():
        try:
            import json
            with config.GEE_SERVICE_ACCOUNT_KEY.open("r", encoding="utf-8") as fh:
                key_json = json.load(fh)
            print(f"    OK  client_email = {key_json.get('client_email', '?')}")
        except Exception as e:        # noqa: BLE001
            logger.warning("[health] could not parse GEE key json: {}", e)
            print(f"    WARN unreadable JSON ({e})")
    else:
        print(f"    WARN absent ->{config.GEE_SERVICE_ACCOUNT_KEY}")

    # ------------------------------------------------------------------ [9]
    print("[9] CDS credentials ...")
    rc = Path.home() / ".cdsapirc"
    if rc.exists():
        print(f"    OK  {rc} present")
    else:
        print(f"    WARN absent ->run scripts/setup_cds_credentials.py before Phase 2")

    # ----------------------------------------------------------------- [10]
    print("[10] Forward-pass sanity (last training-window sample) ...")
    try:
        import numpy as np
        X = np.load(config.CP2_DIR / "X_sunflower.npy")
        if X.ndim != 3 or X.shape[1:] != (config.INPUT_WINDOW, len(config.FEATURE_NAMES)):
            raise RuntimeError(f"Unexpected X_sunflower shape: {X.shape}")
        window = X[-1]  # most recent training window
        out = champion.predict_ndvi_window(window)
        with audit.audited("phase1_smoke", {"sample": "X_sunflower[-1]"}) as scratch:
            scratch["extra"] = out
        print(f"    last_ndvi         = {out['last_ndvi']:+.4f}")
        print(f"    predicted_ndvi    = {out['predicted_ndvi']:+.4f}")
        print(f"    residual_delta    = {out['residual_delta']:+.4f}")
        print(f"    anomaly vs DOY    = {clim.anomaly(out['predicted_ndvi'], 200):+.4f}  (DOY 200 proxy)")
    except Exception as e:            # noqa: BLE001
        logger.error("[health] forward-pass sanity failed: {}", e)
        traceback.print_exc()
        return 13

    print("\n=== Phase 1 GREEN ===")
    print(f"Ledger : {config.INTEGRITY_LEDGER}")
    print(f"Audit  : {config.AUDIT_FILE}")
    print(f"Log    : {config.LOG_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
