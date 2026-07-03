# Methods as Implemented — Paper 1

> Self-sufficient methods record for the manuscript writer. Everything here was
> verified against repo source (`src/cp25/05–07,11`, `src/prospective_validation/*`)
> and reproduced byte-for-byte (fidelity gate: 92/92 checks, max |Δ| = 0.0).
> Crop labels: `bugday` = winter wheat; `aycicegi`/`aycicegi_yaglik` = oilseed sunflower.

---

## 1. Study system, data sources, and units
- **Region:** Trakya (Thrace, NW Türkiye); spatial unit = **ilçe** (district).
- **Yield (target):** TÜİK official district yields, `verim_kg_da` in **kg da⁻¹**
  (1 decare = 1000 m²). Source `data/external/tuik/tuik_ilce_yields_clean.csv`
  (1165 district-year rows; 29 districts; 2004–2025).
- **Climate:** NASA POWER / MERRA-2 reanalysis → seasonal features
  (`data/processed/openmeteo_ilce/`). (Thesis notes a MERRA-2-vs-ERA5-Land
  source caveat.)
- **NDVI:** Sentinel-2 (Google Earth Engine), district-aggregated
  (`data/processed/ndvi_ilce/`); availability from 2017 onward → restricts the
  NDVI tiers to n=213 (wheat) / 209 (sunflower).
- **Soil:** ISRIC SoilGrids (`data/processed/soil_ilce.csv`).
- **Model input matrices** (read-only, exact files used):
  `data/processed/calibration_features_layer{A,B,C}.csv`.

### Crop / tier sample sizes (verified)
| Tier | Features | wheat n | sunflower n |
|---|---|---|---|
| A (climate-only) | 14 | 589 | 576 |
| B (+NDVI) | 21 | 213 | 209 |
| C (+NDVI+soil) | 27 | 213 | 209 |

## 2. Feature tiers (exact, from `src/cp25/07_layer_c_full.py`)
- **FEATURES_A (14, climate):** gdd_cum_season, gdd_flowering, vernalization_days,
  tp_season_sum, tp_winter_sum, tp_flowering, tp_grain_fill, aridity_index,
  heat_stress_days, t2m_flowering_mean, t2m_flowering_max, tdiff_mean,
  ssr_flowering_sum, ssr_season_sum.
- **FEATURES_NDVI (+7):** ndvi_max, ndvi_mean_season, ndvi_integral, ndvi_flowering,
  ndvi_grain_fill, ndvi_spring_slope, greenness_days.
- **FEATURES_SOIL (+6, 0–5 cm):** clay, sand, silt, phh2o, soc, awc.
- Layer A = climate; Layer B = A+NDVI; Layer C = A+NDVI+soil.
- **Imputation:** per-column median; ±inf→NaN first; all-NaN column→0. No row dropping.

## 3. Cross-validation regimes (the experimental backbone)
All three implemented with scikit-learn `LeaveOneGroupOut`; predictions are
**out-of-fold** (each district-year predicted only when its group is held out).
- **LOYO — Leave-One-Year-Out** (groups = `year`): predict a held-out *year* →
  **temporal generalization / forecasting analogue**. ~22 folds.
- **LOILO — Leave-One-İlçe-Out** (groups = `ilce_id`): predict a held-out
  *district* → **spatial generalization / interpolation analogue**. ~29 folds.
- **Spatiotemporal block** (groups = 5 year-blocks × 5 KMeans lat/lon clusters =
  ≤25 blocks): joint space–time extrapolation (Roberts-2017-style). KMeans
  `random_state=42, n_init=10`; coords from real `data/external/tuik/ilce_coords.csv`.
- LOYO and LOILO run on the **same observation set** per tier → per-observation
  errors are **paired** (key for the gap test).

