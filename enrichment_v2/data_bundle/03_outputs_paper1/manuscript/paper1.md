# Spatial skill is not temporal skill: an honest cross-validation audit of satellite-driven wheat and sunflower yield prediction in Trakya, Türkiye

> STRUCTURAL DRAFT. Every quantitative claim traces to `docs/numbers_ledger.md`
> (fidelity-verified, max |Δ|=0.0 vs the thesis cp25 tables). Citations are
> `[VERIFY]`-marked; none are invented. Final prose to be finished from `docs/`.
> Crop labels: winter wheat (`bugday`), oilseed sunflower (`aycicegi`).

## Highlights
- Across 29 Trakya districts (2004–2025), ML beats a climatology baseline for sunflower yield but **not** for winter wheat under leave-one-year-out validation.
- A large, significant **spatial-vs-temporal generalization gap**: ΔR²(LOILO−LOYO) up to +0.64 (wheat) — models interpolate across space far better than they extrapolate across years.
- A **matched-sample ablation** shows NDVI's apparent harm to wheat is a sample-size artifact; NDVI's real value is large for sunflower (ΔR²=+0.43) and ≈0 for wheat.
- On a farmer's **real surveyed parcel**, the frozen forward NDVI forecaster **does not beat naïve persistence** in any season (Wilcoxon p=1.000); late-season skill is unstable.
- Cross-validated accuracy ≠ operational skill: temporal/forward validation and climatology baselines should be standard.

## Abstract
Satellite- and machine-learning-based crop-yield models are frequently reported with high
accuracy, but the cross-validation design behind those numbers often rewards spatial
interpolation rather than the temporal (forward-in-time) extrapolation an operational user needs.
We re-analyse, under a frozen recompute-faithful protocol, winter-wheat and oilseed-sunflower
yield models for 29 districts of Trakya (Türkiye), 2004–2025, built on climate (NASA POWER),
Sentinel-2 NDVI, and SoilGrids soil features. We contrast three cross-validation regimes —
leave-one-year-out (LOYO, temporal), leave-one-district-out (LOILO, spatial), and spatiotemporal
blocking — against climatology and persistence baselines, with bootstrap confidence intervals and
paired significance tests. Under temporal validation, no machine-learning configuration beats the
climatology baseline for winter wheat (best skill score −0.172, 95% CI [−0.238, −0.109]), whereas
a multimodal model does for sunflower (R²=0.386; skill score +0.224 [+0.167, +0.276]). We
quantify a large spatial-vs-temporal generalization gap that is significant across all crops,
feature tiers, and models (e.g. wheat climate-tier ΔR²=+0.639 [+0.545, +0.735]). A matched-sample
ablation shows that NDVI's marginal value is crop-specific and that a naïve comparison over-states
a wheat "harm". Re-validated forward on a farmer's **real surveyed parcel**, the frozen NDVI
forecaster does not beat a naïve persistence baseline in any season (Wilcoxon p=1.000). We conclude
that cross-validated accuracy is not operational skill, and recommend temporal/forward validation
with climatology/persistence baselines as standard practice for agricultural ML.

## 1. Introduction
Machine learning on satellite and reanalysis data is now routine for crop-yield prediction
`[VERIFY: vanklompenburg2020review]`, frequently reporting strong accuracy. However, the headline
metric depends critically on the cross-validation (CV) design: random k-fold or leave-one-location
splits let models exploit spatial structure shared between training and test, inflating apparent
skill relative to the temporal extrapolation operational forecasting actually requires
`[VERIFY: roberts2017crossval; ploton2020spatial; kattenborn2022spatial]`. Honest forward/temporal
validation remains comparatively under-reported `[VERIFY: needs citation]`.

This paper does not propose a new high-accuracy model. Its contribution is a careful, honest audit
of *which* generalization a model achieves, using two crops with contrasting phenology — winter
wheat (vernalization-requiring; grain-fill-sensitive) and oilseed sunflower — across one region.
We ask: (Q1) does ML beat simple climatology/persistence baselines under temporal validation?
(Q2) how large is the gap between spatial and temporal generalization? (Q3) what is the genuine,
sample-controlled marginal value of NDVI and soil? (Q4) how does forward NDVI forecasting behave
across phenological stages? The answers are mixed and crop-specific, and that nuance is the point.

