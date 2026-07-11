# PLAN.md — RS enrichment v2 (T0 inventory)

> Non-destructive, piece-by-piece. WORKDIR = `enrichment_v2/`. Branch =
> `feature/rs-enrichment-v2`. Existing repo is READ-ONLY. Each enabled task below maps to existing
> code as **[READ-ONLY import]** or **[COPY-and-redirect]** or **[NEW]**. No existing functionality
> is duplicated unnecessarily; where the existing pipeline already does a step, we extend it by
> copying and redirecting outputs into `enrichment_v2/outputs/`.

## 0. Isolation status (this task, T0)
- `git status` was DIRTY (9 pre-existing modified tracked files incl. PROTECTED `data/trakai.db`;
  untracked `paper1_generalization/`, `*.zip`, `data/` cache). Per your decision **"proceed isolated"**:
  branch `feature/rs-enrichment-v2` created off current HEAD; dirty files left untouched.
- WORKDIR created: `enrichment_v2/{code, outputs/{geometries,tables,figures}}`.
- Integrity snapshot: **145 protected artifacts** SHA256→`checksums_before.txt`
  (patterns: master_ledger*, champion_metadata*, training_results*, loocv_*.csv, *_results.csv,
  feature_names.json, fig_*.png, *.pt/.pth/.pkl/.joblib/.h5/.onnx/.keras, trakai.db,
  data/processed/*.csv, data/external/tuik/*.csv; excl. venv/ and enrichment_v2/). Re-verified in T9.
- Rollback: delete `enrichment_v2/` + branch `feature/rs-enrichment-v2` → experiment fully undone.

## 1. District-polygon source + CRS (CONFIRMED)
- **Existing pipeline has NO district-polygon source.** Districts are represented as **centroid
  points** (`data/external/tuik/ilce_coords.csv`: ilce_id, ilce, il, lat, lon, is_trakya; **EPSG:4326**)
  with **adaptive buffers**: NDVI 5–8 km (`src/cp25/03b_fetch_ilce_ndvi.py`), soil 2 km
  (`src/cp25/03c_fetch_ilce_soil.py`). GEE geometries are lat/lon (EPSG:4326); SoilGrids reduce uses
  the asset's native projection.
- **T1 admin polygons — SOURCE NOW RESOLVED (user-provided local zip, 2026-06-21).**
  `C:\Users\Melih Kalkan\Downloads\Turkey - Administrative Levels.zip` contains the full shapefile
  component sets for `tur_polbna_adm2` (district), `tur_polbnda_adm1` (province), `tur_polbnda_adm0`,
  `tur_linebnda_adm0`. (No province-coordinate CSV or advisor-specific files are inside — boundaries only.)
  Confirmed read-only (metadata, no extraction):
  - **`tur_polbna_adm2`: CRS = EPSG:4326** (GCS_WGS_1984) → matches pipeline, **no reprojection needed**;
    **973 districts**; fields `OBJECTID, adm2_tr, adm2_en, adm1_tr, adm1_en, adm1, pcode, Shape_*`.
  - **`tur_polbnda_adm1`: EPSG:4326, 81 provinces.**
  - **Join key for T1:** `(adm1_tr = il, adm2_tr = ilçe)` ↔ existing `ilce_coords.csv (il, ilce)`.
    **Province (adm1_tr) is required** to disambiguate repeated district names (multiple "Merkez").
  - T1 will COPY only the needed components (adm2/adm1 .shp/.shx/.dbf/.prj/.cpg) from the external zip
    into `enrichment_v2/code/inputs/` (never into the repo), filter to the 29 Trakya districts, and
    verify all 29 match. **If any of the 29 districts fails to join → STOP and report (no synthetic geometry).**
- ⚠️ **Methodological note (carry into T9):** moving from point-buffers → admin cropland polygons
  changes the spatial support of every extracted feature. This is the intended enrichment, so the new
  features are **not** cell-for-cell comparable to the existing ones; comparison is at the model/skill
  level (T9), and the existing Paper-1 features/results remain untouched.

## 2. Existing code inventory (read for this plan)
| Concern | Existing file | Notes |
|---|---|---|
| District NDVI (GEE) | `src/cp25/03b_fetch_ilce_ndvi.py` | S2_SR_HARMONIZED L2A; s2cloudless<30% (+QA60 fallback); ESA WorldCover v200 `Map==40` cropland; adaptive 5–8 km point buffer; 16-day median; NDVI=(B8−B4)/(B8+B4); reduceRegion mean/p25/p75 @30 m |
| Parcel NDVI (GEE) | `src/cp1_etl/mod_s2_gee.py` | eemont maskClouds+scaleAndOffset; NDVI/EVI/NDWI; mean @10 m |
| Climate seasonal feats | `src/cp25/04_seasonal_features.py` | NASA POWER daily → season/flowering/grain-fill windows; **wheat flowering=May, grain_fill=Jun; sunflower flowering=Jul, grain_fill=Aug**; GDD/precip/radiation/aridity |
| Soil (GEE) | `src/cp25/03c_fetch_ilce_soil.py` | ISRIC SoilGrids 250 m; props clay/sand/silt/phh2o/soc; depths 0-5,5-15,15-30; point+2 km buffer; 0.1 scale; reduceRegion mean (native proj) |
| Model/CV harness | `src/cp25/05,06,07_*.py` (faithful copy already in `paper1_generalization/repro/repro_common.py`) | PLS/ElasticNet/RF/XGB/GPR(+Stacking); fixed hyperparams; LeaveOneGroupOut LOYO/LOILO/Spatiotemporal; SEED=42; scaler/impute fit per-fold |
| Cluster-aware inference | `paper1_generalization/repro/rev_common.py` (+ R0x) | year/ilce cluster bootstrap, year-level signed-rank |
| Feature matrices | `data/processed/calibration_features_layer{A,B,C}.csv` | A=14 climate (n=589/576), B=+NDVI, C=+soil (n=213/209) |
| Coords | `data/external/tuik/ilce_coords.csv` | 29 districts, EPSG:4326 |
| Yields | `data/external/tuik/tuik_ilce_yields_clean.csv` | TÜİK district yields 2004–2025 |

## 3. Task → code mapping (enabled tasks)
- **T1 cropland+admin+built-up** — **[NEW]** (`code/t1_cropland_geometries.py`). Reuse 03b's ESA
  WorldCover idiom *as reference only*. Fetch Drive shapefiles → clip WorldCover (40 cropland, **exclude
  50 built-up**) per district → save geometries to `outputs/geometries/`. All later tasks consume these.
- **T2 multi-index + distributions** — **[COPY-and-redirect from 03b]** (`code/t2_indices.py`). Same
  S2/s2cloudless logic; add 8 indices + 5 reducers (mean/median/std/P10/P90)+CV+range per crop window;
  **clamp EVI,EVI2 to |≤1| (out-of-range→NaN BEFORE compositing)**. Output `outputs/indices_<crop>.csv`.
- **T3 soil enrichment** — **[COPY-and-redirect from 03c]** (`code/t3_soil.py`). Add CEC,bdod,nitrogen,
  cfvo; AWC via **Saxton–Rawls** pedotransfer (cited in code); 0–30 cm aggregate over T1 cropland mask.
  Output `outputs/soil_<crop>.csv`.
- **T4 topography** — **[NEW]** (`code/t4_topography.py`). Copernicus DEM/SRTM via GEE; elevation,
  slope, aspect→northness/eastness, TWI; zonal mean over T1 polygons. Output `outputs/topo.csv`.
- **T5 anomaly features** — **[NEW]** (`code/t5_anomaly.py`). Per-district z-scores of T2 metrics + yield.
- **T6 assemble tiers** — **[NEW assembly; Tier A READ-ONLY reuse]** (`code/t6_assemble.py`). Tier A =
  existing climate (read `calibration_features_layerA.csv`); B=+T2; C=+T3; D=+pheno distrib+soil(+T4).
  Output `outputs/tier_{A,B,C,D}_<crop>.csv`.
- **T7 per-crop feature selection** — **[NEW]** (`code/t7_select.py`). |r|>0.9 collinearity drop +
  training-fold permutation importance + feature-count cap; report surviving sets.
- **T8 re-run evaluation** — **[COPY-and-redirect harness]** (`code/t8_eval.py` + copy of
  `repro_common.py`→`code/`). 4 CV regimes, Tiers A–D, both crops, cluster-aware; outputs only to
  `outputs/`. **Never** overwrite `master_ledger`.
- **T9 comparison + report** — **[READ-ONLY compare]** (`code/t9_report.py`). Regenerate Tables 2/3/4/6/7/8
  equivalents → `outputs/tables/`; `REPORT.md`; recompute `checksums_after.txt` and assert ==before.

## 4. Integrity constraints carried into every task
- CV regimes unchanged (LOYO/LOILO/spatiotemporal/rolling-origin); cluster-aware (year bootstrap +
  year signed-rank); NEVER random k-fold. Fixed hyperparameters, never tuned on test folds.
  Standardization/imputation fit on TRAINING folds only. Small n (213/209) → per-crop selection (T7),
  parsimonious sets. Every value from REAL extraction; auth/source failure → STOP. EVI/EVI2 clamp |≤1|.

## 5. Open risks / STOP triggers
- ~~Drive shapefile access~~ **RESOLVED** (local zip; EPSG:4326, no reproj). Residual T1 STOP: if any
  of the 29 Trakya districts fails the `(il, ilce)`↔`(adm1_tr, adm2_tr)` join → STOP (no synthetic geometry).
- GEE quota/auth for new geometries (T2/T4) — STOP if auth fails (do not invent values).
- Phenological windows are advisor-adjustable (T2) — using spec defaults unless you say otherwise.
- SoilGrids extra-property availability (CEC/bdod/nitrogen/cfvo asset names) — verify in T3; STOP if missing.