## 4. Models (identical configs across tiers; SEED=42)
- **PLS** `n_components=3, scale=True`
- **ElasticNet** `alpha=1.0, l1_ratio=0.5, max_iter=10000`
- **RandomForest** `n_estimators=300, max_depth=5`
- **XGBoost** `n_estimators=200, max_depth=4, learning_rate=0.05`
- **GPR** `Matern(ν=2.5) + WhiteKernel, normalize_y=True, alpha=1e-4`
- **Stacking** (Layer C only, LOYO only): RF+XGB+GPR → Ridge(α=1.0) meta, cv=3.
- StandardScaler fit on train fold for {PLS, ElasticNet, GPR, Stacking}.

## 5. Baselines (`src/cp25/02_baselines.py`)
- **B0 Climatology:** per-(district,crop) leave-one-year-out mean yield. The skill
  reference. (LOYO RMSE_B0 used in skill score.)
- **B1 YearTrend:** linear year trend.
- **B2 Persistence:** previous year's yield.
- **B3 ClimateProxy:** simple climate-based proxy regression.
- Skill score **SS = 1 − RMSE_model / RMSE_B0** (>0 ⇒ beats climatology).

## 6. Error metrics (`sklearn`, verbatim)
R² (`r2_score`), RMSE = √MSE (kg da⁻¹), MAE (kg da⁻¹), MAPE = mean(|.|)·100 (%),
bias = mean(pred − obs), SS vs B0 as above.

## 7. Bootstrap confidence intervals (`repro/02_bootstrap_ci.py`)
- **Primary = case (observation) bootstrap**, **5000** resamples, **seed 12345**;
  percentile 95% CI (2.5/97.5) for R²/RMSE/MAE/MAPE/bias. (Same family as the
  thesis's Görev-13 bootstrap, which used 1000 resamples/seed 42 for the wheat
  LOILO-MAPE case — reproducible here as a cross-check.)
- **Sensitivity = cluster bootstrap** resampling whole CV groups (years for LOYO,
  districts for LOILO). Reported alongside because the district-year panel violates
  iid; cluster CIs are wider and more honest. Spatiotemporal cluster bootstrap is
  omitted (block id not persisted) and flagged.
- **Honesty note:** iid bootstrap CIs are optimistic under spatial/temporal
  correlation; both methods are reported.

## 8. Generalization-gap test (`repro/03_generalization_gap.py`)
- **Descriptive:** ΔR² = R²(LOILO) − R²(LOYO), best model per regime (headline).
- **Fixed-model paired test:** one model (the LOILO champion of that tier×crop)
  evaluated under LOYO and LOILO on identical observations:
  - **Wilcoxon signed-rank** (two-sided) on paired |error| (LOYO vs LOILO).
  - **Effect size:** matched-pairs **rank-biserial** correlation.
  - **Paired bootstrap** (5000, seed 12345) of ΔR² → 95% CI.
- **Per-model consistency:** ΔR² reported for every model (`generalization_gap_per_model.csv`)
  to show the gap is not model-specific.

## 9. Baseline-superiority test (`repro/04_baseline_superiority.py`)
For each tier×model under LOYO, B0 climatology per-sample predictions are computed
on the **same** observation subset (leave-one-year-out district mean):
- SS = 1 − RMSE_model/RMSE_B0; **paired bootstrap** (5000, seed 12345) → SS 95% CI.
- **Paired Wilcoxon** |err_model| vs |err_B0| (two-sided).
- `beats_b0_ci` = (SS CI lower bound > 0); `worse_than_b0_ci` = (CI upper < 0).

## 10. Ablation, matched-sample (`repro/05_ablation.py`)
Because tier A (n=589/576) and tiers B/C (n=213/209) differ in sample, the naïve
A→B comparison conflates sample with features. We additionally evaluate the
climate-only model on the **NDVI-available subset** (A_matched, n=213/209):
- ΔR²(NDVI) = R²(B) − R²(A_matched); ΔR²(soil) = R²(C) − R²(B); best model per tier.
- A_full vs A_matched reported to expose the sample-size effect separately.
- Deterministic inference re-run only (no retraining).

