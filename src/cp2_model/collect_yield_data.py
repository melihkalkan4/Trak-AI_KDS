"""
TÜİK Trakya Bölgesi Mahsul Verimi Verisi
==========================================
Edirne + Kırklareli + Tekirdağ bölgesi 2017-2024 yıllık verim verileri.
Kaynak: TÜİK Bitkisel Üretim İstatistikleri (yaklaşık değerler).
Çıktı: data/yield/trakya_yield_2017_2024.csv
"""
import os
import pandas as pd
from pathlib import Path

TUIK_DATA = {
    "Wheat": {
        2017: 310,
        2018: 330,
        2019: 315,
        2020: 298,
        2021: 350,
        2022: 342,
        2023: 335,
        2024: 318,
    },
    "Sunflower": {
        2017: 168,
        2018: 182,
        2019: 175,
        2020: 158,
        2021: 195,
        2022: 200,
        2023: 190,
        2024: 178,
    },
}

SOURCE = "TÜİK Bitkisel Üretim İstatistikleri (yaklaşık)"


def collect_and_save():
    project_root = Path(__file__).parent.parent.parent
    out_dir = project_root / "data" / "yield"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "trakya_yield_2017_2024.csv"

    rows = []
    for crop, year_map in TUIK_DATA.items():
        for year, yield_val in sorted(year_map.items()):
            rows.append({"year": year, "crop": crop, "yield_kg_dekar": yield_val, "source": SOURCE})

    df = pd.DataFrame(rows).sort_values(["crop", "year"]).reset_index(drop=True)
    df.to_csv(out_path, index=False)

    print(f"Kaydedildi: {out_path}")
    print(f"Toplam kayıt: {len(df)}")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    collect_and_save()
