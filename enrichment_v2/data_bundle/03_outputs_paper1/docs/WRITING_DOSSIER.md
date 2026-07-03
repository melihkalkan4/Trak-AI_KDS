# WRITING DOSSIER — Paper 1 (PRIMARY HANDOFF)

> **Purpose.** This file is self-sufficient: the final author can write the whole
> manuscript from this `docs/` package without re-reading code or CSVs. Every number
> is traceable (see `numbers_ledger.md`); methods in `methods_as_implemented.md`;
> finding-level prose in `results_narrative.md`. Nothing here is fabricated.
> Companion: `tables/tables.md`, `figures/figure_manifest.md`, `refs/citation_todo.md`.

---

## 0. One-paragraph thesis & target
A frozen, retrospective evaluation of satellite-driven crop-yield (and NDVI) models for winter
wheat and sunflower across 29 districts of Trakya (Türkiye), 2004–2025, asking not "can we
predict yield?" but **"does cross-validated skill survive the kind of generalization an
operational user needs?"** The contribution is an honest, nuanced negative/mixed result: (i)
machine-learning models beat a climatology baseline for sunflower but **not** for winter wheat
under leave-one-year-out (temporal) validation; (ii) there is a **large, significant
spatial-vs-temporal generalization gap** — models interpolate across districts far better than
they extrapolate across years; (iii) NDVI's marginal value is crop-specific and a naïve ablation
over-states a wheat "harm"; (iv) forward NDVI forecasting **collapses during senescence** and does
not beat persistence. **Target journal: Computers and Electronics in Agriculture (Q1).** Tone:
methods/validation paper; honest, hedged, no hype.

## 1. KEY HONEST FINDINGS (the spine of the paper)
Each: plain claim · number (95% CI) · provenance.

1. **No ML model beats climatology for winter wheat under temporal CV.** Best wheat ML skill
   score vs B0 = **−0.172 [−0.238, −0.109]** (Wilcoxon p=1.1e−05); 0 of 16 models beat B0; the
   wheat champion *is* the B0 climatology (R²=0.213). → `baseline_superiority.csv`, `12_master_comparison.csv`.
2. **Sunflower multimodal does beat climatology.** Layer C GPR R²=0.386, skill score
   **+0.224 [+0.167, +0.276]** (p=1.0e−08); Layer A (climate-only) does *not* beat B0 (rf SS=+0.009, ns).
   → `baseline_superiority.csv`.
3. **Large spatial>temporal generalization gap.** Paired ΔR²(LOILO−LOYO): wheat climate-tier
   **+0.639 [+0.545, +0.735]** (p=6.2e−26); sunflower **+0.580 [+0.490, +0.674]** (p=5.6e−28);
   positive & significant in all 6 crop×tier cells and all models. → `generalization_gap.csv`, **F4**.
4. **NDVI value is crop-specific; naïve ablation misleads.** Matched-sample ΔR²(NDVI): wheat
   **+0.039** (≈0), sunflower **+0.431** (large). Naïve full-sample wheat ΔNDVI = −0.444 is mostly
   a sample-size artifact (n 589→213). → `T2_ablation.csv`.
5. **On the REAL surveyed parcel, the NDVI forecaster never beats persistence.** EVR_01 re-run on
   the farmer's 4 GPS corners (0.62 ha near Vize): 2025 model R²=0.78 vs persistence 0.91
   (Wilcoxon p=1.000); 2026 partial model R²=**−1.32** vs persistence 0.49 (p=1.000). Late-season
   per-stage skill is unstable (maturity R²=−13.7; MAE stays ~0.05). The placeholder coords were
   mildly optimistic (2026 model 0.703→−1.32) — the finding is **not** a placeholder artifact and is
   stronger at the true site. → `prospective_overall_real.csv`, `T3_per_stage_real.csv`,
   `prospective_placeholder_vs_real.csv`, **F3b** (real) / **F3** (placeholder, comparison).
6. **Wheat residuals are spatially autocorrelated.** Moran's I = **+0.257** (p_norm=0.008);
   sunflower I=+0.117 (ns). → `morans_i.csv`, **F5**.
7. **Temporal skill is fragile (few years).** Year-cluster bootstrap of the best sunflower model's
   LOYO R² = [−0.145, +0.506] (vs iid [+0.296, +0.459]). → `bootstrap_ci.csv` (method=cluster).

## 2. SECTION-BY-SECTION RAW MATERIAL
(Plain statements to be turned into English prose. Citations needed are flagged `[VERIFY]`.)

### 2.1 Introduction
- Problem: ML + remote sensing yield-prediction papers commonly report high accuracy, but often
  under random k-fold CV that leaks spatial/temporal structure and over-states operational skill
  `[VERIFY: needs citation — roberts2017crossval, ploton2020spatial]`.
