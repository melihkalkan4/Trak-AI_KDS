import re
from pathlib import Path

# Pattern: df["xxx"] - sadece double quotes (basit)
pattern_dq = re.compile(r'df\w*\["(\w+)"\]')
pattern_sq = re.compile(r"df\w*\['(\w+)'\]")

db_cols = {"id", "tarla_id", "timestamp", "temperature", "humidity",
           "soil_moisture", "ndvi", "evi", "ndwi", "precipitation",
           "gdd", "drought_index", "data_source", "created_at",
           "tarih_dt", "date", "doy", "year", "month", "day",
           "prediction_date", "target_date", "predicted_ndvi"}

issues = {}
for f in Path("src").rglob("*.py"):
    if "test" in str(f) or "__pycache__" in str(f):
        continue
    try:
        text = f.read_text(encoding="utf-8")
        for pattern in [pattern_dq, pattern_sq]:
            for match in pattern.finditer(text):
                col = match.group(1)
                if col not in db_cols and len(col) > 2 and not col.isdigit():
                    line = text[:match.start()].count("\n") + 1
                    key = f"{f.relative_to(Path('src'))}:{line}"
                    issues[key] = col
    except Exception as e:
        pass

print("Potansiyel column mismatchler:")
for loc, col in sorted(issues.items()):
    print(f"  {loc} -> {col}")

if not issues:
    print("  (yok)")
