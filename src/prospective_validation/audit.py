"""
JSONL audit trail for every external API call.

Each record captures: timestamp, source ('s2_gee'|'era5_cds'|'soilgrids'|…),
query parameters (canonicalised), HTTP-like status, latency, cache_hit,
response size, and a SHA-256 of the response payload when applicable.

Records are append-only.  This file is the evidence base for the
'Reproducibility' section of the methodology document.
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from .logging_setup import logger
from . import config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_api_call(
    source: str,
    params: dict[str, Any],
    *,
    status: str,
    latency_s: float,
    cache_hit: bool = False,
    response_bytes: Optional[int] = None,
    response_sha256: Optional[str] = None,
    error: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Append a single audit record."""
    config.ensure_runtime_dirs()
    rec: dict[str, Any] = {
        "ts_utc": _now_iso(),
        "source": source,
        "params": params,
        "status": status,
        "latency_s": round(latency_s, 4),
        "cache_hit": cache_hit,
    }
    if response_bytes is not None:
        rec["response_bytes"] = response_bytes
    if response_sha256 is not None:
        rec["response_sha256"] = response_sha256
    if error is not None:
        rec["error"] = str(error)[:500]
    if extra:
        rec["extra"] = extra
    with config.AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


@contextmanager
def audited(source: str, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """
    Context manager. Yields a mutable scratch dict you can populate
    (response_bytes, response_sha256, cache_hit, status, extra).  On exit
    the audit record is written exactly once, even on exception.
    """
    scratch: dict[str, Any] = {"status": "OK", "cache_hit": False}
    t0 = time.perf_counter()
    err: Optional[BaseException] = None
    try:
        yield scratch
    except BaseException as e:
        err = e
        scratch["status"] = type(e).__name__
        raise
    finally:
        latency = time.perf_counter() - t0
        log_api_call(
            source=source,
            params=params,
            status=scratch.get("status", "OK"),
            latency_s=latency,
            cache_hit=bool(scratch.get("cache_hit", False)),
            response_bytes=scratch.get("response_bytes"),
            response_sha256=scratch.get("response_sha256"),
            error=str(err) if err else None,
            extra=scratch.get("extra"),
        )
        if err:
            logger.error("[audit] {} FAILED in {:.2f}s: {}", source, latency, err)
        else:
            logger.debug(
                "[audit] {} {} in {:.2f}s (cache_hit={})",
                source,
                scratch.get("status", "OK"),
                latency,
                scratch.get("cache_hit", False),
            )


__all__ = ["log_api_call", "audited"]
