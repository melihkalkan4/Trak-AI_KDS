# TRAK-AI — FINDINGS / RESULTS REPORT
### Spatial-vs-temporal generalization of district crop-yield prediction (winter wheat & oilseed sunflower, Trakya/Türkiye)

> **READ-ONLY COMPILATION.** Every value below is copied from an artifact already on disk and is cited
> by path (+ table/column). **No analysis was run, no model fitted, no statistic computed** to make this
> report. Where a needed number is absent from all artifacts it is written `[NOT IN ARTIFACTS]` — never
> invented. Where two artifacts disagree, **both are shown and the discrepancy flagged**. Existing files
> were not modified; the only new files are this report and `findings_inventory.md`.
> **Rollback** = delete `enrichment_v2/FINDINGS_REPORT.md` (+ `findings_inventory.md`).
> Source map: [`findings_inventory.md`](findings_inventory.md). Crops: `bugday`=winter wheat, `aycicegi`=oilseed sunflower.
> **PRIMARY result set = crop-specific** (`ADVISOR_REPORT.md`, `advisor_*`). **COMPARISON = all-cropland** (`REPORT.md`, `*_v2`).

---

## 1. Executive summary

1. **The thesis holds: spatial skill ≫ temporal skill.** The generalization gap ΔR² = R²_LOILO − R²_LOYO
   is **positive in every crop × tier × model cell** of both result sets. Crop-specific tier-D GPR:
   wheat **+0.572** [+0.429, +0.718], sunflower **+0.600** [+0.482, +0.730] (`advisor_gap.csv`). Original
   point-buffer Paper-1: wheat·A **+0.639** [+0.545, +0.735], sunflower·A **+0.580** [+0.490, +0.674]
   (`paper1_generalization/docs/numbers_ledger.md` C1/C4).
2. **Honest bottom line (PRIMARY, crop-specific).** At full enrichment (tier D), **neither crop robustly
   beats matched climatology under year-clustered LOYO**: best wheat SS **−0.014** [−0.087, **+0.070**],
   best sunflower SS **−0.004** [−0.067, **+0.069**] — both 95% CIs straddle 0 (`advisor_master_ledger.csv`).
3. **Enrichment raises skill toward parity, not past it.** Best-per-tier LOYO SS climbs A→D: wheat
   −0.261 → −0.152 → −0.069 → −0.014; sunflower −0.086 → −0.110 → −0.019 → −0.004 (`advisor_master_ledger.csv`).
   *(Near-monotonic; sunflower dips slightly at B before recovering — see §4.)*
4. **The original sunflower advantage is fragile.** Point-buffer Layer-C GPR beat climatology
   (**SS +0.224** [+0.167, +0.276], `baseline_superiority.csv`); under crop-specific masking it falls to
   **−0.004** (parity). Not cell-for-cell comparable (spatial support changed), but the rigorous test removes the win (§9).
5. **COMPARISON (all-cropland) looks better but is not the headline.** All-cropland sunflower tier-D GPR
   **+0.109** [+0.033, +0.161] does beat climatology (`master_ledger_v2.csv`) — but that reflects
   aggregate-smoothing + a wider 8-index feature set, **not** the advisor-correct crop-specific design.
   It is reported as methodology, never over the crop-specific −0.004.
6. **Forward-in-time + LSTM corroborate.** Monthly-climate LSTM LOYO skill vs climatology: wheat **−0.072**,
   sunflower **−0.021** (`lstm_yield_results.csv`); its LOILO−LOYO R² gap is **+0.195** (wheat) / **+0.422**
   (sunflower) — same spatial≫temporal signature.
7. **Data are clean.** All feature families CLEAN; **0 out-of-bounds** across 33 audited features and across
   clamp-disabled raw pixels (4 districts × 8 indices); **no 12.5× precip bug**, **no EVI blow-up**
   (`audit/DATA_QUALITY_AUDIT.md`). Two preventive flags only: a clamp/guard code-gap on
   CIre/NDRE/NDWI/GNDVI/OSAVI (0 measured garbage) and NDWI `_cv` instability.
8. **Integrity verified.** 145 protected artifacts; `checksums_before.txt` == `checksums_after.txt`
   **byte-identical**; the frozen model was never retrained; non-destruction intact.

