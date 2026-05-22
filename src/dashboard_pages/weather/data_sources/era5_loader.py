"""ERA5 historical loader — reads cached daily parquet/csv for a site.

The FLOV pipeline already produces `unified_features.parquet` with ERA5
columns merged in; this loader simply surfaces the weather subset.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ...shared.data_loaders import load_unified_features_with_era5


_ERA5_COLS = ("t2m_mean", "t2m_max", "t2m_min", "tp_sum",
              "vpd_mean", "soil_moisture", "rh_mean", "wind_mean")


def load_era5_history(site_id: str, year: int) -> Optional[pd.DataFrame]:
    df = load_unified_features_with_era5(site_id, year)
    if df is None or df.empty:
        return None
    keep = ["date"] + [c for c in _ERA5_COLS if c in df.columns]
    if len(keep) <= 1:
        return None
    out = df[keep].copy()
    out["date"] = pd.to_datetime(out["date"])
    return out.sort_values("date").reset_index(drop=True)


__all__ = ["load_era5_history"]
