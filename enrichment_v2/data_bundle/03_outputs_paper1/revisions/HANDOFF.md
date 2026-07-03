# HANDOFF — referee revisions ([P]) → document step ([D])

> Consume this + `CHANGES_vs_old.md`. All artefacts under `paper1_generalization/revisions/`
> (analysis CSVs at root; `tables/`, `figures/`, `code/`). No `.docx` was touched. Every number
> lives in a CSV — read from there, never hand-type. Reproduction of published metrics: model
> RMSE/R² max |Δ| = 0.000497 (3-dp rounding floor; raw recompute identical), SS likewise; 0 cells
> beyond rounding (`CHANGES_vs_old.md`).

## 1. Referee items resolved (with the artefact that answers each)
| # | Item | Resolution / artefact | Key result |
|---|---|---|---|
| 1,2,15 | matched baseline reported | `master_ledger_summary.csv`, `tables/table2_temporal_performance.csv` | wheat tier B/C matched B0 RMSE = **68.975** (not 61.7); sunflower B/C = **54.571** (not 50.0); SS unchanged, now reproducible |
| 3 | rolling-origin forward eval | `rolling_origin_results.csv`, `tables/table_rolling_origin.csv` | wheat forward mean SS<0 at all tiers; sunflower tier C forward mean SS +0.04…+0.13 (4 test yrs → caution) |
| 4 | nested/leak-free tuning | `hyperparameter_protocol.csv` | hyperparameters fixed & pre-specified; no test-set tuning; stacking OOF cv=3 |
| 5,6 | cluster-aware inference | `clustered_inference.csv`, `iid_inference_supplementary.csv`, SS clustered CIs in summary | sunflower tier C GPR SS +0.225, **year-clustered CI [+0.021,+0.353]** (>0); most other sunflower configs' clustered CI **include zero** — reported, not hidden |
| 7 | forecast issuance tiers | `staged_forecast_results.csv`, `tables/table_staged_forecast.csv` | sunflower skill emerges at **flowering** (SS +0.24) and plateaus; wheat negative at every stage |
| 8 | Sentinel-2/crop-mask methods | `ndvi_extraction_methods_EN.md` | **generic ESA WorldCover cropland mask, NOT crop-specific** → wheat/sunflower pixels not separated (limitation) |
| 9 | parcel + per-stage Fig 5 | `parcel_per_stage.csv`, `parcel_per_stage_reconciliation.txt`, `tables/table5_parcel.csv`, `figures/fig5_*` | single authoritative real-parcel table with model + persistence per stage; manuscript's −0.51/+0.59/−13.7 = real-coords 2025 (interp), the +0.74/−0.96/−5.65 = placeholder run |
| 10 | per-algorithm ablation | `ablation_matched_by_algorithm.csv`, `tables/table4_ablation.csv` | NDVI ΔR² mean across algos: sunflower LOYO **+0.38**, wheat LOYO **≈0** |
| 11 | spatiotemporal scheme | `spatiotemporal_blocks.csv`, `spatiotemporal_scenario.txt` | it is **Scenario A = spatiotemporal block interpolation** (cell holdout), not strict extrapolation → rename in text |
| 12 | global Moran's I + k | `morans_i_sensitivity.csv`, `figures/fig6_*` | wheat I≈0.21–0.26 (p<0.05 for k=3–6); sunflower n.s.; labelled **global** |
| 13 | fold-wise importance | `permutation_importance_foldwise.csv`, `tables/table6_importance.csv`, `figures/fig7_*` | metric = **increase in RMSE**, test-fold, mean±CI; sunflower C→ndvi_flowering, wheat C→soil organic carbon |
| 14 | figures regenerated | `figures/fig1..fig7_*.png` + `figure_captions_EN.md` | Tier A/B/C labels, 4-panel pred-vs-actual, split gap figs, global Moran's I, model+persistence per stage |

## 2. Text edits the [D] step must make (English; British orthography)
- **"operational"/"forecasting" → qualified.** End-of-season, full-feature results are **yield
  estimation**, not forecasting (all season variables used). Reserve **"forecasting"** for the
  rolling-origin and staged-issuance results. Use "yield estimation" for the main LOYO/LOILO tables.
- **Operational/forward claims** must cite the **rolling-origin** results (`table_rolling_origin.csv`),
  NOT LOYO. Describe LOYO as "retrospective held-out-year generalization".
- **Spatiotemporal** regime → rename "spatiotemporal block interpolation (Scenario A)" everywhere.
- **Moran's I** → always "global Moran's I"; cite k-sensitivity.
- **Table 2** → show the tier-specific matched baseline RMSE column; report year-clustered SS CI as
  primary (iid in Supplementary).
- **Sunflower skill** → state that under year-clustered resampling only the tier-C GPR/RF intervals
  exclude zero; most configurations' intervals include zero (substantial across-year uncertainty).
- **Importance axis** → "increase in RMSE"; importance = predictive contribution, not causation.
- **NDVI methods** → state the generic (non-crop-specific) cropland mask explicitly as a limitation.

## 3. Forecasting vs estimation — decision
The end-of-season multimodal model uses full-season variables (flowering/grain-fill NDVI, season
precipitation) that are unavailable before harvest → it is **estimation**, not a forecast. Genuine
pre-harvest **forecast** skill is quantified separately (rolling-origin #3; staged issuance #7):
sunflower acquires useful forecast skill from flowering onward; winter wheat does not at any stage.

## 4. Headline narrative (unchanged in spirit, strengthened)
- Winter wheat: no ML configuration beats matched climatology under LOYO **or** forward-in-time
  (rolling-origin); NDVI adds ≈0 (per-algorithm ablation); residuals spatially autocorrelated.
- Sunflower: multimodal (tier C) beats climatology (year-clustered CI excludes zero for GPR/RF) and
  shows modest **forward** skill from flowering; NDVI contribution is real and large (ΔR²≈+0.38).
- Spatial≫temporal generalization gap persists (same-model, significant).

## 5. Remaining TODO / [PLACEHOLDER] (nothing fabricated)
- `# TODO` crop-specific NDVI re-extraction (#8): requires an external wheat/sunflower crop-type map
  for 2004–2025; none available → **limitation + future work** (generic cropland mask used).
- `# TODO` Scenario B (strict spatiotemporal extrapolation, #11): optional stricter variant; not run
  to avoid changing the published metric definition — available on request (code in `R08`).
- NDVI-tier rolling-origin (#3) has only **4 test years** (2017+ panel) → interpret with caution
  (flagged in `rolling_origin_notes.txt`).
- All `[VERIFY]` citations remain for the human (see `../refs/citation_todo.md`); no DOI invented.

## 6. Run order (reproduce everything)
`code/R01 → R02 → R03 → R04 → R05 → R06 → R07 → R08 → R09 → R10 → R11 → R12`
(import `rev_common.py`, which imports the fidelity-verified `../repro/repro_common.py`). Pinned env:
`../repro/requirements_full_venv.txt`. Seeds: models 42, bootstrap 12345.