**One line:** *spatial skill ≠ temporal skill* — and under the most rigorous (crop-specific, year-clustered,
matched-baseline) test, multimodal enrichment closes the temporal gap only to **climatology parity**, not past it.

---

## 2. Study design recap

- **Crops / area:** winter wheat + oilseed sunflower, **29 Trakya districts** (Edirne, Kırklareli, Tekirdağ;
  TÜİK reference adds İstanbul-Thrace). Source: `findings_inventory.md`, `README.md`.
- **Panel:** yield + climate **2004–2025**; Sentinel-2 indices **2017–2024** (8 yr). The enrichment tiers A–D
  run on the common NDVI-era panel **n = 213 wheat / 209 sunflower** (`advisor_master_ledger.csv`); the climate-only
  LSTM uses the full panel **n = 589 wheat / 576 sunflower** (`lstm_yield_results.csv`). Tiers are held to the
  same 213/209 panel so the A→D ablation is fair.
- **Models:** 5 base learners — PLS, Elastic-Net, Random-Forest, XGBoost, GPR — (+ stacking in the original
  Paper-1). Fixed pre-specified hyperparameters, SEED=42; standardization/imputation fit on TRAIN folds only.
  Source: `paper1_generalization/revisions/hyperparameter_protocol.csv`, `README.md`.
- **Four CV regimes:** **LOYO** (leave-one-year-out, temporal), **LOILO** (leave-one-district-out, spatial),
  **Spatiotemporal block** (year-block × KMeans cluster), **rolling-origin** (forward-in-time). Never random k-fold.
  Source: `master_ledger_v2.csv` (cv column), `advisor_rolling.csv`, `paper1_generalization/revisions/spatiotemporal_blocks.csv`.
- **Inference:** year-clustered (group) bootstrap 95% CIs + year-level Wilcoxon signed-rank; iid bootstrap secondary.
  Source: `advisor_master_ledger.csv` (ss_ci_*_clustered), `advisor_gap.csv` (year_signrank_p),
  `paper1_generalization/revisions/clustered_inference.csv`.
- **Baseline:** matched climatology = per-district leave-one-out mean (RMSE_matched: wheat 68.813,
  sunflower 54.44 kg/da). Skill score SS = 1 − RMSE_model / RMSE_baseline,matched. Source: `advisor_master_ledger.csv`.
- **Posture:** this is an **AUDIT** (does enrichment + rigorous CV change the conclusion?), **not** a
  model-maximization exercise. Source: `REPORT.md`, `ADVISOR_REPORT.md`.

---

## 3. Data & feature enrichment

**Spectral indices (8).** NDVI, EVI, EVI2, NDRE, CIre, NDWI, GNDVI, OSAVI. Of these, **NDVI-derived season
metrics are from the thesis** (ndvi_max, ndvi_mean_season, ndvi_integral, ndvi_flowering, ndvi_grain_fill,
ndvi_spring_slope, greenness_days); **EVI, EVI2, NDRE, CIre, NDWI, GNDVI, OSAVI are NEW**, each with a stated
rationale (e.g. EVI = reduce NDVI saturation in dense wheat; NDRE = higher yield correlation; OSAVI =
soil-adjusted). Source: `outputs/tables/rs_variable_inventory.csv` (18 rows).

Each index is summarized by **7 distribution metrics** — mean, median, std, CV, P10, P90, range — over
**phenological windows**. Crop windows (Source: `outputs/tables/crop_masking_windows.csv`):

| crop | greenup | peak | grain-fill / harvest |
|---|---|---|---|
| winter wheat | 02–03 | 04–05 | grain-fill 06 |
| sunflower | 06 | 07–08 | harvest 09 |

**Crop-specific masking** (phenology classification, per pixel) validated against TÜİK planted area
(`ekilen_alan`): **wheat r = 0.954**, **sunflower r = 0.615** (Source: `ADVISOR_REPORT.md:17`; underlying
per-district-year classified areas in `outputs/crop_classified_area.csv`).
> ⚠️ **Traceability note:** the r = 0.954 / 0.615 **scalars are stated only in `ADVISOR_REPORT.md` prose**;
> the correlation coefficient itself is not persisted in a standalone CSV (only the classified-area inputs are).

