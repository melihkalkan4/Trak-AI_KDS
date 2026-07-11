# Integrity Audit — Paper 1

Audit date (UTC): 2026-06-20. Branch: `paper1`.

## 1. Isolation & non-modification (VERIFIED via git)
- All 57 produced files live under `paper1_generalization/` only.
- `git diff --name-only HEAD` lists 9 modified tracked files
  (`data/trakai.db`, `logs/api_audit.jsonl`, `logs/flov.log`, `logs/model_integrity.jsonl`,
  `logs/visual_consensus.jsonl`, `logs/visual_consensus_alerts.jsonl`,
  `reports/prospective/EVR_01_2026_validation_summary.json`, `src/cp4_rag/config.py`,
  `src/cp4_rag/llm_engine.py`) — **all pre-existed in the session-start snapshot; none were
  modified by this work.** My scripts write exclusively to `paper1_generalization/`.
- **No model retrained.** The frozen prospective LSTM+XGB (hash-locked in
  `logs/model_integrity.jsonl`) was never loaded for fitting. The cp25 CV pipeline was
  *replicated for inference only* (`repro/repro_common.py`), not its artifacts overwritten.
- **Real-coordinate prospective re-run (Phase 7) respected isolation (re-verified via git):**
  after running `repro/11_prospective_real_coords.py`, `git diff --name-only HEAD` still shows only
  the SAME 9 pre-existing tracked files (no new tracked-file modification). Audit went to
  `analysis/prospective_real/api_audit_real.jsonl` (26 records) — `logs/api_audit.jsonl`/`flov.log`
  untouched (redirect worked; `configure_logging()` not called). `build_unified_features(save=False)`
  + site id `EVR01R` ⇒ no EVR01R file in `data/prospective/`. `geometry.site_polygon_coords`
  monkeypatched at runtime (no source edit). Frozen LSTM loaded with integrity hash `43ef61b5…`,
  inference only (NOT retrained). API cache (`data/cache/api/`, UNTRACKED) received additive entries
  for the real location — acceptable (not a tracked-file change).
- **No synthetic/mock data** entered any reported number (cf. `docs/MOCK_DATA_AUDIT.md`: the core
  climatology/CV pipeline is built from the real 2017–2024 master CSV). The prospective *site
  coordinates*, previously placeholder, are now the user's **real surveyed GPS corners** for EVR_01;
  all real-coords numbers come only from the actual live re-run.

## 2. Reproduction fidelity (the anti-fabrication guarantee)
- `analysis/fidelity_check.csv`: **92/92** layer×crop×CV×model checks PASS, **global max |Δ| = 0.0**
  on R²/RMSE/MAE/MAPE/bias/SS vs published `reports/cp25/05,06,07_*_results.csv`.
- Per-sample champion predictions vs existing `*_loocv_predictions_*.csv`: **max |Δ| = 0.00000000**.
- ⇒ Regenerated LOILO/Spatiotemporal per-sample predictions (the only previously-unavailable
  inputs) are equally faithful. The fidelity gate halts and reports rather than emit any number if
  reproduction ever drifts.