## 2. Study area and data
**Region.** Trakya (Thrace), north-west Türkiye; spatial unit = district (ilçe), 29 districts
`[VERIFY: regional citation]`. **Target.** TÜİK official district yields in kg da⁻¹ (1 da =
1000 m²); panel of 1165 district-year records, 2004–2025 `[VERIFY: TÜİK citation]`.
**Predictors.** (i) Climate: NASA POWER/MERRA-2 seasonal aggregates (GDD, precipitation windows,
aridity, heat-stress, radiation; 14 features). (ii) NDVI: Sentinel-2 via Google Earth Engine
`[VERIFY: drusch2012; gorelick2017]`, district-aggregated, available 2017 onward (7 features).
(iii) Soil: ISRIC SoilGrids `[VERIFY: poggio2021]` (6 surface-horizon features). NDVI availability
restricts NDVI-bearing tiers to n=213 (wheat) / 209 (sunflower); the climate-only tier uses the
full panel (n=589 / 576). We define three feature tiers — A (climate), B (A+NDVI), C (A+NDVI+soil).
A separate forward-validation (FLOV) component validates site EVR_01 on its **real surveyed parcel
boundary** (four GPS-measured corners → a 0.62 ha field near Vize, centroid 41.531 N, 27.861 E);
Sentinel-2 and ERA5-Land are fetched live for this true geometry. (Four further pilot sites remain
at placeholder coordinates and are not part of the headline prospective analysis.)

## 3. Methods
**Cross-validation regimes** (scikit-learn `LeaveOneGroupOut`, out-of-fold predictions):
*LOYO* (groups = year) = temporal generalization / forecasting analogue; *LOILO* (groups =
district) = spatial generalization / interpolation analogue; *Spatiotemporal* = 5 year-blocks ×
5 KMeans lat/lon clusters. LOYO and LOILO share the same observations per tier, enabling paired tests.
**Models** (seed 42): PLS, ElasticNet, RandomForest, XGBoost, Gaussian-Process Regression (Matern
ν=2.5), and a stacking ensemble (Layer C). **Baselines:** B0 climatology (leave-one-year-out
per-district mean), B1 year-trend, B2 persistence, B3 climate-proxy; skill score SS = 1 −
RMSE/RMSE_B0. **Metrics:** R², RMSE, MAE, MAPE, bias.
**Uncertainty & tests.** 95% confidence intervals by observation (iid) bootstrap (5000 resamples,
seed 12345), with a group-cluster bootstrap (years for LOYO, districts for LOILO) as a sensitivity
analysis for panel non-independence. The spatial-vs-temporal gap is tested with a paired Wilcoxon
signed-rank test on per-observation absolute errors (LOYO vs LOILO), a matched-pairs rank-biserial
effect size, and a paired-bootstrap ΔR² interval. Baseline superiority uses a paired bootstrap of
the skill score and a paired Wilcoxon vs B0. A **matched-sample ablation** evaluates the
climate-only model on the NDVI-available subset to separate feature from sample effects. Residual
spatial autocorrelation is assessed with Moran's I (KNN k=4, 999 permutations) `[VERIFY: moran1950]`.
**Forward validation (FLOV).** A frozen 2017–2024 LSTM NDVI t+7 forecaster plus an XGBoost yield
head, hash-locked and never retrained, are run walk-forward on 2025/2026 data, scored per
phenological stage against observed NDVI and a naïve persistence baseline (one-sided Wilcoxon).
**Reproducibility.** All steps are deterministic; recomputed aggregate metrics matched the original
thesis tables on all 92 layer×crop×CV×model combinations to max |Δ| = 0.0 (`analysis/fidelity_check.csv`).

## 4. Results
**4.1 ML vs climatology under temporal validation (Q1).** For winter wheat, the LOYO champion is
the climatology baseline itself (R²=0.213); *no* ML configuration beats it — the best (Layer C
XGBoost) has skill score −0.172 [−0.238, −0.109] (paired Wilcoxon p=1.1×10⁻⁵), and all 16 ML
configurations are significantly worse than B0 (Fig. 2; Table 1). For sunflower, the multimodal
Layer C GPR reaches R²=0.386 with skill score +0.224 [+0.167, +0.276] (p=1.0×10⁻⁸); climate-only
models do not beat B0 (RandomForest SS=+0.009, ns).

**4.2 The spatial-vs-temporal generalization gap (Q2).** The same model generalizes markedly
better across space than time (Fig. 4). Paired ΔR²(LOILO−LOYO) for the climate tier is +0.639
[+0.545, +0.735] for wheat (Wilcoxon p=6.2×10⁻²⁶, rank-biserial +0.501) and +0.580 [+0.490, +0.674]
for sunflower (p=5.6×10⁻²⁸); the gap is large, significant, and positive in all six crop×tier cells
and across all individual models (Table; `generalization_gap_per_model.csv`).

**4.3 Marginal value of NDVI and soil (Q3).** A matched-sample ablation (Table 2) shows the wheat
"NDVI harm" implied by a naïve full-sample comparison (ΔR²=−0.444) is largely a sample-size
artifact (climate-only R² drops from −0.092 at n=589 to −0.575 at n=213); on matched samples, NDVI
adds only +0.039 for wheat but +0.431 for sunflower, while soil adds +0.224 (wheat) and +0.149
(sunflower). Under LOILO, NDVI/soil add almost nothing (ΔR²≈−0.018), indicating their information
lies in the temporal rather than spatial dimension.

