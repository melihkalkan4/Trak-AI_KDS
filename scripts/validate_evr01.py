"""
Phase 4 runner — predicted-vs-actual validation for one site.

Modes
-----
    --source unified  : read predictions parquet (Phase 3 output) and
                        actuals from the unified-features parquet
                        (Phase 2 output).  Daily interpolated NDVI_int.
    --source s2       : actuals from a fresh GEE pull on target_date
                        bounds (cloud-free overpasses only — gold std).
    --source master   : actuals from the 2017-2024 master CSV
                        (cloud-free raw NDVI).  Useful for backtest
                        smoke tests on the training era.

Outputs
-------
    reports/prospective/<site>_<year>_validation.csv      (per-row matched)
    reports/prospective/<site>_<year>_validation_summary.json
    reports/prospective/<site>_<year>_validation_per_stage.csv
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import date, datetime, timezone
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
    import pandas as pd
    from prospective_validation import (
        actuals as actuals_mod, config, logging_setup,
    )
    from prospective_validation.live_validator import LiveValidator

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=config.MVP_SITE_ID)
    parser.add_argument("--year", type=int,
                        default=config.VALIDATION_2025_START.year)
    parser.add_argument("--source", choices=["unified", "s2", "master"],
                        default="unified")
    parser.add_argument("--tolerance-days", type=int, default=2,
                        help="Nearest-day tolerance for actual_date join "
                             "(0 = strict, 2 default for raw S2)")
    parser.add_argument("--predictions",
                        help="Override predictions parquet path",
                        default=None)
    args = parser.parse_args()

    site = next((s for s in config.EVRENLI_SITES if s.id == args.site), None)
    if site is None:
        logger.error("Unknown site id: {}", args.site)
        return 1

    # Predictions
    preds_path = (Path(args.predictions) if args.predictions else
                  config.REPORTS_DIR / f"{site.id}_{args.year}_predictions.parquet")
    if not preds_path.exists():
        logger.error("Predictions parquet missing: {}", preds_path)
        print(f"\nERROR: run scripts/predict_evr01.py first to produce {preds_path}")
        return 2
    predictions = pd.read_parquet(preds_path)

    # Actuals
    print(f"\n=== Validating {site.id} / {args.year}  (source={args.source}, "
          f"tol=±{args.tolerance_days}d) ===\n")
    if args.source == "unified":
        unified = (config.PROSPECTIVE_DIR / str(args.year)
                   / f"{site.id}_unified_features.parquet")
        actuals = actuals_mod.from_unified_features(unified)
    elif args.source == "s2":
        start = predictions["target_date"].min().date()
        end   = predictions["target_date"].max().date()
        actuals = actuals_mod.from_sentinel2_fetch(site, start, end)
    else:  # master
        actuals = actuals_mod.from_master_matrix(use_raw=True)

    print(f"Predictions       : {len(predictions)} rows from {preds_path.name}")
    print(f"Actuals           : {len(actuals)} rows (source={actuals['source'].iloc[0] if len(actuals) else '—'})")

    validator = LiveValidator(site=site)
    report = validator.report(predictions, actuals,
                              tolerance_days=args.tolerance_days)

    # Write outputs
    out_dir = config.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    matched_csv = out_dir / f"{site.id}_{args.year}_validation.csv"
    per_stage_csv = out_dir / f"{site.id}_{args.year}_validation_per_stage.csv"
    summary_json = out_dir / f"{site.id}_{args.year}_validation_summary.json"

    report.matched.to_csv(matched_csv, index=False)
    report.per_stage.to_csv(per_stage_csv, index=False)
    summary = {
        "site_id": report.site_id,
        "year": args.year,
        "source": args.source,
        "tolerance_days": args.tolerance_days,
        "n_predictions": report.n_predictions,
        "n_matched": report.n_matched,
        "coverage_pct": report.coverage_pct,
        "overall_model": report.overall,
        "overall_naive_persistence": report.overall_naive,
        "wilcoxon_model_vs_naive": report.wilcoxon,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # Pretty print
    print()
    print(f"Coverage          : {report.n_matched}/{report.n_predictions} "
          f"({report.coverage_pct:.1f}%)")
    print()
    print(f"--- Overall ---")
    for k in ("n", "R2", "MAE", "RMSE", "bias", "MAPE_pct"):
        v = report.overall.get(k)
        if v is None:
            continue
        if k == "n":
            print(f"  {k:8s}: {v}")
        else:
            print(f"  {k:8s}: {v:.4f}" if v == v else f"  {k:8s}: nan")

    print(f"\n--- Persistence baseline ---")
    for k in ("R2", "MAE", "RMSE", "bias"):
        v = report.overall_naive.get(k)
        if v is None:
            continue
        print(f"  {k:8s}: {v:.4f}" if v == v else f"  {k:8s}: nan")

    print(f"\n--- Wilcoxon paired (model |err| < naive |err|, one-sided) ---")
    for k in ("n", "mean_abs_err_model", "mean_abs_err_naive",
              "median_abs_err_model", "median_abs_err_naive",
              "wilcoxon_statistic", "wilcoxon_p_value"):
        v = report.wilcoxon.get(k)
        if v is None:
            continue
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

    print(f"\n--- Outputs ---")
    print(f"  matched rows  : {matched_csv}")
    print(f"  per-stage     : {per_stage_csv}")
    print(f"  summary JSON  : {summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
