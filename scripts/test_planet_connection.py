"""Phase 1 smoke test — verify Planet Data API connectivity.

Reads `PLANET_API_KEY` from .env, authenticates, runs a small search for
EVR_01 over the last 7 days, prints a summary, writes an audit entry.

Usage
-----
    python scripts/test_planet_connection.py
    python scripts/test_planet_connection.py --site EVR_02 --days 14
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Make `src/` importable regardless of CWD.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from visual_validation.api_clients.planet_client import PlanetClient


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="EVR_01")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--max-cloud", type=float, default=0.20)
    ap.add_argument("--require-downloadable", action="store_true",
                    help="Add Planet permission_filter (Education tier only).")
    args = ap.parse_args()

    client = PlanetClient()

    print("=" * 60)
    print("Planet Data API — smoke test")
    print("=" * 60)
    key = client.api_key or ""
    print(f"  SDK OK         : {client.available}")
    print(f"  Key present    : {bool(key)}  (prefix: {key[:4] + '****' if key else 'N/A'})")
    print(f"  Base URL       : {client.base_url}")
    print(f"  Site           : {args.site}")
    print(f"  Window (UTC)   : last {args.days} days")
    print(f"  Max cloud      : {args.max_cloud:.0%}")

    if not client.available:
        print("\nFATAL: client.available is False — set PLANET_API_KEY and retry.")
        return 2

    end = date.today()
    start = end - timedelta(days=args.days)

    try:
        scenes = client.search_scenes(
            site_id=args.site,
            start=start,
            end=end,
            max_cloud=args.max_cloud,
            item_types=("PSScene",),
            limit=25,
            require_downloadable=args.require_downloadable,
            use_cache=False,
        )
    except Exception as exc:                                        # noqa: BLE001
        print(f"\nFATAL: search failed -> {type(exc).__name__}: {exc}")
        return 3

    print(f"\n  Scenes found   : {len(scenes)}")
    if scenes:
        dates = [s.acquired_utc[:10] for s in scenes if s.acquired_utc]
        clouds = [s.cloud_cover for s in scenes]
        print(f"  Date range     : {min(dates) if dates else '—'} … {max(dates) if dates else '—'}")
        print(f"  Cloud min/max  : {min(clouds):.0%} / {max(clouds):.0%}")
        print("\n  First 5 scenes (sorted by cloud %):")
        for s in scenes[:5]:
            print(f"    {s.acquired_utc[:19]}   cloud={s.cloud_cover:.0%}   id={s.item_id}")
    else:
        print("  (no scenes — try widening --days or relaxing --max-cloud)")

    client.log_status()
    print(f"\n  Audit log      : logs/planet_api_audit.jsonl")
    print(f"  Status log     : logs/planet_api_status.jsonl")
    print("\nOK" if scenes else "\nOK (empty result)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