## 3. Number → table/figure → source → computation (every reported quantity)
| Manuscript number | Where | Source artifact | Computation |
|---|---|---|---|
| Wheat champion R²=0.213 (B0) | §4.1, T1, Abstract | `12_master_comparison.csv`, `02_baselines.csv` | published, recomputed (Δ=0) |
| Sunflower R²=0.386, SS+0.224 [.167,.276] | §4.1, T1, F2 | `07_layer_c_results.csv`, `baseline_superiority.csv` | recompute + paired bootstrap 5000/seed12345 |
| Wheat best ML SS −0.172 [−.238,−.109], p=1.1e−5 | §4.1, F2 | `baseline_superiority.csv` | paired bootstrap + paired Wilcoxon |
| 0/16 wheat ML beat B0 | §4.1, Abstract | `baseline_superiority.csv` | CI-lower>0 test |
| Gap wheat-A ΔR²+0.639 [.545,.735], p=6.2e−26, rbc+0.501 | §4.2, F4 | `generalization_gap.csv` | paired Wilcoxon + rank-biserial + paired-bootstrap ΔR² |
| Gap sunflower-A ΔR²+0.580 [.490,.674] | §4.2, F4 | `generalization_gap.csv` | same |
| Matched ΔNDVI wheat +0.039 / sunflower +0.431 | §4.3, T2 | `T2_ablation.csv` | CV re-run on matched NDVI subset |
| Naïve ΔNDVI wheat −0.444 (artifact) | §4.3 | `T2_ablation.csv` (A_full vs B) | descriptive |
| REAL parcel FLOV 2025: model R²=0.78 vs persistence 0.91, Wilcoxon p=1.000 | §4.4, F3b | `prospective_overall_real.csv`, `real_coords_validation_summary.json` | live GEE+CDS re-run (frozen inference) |
| REAL parcel FLOV 2026 (partial): model R²=−1.32 vs persistence 0.49, p=1.000 | §4.4 | `prospective_overall_real.csv` | live re-run |
| REAL parcel per-stage 2025: maturity R²=−13.7 (late-season unstable) | §4.4, T3b, F3b | `T3_per_stage_real.csv` | live re-run |
| Placeholder-vs-real (2026 model R² 0.703→−1.32) | §4.4 | `prospective_placeholder_vs_real.csv` | comparison |
| Moran's I wheat +0.257 (p_norm .008) / sunflower +0.117 (.168) | §4.5, F5 | `morans_i.csv` | esda Moran, KNN k=4, 999 perm; reproduced Δ=0 |
| Importances (gdd_cum, ndvi_flowering 0.587, …) | §4.6, T4, F6 | `T4_feature_importance.csv` (perm-importance CSVs) | consolidated |
| Year-cluster CI sunflower [−.145,+.506] | §5 | `bootstrap_ci.csv` (method=cluster) | group bootstrap |
| Spatiotemporal best R² (wheat C .480, sunflower C .556) | §4.7 | `T1_master_results.csv` | recompute (Δ=0) |
| Dataset n (1165; 589/576; 213/209) | §2 | `02_baselines.md`, calibration CSVs | counts |

**Untraceable numbers in the manuscript: NONE.** Every figure traces to a row above /
`docs/numbers_ledger.md`.

## 4. [VERIFY] citation flags (must be resolved by a human; nothing invented)
- All `references.bib` entries carry `note={VERIFY ...}`; DOIs/volumes must be confirmed.
- Manuscript `[VERIFY]` points (consolidated in `refs/citation_todo.md`): random-CV-optimism,
  NDVI-senescence saturation, wheat grain-fill/vernalization agronomy, sunflower flowering NDVI,
  TÜİK data citation, Trakya regional citation, persistence/climatology benchmark, data-source and
  method citations (Sentinel-2/GEE/ERA5/SoilGrids/RF/XGBoost/GPR/SHAP/Moran/Wilcoxon), author
  roles, grant id, advisor full name.

## 5. Point-estimate-only vs CI'd (honesty on uncertainty)
- **With 95% CI:** baseline skill scores, ΔR² gap, LOYO/LOILO R²/RMSE/MAE/MAPE/bias (iid+cluster).
- **Point estimate only (no CI computed):** per-stage FLOV R² (single site/season; n small per
  stage), Moran's I (analytic p reported, no bootstrap CI on I), Spatiotemporal best-R² summary,
  ablation tier R² (CV re-run point values; ΔR² gap CIs are in `generalization_gap.csv`).

## 6. Confirmations
- [x] No fabricated data, metrics, predictions, p-values.
- [x] No invented citations/DOIs.
- [x] No original file modified; outputs only in `paper1_generalization/`.
- [x] Frozen prospective model not retrained/altered.
- [x] Reproduction fidelity proven (max |Δ| = 0.0).