- Operational use is a *forecasting* task: predict an unseen *future year* (and possibly an unseen
  location). Honest prospective/temporal validation is comparatively rare `[VERIFY: needs citation]`.
- This study: a frozen, recompute-faithful re-analysis over Trakya wheat & sunflower contrasting
  temporal (LOYO), spatial (LOILO), and spatiotemporal CV, with climatology/persistence baselines.
- Contribution = the nuanced finding (where ML beats/relies-on baselines; the generalization gap;
  the senescence collapse), not a new high-accuracy model.
- Crops: winter wheat (vernalization-requiring) and oilseed sunflower — contrasting phenology.

### 2.2 Study area & data
- Region: Trakya (Thrace), NW Türkiye; 29 districts (ilçe). Rain-fed wheat & sunflower rotation `[VERIFY: regional citation]`.
- Target: TÜİK official district yields, kg da⁻¹; panel 1165 district-years, 2004–2025 `[VERIFY: TÜİK citation]`.
- Predictors: climate (NASA POWER/MERRA-2 seasonal features), NDVI (Sentinel-2 via GEE, 2017+),
  soil (ISRIC SoilGrids). NDVI availability restricts NDVI tiers to n=213 (wheat)/209 (sunflower).
- Feature tiers: A=climate (14), B=+NDVI (21), C=+NDVI+soil (27). Exact lists in `methods_as_implemented.md` §2.
- Prospective (FLOV): site **EVR_01 now uses REAL surveyed coordinates** (4 GPS corners → 0.62 ha
  parcel near Vize, centroid 41.531 N/27.861 E), re-validated live (GEE+CDS). EVR_02–05 remain
  placeholder (not re-run). State the EVR_01 unblock; keep the small-field/single-site caveats.
- Data-source caveat: MERRA-2 vs ERA5-Land difference noted in the thesis.

### 2.3 Methods (full detail in `methods_as_implemented.md`)
- Three CV regimes via `LeaveOneGroupOut`: **LOYO** (groups=year, temporal), **LOILO**
  (groups=district, spatial), **Spatiotemporal** (5 year-blocks × 5 KMeans spatial clusters).
- Models (SEED=42): PLS, ElasticNet, RandomForest, XGBoost, GPR(Matern), + Stacking (Layer C, LOYO).
- Baselines: B0 climatology (LOO district mean), B1 year-trend, B2 persistence, B3 climate-proxy.
  Skill score SS = 1 − RMSE/RMSE_B0.
- Metrics: R², RMSE, MAE, MAPE, bias (sklearn).
- Bootstrap: observation (iid) 5000/seed12345 primary + group-cluster sensitivity.
- Generalization-gap test: paired Wilcoxon signed-rank on |error| (LOYO vs LOILO, same obs) +
  rank-biserial effect size + paired-bootstrap ΔR² CI.
- Baseline test: paired bootstrap SS CI + paired Wilcoxon vs B0.
- Matched-sample ablation (A on NDVI subset) to separate feature from sample effects.
- Moran's I (esda, KNN k=4, 999 perms) on champion residuals.
- FLOV prospective: frozen LSTM (NDVI t+7) + XGB yield, hash-locked, walk-forward, vs persistence,
  per phenology stage.
- Reproducibility: deterministic; recompute matched published cp25 tables to **max |Δ| = 0.0**.

### 2.4 Results (use `results_narrative.md` findings 1–7 verbatim as the backbone)
- Order: (R1) baseline superiority by crop → (R2) the generalization gap [headline] → (R3)
  ablation/NDVI value → (R4) per-stage senescence → (R5) Moran's I → (R6) importance → (R7)
  spatiotemporal intermediate. Lead with the honest baseline comparison and the gap.

