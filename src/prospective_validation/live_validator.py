"""
Live validator: join predictions with cloud-free actuals, compute metrics.

Phase 4 of FLOV.  Inputs:

    predictions_df : output of FrozenPredictor.predict_ndvi_series
                     (columns include prediction_date, target_date,
                      predicted_ndvi, last_observed_ndvi)
    actuals_df     : columns [date, actual_ndvi]; NaN allowed (skipped)

Two join strategies:

  * ``tolerance_days = 0``  → strict day-of join.  Useful when actuals
    come from a daily interpolated source (NDVI_int).
  * ``tolerance_days >= 1`` → nearest-day join within ±N days of
    target_date.  Useful when actuals are raw S2 overpasses (every ~5
    days).  We pick the actual whose date is closest to target_date and
    is within the tolerance.

For each matched pair we record:
    abs_error          = |predicted - actual|
    abs_err_naive      = |last_observed - actual|       (persistence)
    days_to_actual     = |target_date - actual_date|    (≤ tolerance)

Outputs:
    LiveValidator.merge(...)            → matched DataFrame
    LiveValidator.report(...)           → ValidationReport dataclass with
                                          overall + per-stage metrics
                                          + Wilcoxon (vs persistence)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from . import config, metrics as M
from .logging_setup import logger


@dataclass
class ValidationReport:
    site_id: str
    n_predictions: int
    n_matched: int
    coverage_pct: float           # n_matched / n_predictions * 100
    overall: dict[str, float]
    overall_naive: dict[str, float]
    wilcoxon: dict[str, float]
    per_stage: pd.DataFrame
    matched: pd.DataFrame = field(repr=False)


@dataclass
class LiveValidator:
    site: config.Site

    def merge(
        self,
        predictions: pd.DataFrame,
        actuals: pd.DataFrame,
        *,
        tolerance_days: int = 2,
    ) -> pd.DataFrame:
        """
        Inner-join predictions (on target_date) with actuals (on actual_date),
        nearest within ±tolerance_days.  Drops rows with NaN actual_ndvi.
        """
        if predictions.empty:
            return predictions.head(0).assign(actual_ndvi=np.nan,
                                              actual_date=pd.NaT,
                                              days_to_actual=np.nan)

        pred = predictions.copy()
        act = actuals.copy()
        pred["target_date"] = pd.to_datetime(pred["target_date"])
        act["date"] = pd.to_datetime(act["date"])
        act = act.dropna(subset=["actual_ndvi"]).sort_values("date")
        if act.empty:
            logger.warning("[validator] actuals frame has no non-NaN rows")
            return pred.head(0).assign(actual_ndvi=np.nan,
                                       actual_date=pd.NaT,
                                       days_to_actual=np.nan)

        if tolerance_days == 0:
            merged = pred.merge(
                act.rename(columns={"date": "target_date"}),
                on="target_date", how="inner",
            )
            merged["actual_date"] = merged["target_date"]
            merged["days_to_actual"] = 0
        else:
            merged = pd.merge_asof(
                pred.sort_values("target_date"),
                act.rename(columns={"date": "actual_date"}),
                left_on="target_date", right_on="actual_date",
                direction="nearest",
                tolerance=pd.Timedelta(days=tolerance_days),
            )
            merged = merged.dropna(subset=["actual_ndvi"]).copy()
            merged["days_to_actual"] = (
                (merged["target_date"] - merged["actual_date"]).abs().dt.days
            )

        merged["abs_error"] = (merged["predicted_ndvi"] - merged["actual_ndvi"]).abs()
        if "last_observed_ndvi" in merged.columns:
            merged["abs_err_naive"] = (
                merged["last_observed_ndvi"] - merged["actual_ndvi"]
            ).abs()
        return merged.reset_index(drop=True)

    def report(
        self,
        predictions: pd.DataFrame,
        actuals: pd.DataFrame,
        *,
        tolerance_days: int = 2,
    ) -> ValidationReport:
        merged = self.merge(predictions, actuals, tolerance_days=tolerance_days)
        n_pred = len(predictions)
        n_match = len(merged)
        cov = (n_match / n_pred * 100.0) if n_pred else 0.0

        overall = M.compute_metrics(merged["predicted_ndvi"], merged["actual_ndvi"]) \
            if n_match else {"n": 0}

        if n_match and "last_observed_ndvi" in merged.columns:
            with_naive = M.persistence_baseline(merged)
            overall_naive = M.compute_metrics(with_naive["naive_pred"],
                                              with_naive["actual_ndvi"])
            wilc = M.wilcoxon_paired(
                with_naive["predicted_ndvi"],
                with_naive["actual_ndvi"],
                with_naive["naive_pred"],
            )
        else:
            overall_naive = {"n": 0}
            wilc = {"n": 0}

        per_stage = M.per_stage_metrics(merged) if n_match else pd.DataFrame()

        logger.info(
            "[validator] {}: matched {}/{} ({:.1f}%) — "
            "R²={:.3f}, MAE={:.4f}, naive MAE={:.4f}",
            self.site.id, n_match, n_pred, cov,
            overall.get("R2", float("nan")),
            overall.get("MAE", float("nan")),
            overall_naive.get("MAE", float("nan")),
        )

        return ValidationReport(
            site_id=self.site.id,
            n_predictions=n_pred,
            n_matched=n_match,
            coverage_pct=cov,
            overall=overall,
            overall_naive=overall_naive,
            wilcoxon=wilc,
            per_stage=per_stage,
            matched=merged,
        )


__all__ = ["LiveValidator", "ValidationReport"]
