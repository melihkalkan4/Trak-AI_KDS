"""
CLI: ingest all per-site parquets into `sensor_reading` rows.

    python scripts/ingest_all_retrospective.py
    python scripts/ingest_all_retrospective.py --sites EVR_01 EVR_02
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from data_integration.retrospective_ingester import (
    RetrospectiveDataIngester, EVR_IDS, YEARS,
)

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("ingest_all_retrospective")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", nargs="+", default=list(EVR_IDS))
    parser.add_argument("--years", nargs="+", type=int, default=list(YEARS))
    args = parser.parse_args()

    with RetrospectiveDataIngester() as ing:
        results = ing.ingest_all(sites=args.sites, years=args.years)

    print("\n=== INGESTION RESULTS ===")
    total_rows = 0
    n_ok = n_skipped = n_failed = 0
    for r in results:
        status = r["status"]
        if status == "ok":
            print(f"  OK    {r['site']:<7} {r['year']}: "
                  f"{r['inserted']} inserted "
                  f"({r.get('failed', 0)} failed, "
                  f"{r.get('rows_in_parquet', 0)} in parquet)")
            total_rows += r["inserted"]
            n_ok += 1
        elif status in ("no_parquet", "empty_parquet"):
            print(f"  SKIP  {r['site']:<7} {r['year']}: {status}")
            n_skipped += 1
        else:
            print(f"  FAIL  {r['site']:<7} {r['year']}: {status} "
                  f"({r.get('error', '')})")
            n_failed += 1

    print(f"\nTotal: {n_ok} ok, {n_skipped} skipped, {n_failed} failed")
    print(f"Total sensor_reading rows inserted: {total_rows}")
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
