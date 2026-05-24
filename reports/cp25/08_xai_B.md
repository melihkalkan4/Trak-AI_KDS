# ÇP-2.5 — Görev 8: XAI Layer B

## Yöntem

- Tree-based XGBoost (n=200, max_depth=4) **tüm veride** fit edilir
  (CV burada amaç değil; yorumlanabilirlik).
- SHAP TreeExplainer global summary + waterfall (anomali vakaları).
- PartialDependence top-5 feature.
- Permutation importance (n_repeats=10).

## aycicegi_yaglik (n=209)

### SHAP — Top-5 Global Importance
| Feature | mean(|SHAP|) |
|---|---|
| ndvi_flowering | 24.80 |
| gdd_flowering | 7.55 |
| ssr_season_sum | 4.71 |
| aridity_index | 3.80 |
| gdd_cum_season | 3.54 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| ndvi_flowering | 0.610 | 0.055 |
| gdd_flowering | 0.175 | 0.020 |
| ssr_season_sum | 0.084 | 0.009 |
| ndvi_max | 0.051 | 0.006 |
| gdd_cum_season | 0.047 | 0.006 |

### Görseller
- `reports/cp25/fig_shap_summary_B_aycicegi.png` (SHAP summary)
- `reports/cp25/fig_pdp_B_aycicegi.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_B_çorlu_2023_aycicegi.png` (Local SHAP anomali)
- `reports/cp25/fig_shap_anomaly_B_i̇psala_2025_aycicegi.png` (Local SHAP anomali)

## bugday (n=213)

### SHAP — Top-5 Global Importance
| Feature | mean(|SHAP|) |
|---|---|
| tp_grain_fill | 16.05 |
| ndvi_flowering | 12.02 |
| tp_season_sum | 10.04 |
| gdd_cum_season | 8.22 |
| ndvi_max | 8.14 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| tp_grain_fill | 0.297 | 0.030 |
| ndvi_flowering | 0.234 | 0.020 |
| ssr_flowering_sum | 0.139 | 0.011 |
| gdd_cum_season | 0.138 | 0.017 |
| tp_season_sum | 0.119 | 0.009 |

### Görseller
- `reports/cp25/fig_shap_summary_B_bugday.png` (SHAP summary)
- `reports/cp25/fig_pdp_B_bugday.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_B_i̇psala_2021_bugday.png` (Local SHAP anomali)
