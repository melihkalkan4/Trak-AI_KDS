"""
File-byte SHA-256 integrity verification for frozen artefacts.

The frozen-model rationale collapses without an integrity guarantee.  On
POSIX we *could* use ``chmod 444`` but on Windows that is a no-op.  We
therefore rely on a content hash recorded the first time a file is observed,
then re-checked before every prediction.

Public surface
--------------
file_sha256(path)               → hex digest
ensure_unchanged(path, *, role) → asserts; updates ledger on first sight
read_ledger()                   → dict[role -> {path, sha256, first_seen}]
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .logging_setup import logger
from . import config

_BLOCK = 1024 * 1024  # 1 MiB


def file_sha256(path: Path) -> str:
    """Streaming SHA-256 of a file's bytes."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_BLOCK), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_ledger_raw() -> dict[str, dict]:
    """Replay the append-only JSONL ledger into a {role: latest_entry} dict."""
    ledger: dict[str, dict] = {}
    p = config.INTEGRITY_LEDGER
    if not p.exists():
        return ledger
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed ledger line: {!r}", line[:120])
                continue
            ledger[rec["role"]] = rec
    return ledger


def read_ledger() -> dict[str, dict]:
    """Public read-only view of the integrity ledger."""
    return _read_ledger_raw()


def _append_ledger(role: str, path: Path, sha: str, status: str) -> None:
    config.ensure_runtime_dirs()
    rec = {
        "role": role,
        "path": str(path),
        "sha256": sha,
        "status": status,
        "size_bytes": path.stat().st_size,
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
    with config.INTEGRITY_LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def ensure_unchanged(path: Path, *, role: str, expected_sha: Optional[str] = None) -> str:
    """
    Verify a frozen artefact's content hash.

    - If ``expected_sha`` is provided, assert equality.
    - Else: look up ``role`` in the ledger.  If absent, record first-sight
      hash.  If present, compare against recorded hash and raise on mismatch.

    Returns the current SHA-256 hex digest.
    """
    path = Path(path)
    current = file_sha256(path)

    if expected_sha is not None:
        if current != expected_sha:
            _append_ledger(role, path, current, status="MISMATCH_VS_EXPECTED")
            raise RuntimeError(
                f"INTEGRITY FAILURE — {role} at {path}\n"
                f"  expected: {expected_sha}\n"
                f"  observed: {current}"
            )
        _append_ledger(role, path, current, status="VERIFIED_EXPLICIT")
        logger.info("[integrity] {} verified against caller-supplied hash", role)
        return current

    ledger = _read_ledger_raw()
    prev = ledger.get(role)
    if prev is None:
        _append_ledger(role, path, current, status="FIRST_SIGHT")
        logger.info("[integrity] First-sight recorded for {} → {}", role, current[:12])
        return current

    if prev["sha256"] != current:
        _append_ledger(role, path, current, status="MISMATCH_VS_LEDGER")
        raise RuntimeError(
            f"INTEGRITY FAILURE — {role} at {path}\n"
            f"  ledger sha (first seen {prev['ts_utc']}): {prev['sha256']}\n"
            f"  current sha:                              {current}\n"
            f"The frozen artefact has been modified. Prospective validation "
            f"results before this point are no longer comparable."
        )
    _append_ledger(role, path, current, status="VERIFIED")
    logger.debug("[integrity] {} unchanged ({})", role, current[:12])
    return current


def mark_readonly_best_effort(path: Path) -> None:
    """
    Best-effort read-only flag.  On Windows ``os.chmod(0o444)`` clears only
    the write bit; on POSIX it strips owner+group+other write.  Either way
    the file-byte hash is the actual integrity guarantee.
    """
    try:
        os.chmod(path, 0o444)
        logger.debug("[integrity] read-only bit set on {}", path)
    except OSError as e:
        logger.warning("[integrity] could not chmod {}: {}", path, e)


__all__ = [
    "file_sha256",
    "ensure_unchanged",
    "read_ledger",
    "mark_readonly_best_effort",
]
