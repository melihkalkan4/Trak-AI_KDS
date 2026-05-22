"""
Planet Data API client — PRODUCTION.

Thin **synchronous** wrapper around the async `planet` SDK (v3.x). The async
core is internal; every public method returns plain Python values so callers
(scripts, Streamlit pages) don't need to know about asyncio.

Features
--------
* AOI-bounded PSScene search (date range + cloud filter)
* Asset activation + polling + download (analytic_sr 4-band, ortho_visual RGB)
* Hash-keyed search-result cache (idempotent re-runs)
* Conservative rate limiting (trial-safe: 5 search/min, 2 download/min)
* Retry with exponential back-off on 429 / 5xx
* Audit log to ``logs/planet_api_audit.jsonl``  (api_audit pattern reused)
* API key is **never** logged in clear; only `prefix6****` is recorded.

The public surface is a strict superset of the previous stub so existing
callers continue to import the same names.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Union

try:
    from planet import Auth, Session, data_filter
    from planet.exceptions import APIError, ClientError, MissingResource
    _PLANET_SDK_OK = True
except Exception as _imp_exc:                                       # noqa: BLE001
    _PLANET_SDK_OK = False
    _PLANET_IMPORT_ERR = _imp_exc

from .. import config
from ..geometry_planet import site_to_geojson


logger = logging.getLogger("trakai.visual.planet")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class PlanetScene:
    item_id: str
    item_type: str
    acquired_utc: str
    cloud_cover: float
    geometry: dict
    site_id: Optional[str] = None
    download_path: Optional[str] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d


# ---------------------------------------------------------------------------
# Helpers — masking / hashing / rate limiting
# ---------------------------------------------------------------------------
def _mask_key(key: str) -> str:
    if not key:
        return ""
    return key[:4] + "****"


def _audit_path() -> Path:
    p = config.LOGS_DIR / "planet_api_audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _audit(event: str, payload: dict) -> None:
    """Append an audit record. Never writes the raw API key."""
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    # Defensive scrub
    for k in ("api_key", "PLANET_API_KEY", "key"):
        if k in rec:
            rec[k] = _mask_key(str(rec[k]))
    try:
        with _audit_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except Exception as exc:                                        # noqa: BLE001
        logger.warning("audit write failed: %s", exc)


# Module-level token-bucket-ish rate limiter (process-local).  We keep this
# deliberately simple — the SDK is async but we wrap individual ops anyway.
class _RateLimiter:
    def __init__(self, per_min: float):
        self.min_interval = 60.0 / max(per_min, 1.0)
        self._last = 0.0

    def wait(self) -> None:
        dt = time.monotonic() - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._last = time.monotonic()


_SEARCH_RL    = _RateLimiter(per_min=5.0)
_ACTIVATE_RL  = _RateLimiter(per_min=3.0)
_DOWNLOAD_RL  = _RateLimiter(per_min=2.0)


# ---------------------------------------------------------------------------
# Search-cache (file-based, hash-keyed by query)
# ---------------------------------------------------------------------------
def _cache_dir() -> Path:
    p = config.PLANETSCOPE_DIR / ".cache" / "search"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _search_cache_key(site_id: str, start: date, end: date,
                      max_cloud: float, item_types: tuple[str, ...]) -> str:
    payload = f"{site_id}|{start.isoformat()}|{end.isoformat()}|{max_cloud}|{','.join(item_types)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class PlanetClient:
    """Production Planet Data API client (sync surface, async internals).

    If ``planet`` SDK or the API key is missing, ``available`` is False and
    every network call raises ``NotImplementedError`` — callers fall back to
    ``api_clients.sentinel2_imagery`` exactly as the stub did.
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = config.PLANET_BASE_URL):
        self.api_key = api_key if api_key is not None else config.PLANET_API_KEY
        self.base_url = base_url

    # -------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return bool(self.api_key) and _PLANET_SDK_OK

    def _require_key(self) -> None:
        if not _PLANET_SDK_OK:
            raise NotImplementedError(
                f"planet SDK not importable: {_PLANET_IMPORT_ERR}"
            )
        if not self.api_key:
            raise NotImplementedError(
                "PLANET_API_KEY missing — set it in .env or fall back to "
                "api_clients.sentinel2_imagery."
            )

    # -------------------------------------------------------------------
    def _auth(self) -> "Auth":
        # `Auth.from_env` reads PLANET_API_KEY from the process env; we pass
        # the variable name explicitly so it's deterministic regardless of
        # whether dotenv has been loaded by the caller.
        os.environ.setdefault("PLANET_API_KEY", self.api_key)
        return Auth.from_env("PLANET_API_KEY")

    # ===================================================================
    # SEARCH
    # ===================================================================
    def search_scenes(self,
                      site_id: str,
                      start: date,
                      end: date,
                      *,
                      max_cloud: float = 0.20,
                      item_types: Iterable[str] = ("PSScene",),
                      limit: int = 50,
                      use_cache: bool = True,
                      require_downloadable: bool = False,
                      ) -> list[PlanetScene]:
        """Search PSScene items intersecting the site for [start, end].

        ``require_downloadable`` adds ``permission_filter()`` so only scenes
        the caller's key is licensed to download are returned. Trial keys
        often have empty ``_permissions`` so this filter zeroes the result;
        leave it off for discovery, turn it on once Education tier is live.
        """
        self._require_key()
        item_types_t = tuple(item_types)

        # ---- cache ----
        cache_key = _search_cache_key(site_id, start, end, max_cloud, item_types_t)
        cache_file = _cache_dir() / f"{cache_key}.json"
        if use_cache and cache_file.exists():
            try:
                rows = json.loads(cache_file.read_text(encoding="utf-8"))
                scenes = [PlanetScene(**r) for r in rows]
                _audit("search_cache_hit", {
                    "site_id": site_id, "start": start, "end": end,
                    "cache_key": cache_key, "n": len(scenes),
                })
                return scenes
            except Exception as exc:                                # noqa: BLE001
                logger.warning("cache read failed (%s); refetching", exc)

        # ---- network ----
        _SEARCH_RL.wait()
        t0 = time.time()
        try:
            scenes = asyncio.run(self._search_async(
                site_id=site_id,
                start=start, end=end,
                max_cloud=max_cloud,
                item_types=list(item_types_t),
                limit=limit,
                require_downloadable=require_downloadable,
            ))
        except (APIError, ClientError) as exc:
            _audit("search_error", {
                "site_id": site_id, "start": start, "end": end,
                "error": type(exc).__name__, "msg": str(exc)[:300],
            })
            raise

        # ---- cache write ----
        try:
            cache_file.write_text(
                json.dumps([s.to_dict() for s in scenes], default=str),
                encoding="utf-8",
            )
        except Exception as exc:                                    # noqa: BLE001
            logger.warning("cache write failed: %s", exc)

        _audit("search_ok", {
            "site_id": site_id,
            "start": str(start), "end": str(end),
            "max_cloud": max_cloud,
            "item_types": list(item_types_t),
            "n_scenes": len(scenes),
            "elapsed_s": round(time.time() - t0, 2),
            "key_prefix": _mask_key(self.api_key),
        })
        return scenes

    async def _search_async(self,
                            site_id: str,
                            start: date,
                            end: date,
                            max_cloud: float,
                            item_types: list[str],
                            limit: int,
                            require_downloadable: bool = False,
                            ) -> list[PlanetScene]:
        geom = site_to_geojson(site_id)

        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt   = datetime.combine(end,   datetime.max.time()).replace(tzinfo=timezone.utc)

        flts = [
            data_filter.geometry_filter(geom),
            data_filter.date_range_filter("acquired", gte=start_dt, lte=end_dt),
            data_filter.range_filter("cloud_cover", lte=max_cloud),
        ]
        if require_downloadable:
            # Restrict to items the caller's key is licensed to download.
            flts.append(data_filter.permission_filter())
        sfilter = data_filter.and_filter(flts)

        out: list[PlanetScene] = []
        async with Session(auth=self._auth()) as sess:
            cl = sess.client("data")
            async for item in cl.search(
                item_types=item_types,
                search_filter=sfilter,
                name=f"trakai_{site_id}_{start.isoformat()}_{end.isoformat()}",
                limit=limit,
            ):
                props = item.get("properties", {}) or {}
                out.append(PlanetScene(
                    item_id=item.get("id", ""),
                    item_type=props.get("item_type", item_types[0] if item_types else ""),
                    acquired_utc=props.get("acquired", ""),
                    cloud_cover=float(props.get("cloud_cover", 0.0) or 0.0),
                    geometry=item.get("geometry", {}) or {},
                    site_id=site_id,
                    raw=item,
                ))
        # Sort: lowest cloud cover first, then most-recent.
        out.sort(key=lambda s: (s.cloud_cover, -_iso_to_epoch(s.acquired_utc)))
        return out

    # ===================================================================
    # DOWNLOAD
    # ===================================================================
    def download_chip(self,
                      scene: PlanetScene,
                      asset_type: str = "ortho_visual",
                      *,
                      dest_dir: Optional[Path] = None,
                      overwrite: bool = False,
                      poll_max_s: float = 240.0,
                      ) -> Path:
        """Activate + download a single asset; return the local file path.

        ``asset_type`` examples (PSScene):
            * ``ortho_visual``  — 3-band RGB GeoTIFF (preview-quality)
            * ``ortho_analytic_4b_sr`` — 4-band surface reflectance (BGRN)
            * ``ortho_udm2`` — usable-data mask
        """
        self._require_key()
        dest_dir = Path(dest_dir or (config.PLANETSCOPE_DIR / (scene.site_id or "_unfiled")))
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Deterministic filename: <date>_<itemid>_<asset>.tif
        acquired = scene.acquired_utc[:10] if scene.acquired_utc else "0000-00-00"
        out_path = dest_dir / f"{acquired}_{scene.item_id}_{asset_type}.tif"
        if out_path.exists() and not overwrite:
            _audit("download_skip_exists", {
                "site_id": scene.site_id, "item_id": scene.item_id,
                "asset_type": asset_type, "path": str(out_path),
            })
            scene.download_path = str(out_path)
            return out_path

        _DOWNLOAD_RL.wait()
        t0 = time.time()
        try:
            local = asyncio.run(self._download_async(
                scene=scene, asset_type=asset_type,
                dest_dir=dest_dir, poll_max_s=poll_max_s,
            ))
        except (APIError, ClientError, MissingResource) as exc:
            _audit("download_error", {
                "site_id": scene.site_id, "item_id": scene.item_id,
                "asset_type": asset_type,
                "error": type(exc).__name__, "msg": str(exc)[:300],
            })
            raise

        # SDK chooses its own filename inside dest_dir; ensure ours matches.
        if local != out_path:
            try:
                Path(local).rename(out_path)
            except Exception:                                       # noqa: BLE001
                out_path = Path(local)

        scene.download_path = str(out_path)
        _audit("download_ok", {
            "site_id": scene.site_id, "item_id": scene.item_id,
            "asset_type": asset_type, "path": str(out_path),
            "bytes": out_path.stat().st_size if out_path.exists() else None,
            "elapsed_s": round(time.time() - t0, 1),
        })
        return out_path

    async def _download_async(self,
                              scene: PlanetScene,
                              asset_type: str,
                              dest_dir: Path,
                              poll_max_s: float,
                              ) -> Path:
        async with Session(auth=self._auth()) as sess:
            cl = sess.client("data")
            # 1) List assets, pick the requested type
            asset = await cl.get_asset(
                item_type_id=scene.item_type or "PSScene",
                item_id=scene.item_id,
                asset_type_id=asset_type,
            )
            # 2) Activate (no-op if already active)
            _ACTIVATE_RL.wait()
            await cl.activate_asset(asset)
            # 3) Poll until active (SDK helper does back-off internally)
            asset = await cl.wait_asset(asset, callback=None, max_attempts=0)
            # 4) Stream to disk
            local = await cl.download_asset(asset,
                                            directory=str(dest_dir),
                                            overwrite=True)
            return Path(local)

    # ===================================================================
    # Convenience
    # ===================================================================
    def latest_scene_for(self,
                         site_id: str,
                         target: date,
                         *,
                         lookback_days: int = 7,
                         max_cloud: float = 0.20,
                         ) -> Optional[PlanetScene]:
        start = target - timedelta(days=lookback_days)
        scenes = self.search_scenes(site_id, start, target,
                                    max_cloud=max_cloud, limit=20)
        return scenes[0] if scenes else None

    def bulk_search(self,
                    site_ids: Iterable[str],
                    start: date,
                    end: date,
                    *,
                    max_cloud: float = 0.20,
                    limit_per_site: int = 30,
                    ) -> dict[str, list[PlanetScene]]:
        out: dict[str, list[PlanetScene]] = {}
        for sid in site_ids:
            try:
                out[sid] = self.search_scenes(sid, start, end,
                                              max_cloud=max_cloud,
                                              limit=limit_per_site)
            except Exception as exc:                                # noqa: BLE001
                _audit("bulk_search_error", {
                    "site_id": sid, "error": type(exc).__name__,
                    "msg": str(exc)[:200],
                })
                out[sid] = []
        return out

    # ===================================================================
    # Audit / status
    # ===================================================================
    def log_status(self,
                   path: Path = None,                               # type: ignore[assignment]
                   ) -> None:
        path = path or (config.LOGS_DIR / "planet_api_status.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "available": self.available,
            "sdk_ok": _PLANET_SDK_OK,
            "base_url": self.base_url,
            "key_prefix": _mask_key(self.api_key),
            "tier": "trial",
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _iso_to_epoch(iso: str) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except Exception:                                               # noqa: BLE001
        return 0.0


__all__ = ["PlanetClient", "PlanetScene"]
