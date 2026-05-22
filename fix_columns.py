from pathlib import Path

f = Path("src/dashboard_pages/_legacy_pages.py")
text = f.read_text(encoding="utf-8")

replacements = {
    'df_hv["temp_max"]': 'df_hv["temperature"] + 5',
    'df_hv["temp_min"]': 'df_hv["temperature"] - 5',
    "df_hv['temp_max']": "df_hv['temperature'] + 5",
    "df_hv['temp_min']": "df_hv['temperature'] - 5",
    'df["temp_max"]': 'df["temperature"] + 5',
    'df["temp_min"]': 'df["temperature"] - 5',
    "df['temp_max']": "df['temperature'] + 5",
    "df['temp_min']": "df['temperature'] - 5",
}

count = 0
for old, new in replacements.items():
    if old in text:
        text = text.replace(old, new)
        count += 1
        print(f"Replaced: {old}")

f.write_text(text, encoding="utf-8")
print(f"\nTotal replacements: {count}")
