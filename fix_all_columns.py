from pathlib import Path

# DB column adı eşlemeleri (eski -> yeni)
MAPPINGS = {
    # _legacy_pages.py içindeki Türkçe column adları
    "hava_temp_c": "temperature",
    "yagis_gunluk_mm": "precipitation",
    "gdd_kumulatif": "gdd",
    "don_riski": "drought_index",
    "sicak_stres": "temperature",  # placeholder
    "nem_1_pct": "humidity",
    "nem_2_pct": "soil_moisture",
    "model_nem": "humidity",
    "tarih": "timestamp",
    "ndvi_tahmini": "ndvi",
    
    # weather/historical_trends.py - ERA5 raw -> DB equivalents
    "t2m_max": "temperature",
    "t2m_min": "temperature",
    "t2m_mean": "temperature",
    "tp_sum": "precipitation",
    
    # weather/forecast.py - short names
    "prec": "precipitation",
    "tmax": "temperature",
    "tmin": "temperature",
    
    # shared/data_loaders.py
    "site_id": "evrenli_id",
}

# Hangi dosyalar
TARGET_FILES = [
    "src/dashboard_pages/_legacy_pages.py",
    "src/dashboard_pages/weather/historical_trends.py",
    "src/dashboard_pages/weather/forecast.py",
    "src/dashboard_pages/shared/data_loaders.py",
]

total_replacements = 0
for filepath in TARGET_FILES:
    f = Path(filepath)
    if not f.exists():
        print(f"SKIP: {filepath} (not found)")
        continue
    
    text = f.read_text(encoding="utf-8")
    original_text = text
    file_count = 0
    
    for old_col, new_col in MAPPINGS.items():
        # Double quotes
        old_pattern_dq = f'"{old_col}"'
        new_pattern_dq = f'"{new_col}"'
        if old_pattern_dq in text:
            count = text.count(old_pattern_dq)
            text = text.replace(old_pattern_dq, new_pattern_dq)
            file_count += count
            print(f"  {filepath}: {old_col} -> {new_col} ({count} times)")
        
        # Single quotes
        old_pattern_sq = f"'{old_col}'"
        new_pattern_sq = f"'{new_col}'"
        if old_pattern_sq in text:
            count = text.count(old_pattern_sq)
            text = text.replace(old_pattern_sq, new_pattern_sq)
            file_count += count
            print(f"  {filepath}: {old_col} -> {new_col} ({count} times, single quote)")
    
    if text != original_text:
        # Backup
        backup = f.with_suffix(f.suffix + ".bak")
        backup.write_text(original_text, encoding="utf-8")
        f.write_text(text, encoding="utf-8")
        print(f"FIXED: {filepath} ({file_count} replacements, backup at {backup.name})")
        total_replacements += file_count

print(f"\n=== TOTAL: {total_replacements} replacements across {len(TARGET_FILES)} files ===")
