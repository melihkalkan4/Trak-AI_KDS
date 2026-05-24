# ÇP-2.5 — Görev 12: Final Sentez

Üretim tarihi (UTC): 2026-05-23T16:01:34.236266+00:00

## Master Karşılaştırma Tablosu (LOYO)

| Layer | Model | Ürün | n | R² | RMSE | Skill Score |
|---|---|---|---|---|---|---|
| B0 | Climatology | bugday | 589 | +0.213 | 61.7 | +0.000 |
| B3 | ClimateProxy | bugday | 589 | +0.126 | 65.1 | -0.054 |
| A | elastic_net | bugday | 589 | -0.092 | 72.7 | -0.178 |
| B | gpr | bugday | 213 | -0.536 | 87.3 | -0.266 |
| C | xgboost | bugday | 213 | -0.311 | 80.7 | -0.170 |
| A | random_forest | aycicegi | 576 | +0.051 | 49.5 | +0.009 |
| B | random_forest | aycicegi | 209 | +0.237 | 47.1 | +0.136 |
| C | gpr | aycicegi | 209 | +0.386 | 42.3 | +0.225 |

## Şampiyon Modeller

- **bugday**: Layer B0 / Climatology  (R²=+0.213, RMSE=61.7, SS=+0.000)
- **aycicegi**: Layer C / gpr  (R²=+0.386, RMSE=42.3, SS=+0.225)

## Hipotez Sonuçları

### H1: İlçe-bazlı (n=1165) il-bazlıyı (n=132) outperform eder

- delta_r2_loyo_bugday: `v2=-0.092 vs v1=-0.085 → ΔR²=-0.007`
- delta_r2_loyo_aycicegi: `v2=+0.051 vs v1=+0.646 → ΔR²=-0.595`
- verdict_loyo: `LOYO için RED, LOILO için PASS`

### H2: NDVI ekleme climate-only baseline'ı outperform eder

- delta_r2_loyo_bugday: `-0.092 → -0.536  ΔR²=-0.444`
- delta_r2_loyo_aycicegi: `+0.051 → +0.237  ΔR²=+0.186`
- verdict: `bugday: FAIL (Δ=-0.444); aycicegi: PASS (Δ=+0.186)`

### H3: Multimodal füzyon (Layer C) Layer B'yi outperform eder

- delta_r2_loyo_bugday: `-0.536 → -0.311  ΔR²=+0.225`
- delta_r2_loyo_aycicegi: `+0.237 → +0.386  ΔR²=+0.149`
- verdict: `bugday: PASS (Δ=+0.225); aycicegi: PASS (Δ=+0.149)`

### H4: Anomali yıllarda SS > 0.30

- verdict: `Görev 9 raporlarından oku`

### H5: |LOILO - LOYO| < 0.15

- delta_loyo_loilo_bugday: `LOYO=-0.092, LOILO=+0.441, Δ=+0.533`
- delta_loyo_loilo_aycicegi: `LOYO=+0.051, LOILO=+0.504, Δ=+0.453`
- verdict: `Layer A için reddedildi (fark 0.5+)`

## Veri Kaynak Manifesti

- yields: `TÜİK ilçe-bazlı (data/external/tuik/tuik_ilce_yields_clean.csv)`
- climate: `NASA POWER MERRA-2 (data/processed/openmeteo_ilce/)`
- ndvi: `Sentinel-2 (data/processed/ndvi_ilce/)`
- soil: `ISRIC SoilGrids (data/processed/soil_ilce.csv)`