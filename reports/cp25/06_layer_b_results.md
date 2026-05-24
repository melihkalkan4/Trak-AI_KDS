# ÇP-2.5 — Görev 6: Layer B (Climate + NDVI) + H2 Testi

## H2 — NDVI Marjinal Katkı (ΔR² ≥ 0.10)

| Ürün | CV | LA Champion R² | LB Champion R² | ΔR² | H2 PASS? |
|---|---|---|---|---|---|
| bugday | LOYO | -0.092 | -0.536 | -0.444 | ❌ |
| bugday | LOILO | +0.441 | +0.429 | -0.012 | ❌ |
| bugday | Spatiotemporal | +0.321 | +0.314 | -0.007 | ❌ |
| aycicegi | LOYO | +0.051 | +0.237 | +0.186 | ✅ |
| aycicegi | LOILO | +0.504 | +0.450 | -0.054 | ❌ |
| aycicegi | Spatiotemporal | +0.387 | +0.434 | +0.047 | ❌ |

## bugday (n=213)
- Champion (LOYO): **gpr**
- R²=-0.536, RMSE=87.3, MAE=68.2, SS=-0.266
- Kabul (R²≥0.45, SS≥0.25): ❌ FAIL

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | SS |
|---|---|---|---|---|
| elastic_net | LOILO | +0.066 | 68.1 | +0.013 |
| elastic_net | LOYO | -0.966 | 98.8 | -0.432 |
| elastic_net | Spatiotemporal | -0.058 | 72.5 | -0.051 |
| gpr | LOILO | +0.429 | 53.2 | +0.228 |
| gpr | LOYO | -0.536 | 87.3 | -0.266 |
| gpr | Spatiotemporal | +0.250 | 61.0 | +0.116 |
| pls | LOILO | +0.076 | 67.7 | +0.018 |
| pls | LOYO | -2.044 | 122.9 | -0.782 |
| pls | Spatiotemporal | -0.048 | 72.1 | -0.046 |
| random_forest | LOILO | +0.416 | 53.8 | +0.220 |
| random_forest | LOYO | -0.739 | 92.9 | -0.347 |
| random_forest | Spatiotemporal | +0.273 | 60.1 | +0.129 |
| xgboost | LOILO | +0.395 | 54.8 | +0.206 |
| xgboost | LOYO | -0.637 | 90.1 | -0.307 |
| xgboost | Spatiotemporal | +0.314 | 58.4 | +0.154 |

## aycicegi (n=209)
- Champion (LOYO): **random_forest**
- R²=+0.237, RMSE=47.1, MAE=36.5, SS=+0.136
- Kabul (R²≥0.55, SS≥0.35): ❌ FAIL

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | SS |
|---|---|---|---|---|
| elastic_net | LOILO | +0.249 | 46.8 | +0.143 |
| elastic_net | LOYO | -0.027 | 54.7 | -0.002 |
| elastic_net | Spatiotemporal | +0.271 | 46.1 | +0.156 |
| gpr | LOILO | +0.450 | 40.0 | +0.266 |
| gpr | LOYO | +0.214 | 47.9 | +0.123 |
| gpr | Spatiotemporal | +0.434 | 40.6 | +0.256 |
| pls | LOILO | +0.177 | 49.0 | +0.103 |
| pls | LOYO | -0.122 | 57.2 | -0.048 |
| pls | Spatiotemporal | +0.255 | 46.6 | +0.147 |
| random_forest | LOILO | +0.406 | 41.6 | +0.237 |
| random_forest | LOYO | +0.237 | 47.1 | +0.136 |
| random_forest | Spatiotemporal | +0.338 | 43.9 | +0.195 |
| xgboost | LOILO | +0.329 | 44.2 | +0.190 |
| xgboost | LOYO | -0.112 | 56.9 | -0.043 |
| xgboost | Spatiotemporal | +0.243 | 47.0 | +0.139 |