**Soil enrichment.** SoilGrids depth-weighted 0–30 cm, 9 properties (clay/sand/silt/phh2o/soc from thesis;
cec/bdod/nitrogen/cfvo NEW) **+ AWC via Saxton–Rawls (2006)**. Measured ranges (Source: `audit/DATA_QUALITY_AUDIT.md`
B4): pH 6.58–7.31, SOC 15.9–26.8, CEC 21.8–27.4, bulk density 1.357–1.444, **AWC 0.138–0.154**;
clay+sand+silt = 100.0% for all 29. File: `outputs/soil_features.csv` (29×31).

**Topography.** elevation 39.2–441.7 m, slope 2.29–5.57°, northness/eastness ∈ [−1,1], TWI 7.80–9.40
(Source: `audit/DATA_QUALITY_AUDIT.md` B5). File: `outputs/topo_features.csv` (29×8).

**Anomaly z-scores.** per-district z + yield_z, max|z| = 2.47, 0 non-finite (Source: `audit` B6).
Files: `outputs/anomaly_{bugday,aycicegi}.csv`.

**Tiers A–D** (Source: `outputs/tables/tier_definitions.csv`):

| tier | composition |
|---|---|
| A | climate only (unchanged baseline) |
| B | climate + {NDVI, NDRE, EVI} crop-specific window means |
| C | B + soil |
| D | C + phenological distribution metrics (median/std/CV/P10/P90/range) |

---

## 4. PRIMARY RESULTS — crop-specific (LOYO vs matched climatology)

**Best-per-tier temporal skill (LOYO), year-clustered 95% CI.** Source: `ADVISOR_REPORT.md:20–35`, verified
against `advisor_master_ledger.csv` (best model per crop×tier shown).

| crop | tier | best model | LOYO SS | year-clustered 95% CI | beats climatology? |
|---|---|---|---|---|---|
| winter wheat | A | gpr | **−0.261** | [−0.543, −0.128] | no |
| winter wheat | B | random_forest | **−0.152** | [−0.371, −0.035] | no |
| winter wheat | C | gpr | **−0.069** | [−0.169, −0.020] | no |
| winter wheat | D | gpr | **−0.014** | [−0.087, **+0.070**] | **no (CI straddles 0)** |
| sunflower | A | random_forest | **−0.086** | [−0.255, **+0.007**] | no |
| sunflower | B | random_forest | **−0.110** | [−0.248, −0.026] | no |
| sunflower | C | gpr | **−0.019** | [−0.239, **+0.134**] | no (CI straddles 0) |
| sunflower | D | random_forest | **−0.004** | [−0.067, **+0.069**] | **no (parity)** |

*Caption: crop-specific best-model LOYO skill vs per-district matched climatology, year-clustered bootstrap CI.
Source: `enrichment_v2/outputs/advisor_master_ledger.csv` (cols skill_score, ss_ci_low/high_clustered).*

**Honest reading per tier:**
- **Tiers A–C, both crops:** CIs lie **below 0** (or straddle it for sunflower C) → enrichment up to soil does
  **not** beat climatology temporally.
- **Tier D, wheat (−0.014) and sunflower (−0.004):** CIs **include 0** → **climatology parity, not superiority**.
- **Monotonicity is approximate, not strict.** Wheat improves monotonically A→D (−0.261→−0.152→−0.069→−0.014).
  **Sunflower is non-monotonic at B** (A −0.086 → B **−0.110**, i.e. slightly worse) before improving at C/D.
  > ⚠️ **Discrepancy flagged:** `ADVISOR_REPORT.md:33` states enrichment improves "monotonically A→D" for
  > both crops; the underlying `advisor_master_ledger.csv` shows sunflower B (best −0.110) is marginally
  > below A (best −0.086). The trend is **near-monotonic**; the strict-monotonic wording is slightly optimistic.

---

## 5. METHODOLOGICAL COMPARISON — all-cropland 8-index (NOT the headline)

Same pipeline on **generic cropland** (no crop-specific mask) with the **full 8-index** feature set.
Best-per-tier LOYO SS (Source: `outputs/master_ledger_v2.csv`, summarized in `outputs/tables/table8_enrichment_value_v2.csv`):

| crop | A | B | C | D (best) | D model | D 95% CI |
|---|---|---|---|---|---|---|
| sunflower | −0.0855 | +0.0478 | +0.0470 | **+0.1087** | gpr | [**+0.033, +0.161**] |
| winter wheat | −0.261 | −0.0472 | −0.0258 | **+0.0571** | xgboost | [−0.054, +0.155] |

