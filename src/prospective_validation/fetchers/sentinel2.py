"""
Sentinel-2 daily NDVI/EVI/NDWI fetcher.

Wraps :func:`cp1_etl.mod_s2_gee.fetch_s2_data` (which downloads a full
year-range at a time) and:

  * builds the ROI polygon via :func:`geometry.site_polygon_coords`
  * filters the returned DataFrame to ``[start_date, end_date]``
  * caches the *post-filter* DataFrame keyed by site + date range + polygon
  * audits the call (cache_hit, latency, response size, payload SHA-256)

Re-fetching with the same ``end_date`` is a pure cache hit; extending
``end_date`` recomputes (cheap on incremental runs because the year-range
itself stays the same and GEE responses are fast).
"""

from __future__ import annotations

import hashlib
import pickle
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from .. import cache, config, geometry
from ..audit import audited
from ..logging_setup import logger

# Inject cp1_etl onto sys.path lazily — we don't want a global side-effect
# on import.
_CP1_ON_PATH = False


def _ensure_cp1_path() -> None:
    global _CP1_ON_PATH
    if _CP1_ON_PATH:
        return
    cp1 = config.SRC_DIR / "cp1_etl"
    if str(cp1) not in sys.path:
        sys.path.insert(0, str(cp1))
    _CP1_ON_PATH = True


def _cache_params(
    site: config.Site,
    start_date: date,
    end_date: date,
    poly: geometry.SitePolygon,
) -> dict:
    return {
        "site_id": site.id,
        "lat": round(site.lat, 6),
        "lon": round(site.lon, 6),
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "polygon": geometry.polygon_signature(poly),
        "collection": "COPERNICUS/S2_SR_HARMONIZED",
        "cloud_threshold_pct": 70,
        "indices": ["NDVI", "EVI", "NDWI"],
        "scale_m": 10,
    }


def fetch_sentinel2_daily(
    site: config.Site,
    start_date: date,
    end_date: date,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """
    Returns
    -------
    pd.DataFrame
        Columns: date (datetime64), NDVI, EVI, NDWI.
        One row per distinct cloud-free S2 overpass intersecting the ROI.
        Empty DataFrame if no overpasses (network OK, just no data).
    """
    if end_date < start_date:
        raise ValueError(f"end_date {end_date} precedes start_date {start_date}")

    poly = geometry.site_polygon_coords(site)
    params = _cache_params(site, start_date, end_date, poly)

    # ------------------------------------------------------------ cache ---
    if not force:
        cached = cache.get_pickle("s2_gee", params)
        if cached is not None:
            with audited("s2_gee", params) as scratch:
                scratch["cache_hit"] = True
                scratch["status"] = "OK"
                scratch["extra"] = {"rows": len(cached)}
            logger.info("[s2] cache hit for {} {}→{} ({} rows)",
                        site.id, start_date, end_date, len(cached))
            return cached.copy()

    # -------------------------------------------------------- network ---
    _ensure_cp1_path()
    import importlib
    mod_s2 = importlib.import_module("mod_s2_gee")          # cp1_etl module

    with audited("s2_gee", params) as scratch:
        df_full = mod_s2.fetch_s2_data(
            start_year=start_date.year,
            end_year=end_date.year,
            roi_coords=poly.as_gee_ring(),
            key_path=str(config.GEE_SERVICE_ACCOUNT_KEY),
        )
        if df_full is None or df_full.empty:
            logger.warning("[s2] empty response for {} {}→{}",
                           site.id, start_date, end_date)
            scratch["status"] = "EMPTY"
            scratch["extra"] = {"rows": 0}
            empty = pd.DataFrame(columns=["date", "NDVI", "EVI", "NDWI"])
            cache.put_pickle("s2_gee", params, empty)
            return empty

        df_full["date"] = pd.to_datetime(df_full["date"])
        mask = (df_full["date"].dt.date >= start_date) & (df_full["date"].dt.date <= end_date)
        df = df_full.loc[mask, ["date", "NDVI", "EVI", "NDWI"]].reset_index(drop=True)

        # Capture diagnostics
        payload = pickle.dumps(df)
        scratch["response_bytes"] = len(payload)
        scratch["response_sha256"] = hashlib.sha256(payload).hexdigest()
        scratch["extra"] = {"rows_full_year": len(df_full), "rows_in_window": len(df)}

    cache.put_pickle("s2_gee", params, df)
    logger.info("[s2] {} {}→{}: {} cloud-free passes (full year: {})",
                site.id, start_date, end_date, len(df), len(df_full))
    return df


__all__ = ["fetch_sentinel2_daily"]
