"""
Network-touching wrappers around the existing cp1_etl modules.

All public functions in this package:
    * accept a Site object (or lat/lon) + date range
    * consult :mod:`prospective_validation.cache` before the network
    * record every API attempt via :func:`prospective_validation.audit.audited`
    * return a pandas DataFrame indexed/keyed by the ``date`` column

The underlying cp1_etl extractors are imported but NEVER MODIFIED.
"""

from .sentinel2 import fetch_sentinel2_daily
from .era5 import fetch_era5_daily
from .soilgrids import fetch_soilgrids_static

__all__ = [
    "fetch_sentinel2_daily",
    "fetch_era5_daily",
    "fetch_soilgrids_static",
]