*Caption: all-cropland best-per-tier LOYO skill. Source: `enrichment_v2/outputs/master_ledger_v2.csv`,
`tables/table8_enrichment_value_v2.csv`.*

**Reading (with the required caveat):** in the all-cropland comparison, **sunflower tier D beats climatology**
(SS +0.109, CI > 0), while **wheat tier D does not** (CI straddles 0). The higher absolute sunflower skill
here vs the crop-specific −0.004 is attributable to (a) **spatial/aggregate smoothing** of a generic-cropland
mean and (b) a **wider feature set** (8 indices vs 3) — **not** to a better measurement of sunflower yield drivers.
**Per the integrity contract, the all-cropland +0.109 is NEVER reported as the project's headline over the
crop-specific −0.004.** The crop-specific analysis is the advisor-correct primary; the all-cropland is methodology.

---

## 6. HEADLINE FINDING — spatial ≫ temporal generalization gap (ΔR² = R²_LOILO − R²_LOYO)

The gap is **positive and CI-excludes-zero in essentially every cell** of both result sets. Representative
GPR rows per tier:

**PRIMARY (crop-specific)** — Source: `outputs/advisor_gap.csv` (gpr rows; gap_dR2, gap_ci, year_signrank_p):

| crop | tier | R²_LOYO | R²_LOILO | ΔR² | 95% CI | year sign-rank p |
|---|---|---|---|---|---|---|
| wheat | A | −0.517 | +0.429 | **+0.946** | [+0.780, +1.117] | 0.016 |
| wheat | C | −0.091 | +0.618 | **+0.709** | [+0.570, +0.856] | 0.008 |
| wheat | D | +0.018 | +0.591 | **+0.572** | [+0.429, +0.718] | 0.055 |
| sunflower | A | −0.321 | +0.428 | **+0.749** | [+0.585, +0.914] | 0.016 |
| sunflower | C | −0.057 | +0.438 | **+0.495** | [+0.352, +0.647] | 0.008 |
| sunflower | D | −0.103 | +0.497 | **+0.600** | [+0.482, +0.730] | 0.008 |

**COMPARISON (all-cropland)** — Source: `outputs/gap_v2.csv` (gpr, tier D): wheat ΔR² **+0.470**
[+0.336, +0.612]; sunflower ΔR² **+0.384** [+0.281, +0.490]. Gap persists.

Across **all** crop×tier×model rows the gap ranges from **+0.29** (all-cropland wheat·D elastic_net, `gap_v2.csv`)
to **+1.76** (wheat·A pls, `advisor_gap.csv`), always positive. `ADVISOR_REPORT.md:34` & `tables/advisor_table3_gap.csv`:
"persists = True".

**Original Paper-1 gap (point-buffer support)** — Source: `paper1_generalization/docs/numbers_ledger.md` C1–C6
(from `analysis/generalization_gap.csv`, fixed-model + iid CI + Wilcoxon):

| crop·layer | model | R²_LOYO | R²_LOILO | ΔR² | CI | Wilcoxon p |
|---|---|---|---|---|---|---|
| wheat·A | gpr | −0.198 | +0.441 | **+0.639** | [+0.545, +0.735] | 6.2e−26 |
| wheat·B | gpr | −0.535 | +0.429 | +0.965 | [+0.765, +1.171] | 3.1e−13 |
| wheat·C | xgboost | −0.311 | +0.427 | +0.738 | [+0.527, +0.968] | 3.1e−08 |
| sunflower·A | xgboost | −0.076 | +0.504 | **+0.580** | [+0.490, +0.674] | 5.6e−28 |
| sunflower·B | gpr | +0.214 | +0.450 | +0.236 | [+0.141, +0.326] | 2.6e−07 |
| sunflower·C | gpr | +0.387 | +0.582 | +0.196 | [+0.118, +0.266] | 5.8e−05 |

**The gap is the robust, replicated finding** — present in the original point-buffer analysis, the new
admin-polygon crop-specific analysis, the all-cropland comparison, **and** the LSTM (§8). It does not depend
on which result set, spatial support, feature tier, or model is chosen.

---

## 7. Per-crop index findings & selected features

