# Results Narrative — Paper 1

> Plain-language results, finding by finding, each with the number, its provenance,
> and an honest interpretation. Negative/null results are reported as contributions.
> The manuscript writer can lift these straight into Results/Discussion prose.

---

## Finding 1 — Under temporal generalization (LOYO), ML beats climatology for sunflower but NOT for wheat
**Numbers.** Wheat: the LOYO champion is the **B0 climatology baseline (R²=0.213)**; *no* ML
model (across 16 layer×model combinations) beats it — the best, Layer C XGBoost, has skill
score **SS = −0.172, 95% CI [−0.238, −0.109]** (paired Wilcoxon vs B0 p=1.1e−05), i.e.
*significantly worse* than climatology. Sunflower: the multimodal Layer C GPR reaches **R²=0.386**
and **SS = +0.224 [+0.167, +0.276]** vs B0 (p=1.0e−08), a real improvement; Layer C RandomForest
(+0.205) and Stacking (+0.197) also beat B0.
**Provenance.** `analysis/baseline_superiority.csv`; `reports/cp25/12_master_comparison.csv`.
**Honest reading.** The contribution of satellite/ML to *operational* (forward-in-time) yield
prediction is **crop-dependent**: positive and significant for sunflower, absent (indeed
negative) for winter wheat, where a per-district long-term mean is the better forecast.

## Finding 2 — A large spatial-vs-temporal generalization gap (the central result)
**Numbers.** The same model generalizes far better across *space* (held-out district, LOILO)
than across *time* (held-out year, LOYO). Paired, on identical observations:
- Wheat, climate tier: R²_LOYO=−0.198 → R²_LOILO=+0.441, **ΔR²=+0.639 [+0.545, +0.735]**,
  Wilcoxon p=6.2e−26, rank-biserial +0.501.
- Sunflower, climate tier: ΔR²=**+0.580 [+0.490, +0.674]**, p=5.6e−28.
- The gap is large and significant in **all six** crop×tier combinations and **all** models
  (`generalization_gap_per_model.csv`).
**Provenance.** `analysis/generalization_gap.csv`; figure **F4**.
**Honest reading.** High cross-validation scores under random or leave-one-location-out splits
do **not** imply operational skill. The models interpolate district-level structure well but
fail to anticipate the year-to-year climate variability that actually drives yield anomalies.
Reporting LOILO/spatial CV alone would have over-stated real-world usefulness — this gap is the
paper's cautionary core.

## Finding 3 — NDVI's value is crop-specific, and a naïve ablation over-states a wheat "harm"
**Numbers (matched-sample, LOYO).** Comparing tiers on the *same* NDVI-available rows:
- Wheat: A_matched=−0.575 → B=−0.535, **ΔNDVI=+0.039** (NDVI adds essentially nothing);
  soil adds Δ=+0.224 (B→C), but the model stays negative (C=−0.311).
- Sunflower: A_matched=−0.194 → B=+0.237, **ΔNDVI=+0.431** (large genuine gain); soil adds +0.149.
- The naïve full-sample comparison would report wheat ΔNDVI = **−0.444** ("NDVI hurts"), but
  that is mostly the sample change (n=589→213): A_full=−0.092 vs A_matched=−0.575.
**Provenance.** `tables/T2_ablation.csv`.
**Honest reading.** Proper, matched-sample ablation corrects a misleading conclusion: NDVI does
not "damage" the wheat model — it simply adds little, while the post-2017 NDVI-era subset is
intrinsically harder. For sunflower, flowering-window NDVI is a substantial, real predictor.
Under LOILO, NDVI/soil add almost nothing (ΔNDVI≈−0.018) — their information is in the temporal,
not the spatial, dimension.

