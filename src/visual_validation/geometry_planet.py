"""GeoJSON helpers for Planet Data API queries.

Planet expects GeoJSON `Polygon` features for spatial filtering. We reuse the
existing `prospective_validation.geometry.site_polygon_coords` (already does
the 30 m inward pixel-purity buffer) and emit GeoJSON in the exact shape
Planet's `data_filter.geometry_filter` consumes.

Public API:
    site_to_geojson(site_or_id, buffer_m=30.0) -> dict
    sites_to_features(sites)                   -> dict  (FeatureCollection)
"""
from __future__ import annotations

from typing import Iterable, Union

from . import config

# Lazy import to keep visual_validation import-light if FLOV isn't on path.
def _load_flov_geometry():
    from prospective_validation.geometry import site_polygon_coords  # type: ignore
    return site_polygon_coords


def _resolve_site(site_or_id: Union[str, "config.Site"]):
    if isinstance(site_or_id, str):
        for s in config.EVRENLI_SITES:
            if s.id == site_or_id:
                return s
        raise KeyError(f"Unknown site_id: {site_or_id}")
    return site_or_id


def site_to_geojson(site_or_id: Union[str, "config.Site"],
                    *, buffer_m: float = 30.0) -> dict:
    """Return a GeoJSON Polygon dict for the given site, 30 m inward-buffered.

    The output is the *geometry* dict only (no Feature wrapper) so it can be
    handed straight to ``planet.data_filter.geometry_filter(geom_dict)``.
    """
    site = _resolve_site(site_or_id)
    site_polygon_coords = _load_flov_geometry()
    poly = site_polygon_coords(
        site,
        pixel_purity_buffer_m=buffer_m,
    )
    # GeoJSON Polygon: coordinates is [[ [lon,lat], [lon,lat], ... ]]
    ring = [[float(lon), float(lat)] for (lon, lat) in poly.coords_lonlat]
    return {"type": "Polygon", "coordinates": [ring]}


def sites_to_features(sites: Iterable[Union[str, "config.Site"]] = ()) -> dict:
    """Return a GeoJSON FeatureCollection for one or more sites.

    Useful for batched queries, audit log enrichment, and debugging.
    """
    feats = []
    for s in (sites or config.EVRENLI_SITES):
        site = _resolve_site(s)
        feats.append({
            "type": "Feature",
            "properties": {
                "site_id": site.id,
                "area_da": site.area_da,
                "owner":   site.owner,
            },
            "geometry": site_to_geojson(site),
        })
    return {"type": "FeatureCollection", "features": feats}


__all__ = ["site_to_geojson", "sites_to_features"]
