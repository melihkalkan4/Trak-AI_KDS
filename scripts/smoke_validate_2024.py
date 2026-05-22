"""
Phase 4 smoke test — validator end-to-end on 2024 master-matrix slice.

This is NOT a true held-out test (2024 is inside the training window), it only
exercises the plumbing:
    1. preprocessing_cp2.load_and_clean + engineer_features on the master CSV
    2. FrozenPredictor.predict_ndvi_series on the 2024 rows
    3. actuals.from_master_matrix(use_raw=True) for cloud-free truth
    4. LiveValidator.report — overall, persistence, Wilcoxon, per-stage

A genuine 2025 prospective run will reuse the same validator unchanged.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path


try:
    sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(_project_root() / "src"))
    sys.path.insert(0, str(_project_root() / "src" / "cp2_model"))

    import pandas as pd

    from prospective_validation import (
        actuals as actuals_mod, config, logging_setup,
    )
    from prospective_validation.frozen_model_predictor import make_predictor
    from prospective_validation.live_validator import LiveValidator
    import preprocessing_cp2

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    site = next(s for s in config.EVRENLI_SITES if s.id == config.MVP_SITE_ID)
    print(f"\n=== SMOKE: validator on 2024 slice of master matrix (site={site.id}) ===\n")

    # 1. Run training-era preprocessing on the master CSV verbatim
    df_clean, _ = preprocessing_cp2.load_and_clean(str(config.MASTER_FEATURE_MATRIX))
    df_feat = preprocessing_cp2.engineer_features(df_clean)
    print(f"\n[smoke] feature-engineered rows : {len(df_feat)}")

    # 2. Predict on 2024 only (last full year of training data)
    df_2024 = df_feat[df_feat["date"].dt.year == 2024].reset_index(drop=True)
    print(f"[smoke] 2024 rows                : {len(df_2024)}")

    predictor = make_predictor(load_climatology=True)
    preds = predictor.predict_ndvi_series(df_2024)
    print(f"[smoke] predictions              : {len(preds)} rows")

    # 3. Actuals — raw NDVI from master (NaN on cloudy days)
    actuals = actuals_mod.from_master_matrix(use_raw=True)
    actuals_2024 = actuals[actuals["date"].dt.year == 2024].copy()
    print(f"[smoke] 2024 actuals (raw NDVI)  : "
          f"{actuals_2024['actual_ndvi'].notna().sum()} cloud-free / "
          f"{len(actuals_2024)} days")

    # 4. Validate
    validator = LiveValidator(site=site)
    report = validator.report(preds, actuals_2024, tolerance_days=2)

    print(f"\n--- Coverage ---")
    print(f"  matched : {report.n_matched}/{report.n_predictions} "
          f"({report.coverage_pct:.1f}%)")

    print(f"\n--- Overall (model) ---")
    for k in ("n", "R2", "MAE", "RMSE", "bias", "MAPE_pct"):
        v = report.overall.get(k)
        if v is None: continue
        if k == "n":
            print(f"  {k:9s}: {v}")
        else:
            print(f"  {k:9s}: {v:.4f}" if v == v else f"  {k:9s}: nan")

    print(f"\n--- Persistence baseline ---")
    for k in ("R2", "MAE", "RMSE", "bias"):
        v = report.overall_naive.get(k)
        if v is None: continue
        print(f"  {k:9s}: {v:.4f}" if v == v else f"  {k:9s}: nan")

    print(f"\n--- Wilcoxon (model |err| < naive |err|, one-sided) ---")
    for k in ("n", "mean_abs_err_model", "mean_abs_err_naive",
              "median_abs_err_model", "median_abs_err_naive",
              "wilcoxon_statistic", "wilcoxon_p_value"):
        v = report.wilcoxon.get(k)
        if v is None: continue
        if k == "n":
            print(f"  {k:24s}: {v}")
        elif v != v:
            print(f"  {k:24s}: nan")
        else:
            print(f"  {k:24s}: {v:.4f}")

    print(f"\n--- Per phenological stage ---")
    if not report.per_stage.empty:
        print(report.per_stage.to_string(index=False))
    else:
        print("  (no matches)")

    print(f"\n[smoke] PASS — validator end-to-end ran without error.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
