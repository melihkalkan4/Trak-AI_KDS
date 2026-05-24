# ÇP-2.5 — Görev 8: XAI Layer C

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
| ndvi_flowering | 24.26 |
| sand_0-5cm | 6.99 |
| gdd_flowering | 6.84 |
| ssr_season_sum | 3.23 |
| soc_0-5cm | 3.13 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| ndvi_flowering | 0.587 | 0.053 |
| gdd_flowering | 0.121 | 0.015 |
| sand_0-5cm | 0.087 | 0.008 |
| soc_0-5cm | 0.047 | 0.009 |
| clay_0-5cm | 0.039 | 0.006 |

### Görseller
- `reports/cp25/fig_shap_summary_C_aycicegi.png` (SHAP summary)
- `reports/cp25/fig_pdp_C_aycicegi.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_C_çorlu_2023_aycicegi.png` (Local SHAP anomali)
- `reports/cp25/fig_shap_anomaly_C_i̇psala_2025_aycicegi.png` (Local SHAP anomali)

## bugday (n=213)

### SHAP — Top-5 Global Importance
| Feature | mean(|SHAP|) |
|---|---|
| tp_grain_fill | 14.54 |
| soc_0-5cm | 13.12 |
| tp_season_sum | 11.92 |
| ndvi_flowering | 10.95 |
| ssr_flowering_sum | 7.09 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| tp_grain_fill | 0.258 | 0.024 |
| soc_0-5cm | 0.242 | 0.019 |
| ndvi_flowering | 0.209 | 0.018 |
| tp_season_sum | 0.150 | 0.010 |
| ssr_flowering_sum | 0.106 | 0.006 |

### Görseller
- `reports/cp25/fig_shap_summary_C_bugday.png` (SHAP summary)
- `reports/cp25/fig_pdp_C_bugday.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_C_i̇psala_2021_bugday.png` (Local SHAP anomali)
