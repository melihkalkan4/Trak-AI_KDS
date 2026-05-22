"""
ERA5-Land daily climate fetcher.

We do NOT call :func:`cp1_etl.mod_era5_cds.fetch_era5_data` directly, because
that helper iterates over full years and writes shared raw zips that would
collide between sites and re-download already-cached months.  Instead we
re-use its **inner** functions (download_monthly_data, extract_netcdf_from_zip,
open_netcdf_with_fallback, process_netcdf_to_daily, convert_to_agronomic_units)
in our own per-month loop, with:

    * one cache entry per (lat, lon, year, month)
    * one audit record per month
    * a temporary scratch dir we clean up
    * skip-on-future-month policy (ERA5 lags real time)

The returned DataFrame schema matches what mod_era5_cds.fetch_era5_data
would have produced (date + agronomic units):

    date, t2m_mean, t2m_min, t2m_max, d2m_mean, tp_sum, ssr_sum, e_sum
"""

from __future__ import annotations

import hashlib
import pickle
import sys
import tempfile
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

from .. import cache, config
from ..audit import audited
from ..logging_setup import logger


_CP1_ON_PATH = False
_ERA5_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "surface_net_solar_radiation",
    "total_evaporation",
]


def _ensure_cp1_path() -> None:
    global _CP1_ON_PATH
    if _CP1_ON_PATH:
        return
    cp1 = config.SRC_DIR / "cp1_etl"
    if str(cp1) not in sys.path:
        sys.path.insert(0, str(cp1))
    _CP1_ON_PATH = True


def _iter_months(start: date, end: date) -> Iterator[tuple[int, int]]:
    """Inclusive (year, month) pairs covering [start, end]."""
    cur = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    while cur <= last:
        yield cur.year, cur.month
        # advance one month
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def _month_in_future(year: int, month: int, today: date) -> bool:
    """ERA5 is unavailable for months that have not started yet."""
    return date(year, month, 1) > today


def _cache_params(site: config.Site, year: int, month: int) -> dict:
    return {
        "source": "reanalysis-era5-land",
        "site_id": site.id,
        "lat": round(site.lat, 6),
        "lon": round(site.lon, 6),
        "area_pad_deg": 0.1,                # matches mod_era5_cds default
        "year": year,
        "month": month,
        "variables": _ERA5_VARIABLES,
    }


def _download_and_process_month(
    site: config.Site, year: int, month: int, scratch_dir: Path,
) -> Optional[pd.DataFrame]:
    """One-month fetch using cp1_etl's internal helpers."""
    _ensure_cp1_path()
    import importlib
    era5_mod = importlib.import_module("mod_era5_cds")
    import cdsapi

    area = [site.lat + 0.1, site.lon - 0.1, site.lat - 0.1, site.lon + 0.1]
    zip_path = scratch_dir / f"era5_{site.id}_{year}_{month:02d}.zip"

    try:
        client = cdsapi.Client()
    except Exception as e:                          # noqa: BLE001
        logger.error("[era5] cdsapi client init failed: {}", e)
        return None

    ok = era5_mod.download_monthly_data(
        client, year, month, area, _ERA5_VARIABLES, str(zip_path)
    )
    if not ok:
        return None

    nc_path = era5_mod.extract_netcdf_from_zip(str(zip_path), str(scratch_dir))
    if nc_path is None:
        era5_mod.cleanup_files(str(zip_path))
        return None

    ds = era5_mod.open_netcdf_with_fallback(nc_path)
    if ds is None:
        era5_mod.cleanup_files(str(zip_path), nc_path)
        return None

    df_daily = era5_mod.process_netcdf_to_daily(ds, site.lat, site.lon)
    try:
        ds.close()
    except Exception:                                # noqa: BLE001
        pass
    era5_mod.cleanup_files(str(zip_path), nc_path)
    if df_daily is None:
        return None

    # Agronomic units (K→°C, m→mm, rounding)
    df_daily = era5_mod.convert_to_agronomic_units(df_daily)
    return df_daily


def fetch_era5_daily(
    site: config.Site,
    start_date: date,
    end_date: date,
    *,
    force: bool = False,
    today: Optional[date] = None,
) -> pd.DataFrame:
    """
    Returns a daily-aggregated, unit-converted ERA5-Land DataFrame for
    [start_date, end_date] for ``site``.

    Per-month results are cached.  An already-cached month is never
    re-downloaded.  Future months (past ``today``) are skipped with a log
    line, not an error.
    """
    if end_date < start_date:
        raise ValueError(f"end_date {end_date} precedes start_date {start_date}")
    today = today or datetime.now(timezone.utc).date()

    monthly_dfs: list[pd.DataFrame] = []
    with tempfile.TemporaryDirectory(prefix="flov_era5_") as tmp:
        scratch_dir = Path(tmp)
        for year, month in _iter_months(start_date, end_date):
            if _month_in_future(year, month, today):
                logger.info("[era5] skipping future month {}-{:02d}", year, month)
                continue

            params = _cache_params(site, year, month)

            # ----- cache lookup ---------------------------------------
            if not force:
                cached = cache.get_pickle("era5_cds_month", params)
                if cached is not None:
                    with audited("era5_cds", params) as scratch:
                        scratch["cache_hit"] = True
                        scratch["extra"] = {"rows": len(cached)}
                    monthly_dfs.append(cached)
                    continue

            # ----- network --------------------------------------------
            with audited("era5_cds", params) as scratch:
                df_month = _download_and_process_month(site, year, month, scratch_dir)
                if df_month is None or df_month.empty:
                    scratch["status"] = "EMPTY_OR_FAIL"
                    logger.warning("[era5] {}-{:02d} {} returned no data",
                                   year, month, site.id)
                    continue
                payload = pickle.dumps(df_month)
                scratch["response_bytes"] = len(payload)
                scratch["response_sha256"] = hashlib.sha256(payload).hexdigest()
                scratch["extra"] = {"rows": len(df_month)}

            cache.put_pickle("era5_cds_month", params, df_month)
            monthly_dfs.append(df_month)

    if not monthly_dfs:
        logger.error("[era5] no months returned data for {} {}→{}",
                     site.id, start_date, end_date)
        return pd.DataFrame()

    out = pd.concat(monthly_dfs, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)
    mask = (out["date"].dt.date >= start_date) & (out["date"].dt.date <= end_date)
    out = out.loc[mask].reset_index(drop=True)
    logger.info("[era5] {} {}→{}: {} daily rows from {} months",
                site.id, start_date, end_date, len(out), len(monthly_dfs))
    return out


__all__ = ["fetch_era5_daily"]
