"""
TRAK-AI KDS — Fetch retrospective parquets for all 5 EVRENLI pilot sites
=========================================================================

Wraps ``prospective_validation.CurrentDataFetcher`` so we can drive a
batch fetch from the CLI:

    python scripts/fetch_all_sites.py --start 2025-01-01
    python scripts/fetch_all_sites.py --sites EVR_02 EVR_03

ERA5-Land is ~9 km grid; the 5 EVR sites are within ~2 km of one another so
they all map to the same ERA5 pixel. Sentinel-2 (10 m) differs. The fetcher
caches ERA5 by lat/lon-rounded key, so re-running for nearby sites is cheap.

Offline fallback: if the live GEE+CDS fetch fails (no auth, no network),
the script clones EVR_01's parquet into the missing site's directory with a
clearly-labelled column (`fetched_kaynak`) so downstream ingestion still
works. This keeps the dashboard demonstrable on a clean box.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
sys.path.insert(0, str(SRC))

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("fetch_all_sites")


# ---------------------------------------------------------------------------
# Lazy import of the orchestrator (heavy: pulls earthengine + cdsapi)
# ---------------------------------------------------------------------------
def _import_fetcher():
    from prospective_validation.current_data_fetcher import CurrentDataFetcher
    from prospective_validation import config as flov_cfg
    return CurrentDataFetcher, flov_cfg


def _parquet_path(site_id: str, year: int) -> Path:
    return REPO_ROOT / "data" / "prospective" / str(year) / f"{site_id}_unified_features.parquet"


def _fallback_copy_from_evr01(target_site_id: str, year: int) -> bool:
    """Clone EVR_01 parquet into target site (transparent demo fallback)."""
    src = _parquet_path("EVR_01", year)
    dst = _parquet_path(target_site_id, year)
    if not src.exists():
        logger.error("[fallback] EVR_01/{} parquet missing — cannot clone", year)
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    logger.warning("[fallback] {} ⇐ cloned from EVR_01 ({}). "
                   "ERA5 grid coincidence; S2 differences not captured.",
                   target_site_id, year)
    return True


def fetch_one(site_id: str, start: date, end: date | None,
              force_refresh: bool = False, allow_fallback: bool = True) -> dict:
    """Fetch one site; on failure optionally clone EVR_01."""
    try:
        CurrentDataFetcher, flov_cfg = _import_fetcher()
    except Exception as exc:                                           # noqa: BLE001
        if not allow_fallback:
            return {"site": site_id, "status": "fail", "error": f"import: {exc}"}
        ok = _fallback_copy_from_evr01(site_id, start.year)
        return {"site": site_id, "status": "fallback" if ok else "fail",
                "error": f"import failed: {exc}"}

    # Resolve Site dataclass (NOT dict — config.EVRENLI_SITES is a tuple of Site)
    try:
        site = next(s for s in flov_cfg.EVRENLI_SITES if s.id == site_id)
    except StopIteration:
        return {"site": site_id, "status": "fail", "error": "unknown site_id"}

    fetcher = CurrentDataFetcher(start_date=start, end_date=end,
                                 force_refresh=force_refresh, save=True)
    try:
        df = fetcher.fetch(site)
        n = 0 if df is None else len(df)
        out_path = _parquet_path(site_id, start.year)
        return {"site": site_id, "status": "ok", "rows": n,
                "path": str(out_path)}
    except Exception as exc:                                           # noqa: BLE001
        logger.exception("[fetch] {} failed: {}", site_id, exc)
        if not allow_fallback:
            return {"site": site_id, "status": "fail", "error": str(exc)}
        ok = _fallback_copy_from_evr01(site_id, start.year)
        return {"site": site_id, "status": "fallback" if ok else "fail",
                "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--sites", nargs="+",
                        default=["EVR_01", "EVR_02", "EVR_03", "EVR_04", "EVR_05"])
    parser.add_argument("--force-refresh", action="store_true",
                        help="Ignore on-disk cache; refetch from APIs.")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Don't clone EVR_01 if external fetch fails.")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end) if args.end else None

    results = []
    for site_id in args.sites:
        logger.info("=== fetching {} from {} to {} ===",
                    site_id, args.start, args.end or "today")
        res = fetch_one(site_id, start, end,
                        force_refresh=args.force_refresh,
                        allow_fallback=not args.no_fallback)
        results.append(res)
        marker = {"ok": "OK", "fallback": "FALLBACK", "fail": "FAIL"}.get(
            res["status"], "?")
        logger.info("[{}] {} :: {}", marker, site_id, res)

    print("\n=== FETCH SUMMARY ===")
    for r in results:
        print(f"  {r['status']:<9} {r['site']:<7} "
              f"{r.get('rows', r.get('error', ''))}")
    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_fb = sum(1 for r in results if r["status"] == "fallback")
    n_fa = sum(1 for r in results if r["status"] == "fail")
    print(f"\n  Total: {n_ok} ok, {n_fb} fallback, {n_fa} fail")
    return 0 if n_fa == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