## 11. Per-stage NDVI forecast skill — FLOV (`repro/06_per_stage.py`)
- **FLOV = Forward-Looking Operational Validation** (`src/prospective_validation/`):
  a frozen 2017–2024 sunflower champion (LSTM NDVI t+7 head + XGBoost yield head),
  hash-locked (`logs/model_integrity.jsonl`), run walk-forward on 2025/2026 data it
  never saw. **No retraining/look-ahead.** Inputs: (T=30, F=17) MinMax window;
  NDVI residual update `ndvi_hat = last + tanh(δ)·0.30`.
- **Metrics:** per phenology stage (pre_season, emergence, vegetative, flowering,
  grain_fill, maturity, post_harvest) and overall, vs a **naïve persistence**
  baseline (`pred = last_observed_NDVI`); one-sided **Wilcoxon** |model| vs
  |persistence|. Metrics from `src/prospective_validation/metrics.py` (numpy).
- **REAL-coordinate re-run (`repro/11_prospective_real_coords.py`, PRIMARY):** EVR_01 re-validated
  on the farmer's 4 surveyed GPS corners → true parcel polygon (shapely, 10 m inward buffer,
  0.62 ha, ~3129 m²). Live Sentinel-2 (GEE) + ERA5-Land (CDS, 17 months) fetched for the true
  location; frozen LSTM (`build_unified_features`→`predict_ndvi_series`, integrity hash
  `43ef61b5…`, inference only) run walk-forward; validated vs raw-S2 (gold) and interpolated
  NDVI_int actuals (tolerance 2 d). Isolation: `config.AUDIT_FILE`/`LOG_FILE` redirected to my
  folder, `configure_logging()` not called, `save=False`, site id `EVR01R`,
  `geometry.site_polygon_coords` monkeypatched at runtime — no original file modified; frozen model
  not retrained. Consolidated by `repro/12_update_prospective.py`.
- **Placeholder source artifacts (comparison only):** `reports/prospective/EVR_01_{2025,2026}_*`.
- **Residual caveat:** single small field (0.62 ha → subpixel-noisy), 2026 partial,
  satellite-derived (not in-situ) ground truth; EVR_02–05 remain placeholder (not re-run).

## 12. Feature importance (`repro/07_feature_importance.py`)
Permutation importance from `src/cp25/08_xai_analysis.py`
(`reports/cp25/08_perm_importance_{A,B,C}_{crop}.csv`: `imp_mean`, `imp_std`);
consolidated, ranked. SHAP beeswarms available as figures (`fig_shap_summary_*`).

## 13. Moran's I (`repro/08_morans_i.py`, mirrors `src/cp25/11`)
- Residual = obs − LOYO prediction of the **Layer A champion** (wheat=elastic_net,
  sunflower=random_forest); mean residual per district.
- **KNN(k=4)** weights from lat/lon centroids, row-standardized (`transform="R"`).
- `esda.Moran(residuals, w, permutations=999)`; report I, E[I], z_norm, p_norm, p_sim.
- Observed I is deterministic and reproduced exactly (p_sim varies slightly with
  permutation RNG; p_norm is analytic and reproduced).

## 14. Reproducibility & integrity
- Environment = repo venv (Python 3.13.2; numpy 2.4.3, scikit-learn 1.8.0,
  xgboost 3.2.0, scipy 1.17.1, esda 2.9.0) — the versions that produced the
  originals. Frozen to `repro/requirements_full_venv.txt`.
- All randomness seeded (model SEED=42; bootstrap seed=12345).
- **Fidelity gate:** recomputed aggregate metrics matched published cp25 tables on
  all 92 layer×crop×cv×model combinations with max |Δ| = 0.0; per-sample champion
  predictions matched existing CSVs to 0.0 (`analysis/fidelity_check.csv`).
- No original file modified; no model retrained; outputs only under
  `paper1_generalization/`.
