"""
Run the frozen NDVI predictor on a site's unified-feature parquet.

Phase 3 runner.  Reads
``data/prospective/<year>/<site_id>_unified_features.parquet``, applies the
frozen LSTM + scaler + climatology, and writes
``reports/prospective/<site_id>_<year>_predictions.parquet`` plus a small
CSV summary.

Usage
-----
    python scripts/predict_evr01.py                  # EVR_01, 2025
    python scripts/predict_evr01.py --year 2026
    python scripts/predict_evr01.py --site EVR_02
    python scripts/predict_evr01.py --plumbing       # use training X_sunflower.npy
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_plumbing_smoke(predictor, champion):
    """
    Smoke test using the *already-scaled* training windows.  This bypasses
    the parquet + scaler entirely and just confirms the Keras forward pass
    works on real input shapes.
    """
    import numpy as np
    X = np.load(_project_root() / "src" / "cp2_model" / "X_sunflower.npy")
    print(f"\n[plumbing] X_sunflower.npy shape={X.shape}, "
          f"dtype={X.dtype}, last 5 windows:")
    for w in X[-5:]:
        out = champion.predict_ndvi_window(w)
        print(f"  last={out['last_ndvi']:+.4f}  pred={out['predicted_ndvi']:+.4f}  "
              f"delta={out['residual_delta']:+.4f}")


def main() -> int:
    sys.path.insert(0, str(_project_root() / "src"))

    from prospective_validation import config, logging_setup
    from prospective_validation.frozen_model_predictor import make_predictor

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=config.MVP_SITE_ID)
    parser.add_argument("--year", type=int,
                        default=config.VALIDATION_2025_START.year)
    parser.add_argument("--plumbing", action="store_true",
                        help="Run a forward-pass smoke test on the training "
                             "X_sunflower.npy and exit.")
    args = parser.parse_args()

    print(f"\n=== Frozen-model NDVI predictor — site={args.site}, year={args.year} ===\n")

    predictor = make_predictor(load_climatology=True)
    print(f"LSTM sha256       : {predictor.champion.artefact_hashes['lstm_champion_sunflower'][:16]}...")
    print(f"Scaler sha256     : {predictor.champion.artefact_hashes['scaler_sunflower'][:16]}...")
    print(f"Feature contract  : {len(predictor.champion.feature_names)} features, "
          f"NDVI@idx {predictor.champion.ndvi_index}")
    print(f"Climatology       : {len(predictor.climatology.table)} DOY rows loaded")

    if args.plumbing:
        _run_plumbing_smoke(predictor, predictor.champion)
        return 0

    parquet = (config.PROSPECTIVE_DIR / str(args.year)
               / f"{args.site}_unified_features.parquet")
    if not parquet.exists():
        logger.error("Unified features parquet missing: {}", parquet)
        print(f"\nERROR: expected parquet at {parquet}")
        print("       Run scripts/fetch_evr01_2025.py first (or --plumbing for smoke).")
        return 2

    import pandas as pd
    df = pd.read_parquet(parquet)
    print(f"Input parquet     : {parquet}")
    print(f"Rows              : {len(df)}  ({df['date'].min().date()} → "
          f"{df['date'].max().date()})")
    print()

    preds = predictor.predict_ndvi_series(df)
    if preds.empty:
        print("No predictions produced (input shorter than 30 days).")
        return 3

    out_dir = config.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = out_dir / f"{args.site}_{args.year}_predictions.parquet"
    out_csv     = out_dir / f"{args.site}_{args.year}_predictions.csv"
    preds.to_parquet(out_parquet, index=False)
    preds.to_csv(out_csv, index=False)

    print(f"\n=== DONE ===")
    print(f"Predictions       : {len(preds)} rows")
    print(f"First / last      : {preds['prediction_date'].iloc[0].date()} -> "
          f"{preds['target_date'].iloc[0].date()}  ...  "
          f"{preds['prediction_date'].iloc[-1].date()} -> "
          f"{preds['target_date'].iloc[-1].date()}")
    print(f"predicted_ndvi    : "
          f"min={preds['predicted_ndvi'].min():+.4f}, "
          f"mean={preds['predicted_ndvi'].mean():+.4f}, "
          f"max={preds['predicted_ndvi'].max():+.4f}")
    print(f"residual_delta    : "
          f"min={preds['residual_delta'].min():+.4f}, "
          f"mean={preds['residual_delta'].mean():+.4f}, "
          f"max={preds['residual_delta'].max():+.4f}")
    print(f"anomaly vs DOY    : "
          f"min={preds['anomaly_vs_climatology'].min():+.4f}, "
          f"mean={preds['anomaly_vs_climatology'].mean():+.4f}, "
          f"max={preds['anomaly_vs_climatology'].max():+.4f}")
    print(f"Parquet           : {out_parquet}")
    print(f"CSV               : {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
