"""
TRAK-AI KDS — One-Shot Bootstrap
=================================
Single command to take a fresh checkout to a fully-populated dashboard:

    .\\venv\\Scripts\\python.exe scripts\\bootstrap_dashboard.py

Pipeline (idempotent, continues on per-step failure):
    1. init_database.py             -> tables + 5 seed tarlalar
    2. fetch_all_sites.py           -> 5 unified-features parquets (offline fallback)
    3. ingest_all_retrospective.py  -> parquet -> sensor_reading
    4. ingest_predictions.py        -> reports parquet -> ndvi_prediction
                                       (auto-generates missing per-site predictions)

After this finishes you should be able to:
    streamlit run src/dashboard.py

and see real NDVI / timeseries for any of the 5 EVRENLI sites.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], desc: str) -> bool:
    print("\n" + "=" * 60)
    print(f"  {desc}")
    print(f"  $ {' '.join(cmd)}")
    print("=" * 60)
    try:
        result = subprocess.run(
            [sys.executable, *cmd],
            cwd=str(REPO_ROOT),
            capture_output=False,
        )
        return result.returncode == 0
    except Exception as exc:                                           # noqa: BLE001
        print(f"  !! exception: {exc}")
        return False


def main() -> int:
    steps = [
        (["scripts/init_database.py"],
         "1.  Database initialization"),
        (["scripts/fetch_all_sites.py", "--start", "2025-01-01"],
         "2.  Fetch parquets for all 5 EVRENLI sites"),
        (["scripts/ingest_all_retrospective.py"],
         "3.  Parquet -> sensor_reading"),
        (["scripts/ingest_predictions.py"],
         "4.  NDVI predictions -> ndvi_prediction "
         "(auto-runs frozen LSTM if missing)"),
    ]

    success_count = 0
    for cmd, desc in steps:
        ok = _run(cmd, desc)
        if ok:
            success_count += 1
        else:
            print(f"\n  !! Step failed: {desc} — continuing")

    # ---------------- final smoke test ----------------
    print("\n" + "=" * 60)
    print("  5.  Final smoke test")
    print("=" * 60)
    import sqlite3
    db_path = REPO_ROOT / "data" / "trakai.db"
    if not db_path.exists():
        print("  !! DB still missing — bootstrap FAILED")
        return 1
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        for label, sql in [
            ("tarla",            "SELECT COUNT(*) FROM tarla"),
            ("sensor_reading",   "SELECT COUNT(*) FROM sensor_reading"),
            ("ndvi_prediction",  "SELECT COUNT(*) FROM ndvi_prediction"),
        ]:
            cur.execute(sql)
            n = cur.fetchone()[0]
            print(f"  {label:<18} : {n}")
        cur.execute(
            "SELECT t.evrenli_id, COUNT(s.id) AS n_obs, "
            "  MIN(s.timestamp), MAX(s.timestamp) "
            "FROM tarla t LEFT JOIN sensor_reading s ON s.tarla_id = t.id "
            "GROUP BY t.id ORDER BY t.id"
        )
        print("\n  per-site observation coverage:")
        for evr, n, t0, t1 in cur.fetchall():
            print(f"    {evr}: {n} rows, {t0} -> {t1}")
    finally:
        con.close()

    print("\n" + "=" * 60)
    print(f"  BOOTSTRAP DONE ({success_count}/{len(steps)} steps OK)")
    print("=" * 60)
    print("\n  Next step:")
    print("    streamlit run src/dashboard.py")
    return 0 if success_count == len(steps) else 1


if __name__ == "__main__":
    sys.exit(main())
