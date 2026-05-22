"""
Interactive setup for the Copernicus Climate Data Store (CDS) API.

Writes ``~/.cdsapirc`` so that ``cdsapi.Client()`` picks up credentials
implicitly. On Windows the canonical path is ``%USERPROFILE%\\.cdsapirc``.

Endpoint
--------
We target the new CDS-Beta URL the user specified:
    https://cds-beta.climate.copernicus.eu/api

Usage
-----
    python scripts/setup_cds_credentials.py
        --uid    <numeric UID>     # optional, will prompt if absent
        --key    <api key>         # optional, will prompt if absent
        --force                    # overwrite without confirmation

Side effects
------------
- Creates ~/.cdsapirc with mode 600 on POSIX, default on Windows
- Logs the action via the FLOV audit trail
- Does NOT echo the API key to stdout after writing
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_path_on_syspath() -> None:
    root = _project_root()
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))


def main() -> int:
    _ensure_path_on_syspath()
    from prospective_validation import config, audit, logging_setup  # noqa: E402

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    parser = argparse.ArgumentParser(description="Set up ~/.cdsapirc for CDS-Beta")
    parser.add_argument("--uid", help="CDS UID (numeric)", default=None)
    parser.add_argument("--key", help="CDS API key", default=None)
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing ~/.cdsapirc without prompt")
    args = parser.parse_args()

    home = Path.home()
    target = home / ".cdsapirc"

    if target.exists() and not args.force:
        resp = input(f"{target} already exists. Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            logger.info("[cds-setup] aborted by user — existing file kept")
            return 0

    uid = args.uid or input("CDS UID (numeric): ").strip()
    key = args.key or getpass.getpass("CDS API key (hidden): ").strip()

    if not uid or not key:
        logger.error("[cds-setup] UID and key are both required")
        return 2

    body = f"url: {config.CDS_API_URL}\nkey: {uid}:{key}\n"
    target.write_text(body, encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        # Windows: chmod has limited effect; ACL is owner-only by default.
        pass

    with audit.audited("cds_setup", {"endpoint": config.CDS_API_URL}) as scratch:
        scratch["status"] = "OK"
        scratch["extra"] = {
            "rcfile": str(target),
            "written_utc": datetime.now(timezone.utc).isoformat(),
            "uid_len": len(uid),
            "key_len": len(key),
        }

    logger.info("[cds-setup] wrote {} → endpoint={}", target, config.CDS_API_URL)
    print("\nDone. Test with:\n  python -c \"import cdsapi; cdsapi.Client(); print('CDS OK')\"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
