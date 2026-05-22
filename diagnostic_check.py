import sqlite3
from pathlib import Path

print("=== DB CHECK ===")
db_path = Path("data/trakai.db")
print(f"DB exists: {db_path.exists()}")
if db_path.exists():
    print(f"DB size: {db_path.stat().st_size / 1024:.1f} KB")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type=" + chr(39) + "table" + chr(39))
    tables = [r[0] for r in cursor.fetchall()]
    print(f"Tables: {tables}")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cursor.fetchone()[0]} rows")
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"    Cols: {cols}")

print("")
print("=== SCRIPTS ===")
for s in sorted(Path("scripts").glob("*.py")):
    print(f"  {s.name}")

print("")
print("=== PARQUET FILES ===")
for year in [2024, 2025, 2026]:
    for site in ["EVR_01", "EVR_02", "EVR_03", "EVR_04", "EVR_05"]:
        p = Path(f"data/prospective/{year}/{site}_unified_features.parquet")
        if p.exists():
            print(f"  {p.name}: {p.stat().st_size / 1024:.1f} KB")

print("")
print("=== PREDICTIONS ===")
pred_dir = Path("reports/prospective")
if pred_dir.exists():
    for f in sorted(pred_dir.glob("*.parquet")):
        print(f"  {f.name}")

print("")
print("=== DATA_INTEGRATION MODULE ===")
di = Path("src/data_integration")
if di.exists():
    for f in sorted(di.glob("*.py")):
        print(f"  {f.name}")
else:
    print("  YOK")

print("")
print("=== DASHBOARD_PAGES ===")
dp = Path("src/dashboard_pages")
if dp.exists():
    for f in sorted(dp.rglob("*.py")):
        print(f"  {f.relative_to(dp.parent)}")
else:
    print("  YOK")
