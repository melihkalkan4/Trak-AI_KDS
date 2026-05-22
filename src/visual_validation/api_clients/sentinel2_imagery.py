"""
Sentinel-2 RGB chip stand-in (used while Planet Education key is pending).

The FLOV fetcher already pulls Sentinel-2 NDVI/EVI/NDWI per-pixel time
series via Earth Engine.  This module focuses on the visual side: pull a
small RGB chip centred on the parcel, save as a PNG/GeoTIFF, and return
the local path that the satellite CNN (ResNet50) can consume.

Two paths:

    fetch_rgb_chip(site_id, target_date)     -> Path | None
        Earth-Engine route — best quality, requires `earthengine-api`
        and an authenticated GEE account.

    fetch_rgb_chip_stub(site_id, target_date) -> Path | None
        Pure-numpy synthetic chip when GEE isn't available.  Useful for
        CI / dev boxes; the resulting chip is intentionally low-signal so
        no one mistakes it for a real observation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .. import config


logger = logging.getLogger("trakai.visual.s2")


# ---------------------------------------------------------------------------
@dataclass
class S2Chip:
    site_id: str
    target_date: str
    asset_path: str
    width: int
    height: int
    source: str            # "earth_engine" | "stub"
    cloud_cover: float
    metadata: dict
    generated_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
def _site_lookup(site_id: str):
    for s in config.EVRENLI_SITES:
        if getattr(s, "id", None) == site_id:
            return s
    return None


def _chip_path(site_id: str, target_date: date, suffix: str = "png") -> Path:
    out_dir = config.PLANETSCOPE_DIR / "s2_standin" / site_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{site_id}_{target_date.isoformat()}.{suffix}"


# ---------------------------------------------------------------------------
# Real path — Earth Engine
# ---------------------------------------------------------------------------
def fetch_rgb_chip(site_id: str,
                   target_date: date,
                   *,
                   buffer_m: int = 500,
                   max_cloud: float = 0.20,
                   lookback_days: int = 7,
                   ) -> Optional[S2Chip]:
    """Pull a Sentinel-2 L2A RGB thumbnail centred on the site."""
    try:
        import ee  # noqa: F401
    except ImportError:
        logger.warning("earthengine-api not installed; cannot fetch S2 chip.")
        return None

    site = _site_lookup(site_id)
    if site is None:
        logger.warning("site_id %s not in EVRENLI_SITES", site_id)
        return None

    try:
        import ee
        # Caller is expected to have run `ee.Initialize()` once (or via FLOV)
        pt = ee.Geometry.Point([site.lon, site.lat])
        roi = pt.buffer(buffer_m).bounds()
        start = (target_date - timedelta(days=lookback_days)).isoformat()
        end = (target_date + timedelta(days=1)).isoformat()
        col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
               .filterDate(start, end)
               .filterBounds(roi)
               .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud * 100)))
        size = col.size().getInfo()
        if not size:
            logger.info("No S2 scene for %s @ %s within %dd lookback",
                        site_id, target_date, lookback_days)
            return None
        img = col.sort("system:time_start", False).first()
        rgb = img.select(["B4", "B3", "B2"]).visualize(min=0, max=3000)
        url = rgb.getThumbURL({"region": roi, "dimensions": 256, "format": "png"})

        import urllib.request
        out = _chip_path(site_id, target_date)
        urllib.request.urlretrieve(url, out)
        chip = S2Chip(
            site_id=site_id,
            target_date=target_date.isoformat(),
            asset_path=str(out),
            width=256, height=256,
            source="earth_engine",
            cloud_cover=float(img.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()),
            metadata={"system_id": img.id().getInfo()},
            generated_utc=datetime.now(timezone.utc).isoformat(),
        )
        _log_chip(chip)
        return chip
    except Exception:                                           # noqa: BLE001
        logger.exception("S2 chip fetch failed for %s @ %s", site_id, target_date)
        return None


# ---------------------------------------------------------------------------
# Fallback — pure-numpy synthetic chip (CI / dev box)
# ---------------------------------------------------------------------------
def fetch_rgb_chip_stub(site_id: str,
                        target_date: date,
                        ) -> Optional[S2Chip]:
    """
    Generate a synthetic 256×256 RGB chip so downstream code can be
    exercised without GEE.  The chip is uniform grey with a tiny green
    blob — deliberately low-information so it cannot be confused with a
    real observation.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        logger.warning("Pillow/numpy missing — cannot synth a stub S2 chip.")
        return None
    arr = np.full((256, 256, 3), 128, dtype="uint8")
    arr[96:160, 96:160, 1] = 180         # faint green blob
    out = _chip_path(site_id, target_date)
    Image.fromarray(arr).save(out, "PNG")
    chip = S2Chip(
        site_id=site_id,
        target_date=target_date.isoformat(),
        asset_path=str(out),
        width=256, height=256,
        source="stub",
        cloud_cover=0.0,
        metadata={"note": "synthetic; not a real observation"},
        generated_utc=datetime.now(timezone.utc).isoformat(),
    )
    _log_chip(chip)
    return chip


# ---------------------------------------------------------------------------
def _log_chip(chip: S2Chip) -> None:
    out = config.LOGS_DIR / "s2_chip_audit.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(chip.to_dict(), ensure_ascii=False) + "\n")


__all__ = ["S2Chip", "fetch_rgb_chip", "fetch_rgb_chip_stub"]
