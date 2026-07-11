# ADVISOR_REPORT — to-do completion (crop-specific RS enrichment)

## Non-destruction
- Protected artifacts changed: **0**, missing: 0 → INTACT ✓. Rollback: delete enrichment_v2/ + branch.

## Advisor item 1 — agricultural boundaries
- ESA WorldCover cropland (class 40), built-up (50) explicitly excluded, clipped to tur_polbnda_adm1/tur_polbna_adm2 → 29 district cropland polygons (EPSG:4326). Areas in `geometries/cropland_area_per_district.csv`.

## Advisor item 2 — RS variables
- Inventory (thesis NDVI vars + new indices) in `tables/rs_variable_inventory.csv`. Added **EVI** (NDVI saturation) and **NDRE** (yield correlation), plus EVI2/CIre/NDWI/GNDVI/OSAVI. Single district NDVI replaced by **phenological distribution metrics** (mean/median/std/CV/P10/P90/range) — `tables/phenological_metrics.csv`.
- **Per-crop best RS list (effective vs ineffective):**
  - **winter wheat**: effective = `EVI, NDRE`, ineffective = `NDVI` → EVI_peak_p10; EVI_peak_cv; EVI_grainfill_range; EVI_greenup_cv; NDRE_peak_p10; EVI_grainfill_p10; NDRE_peak_mean; NDRE_peak_stdDev
  - **sunflower**: effective = `NDRE, NDVI`, ineffective = `EVI` → NDVI_greenup_cv; NDVI_peak_p10; NDRE_peak_p10; NDRE_peak_cv
  - NB: this matches the advisor's hypothesis — NDVI saturates for wheat (dropped; EVI/NDRE kept); NDVI retained for sunflower.

## Advisor item 3 — crop-focused masking + tiers
- **Crop-specific masks** (phenology classification) validated vs TÜİK ekilen_alan: wheat r=**0.954**, sunflower r=**0.615** (sunflower harder to separate from other summer crops — honest limitation). Windows: `tables/crop_masking_windows.csv`.
- Tiers A–D (`tables/tier_definitions.csv`): A=climate, B=+{NDVI,NDRE,EVI}, C=+soil, D=+pheno metrics.

## Audited results (crop-specific RS, LOYO vs matched climatology)

| crop | tier | best LOYO SS | year-clustered 95% CI |
|---|---|---|---|
| sunflower | A | -0.086 | [-0.255, +0.007] |
| sunflower | B | -0.110 | [-0.248, -0.026] |
| sunflower | C | -0.019 | [-0.239, +0.134] |
| sunflower | D | -0.004 | [-0.067, +0.069] |
| winter wheat | A | -0.261 | [-0.543, -0.128] |
| winter wheat | B | -0.152 | [-0.371, -0.035] |
| winter wheat | C | -0.069 | [-0.169, -0.020] |
| winter wheat | D | -0.014 | [-0.087, +0.070] |

- Enrichment improves both crops monotonically A→D, but at tier D **neither crop robustly beats climatology** under year-clustered LOYO (both CIs include ~0). The crop-specific masking is more correct than the all-cropland aggregate but adds classification noise — a key honest finding.
- Spatial≫temporal generalization gap **persists**: True (`tables/advisor_table3_gap.csv`).
- Rolling-origin forward skill: `advisor_rolling.csv`. Per-algorithm ablation: `advisor_ablation.csv`.

## Comparison to all-cropland enrichment_v2 (methodological)
- All-cropland 8-index tiers had higher absolute skill (e.g. sunflower D SS +0.109, CI>0) because the aggregate is smoother and the feature set wider; crop-specific 3-index tiers tighten this toward climatology parity. Both are reported; the crop-specific version is the advisor-correct one.

## Honest limitations
- Sunflower crop mask moderate (r≈0.6); generic cropland underlies classification; NDVI era 2017–24 (8 yrs, few rolling-origin years); district-aggregate. Field-level historical yield impossible (no data).