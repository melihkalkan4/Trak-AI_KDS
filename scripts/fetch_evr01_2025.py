"""
EVR_01 MVP runner — Phase 2 end-to-end smoke test.

Fetches Sentinel-2 + ERA5 + SoilGrids for the EVR_01 placeholder site
between ``--start`` and ``--end`` (defaults: 2025-01-01 → today), assembles
the raw master matrix, runs the FROZEN training preprocessing pipeline
over it, and saves the unified 17-feature daily parquet to
``data/prospective/<year>/EVR_01_unified_features.parquet``.

Usage
-----
    python scripts/fetch_evr01_2025.py                       # full 2025-now
    python scripts/fetch_evr01_2025.py --start 2026-04-01    # short window
    python scripts/fetch_evr01_2025.py --dry-run             # cache-only

In dry-run mode no network call is attempted — all fetchers must hit cache
or the script reports the gap and exits with code 2.  Useful for offline
inspection after a one-time full fetch.
"""

from __future__ import annotations

import argparse
import io
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")            # type: ignore[attr-defined]
except (AttributeError, io.UnsupportedOperation):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> int:
    sys.path.insert(0, str(_project_root() / "src"))

    from prospective_validation import (
        config, logging_setup, cache, fetchers, feature_builder,
    )
    from prospective_validation.current_data_fetcher import CurrentDataFetcher
    from prospective_validation.logging_setup import logger
    logging_setup.configure_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=_parse_date, default=config.VALIDATION_2025_START)
    parser.add_argument("--end",   type=_parse_date,
                        default=datetime.now(timezone.utc).date())
    parser.add_argument("--force",   action="store_true",
                        help="Bypass cache (re-download everything)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Cache-only; fail if any leg would need the network")
    args = parser.parse_args()

    # Resolve EVR_01
    site = next((s for s in config.EVRENLI_SITES if s.id == config.MVP_SITE_ID), None)
    if site is None:
        logger.error("MVP site {} not found in EVRENLI_SITES", config.MVP_SITE_ID)
        return 1

    print(f"\n=== EVR_01 MVP fetch — {args.start} → {args.end} ===\n")
    print(f"Site            : {site.id}  ({site.name})")
    print(f"Centroid        : lat={site.lat}, lon={site.lon}")
    print(f"Area            : {site.area_da} da ({site.area_ha:.1f} ha)")
    print(f"Cache root      : {config.CACHE_DIR}")
    print(f"Output target   : data/prospective/{args.start.year}/"
          f"{site.id}_unified_features.parquet")
    print()

    if args.dry_run:
        from prospective_validation import geometry
        poly = geometry.site_polygon_coords(site)

        soil_params = {
            "source": "isric_soilgrids_v2", "site_id": site.id,
            "lat": round(site.lat, 6), "lon": round(site.lon, 6),
            "buffer_m": 2000,
            "depths": ["0-5cm", "5-15cm", "15-30cm"],
            "properties": ["clay", "sand", "phh2o"],
        }
        s2_params = {
            "site_id": site.id, "lat": round(site.lat, 6), "lon": round(site.lon, 6),
            "start": args.start.isoformat(), "end": args.end.isoformat(),
            "polygon": geometry.polygon_signature(poly),
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "cloud_threshold_pct": 70, "indices": ["NDVI", "EVI", "NDWI"], "scale_m": 10,
        }
        missing = []
        if cache.get_pickle("soilgrids", soil_params) is None:
            missing.append("soilgrids")
        if cache.get_pickle("s2_gee", s2_params) is None:
            missing.append(f"s2_gee[{args.start}..{args.end}]")

        # ERA5 per-month
        from prospective_validation.fetchers.era5 import _iter_months, _cache_params as era5_params
        for y, m in _iter_months(args.start, args.end):
            if date(y, m, 1) > datetime.now(timezone.utc).date():
                continue
            if cache.get_pickle("era5_cds_month", era5_params(site, y, m)) is None:
                missing.append(f"era5[{y}-{m:02d}]")

        if missing:
            print("DRY-RUN: cache GAPS detected — would hit network for:")
            for x in missing:
                print(f"   - {x}")
            print("\nRun without --dry-run to populate the cache.")
            return 2
        print("DRY-RUN: every leg cache-resident. A real run would be free.\n")

    runner = CurrentDataFetcher(
        start_date=args.start, end_date=args.end, force_refresh=args.force, save=True,
    )
    df = runner.fetch(site)

    print(f"\n=== DONE ===")
    print(f"Rows           : {len(df)}")
    print(f"Columns        : {df.shape[1]} ({list(df.columns)[:6]} ...)")
    print(f"NDVI_int range : {df['NDVI_int'].min():.4f} ... {df['NDVI_int'].max():.4f}")
    print(f"Date range     : {df['date'].min().date()} → {df['date'].max().date()}")
    out = config.PROSPECTIVE_DIR / str(args.start.year) / f"{site.id}_unified_features.parquet"
    print(f"Parquet        : {out}")
    print(f"Audit          : {config.AUDIT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
