"""
Batch-run the cross-modal validator over a (site, date-range) window.

Usage:
    python scripts/run_cross_modal_validation.py --site EVR_01 \
        --start 2026-05-01 --end 2026-05-22 --step 5
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path


def _bootstrap() -> None:
    here = Path(__file__).resolve()
    root = here.parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cross-modal validator runner.")
    p.add_argument("--site", required=True, help="Site ID (e.g. EVR_01).")
    p.add_argument("--start", required=True, help="Start date YYYY-MM-DD.")
    p.add_argument("--end", required=True, help="End date YYYY-MM-DD.")
    p.add_argument("--step", type=int, default=5, help="Days between samples.")
    p.add_argument("--no-stub-sat", action="store_true",
                   help="Disable the synthetic satellite chip fallback.")
    return p.parse_args()


def main() -> int:
    _bootstrap()
    args = _parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    from visual_validation import config
    from visual_validation.analyzers.cross_modal_validator import CrossModalValidator

    config.ensure_dirs()
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    val = CrossModalValidator(use_stub_satellite_chip=not args.no_stub_sat)
    runs = val.validate_batch(args.site, start, end, step_days=args.step)

    print(f"\n=== {len(runs)} consensus run(s) for {args.site} ===")
    for r in runs:
        c = r.consensus
        a = r.alert
        print(f"  {r.target_date}  class={c['consensus_class']:<14} "
              f"flag={c['flag']:<18} severity={a['severity']:<8} "
              f"present={','.join(r.available_modalities) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