## Finding 4 — On the REAL parcel, the frozen NDVI forecaster does not beat persistence; late-season skill is unstable (FLOV)
**Setting.** Re-run on the farmer's **real surveyed parcel** (4 GPS corners → 0.62 ha field near
Vize, centroid 41.531 N, 27.861 E; ~3129 m²/≈31 S2 pixels used after a 10 m inward buffer;
small-field/subpixel-flagged). Live Sentinel-2 (GEE) + ERA5 (CDS); frozen LSTM (hash
`43ef61b5…`) inference only.
**Robust numbers (the headline).** The frozen NDVI t+7 model does **not** beat naïve persistence
at the real field — in every window and actual-source:
- 2025 (raw S2 actuals): model R²=0.775 vs persistence R²=0.899; median |err| 0.069 vs 0.042; one-sided Wilcoxon p=1.000.
- 2025 (interpolated NDVI_int): model R²=0.783 vs persistence R²=0.911; p=1.000.
- 2026 (partial season, raw S2): model R²=−0.191 vs persistence R²=0.540; p=1.000.
- 2026 (interpolated): model R²=−1.319 vs persistence R²=0.490; p=1.000.
**Per-stage (2025, interpolated).** vegetative 0.578, grain_fill 0.590, post_harvest 0.834, but
flowering −0.51, **maturity −13.7**, emergence −31.7 (near-zero NDVI variance early/late inflates
negative R²; stage MAE stays small, ~0.05). Late-season instability/collapse persists; the
well-posed statement is the overall persistence comparison.
**Placeholder vs real.** The earlier placeholder coordinates were mildly *optimistic*: 2025 model
0.865→0.783, persistence 0.963→0.911; and 2026 model 0.703→**−1.319** — the placeholder masked how
poorly the model performs at the true location, especially in 2026. The qualitative conclusion
(persistence > model) is unchanged and, if anything, stronger at the real parcel.
**Provenance.** `tables/T3_per_stage_real.csv`, `analysis/prospective_overall_real.csv`,
`analysis/prospective_placeholder_vs_real.csv`, `analysis/prospective_real/real_coords_validation_summary.json`;
figure **F3b** (real) / **F3** (placeholder, retained for comparison).
**Honest reading.** Even with real surveyed coordinates, the operational NDVI forecaster adds no
value over "tomorrow ≈ today": persistence wins on R² and median error in all windows. The model's
absolute errors stay small but it captures no exploitable forward dynamics, and late-season R²/MAPE
are ill-behaved because NDVI is near-flat then. This bounds the operational value of NDVI-driven
forecasting and shows the finding is not an artifact of placeholder geometry.
**Residual caveats.** Single small field (0.62 ha, subpixel-noisy); 2026 season partial; ground
truth is satellite-derived (raw S2 + interpolated), not in-situ/expert-measured.

## Finding 5 — Wheat residuals are spatially autocorrelated; sunflower's are not
**Numbers.** Moran's I on Layer A LOYO residuals (KNN k=4): wheat **I=+0.257** (E[I]=−0.036,
z=+2.64, p_norm=0.008) — significant positive spatial autocorrelation; sunflower I=+0.117
(p_norm=0.168) — not significant. Reproduced exactly (Δ vs published I = 0.000).
**Provenance.** `analysis/morans_i.csv`; figure **F5**.
**Honest reading.** For wheat, neighbouring districts share residual patterns → unmodelled
geographic structure (micro-climate, soil, management) that climate features miss; this is
consistent with wheat's poor temporal skill. Sunflower residuals are spatially unstructured.

## Finding 6 — What the models key on (interpretability)
**Numbers.** Permutation importance: climate tier is **GDD-dominated** (wheat also
vernalization_days — agronomically expected for winter wheat). Multimodal tier: sunflower is
dominated by **ndvi_flowering (0.587)**; wheat by **tp_grain_fill (0.258), soil organic carbon
(0.242), ndvi_flowering (0.209)**.
**Provenance.** `tables/T4_feature_importance.csv`; figure **F6**.
**Honest reading.** The model "agrees with agronomy" (flowering canopy for sunflower; grain-fill
water for wheat), yet this agronomic plausibility does **not** translate into temporal skill for
wheat — a useful reminder that interpretability ≠ predictive validity out-of-time.

## Finding 7 — Spatiotemporal block CV sits between LOYO and LOILO
**Numbers.** Best R² (Spatiotemporal): wheat A 0.321 / C 0.480; sunflower A 0.387 / C 0.556 —
intermediate between the optimistic LOILO and the pessimistic LOYO.
**Provenance.** `tables/T1_master_results.csv` (cv=Spatiotemporal).
**Honest reading.** As expected, partial space–time blocking is harder than pure spatial
interpolation but easier than pure temporal extrapolation; LOYO remains the most honest proxy for
operational forecasting.

---

## Cross-cutting honesty notes
- **Few years anchor temporal skill.** Year-cluster bootstrap widens LOYO R² CIs dramatically;
  even sunflower's best model (R²=0.387) has a year-cluster CI of [−0.145, +0.506] — temporal
  skill is real on point estimate but fragile given ~22 years. (`bootstrap_ci.csv`, method=cluster.)
- **iid CIs are optimistic** under the district-year panel; both iid and cluster are reported.
- **District (ilçe) vs province (il).** An earlier province-level calibration gave a higher
  sunflower LOYO R² (0.646) but on n≈21–24; the district-level analysis (n=576) used here is more
  granular, larger, and harder — the honest choice. (`12_master_comparison.csv`, H1.)
- **Frozen / no leakage.** All CV predictions are out-of-fold; the prospective FLOV model is
  hash-locked and never retrained; the retrospective reproduction matched published numbers to 0.0.
