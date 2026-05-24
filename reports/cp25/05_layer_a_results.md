# ÇP-2.5 — Görev 5: Layer A (Climate-Only) Sonuçları

## Yapılan

- 5 model × 2 ürün × 3 CV = **30 değerlendirme**
- Modeller: PLS, ElasticNet, Random Forest, XGBoost, GPR
- CV: LOYO (yıl bazlı), LOILO (ilçe bazlı), Spatiotemporal (5×5 blok)

## BUGDAY (n=589)
- B0 Climatology RMSE: **61.74 kg/da** (skill score referansı)
- Şampiyon model (LOYO en düşük RMSE): **elastic_net**
  - R² = **-0.092**
  - RMSE = **72.7 kg/da**
  - MAE = 57.0 kg/da · MAPE = 16.0%
  - Skill Score vs B0 = **-0.178**
- **Kabul kriteri (R²≥0.35, SS≥0.15): ❌ FAIL**

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | MAE | SS | Süre |
|---|---|---|---|---|---|---|
| elastic_net | LOILO | +0.048 | 67.9 | 53.3 | -0.100 | 0.1s |
| elastic_net | LOYO | -0.092 | 72.7 | 57.0 | -0.178 | 0.1s |
| elastic_net | Spatiotemporal | +0.038 | 68.2 | 53.7 | -0.105 | 0.1s |
| gpr | LOILO | +0.441 | 52.0 | 40.0 | +0.158 | 19.3s |
| gpr | LOYO | -0.198 | 76.2 | 59.7 | -0.233 | 16.3s |
| gpr | Spatiotemporal | +0.321 | 57.4 | 43.9 | +0.071 | 17.7s |
| pls | LOILO | +0.013 | 69.1 | 54.4 | -0.120 | 0.1s |
| pls | LOYO | -0.248 | 77.7 | 61.0 | -0.259 | 0.1s |
| pls | Spatiotemporal | -0.013 | 70.0 | 55.4 | -0.134 | 0.1s |
| random_forest | LOILO | +0.362 | 55.6 | 43.2 | +0.100 | 12.1s |
| random_forest | LOYO | -0.169 | 75.2 | 59.7 | -0.218 | 11.5s |
| random_forest | Spatiotemporal | +0.225 | 61.2 | 47.7 | +0.008 | 11.2s |
| xgboost | LOILO | +0.371 | 55.2 | 41.9 | +0.106 | 3.3s |
| xgboost | LOYO | -0.234 | 77.3 | 61.6 | -0.252 | 3.6s |
| xgboost | Spatiotemporal | +0.275 | 59.2 | 45.9 | +0.040 | 4.0s |

## AYCICEGI (n=576)
- B0 Climatology RMSE: **50.00 kg/da** (skill score referansı)
- Şampiyon model (LOYO en düşük RMSE): **random_forest**
  - R² = **+0.051**
  - RMSE = **49.5 kg/da**
  - MAE = 39.8 kg/da · MAPE = 22.4%
  - Skill Score vs B0 = **+0.009**
- **Kabul kriteri (R²≥0.4, SS≥0.2): ❌ FAIL**

### Tüm model × CV matrisi

| Model | CV | R² | RMSE | MAE | SS | Süre |
|---|---|---|---|---|---|---|
| elastic_net | LOILO | +0.129 | 47.5 | 37.6 | +0.051 | 0.2s |
| elastic_net | LOYO | +0.002 | 50.8 | 40.7 | -0.016 | 0.1s |
| elastic_net | Spatiotemporal | +0.077 | 48.9 | 39.0 | +0.023 | 0.1s |
| gpr | LOILO | +0.493 | 36.2 | 27.7 | +0.276 | 20.2s |
| gpr | LOYO | -0.112 | 53.6 | 42.9 | -0.073 | 13.5s |
| gpr | Spatiotemporal | +0.387 | 39.8 | 30.7 | +0.204 | 16.6s |
| pls | LOILO | +0.173 | 46.2 | 36.1 | +0.075 | 0.2s |
| pls | LOYO | -0.073 | 52.7 | 41.9 | -0.053 | 0.1s |
| pls | Spatiotemporal | +0.099 | 48.3 | 38.3 | +0.035 | 0.2s |
| random_forest | LOILO | +0.439 | 38.1 | 29.4 | +0.238 | 15.2s |
| random_forest | LOYO | +0.051 | 49.5 | 39.8 | +0.009 | 9.4s |
| random_forest | Spatiotemporal | +0.320 | 41.9 | 32.4 | +0.161 | 13.1s |
| xgboost | LOILO | +0.504 | 35.8 | 27.1 | +0.284 | 4.6s |
| xgboost | LOYO | -0.076 | 52.7 | 42.3 | -0.055 | 2.1s |
| xgboost | Spatiotemporal | +0.385 | 39.9 | 30.9 | +0.202 | 4.3s |

## Hipotez H1 Testi — n=1165 vs n=132 ΔR² ≥ 0.15

Önceki il-bazlı kalibrasyon (cp25-v1): n=21/24, Ridge(α=100/α=1.0).

| Ürün | v1 (il) R² | v2 (ilçe) R² | ΔR² | H1 PASS? |
|---|---|---|---|---|
| bugday | -0.085 | -0.092 | -0.007 | ❌ |
| aycicegi | +0.646 | +0.051 | -0.595 | ❌ |

## Görsel

`reports/cp25/fig_layer_a_comparison.png`