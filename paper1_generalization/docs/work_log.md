# Work Log — Paper 1 (chronological)

Each command/script + what it produced. Session date: 2026-06-20.

## Phase 0 — Inventory & setup
1. Searched repo (excl. venv) for all named artifacts → mapped prompt names to real paths.
   Found core CV pipeline `reports/cp25/` (01–13), models `models/cp25/`, methodology docs `docs/`.
2. Located **core input** `data/processed/master_feature_matrix_2017_2024.csv` + calibration
   feature matrices `calibration_features_layer{A,B,C}.csv` (1165/422/422 rows) + real district
   coords `data/external/tuik/ilce_coords.csv` → no STOP&ASK triggered.
3. Read result CSVs (`12_master_comparison`, `05/06/07_*_results`, `02_baselines`), champion
   metadata, loocv per-sample CSVs, layer scripts `src/cp25/05,06,07`, `11_spatial_diagnostics`,
   FLOV docs, prospective summaries → verified schemas, CV defs, model configs (SEED=42).
4. `git checkout -b paper1`; created `paper1_generalization/{analysis,figures,tables,manuscript,refs,repro,logs,docs}`.
5. Verified repo venv (Python 3.13.2; numpy 2.4.3, sklearn 1.8.0, xgboost 3.2.0, esda 2.9.0, …) →
   `pip freeze` → `repro/requirements_full_venv.txt` (257 pkgs).
6. Wrote `logs/artifact_manifest.md`, `logs/decisions.md`.

## Phase 1 — Analysis
7. `repro/repro_common.py` — faithful replication of cp25 Layer A/B/C model race (feature lists,
   model configs, imputation, `_cv_predict`, `_block_groups`) + vectorized bootstrap helpers +
   per-sample B0 climatology. Verified against source line-by-line.
8. `repro/01_regenerate_per_sample.py` → **per_sample_predictions.csv (30,557 rows)** for all
   layer×crop×cv×model; **FIDELITY GATE: 92/92 PASS, max |Δ| = 0.0** vs published tables;
   per-sample champion cross-check vs existing loocv CSVs **max|Δpred| = 0.00000000**.
   (Cosmetic cp1254 console crash on a Δ glyph after all files saved → fixed by PYTHONIOENCODING=utf-8.)
9. `repro/06_per_stage.py` → `T3_per_stage.csv`, `prospective_overall.csv` (senescence collapse;
   model loses to persistence).
10. `repro/07_feature_importance.py` → `T4_feature_importance.csv` (124 rows).
11. `repro/08_morans_i.py` → `morans_i.csv` — reproduced wheat I=0.2572 / sunflower I=0.1173
    (Δ vs published 0.000).
12. First run of `02_bootstrap_ci.py` was slow (per-call sklearn in 1.6M-iter loop) → stopped,
    **vectorized** all bootstraps (per-group sufficient statistics) in `repro_common.py`.
13. `repro/02_bootstrap_ci.py` (9 s) → `bootstrap_ci.csv` (770 rows; iid + cluster).
14. `repro/03_generalization_gap.py` → `generalization_gap.csv` (+ per_model + `gap_readme.md`):
    paired Wilcoxon + rank-biserial + paired-bootstrap ΔR² CI. All gaps large/significant.
15. `repro/04_baseline_superiority.py` → `baseline_superiority.csv`: wheat 0/16 beat B0 (all
    significantly worse); sunflower Layer C beats B0.
16. `repro/05_ablation.py` (4m24s, CV re-run) → `T2_ablation.csv`: matched-sample ΔNDVI wheat
    +0.039 vs naïve −0.444 (sample artifact); sunflower +0.431.

## Phase 2 — Figures
17. `repro/10_figures.py` → F1–F6 (PDF + PNG, 300 dpi). Visually verified F4 (gap) and F2 (skill).
    `figures/figure_manifest.md`.

## Phase 1/3 wrap — Tables
18. `repro/09_tables.py` → `T1_master_results.csv` (100 rows) + `tables/tables.md`.

## Phase 5 — Documentation
19. `docs/methods_as_implemented.md`, `docs/numbers_ledger.md`, `docs/results_narrative.md`,
    `docs/WRITING_DOSSIER.md`, `docs/work_log.md` (this file).

## Phase 4 — References
20. `refs/references.bib` (real anchor works only, every entry VERIFY, no invented DOIs) +
    `refs/citation_todo.md`.

## Phase 3 / 6 — Manuscript & repro/integrity (see those files)
21. `manuscript/paper1.md` (+ `.tex` skeleton); `repro/run_all.py`, `repro/README.md`;
    `logs/integrity_audit.md`, `logs/SUMMARY.md`.

## Phase 7 — Real-coordinate prospective unblock (user supplied GPS corners 2026-06-20)
22. Verified live access in-session: GEE service account (10 S2 scenes near field), CDS client OK,
    shapely available. Computed parcel geometry from 4 corners: 0.62 ha, centroid 41.531/27.861.
23. `repro/11_prospective_real_coords.py` — real-polygon FLOV re-run (isolation: redirected
    audit/log to my folder, save=False, monkeypatched geometry, site EVR01R, frozen inference only).
    Smoke test validated the chain; full run (17 ERA5 CDS months, ~background) exit 0.
24. `repro/12_update_prospective.py` → `T3_per_stage_real.csv`, `prospective_overall_real.csv`,
    `prospective_placeholder_vs_real.csv`, figure `F3b_per_stage_real`.
25. Result: model never beats persistence at real coords (2025 0.78 vs 0.91; 2026 −1.32 vs 0.49;
    Wilcoxon p=1.000) — finding robust, placeholder was mildly optimistic.
26. Updated docs (results_narrative F4, WRITING_DOSSIER, numbers_ledger F/I, methods §11),
    manuscript (abstract, highlights, §2, §4.4, §6, .tex), figure_manifest, integrity_audit,
    SUMMARY, decisions. Re-verified isolation via git (still only the 9 pre-existing tracked files).
