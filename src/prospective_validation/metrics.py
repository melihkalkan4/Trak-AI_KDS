"""
Validation metrics for paired (predicted, actual) NDVI series.

We deliberately keep this self-contained — sklearn is already a dependency
but we re-implement metrics in numpy so failures here are easy to diagnose
and the math is auditable for thesis Section 4.

Public API
----------
compute_metrics(predicted, actual)            → dict of scalar metrics
persistence_baseline(merged_df)               → adds 'naive_pred' column
wilcoxon_paired(pred, actual, naive)          → dict with W, p, n
per_stage_metrics(merged_df, doy_col)         → DataFrame per phenology stage
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from . import config


# ---------------------------------------------------------------------------
# Scalar metrics
# ---------------------------------------------------------------------------
def _to_arrays(predicted, actual) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(predicted, dtype="float64")
    a = np.asarray(actual,    dtype="float64")
    mask = np.isfinite(p) & np.isfinite(a)
    return p[mask], a[mask]


def compute_metrics(predicted, actual) -> dict[str, float]:
    """
    R² (1 − SSres/SStot), MAE, RMSE, bias (mean residual), MAPE (%).

    Returns 'n' as well so the caller can spot tiny-sample artefacts.
    """
    p, a = _to_arrays(predicted, actual)
    n = int(len(p))
    out = {"n": n}
    if n == 0:
        return {**out, "R2": np.nan, "MAE": np.nan, "RMSE": np.nan,
                "bias": np.nan, "MAPE_pct": np.nan}

    res = p - a
    ss_res = float(np.sum(res * res))
    ss_tot = float(np.sum((a - a.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

    out.update(
        R2=float(r2),
        MAE=float(np.mean(np.abs(res))),
        RMSE=float(np.sqrt(np.mean(res * res))),
        bias=float(np.mean(res)),
        MAPE_pct=float(np.mean(np.abs(res / np.where(np.abs(a) < 1e-6, np.nan, a)))) * 100.0,
    )
    return out


# ---------------------------------------------------------------------------
# Persistence baseline (naïve: predict t+7 NDVI = NDVI at prediction_date)
# ---------------------------------------------------------------------------
def persistence_baseline(merged: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'naive_pred' column equal to ``last_observed_ndvi``.

    This is the standard agronomic naïve baseline.  A model that fails to
    beat persistence on R² + MAE is contributing nothing.
    """
    if "last_observed_ndvi" not in merged.columns:
        raise ValueError("persistence_baseline needs 'last_observed_ndvi'")
    out = merged.copy()
    out["naive_pred"] = out["last_observed_ndvi"]
    return out


# ---------------------------------------------------------------------------
# Wilcoxon signed-rank (paired, two-sided) — distribution-free
# ---------------------------------------------------------------------------
def wilcoxon_paired(
    predicted, actual, naive,
) -> dict[str, float]:
    """
    Wilcoxon signed-rank on |predicted - actual| vs |naive - actual|.

    Negative median difference ⇒ model errors are smaller than naïve.
    Uses scipy.stats.wilcoxon when available; otherwise returns NaN p.
    """
    p = np.asarray(predicted, dtype="float64")
    a = np.asarray(actual,    dtype="float64")
    n = np.asarray(naive,     dtype="float64")
    mask = np.isfinite(p) & np.isfinite(a) & np.isfinite(n)
    p, a, n = p[mask], a[mask], n[mask]
    abs_m = np.abs(p - a)
    abs_n = np.abs(n - a)
    out = {
        "n": int(len(p)),
        "median_abs_err_model": float(np.median(abs_m)) if len(p) else np.nan,
        "median_abs_err_naive": float(np.median(abs_n)) if len(p) else np.nan,
        "mean_abs_err_model":   float(np.mean(abs_m))   if len(p) else np.nan,
        "mean_abs_err_naive":   float(np.mean(abs_n))   if len(p) else np.nan,
    }
    try:
        from scipy.stats import wilcoxon
        if len(p) < 6:
            out["wilcoxon_statistic"] = np.nan
            out["wilcoxon_p_value"]   = np.nan
        else:
            stat, pval = wilcoxon(abs_m, abs_n, alternative="less", zero_method="zsplit")
            out["wilcoxon_statistic"] = float(stat)
            out["wilcoxon_p_value"]   = float(pval)
    except ImportError:
        out["wilcoxon_statistic"] = np.nan
        out["wilcoxon_p_value"]   = np.nan
    return out


# ---------------------------------------------------------------------------
# Per-phenological-stage breakdown
# ---------------------------------------------------------------------------
def per_stage_metrics(
    merged: pd.DataFrame,
    *,
    target_date_col: str = "target_date",
    predicted_col:   str = "predicted_ndvi",
    actual_col:      str = "actual_ndvi",
) -> pd.DataFrame:
    """
    Group rows by sunflower phenological stage (DOY of ``target_date``)
    and compute compute_metrics per group.
    """
    if merged.empty:
        return pd.DataFrame()
    out = merged.copy()
    out[target_date_col] = pd.to_datetime(out[target_date_col])
    out["doy"]   = out[target_date_col].dt.dayofyear
    out["stage"] = out["doy"].apply(config.stage_for_doy)

    rows = []
    for stage_name in [s.name for s in config.SUNFLOWER_PHENOLOGY]:
        sub = out[out["stage"] == stage_name]
        if sub.empty:
            continue
        m = compute_metrics(sub[predicted_col], sub[actual_col])
        rows.append({"stage": stage_name, **m})
    return pd.DataFrame(rows)


__all__ = [
    "compute_metrics",
    "persistence_baseline",
    "wilcoxon_paired",
    "per_stage_metrics",
]
