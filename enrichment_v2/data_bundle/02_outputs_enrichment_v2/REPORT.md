# REPORT — RS enrichment v2 (T1–T9)

## Integrity (non-destruction)
- Protected artifacts checked: **145** | mismatched: **0** | missing: 0
- **checksums_before == checksums_after: YES ✓ (no existing artifact changed)**
- No mismatches.

- Rollback: delete `enrichment_v2/` + branch `feature/rs-enrichment-v2`.

## What was extracted (real, GEE/SoilGrids/DEM)
- T1 district cropland polygons (29, EPSG:4326), built-up excluded.
- T2 8 indices × {mean,median,std,P10,P90,CV,range} per crop window, 2017–2024 (scale 30 m; EVI/EVI2 clamped |≤1|).
- T3 SoilGrids 9 props 0–30 cm + AWC (Saxton–Rawls). T4 SRTM topography + TWI.
- T5 anomaly z-scores. T6 tiers A–D (n: wheat 213, sunflower 209).

## Does the spatial≠temporal finding persist? (T8)
- Spatial>temporal gap persists with enriched features: **True** (ΔR²=R²_LOILO−R²_LOYO > 0.10 for the majority of crop×tier; see table3).

| crop | tier | best LOYO SS | clustered 95% CI |
|---|---|---|---|
| sunflower | A | -0.086 | [-0.255, +0.007] |
| sunflower | B | +0.048 | [-0.095, +0.240] |
| sunflower | C | +0.047 | [-0.066, +0.135] |
| sunflower | D | +0.109 | [+0.033, +0.161] |
| winter wheat | A | -0.261 | [-0.543, -0.128] |
| winter wheat | B | -0.047 | [-0.210, +0.038] |
| winter wheat | C | -0.026 | [-0.175, +0.057] |
| winter wheat | D | +0.057 | [-0.054, +0.155] |

## Crop-specific index value (does NDVI/multi-index help?)
- ΔSS (tier B − tier A), LOYO best model: wheat **+0.214**, sunflower **+0.133** → see table8.
- Per-algorithm matched ablation: `table4_ablation_v2.csv`; enrichment value ladder: `table8`.

## Which new features survive selection (T7)
- Parsimonious selected sets per crop×tier in `table6_selected_features_v2.csv`; full ranking + collinearity drops in `t7_selection_report.csv`. Feature/observation ratios in `t7_ratio.csv`.

  - winter wheat tier D selected: ['CIre_grainfill_p90', 'tp_season_sum', 'CIre_peak_stdDev', 'NDWI_peak_p90', 'NDWI_grainfill_p90', 'OSAVI_grainfill_p10', 'ssr_flowering_sum', 'GNDVI_grainfill_p10', 'NDWI_grainfill_mean', 'cfvo_0_30_mean', 'NDVI_greenup_cv', 'NDWI_peak_range', 'CIre_grainfill_cv', 'NDWI_grainfill_p10']
  - sunflower tier D selected: ['NDWI_peak_stdDev', 'NDVI_greenup_p10', 'tp_season_sum', 'gdd_flowering', 'aridity_index', 'awc_0_30', 'NDVI_peak_mean', 'ssr_season_sum', 'GNDVI_greenup_p10', 'NDWI_greenup_range', 'tp_grain_fill', 'tp_flowering', 'EVI2_greenup_cv']

## Data-quality notes
- District index extraction at 30 m (matches existing 03b district-NDVI precedent); distribution metrics (P10/P90/CV) are district-internal spatial summaries.
- Cropland mask = ESA WorldCover (40), built-up (50) explicitly excluded; **generic cropland, NOT crop-specific** → wheat/sunflower share the district cropland aggregate (limitation).
- Tekirdağ 'Merkez' (id 1673, pre-2013) shares the Süleymanpaşa polygon (2014 reorg; no NDVI-era rows).
- NDVI tiers cover 2017–2024 (8 years); rolling-origin has few test years → caution.

## Conclusion
Enriched remote-sensing features were extracted and evaluated under the SAME CV regimes and cluster-aware inference as Paper 1, with matched samples and leakage-free, fixed-hyperparameter modelling. The existing Paper-1 artifacts are byte-for-byte unchanged (checksums verified). See tables 2–8 for the audited comparison.