import sqlite3
import pandas as pd

conn = sqlite3.connect("data/trakai.db")

# Dashboard'un kullandigi query'yi taklit et
df = pd.read_sql_query("""
    SELECT * FROM sensor_reading WHERE tarla_id = 1 ORDER BY timestamp DESC LIMIT 5
""", conn)

print("=== DATAFRAME COLUMNS ===")
print(list(df.columns))
print()
print("=== SAMPLE ROW ===")
print(df.head(1).T)
print()
print("=== DATA LOADERS FONKSIYONLARI ===")

# Dashboard data_loaders.py'da hangi query atiliyor?
from pathlib import Path
dl = Path("src/dashboard_pages/shared/data_loaders.py")
if dl.exists():
    text = dl.read_text(encoding="utf-8")
    # SELECT statement bul
    import re
    for match in re.finditer(r'SELECT[^"\']{20,500}', text, re.IGNORECASE | re.DOTALL):
        snippet = match.group(0)[:300]
        print(f"\n--- Query found ---")
        print(snippet)

conn.close()
