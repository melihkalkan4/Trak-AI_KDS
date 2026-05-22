"""
Convenience launcher for the FLOV Streamlit dashboard.

Runs:
    streamlit run dashboard/flov_dashboard.py

with the same Python that imports prospective_validation correctly (i.e.
the project venv).  Use this instead of plain `streamlit ...` so the venv
is always picked up on Windows.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = _project_root()
    dash = root / "dashboard" / "flov_dashboard.py"
    if not dash.exists():
        print(f"ERROR: dashboard not found at {dash}")
        return 1
    cmd = [sys.executable, "-m", "streamlit", "run", str(dash),
           "--server.headless", "false"]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(root))


if __name__ == "__main__":
    raise SystemExit(main())
