"""
TRAK-AI KDS — Master Bootstrap (one-shot, idempotent)
=====================================================
Single command takes a fresh checkout to a fully-populated dashboard:

    venv\\Scripts\\python.exe scripts\\master_bootstrap.py

Pipeline (continues on per-step failure, summarises at the end):

    1. init_database.py                  — schema + 5 EVRENLI seed
    2. update_tarla_diversity.py         — 3 sunflower + 2 wheat,
                                           distinct coords, soil_type column
    3. synthesize_per_site_parquets.py   — per-site NDVI/EVI/NDWI curves
                                           (offline-first; ERA5 shared, S2 derived)
    4. ingest_all_retrospective.py       — parquet → sensor_reading
    5. predict_all_tarlalar.py           — NDVI + crop-aware yield →
                                           ndvi_prediction + yield_prediction +
                                           tarla_tahminler (dashboard reads this)

After this finishes:

    venv\\Scripts\\streamlit run src\\dashboard.py
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "trakai.db"


STEPS: list[tuple[list[str], str, bool]] = [
    (["scripts/init_database.py"],
     "1.  Database initialization (schema + 5 EVRENLI seed)", True),
    (["scripts/update_tarla_diversity.py"],
     "2.  Diversify tarlalar (3 sunflower + 2 wheat, distinct coords)", True),
    (["scripts/synthesize_per_site_parquets.py"],
     "3.  Per-site distinct NDVI/EVI/NDWI parquets (offline-first)", True),
    (["scripts/ingest_all_retrospective.py"],
     "4.  Parquet -> sensor_reading", True),
    (["scripts/predict_all_tarlalar.py"],
     "5.  Crop-aware NDVI + yield predictions -> 3 tables", True),
]


def _run(cmd: list[str], desc: str) -> bool:
    print("\n" + "=" * 64)
    print(f"  {desc}")
    print(f"  $ {sys.executable} {' '.join(cmd)}")
    print("=" * 64)
    try:
        result = subprocess.run(
            [sys.executable, *cmd],
            cwd=str(REPO_ROOT),
            capture_output=False,
        )
        return result.returncode == 0
    except Exception as exc:                                       # noqa: BLE001
        print(f"  !! exception: {exc}")
        return False


def _smoke_test() -> dict:
    print("\n" + "=" * 64)
    print("  6.  Final smoke test")
    print("=" * 64)
    if not DB_PATH.exists():
        print("  !! DB still missing — bootstrap FAILED")
        return {"ok": False}

    out: dict = {"ok": True, "counts": {}, "per_site": []}
    con = sqlite3.connect(DB_PATH)
    try:
        for label, sql in [
            ("tarla",            "SELECT COUNT(*) FROM tarla"),
            ("sensor_reading",   "SELECT COUNT(*) FROM sensor_reading"),
            ("ndvi_prediction",  "SELECT COUNT(*) FROM ndvi_prediction"),
            ("yield_prediction", "SELECT COUNT(*) FROM yield_prediction"),
            ("tarla_tahminler",  "SELECT COUNT(*) FROM tarla_tahminler"),
        ]:
            n = con.execute(sql).fetchone()[0]
            out["counts"][label] = n
            print(f"  {label:<18} : {n}")

        rows = con.execute("""
            SELECT t.evrenli_id, t.crop_type, t.lat, t.lon,
                   ROUND(tt.ndvi_mevcut, 3) AS ndvi_now,
                   ROUND(tt.ndvi_tahmin_7gun, 3) AS ndvi_7d,
                   tt.saglik_durumu AS health,
                   ROUND(tt.verim_tahmini_kg_dekar, 1) AS yield_kg
            FROM tarla t
            LEFT JOIN (
                SELECT tarla_id, ndvi_mevcut, ndvi_tahmin_7gun,
                       saglik_durumu, verim_tahmini_kg_dekar,
                       ROW_NUMBER() OVER (PARTITION BY tarla_id
                                          ORDER BY timestamp DESC) rn
                FROM tarla_tahminler
            ) tt ON tt.tarla_id = t.id AND tt.rn = 1
            ORDER BY t.id
        """).fetchall()
        print("\n  Per-site dashboard view (what page_tarla will render):")
        print(f"    {'site':<7} {'crop':<10} {'coord':<22} "
              f"{'NDVI':<6} {'7d':<6} {'health':<10} {'yield':>7}")
        for r in rows:
            evr, crop, lat, lon, n_now, n_7d, health, yld = r
            coord = f"({lat:.4f}, {lon:.4f})"
            print(f"    {evr:<7} {crop or '-':<10} {coord:<22} "
                  f"{n_now or '-':<6} {n_7d or '-':<6} "
                  f"{health or '-':<10} {yld or '-':>7}")
            out["per_site"].append({
                "evrenli_id": evr, "crop": crop,
                "ndvi_now": n_now, "ndvi_7d": n_7d,
                "health": health, "yield_kg_da": yld,
            })
    finally:
        con.close()
    return out


def main() -> int:
    print("\n" + "#" * 64)
    print("#  TRAK-AI KDS — MASTER BOOTSTRAP")
    print("#  (1 init + 2 diversify + 3 synth + 4 ingest + 5 predict)")
    print("#" * 64)

    success = 0
    for cmd, desc, critical in STEPS:
        ok = _run(cmd, desc)
        if ok:
            success += 1
        else:
            print(f"\n  !! Step failed: {desc} — continuing")

    smoke = _smoke_test()

    print("\n" + "=" * 64)
    print(f"  BOOTSTRAP DONE ({success}/{len(STEPS)} steps OK)")
    print("=" * 64)
    print("\n  Next step:")
    print(f"    {sys.executable.replace('python.exe', 'streamlit.exe')} "
          f"run src/dashboard.py")
    print("    (or:  venv\\Scripts\\streamlit run src\\dashboard.py)")
    return 0 if success == len(STEPS) and smoke.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