**Effective vs ineffective indices** (Source: `outputs/advisor_percrop_rs_list.csv`, `ADVISOR_REPORT.md:11–14`):

| crop | effective | ineffective (dropped) | interpretation |
|---|---|---|---|
| winter wheat | **EVI, NDRE** | NDVI | NDVI saturates in dense wheat → EVI/NDRE carry the signal (advisor hypothesis confirmed) |
| sunflower | **NDRE, NDVI** | EVI | red-edge + NDVI separate sunflower; EVI less useful |

**Selected feature sets (tier D, verbatim)** — Source: `outputs/advisor_selected_features.json`:
- **wheat D:** tp_season_sum, EVI_peak_p10, cfvo_0_30_mean, ssr_flowering_sum, EVI_peak_cv, bdod_0_30_mean,
  EVI_grainfill_range, EVI_greenup_cv, tp_grain_fill, NDRE_peak_p10, vernalization_days, EVI_grainfill_p10,
  NDRE_peak_mean, NDRE_peak_stdDev.
- **sunflower D:** tp_season_sum, NDVI_greenup_cv, cfvo_0_30_mean, aridity_index, NDVI_peak_p10,
  t2m_flowering_mean, awc_0_30, NDRE_peak_p10, tp_grain_fill, sand_0_30_mean, ssr_season_sum, NDRE_peak_cv, tp_flowering.

Selection is not over-fit: **obs-per-feature 15.2–19.4**, cap_k 13–14, **risky = False** for all crop×tier
(Source: `outputs/t7_ratio.csv`).

**Enrichment value ΔSS (A→D ladder).** Source: `outputs/tables/table8_enrichment_value_v2.csv` (all-cropland)
and `advisor_master_ledger.csv` (crop-specific):

| crop | result set | D − A (ΔSS) |
|---|---|---|
| winter wheat | all-cropland | **+0.318** (−0.261 → +0.057) |
| sunflower | all-cropland | **+0.194** (−0.086 → +0.109) |
| winter wheat | crop-specific | **+0.247** (−0.261 → −0.014) |
| sunflower | crop-specific | **+0.082** (−0.086 → −0.004) |

Enrichment adds real skill (positive ΔSS everywhere); for crop-specific it lifts both crops **to** parity, not past.

---

## 8. Forward-in-time, ablation & LSTM

**Rolling-origin (forward, 4 test years), mean skill vs climatology:**

| crop | tier | crop-specific (`advisor_rolling.csv`) | all-cropland (`rolling_origin_v2.csv`) |
|---|---|---|---|
| wheat | A | −0.364 | −0.364 |
| wheat | C | +0.048 | +0.029 |
| wheat | D | +0.085 | +0.082 |
| sunflower | A | +0.009 | +0.009 |
| sunflower | C | +0.069 | +0.065 |
| sunflower | D | +0.059 | +0.140 |

*Caption: forward-in-time mean skill, n_test_years = 4. Sources as labeled.* Tier C/D forward skill is small and
positive but rests on **only 4 test years** — weak evidence; A is strongly negative.

**Original rolling-origin (point-buffer, up to 15 test years)** — Source: `paper1_generalization/revisions/rolling_origin_summary.csv`:
tier A is **negative for all 5 models, both crops** (wheat mean −0.18 to −0.33; sunflower −0.05 to −0.12);
tier C mixed (sunflower rf +0.128, gpr +0.134; wheat rf −0.147), frac-years-skill-positive 0.13–0.75.
Forward skill is weak/inconsistent — consistent with "temporal prediction is hard."

**Per-algorithm matched ablation (original support)** — Source: `paper1_generalization/revisions/ablation_by_algorithm_summary.csv`:

| crop | cv | mean Δ(NDVI) | mean Δ(soil) |
|---|---|---|---|
| sunflower | LOYO | **+0.382** | +0.217 |
| sunflower | LOILO | −0.001 | +0.143 |
| wheat | LOYO | −0.001 | **+0.331** |
| wheat | LOILO | +0.044 | +0.034 |

→ NDVI helps **sunflower** temporally; soil helps **wheat** temporally; in the spatial (LOILO) regime both
deltas shrink. (5 algorithms averaged.)