**4.4 Forward NDVI forecasting fails to beat persistence on the real parcel (Q4).** Re-validated on
the farmer's real surveyed field (0.62 ha), the frozen NDVI t+7 forecaster does **not** beat a naïve
persistence baseline in any window: 2025 model R²=0.78 vs persistence R²=0.91 (median |error| 0.077
vs 0.032; one-sided Wilcoxon p=1.000), and the partial 2026 season is worse still (model R²=−1.32 vs
persistence R²=0.49; p=1.000) (Fig. 3b). Per-stage skill is unstable and degrades late season
(maturity R²=−13.7; absolute errors remain small, ≈0.05, so R² is dominated by the low NDVI variance
during senescence). The earlier placeholder coordinates were mildly optimistic (2026 model R²
0.70→−1.32), confirming the conclusion is not an artifact of approximate geometry.

**4.5 Spatial structure of errors.** Winter-wheat LOYO residuals exhibit significant positive
spatial autocorrelation (Moran's I=+0.257, p_norm=0.008), whereas sunflower residuals do not
(I=+0.117, p_norm=0.168) (Fig. 5), implying unmodelled geographic structure for wheat.

**4.6 What the models use.** Permutation importance (Fig. 6) shows climate-tier models are
GDD-dominated (wheat additionally weights vernalization days); the multimodal sunflower model is
dominated by flowering NDVI (0.587), the wheat model by grain-fill precipitation, soil organic
carbon, and flowering NDVI.

## 5. Discussion
The wheat result — a per-district climatological mean out-forecasting every ML model out-of-year —
is explained by a strong B0 (R²=0.213 captures stable district differences), by inter-annual wheat
yield being governed by grain-fill-period weather that is hard to anticipate `[VERIFY]`, and by
spatially autocorrelated residuals revealing geography the climate features miss. Sunflower differs:
B0 is weak (R²=0.033), flowering-window NDVI carries genuine signal, and the multimodal model
converts this into out-of-year skill. The dominant message is the generalization gap: spatial
(LOILO) and even spatiotemporal CV substantially over-state the temporal skill an operational
forecast needs; LOYO is the more honest proxy. This recontextualises optimistic accuracy reports in
the yield-ML literature `[VERIFY: roberts2017; ploton2020]`. The senescence collapse bounds the
operational value of NDVI-driven forecasting late in the season, when the canopy signal saturates
and decays `[VERIFY: phenology citation]`. Finally, agronomic interpretability (the wheat model
keys on sensible features) does not guarantee out-of-time validity — a caution for explainability-
as-validation. Temporal skill here is also *fragile*: with ~22 years, a year-cluster bootstrap of
even the best sunflower model spans [−0.145, +0.506].

## 6. Limitations
Single region; ~22 years → small-n LOYO and wide year-cluster CIs. NDVI tiers limited to 2017+;
the A-vs-B/C sample mismatch is mitigated but not eliminated by the matched ablation. The forward
(FLOV) component, although now run on **real surveyed coordinates** for EVR_01, rests on a single
small field (0.62 ha, near the Sentinel-2 sub-pixel limit), satellite-derived (not in-situ) NDVI
ground truth, and a partial 2026 season (EVR_02–05 remain at placeholder coordinates); its
conclusions are single-site and illustrative rather than regionally representative. District yields
are administrative
aggregates, not field measurements. iid bootstrap CIs are optimistic under panel correlation
(cluster CIs reported alongside). Climate inputs are MERRA-2 (NASA POWER); an ERA5-Land difference
is noted.

## 7. Conclusion
Honest cross-validation reframes the value proposition of satellite-driven yield ML: cross-validated
accuracy is not operational skill. In Trakya, ML adds genuine mid-season value for sunflower but not
for winter wheat, where climatology is the honest operational default; a large spatial-vs-temporal
generalization gap holds across crops and models; and forward NDVI forecasting fails during
senescence. We recommend temporal/forward validation and climatology/persistence baselines as
standard practice, and report all results under a frozen, fully reproducible protocol.

## Data availability
Derived metrics, per-sample out-of-fold predictions, and figure/table-generating code are in
`paper1_generalization/`. Underlying yields are TÜİK public statistics `[VERIFY]`; Sentinel-2,
ERA5/POWER, and SoilGrids are public `[VERIFY]`.

## Code availability
All analysis is reproduced by `paper1_generalization/repro/run_all.py` (Python 3.13; pinned
environment in `repro/requirements_full_venv.txt`).

## CRediT author statement
`[VERIFY: author roles]` — Melih Kalkan: conceptualization, methodology, software, analysis,
writing. `[VERIFY: advisor role]` Dr. Çavdaroğlu: supervision, review.

## Acknowledgements
Supported by TÜBİTAK 2209-A `[VERIFY: grant id]`. Advisor: Dr. Çavdaroğlu `[VERIFY: full name/affiliation]`.

## References
See `refs/references.bib` (skeleton; all entries `VERIFY`) and `refs/citation_todo.md`. No DOIs invented.
