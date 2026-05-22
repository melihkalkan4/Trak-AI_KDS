"""
SoilGrids static fetcher.

Soil profile is time-invariant.  We cache once per site and never refresh
unless the user manually deletes the cache entry.  Cached output is the
dict of nine values (clay/sand/phh2o × 0-5/5-15/15-30 cm) produced by
:func:`cp1_etl.mod_soil_isric.fetch_soil_data`.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
from typing import Optional

from .. import cache, config
from ..audit import audited
from ..logging_setup import logger


_CP1_ON_PATH = False


def _ensure_cp1_path() -> None:
    global _CP1_ON_PATH
    if _CP1_ON_PATH:
        return
    cp1 = config.SRC_DIR / "cp1_etl"
    if str(cp1) not in sys.path:
        sys.path.insert(0, str(cp1))
    _CP1_ON_PATH = True


def _cache_params(site: config.Site) -> dict:
    return {
        "source": "isric_soilgrids_v2",
        "site_id": site.id,
        "lat": round(site.lat, 6),
        "lon": round(site.lon, 6),
        "buffer_m": 2000,
        "depths": ["0-5cm", "5-15cm", "15-30cm"],
        "properties": ["clay", "sand", "phh2o"],
    }


def fetch_soilgrids_static(site: config.Site, *, force: bool = False) -> dict:
    """Return the 9-key soil dict for ``site``. Idempotent."""
    params = _cache_params(site)

    if not force:
        cached = cache.get_pickle("soilgrids", params)
        if cached is not None:
            with audited("soilgrids", params) as scratch:
                scratch["cache_hit"] = True
                scratch["extra"] = {"keys": len(cached)}
            return dict(cached)

    _ensure_cp1_path()
    import importlib
    soil_mod = importlib.import_module("mod_soil_isric")

    with audited("soilgrids", params) as scratch:
        soil = soil_mod.fetch_soil_data(
            lat=site.lat, lon=site.lon,
            key_path=str(config.GEE_SERVICE_ACCOUNT_KEY),
        )
        if not soil:
            scratch["status"] = "EMPTY"
            logger.error("[soilgrids] empty response for {}", site.id)
            return {}
        payload = pickle.dumps(soil)
        scratch["response_bytes"] = len(payload)
        scratch["response_sha256"] = hashlib.sha256(payload).hexdigest()
        scratch["extra"] = {"keys": len(soil)}

    cache.put_pickle("soilgrids", params, soil)
    logger.info("[soilgrids] {} cached ({} keys)", site.id, len(soil))
    return soil


__all__ = ["fetch_soilgrids_static"]
