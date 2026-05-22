import sqlite3

conn = sqlite3.connect("data/trakai.db")
c = conn.cursor()

print("=== TARLA TABLE ===")
c.execute("SELECT id, name, evrenli_id, lat, lon FROM tarla")
for r in c.fetchall():
    print(f"  {r}")

print()
print("=== SENSOR_READING — Row Counts Per Tarla ===")
c.execute("""
    SELECT t.id, t.name, COUNT(s.id) as rows, 
           MIN(s.timestamp), MAX(s.timestamp)
    FROM tarla t 
    LEFT JOIN sensor_reading s ON t.id = s.tarla_id 
    GROUP BY t.id
""")
for r in c.fetchall():
    print(f"  Tarla {r[0]} ({r[1]}): {r[2]} rows  ({r[3]} -> {r[4]})")

print()
print("=== SAMPLE NDVI VALUES (Tarla 1, last 5) ===")
c.execute("""
    SELECT timestamp, ndvi, evi, temperature, precipitation 
    FROM sensor_reading 
    WHERE tarla_id = 1 
    ORDER BY timestamp DESC LIMIT 5
""")
for r in c.fetchall():
    print(f"  {r[0]}: ndvi={r[1]}, evi={r[2]}, temp={r[3]}, precip={r[4]}")

print()
print("=== NDVI PREDICTION TABLE ===")
c.execute("SELECT COUNT(*) FROM ndvi_prediction")
print(f"  Total predictions: {c.fetchone()[0]}")
c.execute("""
    SELECT prediction_date, target_date, predicted_ndvi, anomaly_vs_climatology 
    FROM ndvi_prediction 
    WHERE tarla_id = 1 
    ORDER BY prediction_date DESC LIMIT 3
""")
for r in c.fetchall():
    print(f"  {r}")

print()
print("=== YIELD PREDICTION TABLE ===")
c.execute("SELECT COUNT(*) FROM yield_prediction")
print(f"  Total yield predictions: {c.fetchone()[0]}")

conn.close()