### 2.5 Discussion
- Why wheat ML ≤ climatology under LOYO: strong B0 (per-district mean captures most variance,
  R²=0.213); inter-annual wheat yield driven by hard-to-anticipate grain-fill weather; spatially
  autocorrelated residuals (Moran's I) reveal unmodelled geography; small year count.
- Why sunflower multimodal helps: flowering-window NDVI carries real signal (importance 0.587);
  B0 is weak (R²=0.033) so there is room to beat it; ΔNDVI matched +0.431.
- The gap's implication: spatial CV (still common) is an optimistic proxy; LOYO/forward validation
  is necessary for operational claims. Compare with literature optimism `[VERIFY: needs citation]`.
- Senescence collapse: NDVI saturation/decay late season caps NDVI-driven forecasting `[VERIFY: phenology citation]`.
- Interpretability ≠ out-of-time validity (wheat keys on agronomically sensible features yet fails LOYO).
- Practical guidance: for wheat, a climatology/persistence forecast is the honest operational
  default; ML adds value for sunflower mid-season but with fragile, few-year-anchored temporal skill.

### 2.6 Limitations
- Single region (Trakya); ~22 years → small-n LOYO; year-cluster CIs wide.
- NDVI tiers restricted to 2017+ (n=213/209); A vs B/C sample mismatch (mitigated by matched ablation).
- Prospective FLOV: EVR_01 now real-coordinate, but a **single small field** (0.62 ha →
  subpixel-noisy S2), satellite-derived (not in-situ) ground truth, 2026 season partial; EVR_02–05
  still placeholder. Conclusions are single-site.
- District-level yields are administrative aggregates (not field-level).
- iid bootstrap optimistic under panel correlation (cluster reported alongside).
- MERRA-2 vs ERA5-Land climate-source difference.

### 2.7 Conclusion
- Honest validation reframes the value proposition: cross-validated accuracy ≠ operational skill;
  the spatial-vs-temporal gap and the wheat-vs-sunflower asymmetry are the transferable lessons;
  recommend LOYO/forward validation + climatology baselines as standard practice.

## 3. TABLES (captions + what they show + source)
- **T1** `tables/T1_master_results.csv` — Master metric matrix: baselines B0–B3 + all
  layer×model×CV (R²,RMSE,MAE,MAPE,bias,SS,n). *Caption:* "Cross-validated performance across
  feature tiers, models, and CV regimes for both crops."
- **T2** `tables/T2_ablation.csv` — Matched-sample ablation A_full/A_matched/B/C with ΔNDVI, Δsoil.
  *Caption:* "Marginal value of NDVI and soil, controlling for sample (matched n)."
- **T3** `tables/T3_per_stage.csv` — Per-phenology-stage NDVI t+7 skill, EVR_01 2025 & 2026.
  *Caption:* "Forward NDVI forecast skill by phenological stage; note senescence collapse."
- **T4** `tables/T4_feature_importance.csv` — Permutation importance by layer×crop.
  *Caption:* "Permutation feature importance."
- Rendered preview: `tables/tables.md`.

## 4. FIGURES (see `figures/figure_manifest.md` for full detail)
- **F1** pred-vs-actual (Layer C, LOYO) — multimodal temporal performance per crop.
- **F2** skill-score vs B0 (LOYO) with CIs — wheat all worse, sunflower Layer C beats B0.
- **F3** per-stage NDVI R² — senescence collapse.
- **F4** generalization gap (LOYO/LOILO/Spatiotemporal × tier × crop) — **headline**.
- **F5** Moran's I residual maps.
- **F6** permutation importance (Layer C).

## 5. CONSOLIDATED [VERIFY] / CITATION NEEDS (full list in `refs/citation_todo.md`)
- Random-CV optimism vs blocked CV; spatial-CV over-statement (roberts2017, ploton2020, meyer2021, kattenborn2022).
- ML crop-yield review anchor (vanklompenburg2020, CEA).
- NDVI+phenology yield forecasting (bolton2013); NDVI senescence saturation `[VERIFY]`.
- Winter-wheat vernalization & grain-fill-precip agronomy `[VERIFY]`; sunflower flowering NDVI `[VERIFY]`.
- TÜİK data citation; Trakya regional description; persistence/climatology as forecast benchmark (hyndman2006).
- Data/model: Sentinel-2 (drusch2012), GEE (gorelick2017), ERA5 (hersbach2020), SoilGrids (poggio2021).
- Methods: RF (breiman2001), XGBoost (chen2016), GPR (rasmussen2006), SHAP (lundberg2017),
  Moran (moran1950), LISA (anselin1995), Wilcoxon (wilcoxon1945).
- **Every bib entry needs DOI/details verified — none invented.**

## 6. REAL-WORLD INPUT STATUS (was blocked — now largely unblocked)
- ✅ **Real parcel coordinates supplied (2026-06-20)** for EVR_01 → re-validated live; the
  prospective section now uses true geometry. Placeholder-coordinate blocker is RESOLVED for EVR_01.
- Remaining (out of scope / optional): EVR_02–05 real coordinates; in-situ (non-satellite) ground
  truth; more years/regions to tighten temporal CIs.

## 7. WHAT IS SOLID vs HEDGED (for tone calibration)
- **Solid (point + CI, fidelity-verified):** baseline comparison, the generalization gap,
  matched ablation, Moran's I, per-stage collapse, importances.
- **Hedge explicitly:** absolute temporal R² magnitudes (few years; cluster CIs wide); prospective
  /FLOV numbers (single small field, satellite ground truth, partial 2026) — but the
  persistence-beats-model conclusion there is robust (Wilcoxon p=1.000 in all windows, real coords).
