# INPUTS_FOUND — referee-revision pipeline

> Inventory for the [P]-class referee revisions. All paths verified (opened/inspected),
> relative to repo root. Read-only inputs. Output root for this task:
> **`paper1_generalization/revisions/`** (isolation preserved; `.docx` untouched; nothing
> outside `paper1_generalization/` modified). Crop labels: `bugday`=winter wheat,
> `aycicegi`/`aycicegi_yaglik`=oilseed sunflower.

## Reuse from the completed Phase 0–7 work (already fidelity-verified, max |Δ|=0.0)
- `paper1_generalization/repro/repro_common.py` — faithful cp25 CV pipeline (feature tiers A/B/C,
  model defs PLS/ElasticNet/RF/XGB/GPR/Stacking, `_cv_predict` LOGO, `_block_groups`,
  imputation, `b0_per_sample`, vectorized bootstraps). **Imported by all revision scripts.**
- `paper1_generalization/analysis/per_sample_predictions.csv` (30,557 rows) — out-of-fold
  predictions for every crop×tier×cv×model (LOYO/LOILO/Spatiotemporal).
- `paper1_generalization/analysis/ablation_per_model.csv` — tier {A_full,A_matched,B,C} × model × cv R².
- `paper1_generalization/analysis/prospective_real/` — real-coords parcel FLOV (matched_*.csv have
  predicted_ndvi, last_observed_ndvi, actual_ndvi, target_date → per-stage persistence derivable).

## Reproduction sources (for CHANGES_vs_old.md)
- `reports/cp25/12_master_comparison.csv`, `02_baselines.csv`, `05/06/07_*_results.csv` — published metrics.

## Model inputs (read-only)
- `data/processed/calibration_features_layer{A,B,C}.csv` (1165 / 422 / 422 rows incl. header).
- `data/external/tuik/ilce_coords.csv` (real 29-district centroids; used by spatiotemporal + Moran).

## CV / fold definitions (reused verbatim via repro_common)
- LOYO = `LeaveOneGroupOut(groups=year)`; LOILO = `groups=ilce_id`;
  Spatiotemporal = 5 year-blocks × 5 KMeans(lat/lon) clusters → `LeaveOneGroupOut` over ≤25 cells.
- Source: `src/cp25/05_layer_a_climate_only.py`, `06_*.py`, `07_*.py` (SEED=42).

## Hyperparameters (FIXED, pre-specified — verified in source; no test-set tuning)
- PLS n_components=3; ElasticNet alpha=1.0,l1_ratio=0.5,max_iter=10000; RF n_estimators=300,max_depth=5;
  XGB n_estimators=200,max_depth=4,lr=0.05; GPR Matern(ν=2.5)+WhiteKernel,normalize_y,alpha=1e-4;
  Stacking RF+XGB+GPR→Ridge(α=1.0),cv=3 (Layer C, LOYO only). Scaler on {PLS,ElasticNet,GPR,Stacking}.
- `models/cp25/champion_metadata.json` carries no hyperparameters → they live in code (above).

## Parcel / LSTM walk-forward
- `src/prospective_validation/*` (frozen LSTM NDVI t+7 + XGB yield, hash-locked); real-coords
  re-run `paper1_generalization/repro/11_prospective_real_coords.py` (outputs in `analysis/prospective_real/`).
- `analysis/prospective_real/matched_2025_raw_s2.csv` (210 rows), `matched_2026_raw_s2.csv`, and
  `per_stage_*` (raw_s2 + unified, 2025 + 2026).

## Sentinel-2 NDVI extraction code (for ndvi_extraction_methods_EN.md, #8)
- **Panel (district-level):** `src/cp25/03b_fetch_ilce_ndvi.py` — S2_SR_HARMONIZED (L2A),
  s2cloudless prob<30% (+QA60 fallback), **ESA WorldCover v200 cropland mask (Map==40, GENERIC —
  NOT crop-specific)**, adaptive 5–8 km point buffer, 16-day median composite, NDVI=(B8−B4)/(B8+B4),
  reduceRegion mean/p25/p75 @30 m. ⚠️ wheat vs sunflower pixels are **NOT** separated.
- **Parcel:** `src/cp1_etl/mod_s2_gee.py` — S2_SR_HARMONIZED, CLOUDY_PIXEL_PERCENTAGE<70,
  eemont maskClouds+scaleAndOffset, NDVI/EVI/NDWI, reduceRegion mean @10 m, per-date (no composite).

## Critical gaps (→ TODO/limitation, NOT fabricated)
- **No crop-type map** for wheat/sunflower pixel separation (only generic cropland) → crop-specific
  NDVI re-extraction is NOT feasible without an external crop map → reported as limitation (#8).
- **Staged-forecast (#7):** season-level features ARE phenology-tagged (ndvi_flowering, tp_grain_fill,
  …) so issuance-time tiers can be built by feature subsetting → feasible (R05).
