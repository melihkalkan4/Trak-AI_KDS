"""
Site-to-polygon utilities for satellite queries.

A pilot Site is a (lat, lon) centroid + parcel area.  Sentinel-2 sees the
world at 10 m pixels; to claim "parcel-aggregate ground truth at 10 m
resolution" (per the user's Phase 6 methodology note) we must:

    1. Approximate the parcel as a square of side sqrt(area_m²).
    2. Apply a 30 m inward buffer to avoid mixed-pixel edge contamination.
    3. Warn loudly if the remaining footprint is too small for stable S2
       statistics (< 2.5 x 2.5 pixel block, ~25 m half-side).

We do NOT need a precise parcel outline at this stage — the goal is a
reproducible ROI keyed to the Site definition, not cadastral accuracy.
When real coordinates and parcel geometries arrive in Phase 6, replace
:func:`site_polygon_coords` with a shapefile-driven equivalent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from . import config
from .logging_setup import logger

# Approximate metres-per-degree at the latitude of Trakya (~41° N).
_METERS_PER_DEG_LAT = 111_320.0


def _meters_per_deg_lon(lat_deg: float) -> float:
    return 111_320.0 * math.cos(math.radians(lat_deg))


@dataclass(frozen=True)
class SitePolygon:
    site_id: str
    coords_lonlat: tuple[tuple[float, float], ...]   # closed ring, lon-lat order
    half_side_m: float
    inward_buffer_m: float
    subpixel_risk: bool

    def as_gee_ring(self) -> list[list[float]]:
        """Open ring as nested list, format expected by ee.Geometry.Polygon."""
        return [list(p) for p in self.coords_lonlat]

    def as_bbox_NWSE(self) -> tuple[float, float, float, float]:
        """North, West, South, East — the order CDS 'area' expects."""
        lats = [p[1] for p in self.coords_lonlat]
        lons = [p[0] for p in self.coords_lonlat]
        return max(lats), min(lons), min(lats), max(lons)


def site_polygon_coords(
    site: config.Site,
    *,
    pixel_purity_buffer_m: float = config.PIXEL_PURITY_BUFFER_M,
) -> SitePolygon:
    """
    Build a square ROI polygon centred on ``site`` with the 30 m inward
    buffer applied.  Coordinate ring is lon-lat order, closed.

    Raises ValueError only if the result has negative side length, which
    only happens for area_da near zero.  A merely 'risky' site (< 5 ha
    after buffering) is logged as a WARNING but the polygon is returned.
    """
    area_m2 = site.area_da * 1000.0
    full_half_side_m = math.sqrt(area_m2) / 2.0
    buffered_half_side_m = full_half_side_m - pixel_purity_buffer_m

    if buffered_half_side_m <= 0:
        raise ValueError(
            f"Site {site.id} ({site.area_da} da) is too small for a "
            f"{pixel_purity_buffer_m} m inward buffer — full half-side "
            f"{full_half_side_m:.1f} m"
        )

    risky = buffered_half_side_m < 25.0  # < 2.5 S2 pixels per side
    if risky:
        logger.warning(
            "[geometry] {} ({:.1f} ha) buffered half-side {:.1f} m → "
            "< 2.5 S2 pixels per side; treat NDVI stats as subpixel-noisy",
            site.id, site.area_ha, buffered_half_side_m,
        )
    elif site.subpixel_risk:
        logger.warning(
            "[geometry] {} ({:.1f} ha) is < 5 ha; flagged as 'subpixel risk' "
            "in config — narrative reports should mark this site cautiously",
            site.id, site.area_ha,
        )

    d_lat = buffered_half_side_m / _METERS_PER_DEG_LAT
    d_lon = buffered_half_side_m / _meters_per_deg_lon(site.lat)

    # Closed counter-clockwise ring (standard GeoJSON / GEE order)
    ring = (
        (site.lon - d_lon, site.lat - d_lat),
        (site.lon + d_lon, site.lat - d_lat),
        (site.lon + d_lon, site.lat + d_lat),
        (site.lon - d_lon, site.lat + d_lat),
        (site.lon - d_lon, site.lat - d_lat),  # close
    )

    return SitePolygon(
        site_id=site.id,
        coords_lonlat=ring,
        half_side_m=buffered_half_side_m,
        inward_buffer_m=pixel_purity_buffer_m,
        subpixel_risk=risky or site.subpixel_risk,
    )


def polygon_signature(poly: SitePolygon) -> tuple:
    """Stable, hashable representation for cache keys."""
    return (
        poly.site_id,
        round(poly.half_side_m, 4),
        round(poly.inward_buffer_m, 4),
        tuple((round(x, 6), round(y, 6)) for x, y in poly.coords_lonlat),
    )


__all__ = ["SitePolygon", "site_polygon_coords", "polygon_signature"]
