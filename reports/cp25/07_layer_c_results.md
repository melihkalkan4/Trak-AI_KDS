# ÇP-2.5 — Görev 7: Layer C (Climate + NDVI + Soil) + H3 Testi

## H3 — Multimodal Füzyon Marjinal (ΔR² ≥ 0.05 vs Layer B)

| Ürün | CV | LB Champ R² | LC Champ R² | ΔR² | H3 PASS? |
|---|---|---|---|---|---|
| bugday | LOYO | -0.536 | -0.311 | +0.225 | ✅ |
| bugday | LOILO | +0.429 | +0.427 | -0.002 | ❌ |
| bugday | Spatiotemporal | +0.314 | +0.480 | +0.166 | ✅ |
| aycicegi | LOYO | +0.237 | +0.386 | +0.149 | ✅ |
| aycicegi | LOILO | +0.450 | +0.582 | +0.132 | ✅ |
| aycicegi | Spatiotemporal | +0.434 | +0.556 | +0.122 | ✅ |

## bugday (n=213)
- Champion (LOYO): **xgboost**
- R²=-0.311, RMSE=80.7, SS=-0.170
- Kabul (R²≥0.5, SS≥0.3): ❌ FAIL

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | SS |
|---|---|---|---|---|
| elastic_net | LOILO | +0.180 | 63.8 | +0.075 |
| elastic_net | LOYO | -0.724 | 92.5 | -0.341 |
| elastic_net | Spatiotemporal | +0.059 | 68.3 | +0.009 |
| gpr | LOILO | +0.342 | 57.2 | +0.171 |
| gpr | LOYO | -0.541 | 87.5 | -0.268 |
| gpr | Spatiotemporal | +0.264 | 60.5 | +0.124 |
| pls | LOILO | +0.210 | 62.6 | +0.092 |
| pls | LOYO | -1.134 | 102.9 | -0.492 |
| pls | Spatiotemporal | +0.079 | 67.6 | +0.020 |
| random_forest | LOILO | +0.392 | 54.9 | +0.204 |
| random_forest | LOYO | -0.554 | 87.8 | -0.273 |
| random_forest | Spatiotemporal | +0.372 | 55.8 | +0.191 |
| stacking | LOYO | -0.658 | 90.7 | -0.315 |
| xgboost | LOILO | +0.427 | 53.3 | +0.227 |
| xgboost | LOYO | -0.311 | 80.7 | -0.170 |
| xgboost | Spatiotemporal | +0.480 | 50.8 | +0.263 |

## aycicegi (n=209)
- Champion (LOYO): **gpr**
- R²=+0.386, RMSE=42.3, SS=+0.225
- Kabul (R²≥0.6, SS≥0.4): ❌ FAIL

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | SS |
|---|---|---|---|---|
| elastic_net | LOILO | +0.392 | 42.1 | +0.229 |
| elastic_net | LOYO | +0.186 | 48.7 | +0.108 |
| elastic_net | Spatiotemporal | +0.408 | 41.5 | +0.239 |
| gpr | LOILO | +0.582 | 34.9 | +0.361 |
| gpr | LOYO | +0.386 | 42.3 | +0.225 |
| gpr | Spatiotemporal | +0.556 | 35.9 | +0.341 |
| pls | LOILO | +0.337 | 43.9 | +0.195 |
| pls | LOYO | +0.151 | 49.7 | +0.089 |
| pls | Spatiotemporal | +0.413 | 41.4 | +0.242 |
| random_forest | LOILO | +0.490 | 38.5 | +0.294 |
| random_forest | LOYO | +0.358 | 43.3 | +0.207 |
| random_forest | Spatiotemporal | +0.440 | 40.4 | +0.260 |
| stacking | LOYO | +0.343 | 43.7 | +0.199 |
| xgboost | LOILO | +0.521 | 37.3 | +0.316 |
| xgboost | LOYO | +0.194 | 48.5 | +0.112 |
| xgboost | Spatiotemporal | +0.355 | 43.3 | +0.206 |
