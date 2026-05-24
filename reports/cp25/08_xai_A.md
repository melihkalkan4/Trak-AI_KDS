# ÇP-2.5 — Görev 8: XAI Layer A

## Yöntem

- Tree-based XGBoost (n=200, max_depth=4) **tüm veride** fit edilir
  (CV burada amaç değil; yorumlanabilirlik).
- SHAP TreeExplainer global summary + waterfall (anomali vakaları).
- PartialDependence top-5 feature.
- Permutation importance (n_repeats=10).

## aycicegi_yaglik (n=576)

### SHAP — Top-5 Global Importance
| Feature | mean(|SHAP|) |
|---|---|
| tp_season_sum | 10.91 |
| gdd_cum_season | 9.96 |
| gdd_flowering | 5.70 |
| tp_flowering | 5.21 |
| aridity_index | 5.17 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| gdd_cum_season | 0.296 | 0.012 |
| tp_season_sum | 0.196 | 0.018 |
| aridity_index | 0.107 | 0.009 |
| tp_flowering | 0.105 | 0.009 |
| gdd_flowering | 0.101 | 0.006 |

### Görseller
- `reports/cp25/fig_shap_summary_A_aycicegi.png` (SHAP summary)
- `reports/cp25/fig_pdp_A_aycicegi.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_A_çorlu_2023_aycicegi.png` (Local SHAP anomali)
- `reports/cp25/fig_shap_anomaly_A_i̇psala_2025_aycicegi.png` (Local SHAP anomali)

## bugday (n=589)

### SHAP — Top-5 Global Importance
| Feature | mean(|SHAP|) |
|---|---|
| gdd_cum_season | 17.45 |
| vernalization_days | 9.72 |
| tp_flowering | 7.50 |
| tp_season_sum | 6.72 |
| tp_winter_sum | 6.67 |

### Permutation Importance — Top-5
| Feature | imp_mean | imp_std |
|---|---|---|
| gdd_cum_season | 0.274 | 0.019 |
| vernalization_days | 0.142 | 0.011 |
| tp_flowering | 0.112 | 0.013 |
| ssr_season_sum | 0.110 | 0.009 |
| tp_season_sum | 0.108 | 0.011 |

### Görseller
- `reports/cp25/fig_shap_summary_A_bugday.png` (SHAP summary)
- `reports/cp25/fig_pdp_A_bugday.png` (PDP top-5)
- `reports/cp25/fig_shap_anomaly_A_i̇psala_2021_bugday.png` (Local SHAP anomali)