**Staged-issuance forecast** — exists **only for the original point-buffer Paper-1**
(`paper1_generalization/revisions/staged_forecast_results.csv`), **NOT re-run on the admin-polygon enrichment**.
Wheat, LOYO, by issuance stage (best across models): pre-season SS ≈ +0.002 (rf) down to flowering SS ≈ −0.20
to −0.36 — adding mid-season features does **not** improve temporal skill. Flagged: do not blend with §4/§5.

**Yield LSTM (monthly NASA-POWER climate sequence → district yield)** — Source: `outputs/lstm_yield_results.csv`:

| crop | LOYO R² | LOYO RMSE | LOYO SS vs clim | LOILO R² | LOILO−LOYO R² gap | vs cp25 layer-A R² (Δ) |
|---|---|---|---|---|---|---|
| wheat | 0.096 | 66.17 | **−0.072** | 0.291 | **+0.195** | layerA −0.092 (Δ +0.188) |
| sunflower | −0.008 | 51.05 | **−0.021** | 0.415 | **+0.422** | layerA +0.051 (Δ −0.059) |

→ The LSTM **does not beat climatology temporally** (both SS < 0) and **reproduces the spatial≫temporal gap**
(LOILO R² ≫ LOYO R²) — independent architecture, same conclusion.

---

## 9. Comparison to the original Paper-1

| quantity | original (point-buffer) | new (admin-polygon, crop-specific) | source |
|---|---|---|---|
| Sunflower best temporal SS | **+0.224** [+0.167, +0.276] (Layer-C GPR) | **−0.004** [−0.067, +0.069] (tier-D rf) | `baseline_superiority.csv` ; `advisor_master_ledger.csv` |
| Wheat: # ML models beating B0 | **0 / 16** | 0 (all tiers, best −0.014) | `numbers_ledger.md` B3 ; `advisor_master_ledger.csv` |
| Spatial≫temporal gap | wheat·A +0.639 / sunflower·A +0.580 | wheat·D +0.572 / sunflower·D +0.600 | `numbers_ledger.md` C1/C4 ; `advisor_gap.csv` |

**What changed:** the **sunflower advantage is fragile**. Under crop-specific masking + admin-polygon support it
collapses from +0.224 to parity (−0.004). The audit conclusion is therefore **cleaner and stronger**: under the
most rigorous design, *neither* crop robustly beats climatology, while the spatial-vs-temporal gap survives intact.

> ⚠️ **Discrepancy flagged (original sunflower number).** Two artifacts give slightly different values for the
> original sunflower advantage: `analysis/baseline_superiority.csv` (paired-bootstrap) = **+0.2235 → +0.224**;
> `docs/numbers_ledger.md` A2 (from published `12_master_comparison.csv`) = **+0.225**. Both are shown; the
> difference (0.001) is rounding/source-of-record, not a substantive conflict.

> ⚠️ **Comparability caveat.** The spatial support changed (adaptive **point-buffer** → **admin-polygon cropland**),
> the mask changed (generic → crop-specific phenology), and tier composition differs. The +0.224 → −0.004 drop
> therefore **conflates** support, masking, and feature changes — it is **not** a cell-for-cell diff and is described,
> not tabulated as one (`[NOT IN ARTIFACTS]` for an identical-support comparison; impossible by construction).

---

## 10. Data-quality & integrity

**Audit verdict (Source: `audit/DATA_QUALITY_AUDIT.md`, `feature_summary.csv`, `flagged_records.csv`,
`raw_sample_anomaly_rates.csv`, `collinear_pairs.csv`):**

| family | verdict | evidence |
|---|---|---|
| Spectral indices | CLEAN outputs / code-gap flag | **0 OOB** in 33 saved features; **0 OOB** in clamp-disabled raw pixels (4 districts × 8 indices) |
| Climate | **CLEAN** | raw annual precip 307–965 mm, mean **594** → **no 12.5× bug**; GDD 1938–4716; aridity 0.1–1.1 |
| Soil | **CLEAN** | all in range; texture sums = 100%; AWC 0.138–0.154 |
| Topography | **CLEAN** | elev 39–442 m, slope 2.3–5.6°, north/eastness ∈[−1,1], TWI 7.8–9.4 |
| Yield + anomaly | **CLEAN** | wheat 147–589, sunflower 52–372 kg/da; 0 zeros/neg/>5×IQR; max\|z\|=2.47 |
| Coverage | FLAG | **25.1% NaN** in index metrics (cloud-free gaps), not garbage |
| Structural | NOTE | 217 collinear pairs \|r\|>0.98 (by-design) |

