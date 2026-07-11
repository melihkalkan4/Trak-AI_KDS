# Numbers Ledger — Paper 1

> Every reportable number → value → 95% CI (if any) → source artifact → producing
> script → manuscript claim it supports. **No number here is fabricated**; all trace
> to a fidelity-verified artifact (recompute vs published cp25: max |Δ| = 0.0).
> CI method: `iid` = observation bootstrap (5000, seed 12345); `cluster` = group
> (year/district) bootstrap. Crop: wheat=`bugday`, sunflower=`aycicegi`.

## A. Champions & baselines (LOYO)
| # | Quantity | Value | Source | Script | Claim |
|---|---|---|---|---|---|
|A1| Wheat champion = B0 climatology R²(LOYO) | **0.213**, RMSE 61.7, n=589 | `reports/cp25/12_master_comparison.csv`, `02_baselines.csv` | (published, recomputed) | Best wheat temporal predictor is climatology |
|A2| Sunflower champion = Layer C GPR R²(LOYO) | **0.386**, RMSE 42.3, SS +0.225, n=209 | `12_master_comparison.csv`, `07_layer_c_results.csv` | Sunflower multimodal beats climatology |
|A3| Wheat baselines R²: B0/B1/B2/B3 | 0.213 / 0.208 / −0.269 / 0.126 | `02_baselines.csv` | B0 is the strong wheat benchmark |
|A4| Sunflower baselines R²: B0/B1/B2/B3 | 0.033 / 0.001 / 0.210 / 0.087 | `02_baselines.csv` | B0 weak; persistence strongest naive |

## B. Baseline superiority (LOYO; paired bootstrap CI + Wilcoxon) — `analysis/baseline_superiority.csv`
| # | Quantity | Value | CI (iid) | Wilcoxon p | Verdict |
|---|---|---|---|---|---|
|B1| Wheat best ML SS vs B0 (LC xgboost) | **−0.172** | [−0.238, −0.109] | 1.1e−05 | **worse than B0** |
|B2| Wheat worst ML SS (LB pls) | −0.786 | [−0.906, −0.673] | 2.6e−24 | worse |
|B3| Wheat: # models beating B0 (CI>0) | **0 / 16** | — | — | No ML beats climatology |
|B4| Sunflower best ML SS (LC gpr) | **+0.224** | [+0.167, +0.276] | 1.0e−08 | **beats B0** |
|B5| Sunflower LC random_forest SS | +0.205 | [+0.141, +0.265] | 5.8e−09 | beats B0 |
|B6| Sunflower LC stacking SS | +0.197 | [+0.140, +0.250] | 1.2e−07 | beats B0 |
|B7| Sunflower Layer A best SS (rf) | +0.009 | [−0.031, +0.048] | 0.45 | ns (climate alone ≈ B0) |

## C. Generalization gap (paired, fixed = LOILO champion) — `analysis/generalization_gap.csv`
| # | Crop·Layer | model | R²_LOYO | R²_LOILO | ΔR² | ΔR² CI | Wilcoxon p | rank-biserial |
|---|---|---|---|---|---|---|---|---|
|C1| wheat·A | gpr | −0.198 | +0.441 | **+0.639** | [+0.545, +0.735] | 6.2e−26 | +0.501 |
|C2| wheat·B | gpr | −0.535 | +0.429 | +0.965 | [+0.765, +1.171] | 3.1e−13 | +0.576 |
|C3| wheat·C | xgboost | −0.311 | +0.427 | +0.738 | [+0.527, +0.968] | 3.1e−08 | +0.438 |
|C4| sunflower·A | xgboost | −0.076 | +0.504 | **+0.580** | [+0.490, +0.674] | 5.6e−28 | +0.527 |
|C5| sunflower·B | gpr | +0.214 | +0.450 | +0.236 | [+0.141, +0.326] | 2.6e−07 | +0.411 |
|C6| sunflower·C | gpr | +0.387 | +0.582 | +0.196 | [+0.118, +0.266] | 5.8e−05 | +0.321 |
- Descriptive best-per-regime gap (ΔR² LOILO−LOYO): wheat A +0.533, sunflower A +0.453 (matches thesis H5). Per-model consistency: `analysis/generalization_gap_per_model.csv` (gap positive for all 5–6 models).

## D. Bootstrap CIs, LOYO R² (headline rows) — `analysis/bootstrap_ci.csv`
| # | Crop·Layer·model | R² | iid CI | cluster (year) CI | Note |
|---|---|---|---|---|---|
|D1| sunflower·C·gpr | +0.387 | [+0.296, +0.459] | **[−0.145, +0.506]** | best model; cluster CI includes 0 → fragile temporal skill (few years) |
|D2| sunflower·C·rf | +0.357 | [+0.245, +0.446] | [−0.065, +0.442] | cluster includes 0 |
|D3| wheat·A·elastic_net | −0.092 | [−0.150, −0.039] | [−0.244, +0.007] | |
|D4| wheat·C·xgboost | −0.311 | [−0.522, −0.147] | [−1.270, +0.121] | |
- **Honest caveat:** iid CIs are optimistic (panel non-independence); year-cluster CIs are wide because only ~22 years anchor temporal generalization.

