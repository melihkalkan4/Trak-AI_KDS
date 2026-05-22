"""
Hash-based response cache.

A canonical JSON encoding of the query parameters is SHA-256-hashed; the
digest becomes the cache key.  Bytes payloads are stored verbatim under
``data/cache/api/<source>/<hash>.bin`` with a sibling ``<hash>.meta.json``
recording shape (params, source, content-type, size, created_at).

Identical queries never re-hit the network.  This is the single mechanism
backing the user's "never re-download same query" requirement.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .logging_setup import logger
from . import config


def _canon(obj: Any) -> Any:
    """Recursively canonicalise a value for stable hashing."""
    if isinstance(obj, dict):
        return {k: _canon(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        return [_canon(x) for x in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def query_hash(source: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"source": source, "params": _canon(params)},
                         sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class CacheEntry:
    key: str
    bin_path: Path
    meta_path: Path

    @property
    def exists(self) -> bool:
        return self.bin_path.exists() and self.meta_path.exists()


def entry_for(source: str, params: dict[str, Any]) -> CacheEntry:
    key = query_hash(source, params)
    root = config.CACHE_DIR / source
    root.mkdir(parents=True, exist_ok=True)
    return CacheEntry(
        key=key,
        bin_path=root / f"{key}.bin",
        meta_path=root / f"{key}.meta.json",
    )


def get(source: str, params: dict[str, Any]) -> Optional[bytes]:
    """Return cached bytes if present, else None."""
    e = entry_for(source, params)
    if not e.exists:
        return None
    try:
        data = e.bin_path.read_bytes()
        logger.debug("[cache] HIT {} {}", source, e.key[:12])
        return data
    except OSError as ex:
        logger.warning("[cache] read failure for {}: {}", e.bin_path, ex)
        return None


def put(
    source: str,
    params: dict[str, Any],
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
) -> CacheEntry:
    e = entry_for(source, params)
    e.bin_path.write_bytes(data)
    meta = {
        "source": source,
        "params": _canon(params),
        "content_type": content_type,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    e.meta_path.write_text(json.dumps(meta, indent=2, default=str),
                           encoding="utf-8")
    logger.debug("[cache] PUT {} {} ({} bytes)", source, e.key[:12], len(data))
    return e


def get_pickle(source: str, params: dict[str, Any]) -> Optional[Any]:
    raw = get(source, params)
    if raw is None:
        return None
    try:
        return pickle.loads(raw)
    except Exception as ex:                                  # noqa: BLE001
        logger.warning("[cache] pickle decode failed: {}", ex)
        return None


def put_pickle(source: str, params: dict[str, Any], obj: Any) -> CacheEntry:
    return put(source, params, pickle.dumps(obj),
               content_type="application/python-pickle")


__all__ = [
    "query_hash",
    "entry_for",
    "get",
    "put",
    "get_pickle",
    "put_pickle",
    "CacheEntry",
]
