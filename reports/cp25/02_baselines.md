# ÇP-2.5 — Görev 2: Baseline Modeller (LOYO)

## Veri

- TÜİK ilçe-bazlı dataset: **1165 satır**, 29 ilçe, 2004-2025

## Sonuçlar — LOYO (Leave-One-Year-Out)

### aycicegi_yaglik (n=576)

| Model | R² | RMSE | MAE | MAPE | Bias | Skill Score vs B0 |
|---|---|---|---|---|---|---|
| B0_Climatology | +0.033 | 50.0 | 40.4 | 22.9% | -0.0 | +0.000 |
| B1_YearTrend | +0.001 | 50.8 | 39.5 | 22.7% | +1.4 | -0.017 |
| B2_Persistence | +0.210 | 45.2 | 33.4 | 18.8% | +3.7 | +0.096 |
| B3_ClimateProxy | +0.087 | 48.6 | 37.4 | 21.1% | +1.6 | +0.028 |

### bugday (n=589)

| Model | R² | RMSE | MAE | MAPE | Bias | Skill Score vs B0 |
|---|---|---|---|---|---|---|
| B0_Climatology | +0.213 | 61.7 | 48.7 | 13.4% | -0.0 | +0.000 |
| B1_YearTrend | +0.208 | 61.9 | 49.0 | 13.4% | +0.4 | -0.003 |
| B2_Persistence | -0.269 | 78.4 | 62.6 | 16.7% | +2.2 | -0.270 |
| B3_ClimateProxy | +0.126 | 65.1 | 50.0 | 13.7% | -0.3 | -0.054 |

## Kabul Kriteri

Hiçbir ileri model bu baseline'ları yenmiyorsa **deploy edilemez**.
Özellikle B3 (climate-proxy) R²>0 olmalı (yoksa veri/kod hatası).

⚠️ **Not**: B3 burada ETL beklemediği için TÜİK ekilen_alan_da + year üzerinden vekildir. Gerçek climate B3 baseline'ı Görev 3 ETL sonrası Katman A modellerinde test edilecek.

## Görseller
- `reports/cp25/fig_baseline_comparison.png`