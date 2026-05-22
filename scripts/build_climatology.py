"""
Build the DOY-mean NDVI climatology (2017-2024) and lock its hash.

Run once.  Subsequent runs are no-ops (idempotent integrity check).

Usage
-----
    python scripts/build_climatology.py
    python scripts/build_climatology.py --rebuild   # delete + rebuild
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(_project_root() / "src"))

    from prospective_validation import climatology, config, logging_setup  # noqa: E402

    logging_setup.configure_logging()
    from prospective_validation.logging_setup import logger

    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="Delete existing artefact and rebuild")
    args = parser.parse_args()

    if args.rebuild and climatology.CLIMATOLOGY_PATH.exists():
        logger.warning("[climatology] --rebuild requested; removing {}",
                       climatology.CLIMATOLOGY_PATH)
        # Best-effort: read-only bit may block delete on Windows
        try:
            climatology.CLIMATOLOGY_PATH.chmod(0o666)
        except OSError:
            pass
        climatology.CLIMATOLOGY_PATH.unlink()

    df = climatology.build_climatology()
    logger.info("[climatology] rows={}, mean(count)={:.1f}, peak(smooth)={:.3f}",
                len(df), df["ndvi_count"].mean(), df["ndvi_smooth"].max())
    print(f"\nClimatology written: {climatology.CLIMATOLOGY_PATH}")
    print(f"Rows         : {len(df)}")
    print(f"Mean samples : {df['ndvi_count'].mean():.1f} per DOY")
    print(f"Peak NDVI    : {df['ndvi_smooth'].max():.3f} (DOY "
          f"{int(df['ndvi_smooth'].idxmax()) + 1})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
