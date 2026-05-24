# ÇP-2.5 — Görev 1: Veri Schema Doğrulaması ve EDA

## 1. Schema Özeti

### `master_feature_matrix_2017_2024.csv`
- Shape: **2922 × 23**
- Yıl aralığı: [2017, 2024]
- Unique dates: 2922
- Spatial granularity tespiti: **{'il': False, 'ilce': False, 'parsel': False, 'lat_lon': False, 'single_pt': True, '_soil_uniques': {'clay_0-5cm': 1, 'clay_5-15cm': 1, 'clay_15-30cm': 1, 'sand_0-5cm': 1, 'sand_5-15cm': 1, 'sand_15-30cm': 1, 'phh2o_0-5cm': 1, 'phh2o_5-15cm': 1, 'phh2o_15-30cm': 1}}**

### `tuik_ilce_yields_clean.csv` (YENİ)
- Shape: **1165 × 10**
- 29 ilçe × 3 il × 2 ürün × 22 yıl
- Kolonlar: ['ilce_id', 'ilce', 'il', 'year', 'crop', 'urun_tr', 'ekilen_alan_da', 'hasat_alan_da', 'verim_kg_da', 'uretim_ton']
- Per crop: {'aycicegi_yaglik': 576, 'bugday': 589}

### `ilce_coords.csv`
- 34 ilçe centroid (lat/lon)
- Lat: [40.6131, 41.9633], Lon: [26.09, 28.9337]

## 2. JOIN Olabilirliği

- **join_ilce_year**: `skipped (key missing)`
- **join_il_year**: `skipped (key missing)`
- **join_year_only_centroid_proxy**: `{'n_rows': 436, 'note': 'Vize centroid features replicated to every (ilçe, year) label.'}`

## 3. Top-5 Korelasyon (verim_kg_da'ya göre)

### aycicegi_yaglik (n=216)
- year: -0.530
- e_sum: -0.484
- t2m_max: -0.447
- t2m_mean: -0.419
- NDWI_int: +0.395

### bugday (n=220)
- NDVI: -0.456
- uretim_ton: +0.368
- NDWI: +0.364
- NDVI_int: -0.271
- phh2o_0-5cm: +0.223

## 4. Anomali Yıl Özeti

- Toplam anomali satırı (|z|>1.5): **147**
- z<-1.5 (kuraklık şokları): 76
- z>+1.5 (yüksek-verim): 69

## 5. Veri Kalitesi

- **yields_duplicates**: `0`
- **coords_missing_ilce**: `[]`
- **yield_lt_50_kg_da**: `0`
- **yield_gt_700_kg_da**: `0`
- **mfm_ndvi_int_missing_pct**: `0.0`
- **mfm_NDVI_raw_missing_pct**: `87.75`

## 6. EDA Görselleri Üretildi

- `reports/cp25/fig_yield_distribution.png`
- `reports/cp25/fig_yield_vs_year.png`
- `reports/cp25/fig_correlation_matrix.png`
- `reports/cp25/fig_spatial_yield_map.png`