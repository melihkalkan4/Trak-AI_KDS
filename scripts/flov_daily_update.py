"""
FLOV daily auto-update — wired to Windows Task Scheduler.

For each site in config.EVRENLI_SITES:
    1.  Refresh the prospective unified-features parquet up to today
        (incrementally — fetchers are hash-cached, so this is cheap).
    2.  Run the frozen LSTM predictor.
    3.  Run the validator against the unified actuals (NDVI_int).
    4.  Run the alert engine on the new predictions and append to
        logs/alerts.jsonl.

Idempotent: re-running on the same day is a no-op for the fetchers
(cache hit), and predictions/validation outputs are overwritten in
place. Designed to be invoked daily; if it misses a day the next run
catches up automatically.

Usage (CLI):
    python scripts/flov_daily_update.py              # all sites, current year
    python scripts/flov_daily_update.py --year 2026
    python scripts/flov_daily_update.py --site EVR_01

Wired by:
    scripts/install_flov_scheduled_task.ps1
"""

from __future__ import annotations

import argparse
import io
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

    from prospective_validation import (
        config, logging_setup, alerts as alerts_mod,
        actuals as actuals_mod,
    )
    from prospective_validation.current_data_fetcher import CurrentDataFetcher
    from prospective_validation.frozen_model_predictor import make_predictor
    from prospective_validation.live_validator import LiveValidator

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default=None,
                        help="Run a single site id (default: all)")
    parser.add_argument("--year", type=int, default=date.today().year,
                        help="Calendar year window (default: current)")
    parser.add_argument("--tolerance-days", type=int, default=2)
    args = parser.parse_args()

    config.ensure_runtime_dirs()
    target_sites = [s for s in config.EVRENLI_SITES
                    if args.site is None or s.id == args.site]
    if args.site and not target_sites:
        logger.error("Unknown site id: {}", args.site)
        return 1

    started = datetime.now(timezone.utc)
    logger.info("=== FLOV daily update started — {} sites, year={} ===",
                len(target_sites), args.year)

    fetcher   = CurrentDataFetcher()
    predictor = make_predictor(load_climatology=True)

    n_ok = 0
    n_fail = 0
    for site in target_sites:
        try:
            logger.info("[daily] {} — starting", site.id)

            # 1. Refresh features (cache-hit on stable months)
            df_feat = fetcher.fetch(site)
            if df_feat is None or df_feat.empty:
                logger.warning("[daily] {} — empty features; skipping", site.id)
                continue
            unified_path = (config.PROSPECTIVE_DIR / str(args.year)
                            / f"{site.id}_unified_features.parquet")
            df_feat.to_parquet(unified_path, index=False)
            logger.info("[daily] {} — features parquet refreshed: {} rows",
                        site.id, len(df_feat))

            # 2. Predict
            preds = predictor.predict_ndvi_series(df_feat)
            if preds.empty:
                logger.warning("[daily] {} — no predictions produced", site.id)
                continue
            out_parquet = (config.REPORTS_DIR
                           / f"{site.id}_{args.year}_predictions.parquet")
            preds.to_parquet(out_parquet, index=False)
            preds.to_csv(out_parquet.with_suffix(".csv"), index=False)
            logger.info("[daily] {} — predictions: {} rows -> {}",
                        site.id, len(preds), out_parquet.name)

            # 3. Validate (unified NDVI_int)
            actuals = actuals_mod.from_unified_features(unified_path)
            report = LiveValidator(site=site).report(
                preds, actuals, tolerance_days=args.tolerance_days,
            )
            report.matched.to_csv(
                config.REPORTS_DIR / f"{site.id}_{args.year}_validation.csv",
                index=False,
            )
            report.per_stage.to_csv(
                config.REPORTS_DIR / f"{site.id}_{args.year}_validation_per_stage.csv",
                index=False,
            )
            import json
            summary = {
                "site_id":            report.site_id,
                "year":               args.year,
                "source":             "unified",
                "tolerance_days":     args.tolerance_days,
                "n_predictions":      report.n_predictions,
                "n_matched":          report.n_matched,
                "coverage_pct":       report.coverage_pct,
                "overall_model":      report.overall,
                "overall_naive_persistence": report.overall_naive,
                "wilcoxon_model_vs_naive":   report.wilcoxon,
                "generated_utc":      datetime.now(timezone.utc).isoformat(),
            }
            (config.REPORTS_DIR / f"{site.id}_{args.year}_validation_summary.json"
             ).write_text(json.dumps(summary, indent=2, default=str),
                          encoding="utf-8")

            # 4. Alerts (only on the most recent 14 prediction days to avoid
            #    re-firing historical alerts)
            recent_cutoff = preds["target_date"].max() - \
                            __import__("pandas").Timedelta(days=14)
            recent = preds[preds["target_date"] >= recent_cutoff]
            new_alerts = alerts_mod.evaluate(recent, site=site)
            if new_alerts:
                alerts_mod.persist(new_alerts)

            logger.info(
                "[daily] {} OK — preds={} matched={} R2={:.3f} alerts={}",
                site.id, report.n_predictions, report.n_matched,
                report.overall.get("R2", float("nan")), len(new_alerts),
            )
            n_ok += 1

        except Exception as e:                                # noqa: BLE001
            logger.exception("[daily] {} FAILED — {}", site.id, e)
            n_fail += 1

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info("=== FLOV daily update finished in {:.1f}s — {} ok, {} fail ===",
                elapsed, n_ok, n_fail)
    return 0 if n_fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