## E. Ablation, matched-sample (best model per tier) — `tables/T2_ablation.csv`
| # | Crop·CV | A_full | A_matched | B | C | ΔNDVI(matched) | Δsoil | naive ΔNDVI(full) |
|---|---|---|---|---|---|---|---|---|
|E1| wheat·LOYO | −0.092 (n589) | −0.575 (n213) | −0.535 | −0.311 | **+0.039** | +0.224 | −0.444 (sample artifact) |
|E2| wheat·LOILO | +0.441 | +0.448 | +0.429 | +0.427 | −0.018 | −0.003 | — |
|E3| sunflower·LOYO | +0.051 (n576) | −0.194 (n209) | +0.237 | +0.387 | **+0.431** | +0.149 | +0.186 |
|E4| sunflower·LOILO | +0.504 | +0.467 | +0.450 | +0.582 | −0.018 | +0.132 | — |
- Key: wheat's apparent "NDVI hurts" (naive −0.444) is mostly the n=589→213 sample change; matched NDVI effect is ≈0. Sunflower NDVI effect is genuinely large (+0.431).

## F. Prospective FLOV — REAL surveyed parcel (primary) — `analysis/prospective_overall_real.csv`, `tables/T3_per_stage_real.csv`, `analysis/prospective_real/real_coords_validation_summary.json`
Real field: 4 GPS corners → 0.62 ha near Vize (centroid 41.531 N, 27.861 E), ~3129 m²/≈31 px (10 m buffer). Live GEE+CDS; frozen LSTM inference.
| # | Window·source | n | model R² | persistence R² | median\|err\| m/p | Wilcoxon p | Verdict |
|---|---|---|---|---|---|---|---|
|F1| 2025 raw S2 | 210 | 0.775 | **0.899** | 0.069 / 0.042 | 1.000 | persistence beats model |
|F2| 2025 interp NDVI_int | 331 | 0.783 | **0.911** | 0.077 / 0.032 | 1.000 | persistence beats model |
|F3| 2026 raw S2 (partial) | 81 | −0.191 | **0.540** | 0.216 / 0.048 | 1.000 | persistence beats model |
|F4| 2026 interp (partial) | 132 | **−1.319** | 0.490 | 0.166 / 0.039 | 1.000 | persistence beats model |
|F5| 2025 per-stage (interp) | — | maturity **−13.7**, flowering −0.51, grain_fill +0.59, post_harvest +0.83 | — | — | — | late-season unstable; MAE small (~0.05); R² ill-posed at low-variance stages |

## F′. Placeholder-coords FLOV (retained for comparison only) — `analysis/prospective_overall.csv`, `tables/T3_per_stage.csv`
| # | Quantity | Value | Note |
|---|---|---|---|
|F′1| 2025 model / persistence R² | 0.865 / 0.963 | placeholder; persistence wins (Wilcoxon p=1.000) |
|F′2| 2025 per-stage flowering / grain_fill / maturity | 0.741 / −0.964 / −5.649 | placeholder per-stage |
|F′3| 2026 model / persistence R² | 0.703 / 0.749 | placeholder partial |
|F′4| placeholder vs real (2026 model R²) | 0.703 → **−1.319** | placeholder was optimistic; real site worse | `prospective_placeholder_vs_real.csv` |

## G. Spatial autocorrelation (Moran's I) — `analysis/morans_i.csv`
| # | Crop | I | E[I] | z | p_norm | p_sim | n | Reproduced |
|---|---|---|---|---|---|---|---|---|
|G1| wheat | **+0.2572** | −0.0357 | +2.64 | 0.0082 | ~0.004–0.011 | 29 | yes (Δ vs published 0.000) |
|G2| sunflower | +0.1173 | −0.0370 | +1.38 | 0.1679 | ~0.08 | 28 | yes (Δ 0.000) |
- Wheat residuals: significant positive spatial autocorrelation → missing geographic structure. Sunflower: not significant.

## H. Feature importance (permutation, top features) — `tables/T4_feature_importance.csv`
| # | Layer·crop | Top features (imp_mean) |
|---|---|---|
|H1| A·wheat | gdd_cum_season .274, vernalization_days .142, tp_flowering .112 |
|H2| A·sunflower | gdd_cum_season .296, tp_season_sum .196, aridity_index .107 |
|H3| C·wheat | tp_grain_fill .258, soc_0-5cm .242, ndvi_flowering .209 |
|H4| C·sunflower | ndvi_flowering .587, gdd_flowering .121, sand_0-5cm .087 |

## I. Dataset descriptors
| # | Quantity | Value | Source |
|---|---|---|---|
|I1| TÜİK panel | 1165 district-year rows, 29 districts, 2004–2025 | `02_baselines.md`, `tuik_ilce_yields_clean.csv` |
|I2| Climate-tier n | wheat 589 / sunflower 576 | `calibration_features_layerA.csv` |
|I3| NDVI-tier n | wheat 213 / sunflower 209 | `calibration_features_layer{B,C}.csv` |
|I4| Prospective site EVR_01 | **REAL surveyed parcel** (4 GPS corners, 0.62 ha, centroid 41.531 N/27.861 E) | user-supplied 2026-06-20; `real_coords_validation_summary.json` |
|I5| EVR_02–05 | still placeholder (not re-run) | `config.py` |

> **Unverified-by-this-analysis numbers:** none reported as results. Any figure in the
> manuscript not in this ledger must be added here or marked `[VERIFY]`.