- **flagged_records.csv = 0 rows** (no out-of-bounds records). **feature_summary.csv = 33 features**, all
  verdict CLEAN. **collinear_pairs.csv = 217** (informational).
- **Clamp/guard answer (the #1 question):** the |value|≤1 clamp is on **EVI/EVI2 only**;
  CIre/NDRE/NDWI/GNDVI/OSAVI are **unguarded** (CIre = (B7/B5)−1 highest risk). **Measured impact = none:**
  raw clamp-disabled sample shows 0 OOB everywhere; CIre max 5.09–7.86 = legitimate dense canopy; raw EVI
  exceeded 1 in only 36/1,246,884 px (0.003%) at Hayrabolu → the EVI clamp is doing tiny real work. The
  cloud+cropland mask + per-window median composite suppress the failure mode. **Recommendation: extend the
  guard preventively** (no fix applied — audit only).
- **NDWI CV instability (real action item):** max\|CV\| = **708**, **465 non-finite CV cells** where index
  mean ≈ 0 → drop/guard `*_cv` for low-mean indices (esp. NDWI).

**Integrity (Source: `checksums_before.txt`, `checksums_after.txt`, `POST_RESTART_VERIFICATION.txt`):**
145 protected artifacts; **before == after, byte-identical** (verified via diff: IDENTICAL, 145 lines each);
0 protected artifacts changed/missing; the frozen model was never retrained.

---

## 11. Honest limitations

1. **Neither crop robustly beats climatology** under the crop-specific year-clustered LOYO test (tiers A–D);
   tier D reaches parity only (§4).
2. **Sunflower mask is moderate** (r = 0.615) — harder to separate from other summer crops; adds classification
   noise that partly explains sunflower's tighter-to-parity behavior (`ADVISOR_REPORT.md:17,40`).
3. **Short RS era** (Sentinel-2 2017–2024 = 8 yr) → few **rolling-origin** test years (4) → weak forward evidence (§8).
4. **District-aggregate, not field-level** — yields are TÜİK district means; field-level historical yield is
   unavailable (`ADVISOR_REPORT.md:41`).
5. **Generic-vs-crop-specific tension** — the all-cropland comparison looks better (sunflower D +0.109) but is
   methodologically the wrong primary; the crop-specific (−0.004) is correct (§5).
6. **Spatial-support change** (point-buffer → admin-polygon) means new numbers are **not cell-for-cell**
   comparable to the originals (§9).
7. **Unguarded indices** (CIre/NDRE/NDWI/GNDVI/OSAVI) — preventive fix pending; 0 measured garbage today (§10).
8. **NDWI `_cv` to be cleaned** (max\|CV\| 708) before any reuse of low-mean-index CV features (§10).

---

## 12. Scientific interpretation

- **The design is the contribution.** Multimodal features (spectral + soil + topo + climate) + structure-aware
  CV (LOYO/LOILO/spatiotemporal/rolling) + a **temporal** target + **meaningful matched baselines** make this a
  *harder, more honest* test than random k-fold against a naive mean. Source basis: `REPORT.md` Conclusion,
  `docs/WRITING_DOSSIER.md`, `docs/results_narrative.md`.
- **A rigorous negative is a strong result.** That enrichment closes the temporal gap only to climatology
  parity — while spatial interpolation (LOILO) reaches R² ≈ 0.5–0.6 — is a clean, publishable audit finding:
  it tells practitioners that **predicting *which district* is easy and *which year* is hard**, and that
  buying more features does not fix the temporal problem.
- **"More robust test, not better prediction."** Skill did not rise; **rigor** did. The headline is the
  **gap** (replicated across supports, masks, tiers, models, and an LSTM), not a skill score to advertise.

---

## 13. Open decisions & next steps

1. **Paper 1 vs Paper 2 scope** — the gap + the fragility-of-sunflower-advantage is a coherent single story
   (recommend Paper 1: "spatial ≠ temporal, and enrichment doesn't close the temporal gap").
2. **Primary result set** — **recommend crop-specific** as primary throughout the manuscript; all-cropland as a
   methodological supplement only.
3. **If integrating** — re-baseline the original NDVI-only models on **admin-polygon** support so a like-for-like
   comparison becomes possible (currently `[NOT IN ARTIFACTS]`).
4. **Audit follow-ups** — extend the |value|≤1 guard to CIre/NDRE/NDWI/GNDVI/OSAVI; drop/guard NDWI `_cv`;
   then re-run the T8 ledgers and confirm numbers unchanged (expected, since measured garbage = 0).
5. **Advisor ORCID / email** — `[NOT IN ARTIFACTS]` (not on disk); needed for submission metadata.
6. **Manuscript table updates** — Tables for §4 (primary), §6 (gap, all three supports), §8 (LSTM) are ready
   to drop in from the cited CSVs.

**Extra independent validation (not in the core 14-section scope):** two large Vize plains tested with the same
crop-specific pipeline (Source: `outputs/plains_test_summary.csv`, `plains_geometry.json`):
**Ahmetbey ~2,640 ha** (wheat mean 1,214 ha / sunflower 884 ha; wheat peak NDVI 0.802, NDRE 0.608, EVI 0.623)
and **Müsellim ~6,026 ha** (wheat 2,590 ha / sunflower 534 ha; wheat peak NDVI 0.800, NDRE 0.611, EVI 0.631).
Both wheat-dominant, all index values physically plausible — the pipeline behaves correctly on independent large areas.

---

## 14. Appendix

### A. Source-file index (table → path)
| Report table | Source file |
|---|---|
| §4 primary SS | `outputs/advisor_master_ledger.csv`, `ADVISOR_REPORT.md`, `tables/advisor_table2_temporal.csv` |
| §5 all-cropland SS | `outputs/master_ledger_v2.csv`, `tables/table8_enrichment_value_v2.csv` |
| §6 gap (primary) | `outputs/advisor_gap.csv`, `tables/advisor_table3_gap.csv` |
| §6 gap (comparison) | `outputs/gap_v2.csv`, `tables/table3_generalization_gap_v2.csv` |
| §6 gap (original) | `paper1_generalization/analysis/generalization_gap.csv`, `docs/numbers_ledger.md` |
| §7 indices/features | `outputs/advisor_percrop_rs_list.csv`, `advisor_selected_features.json`, `t7_ratio.csv` |
| §8 rolling | `outputs/advisor_rolling.csv`, `rolling_origin_v2.csv`, `revisions/rolling_origin_summary.csv` |
| §8 ablation | `outputs/advisor_ablation.csv`, `ablation_v2.csv`, `revisions/ablation_by_algorithm_summary.csv` |
| §8 staged | `paper1_generalization/revisions/staged_forecast_results.csv` |
| §8 LSTM | `outputs/lstm_yield_results.csv`, `lstm_yield_persample.csv` |
| §9 original baselines | `paper1_generalization/analysis/baseline_superiority.csv`, `docs/numbers_ledger.md` |
| §10 audit | `audit/DATA_QUALITY_AUDIT.md`, `feature_summary.csv`, `flagged_records.csv`, `raw_sample_anomaly_rates.csv`, `collinear_pairs.csv` |
| §10 integrity | `checksums_before.txt`, `checksums_after.txt`, `POST_RESTART_VERIFICATION.txt` |
| §13 plains | `outputs/plains_test_summary.csv`, `plains_geometry.json` |

### B. Per-crop selected features (tiers A–C, verbatim)
Full lists for all tiers in `outputs/advisor_selected_features.json` (crop-specific) and `outputs/selected_features.json`
(all-cropland). Tier-D lists are in §7; tiers A/B/C are in the JSON files (not re-typed here to avoid transcription error).

### C. Collinearity note
217 index-feature pairs with |r| > 0.98 (`audit/collinear_pairs.csv`) — expected by construction
(mean≈median, range≈P90−P10, intercorrelated indices). Handled downstream by T7 selection (obs/feat 15–19, risky=False).

### D. Items written `[NOT IN ARTIFACTS]`
- Advisor ORCID / email (§13).
- Identical-spatial-support crop-specific-vs-original diff (§9) — impossible by construction (support changed).

---

*Compiled READ-ONLY from the artifacts cited above. No new computation; conflicts shown not hidden; existing
files untouched. Rollback = delete this file (+ `findings_inventory.md`).*
