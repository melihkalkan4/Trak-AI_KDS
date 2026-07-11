# Referee revisions ([P]) — analysis artefacts

Self-contained package that resolves the rerun-requiring referee items (#1–#15) for
*"Spatial skill is not temporal skill"*. **Produces analysis artefacts only; the `.docx` is
untouched.** Start with **`HANDOFF.md`** (what changed + text edits for the [D] step) and
**`CHANGES_vs_old.md`** (reproduction).

## Reproduce
```bash
# from repo root, pinned venv (../repro/requirements_full_venv.txt)
venv/Scripts/python.exe paper1_generalization/revisions/code/run_all_revisions.py
```
Run order R01→R12 (each imports `code/rev_common.py` → `../repro/repro_common.py`, the
fidelity-verified cp25 pipeline). Seeds: models 42, bootstrap 12345. Offline (live real-coords
FLOV is upstream in `../repro/11_prospective_real_coords.py`).

## Contents
- `INPUTS_FOUND.md` — verified inputs + reuse map.
- `master_ledger.csv` / `master_ledger_summary.csv` — matched-baseline ledger (#1/#2/#15) + iid & clustered SS CIs.
- `rolling_origin_results.csv` / `_summary.csv` — forward-in-time eval (#3).
- `hyperparameter_protocol.csv` — fixed/leak-free tuning (#4).
- `clustered_inference.csv` / `iid_inference_supplementary.csv` — cluster-aware tests (#5/#6).
- `ablation_matched_by_algorithm.csv` — per-algorithm NDVI/soil ΔR² (#10).
- `staged_forecast_results.csv` — issuance-time tiers (#7).
- `parcel_per_stage.csv` (+ reconciliation .txt) — single authoritative per-stage (#9).
- `morans_i_sensitivity.csv` — global Moran's I, k=3–6 (#12).
- `permutation_importance_foldwise.csv` — fold-wise importance, increase in RMSE (#13).
- `spatiotemporal_blocks.csv` (+ scenario .txt) — Scenario A naming (#11).
- `tables/table2..6, table_rolling_origin, table_staged_forecast` (#15).
- `figures/fig1..fig7` + `figure_captions_EN.md` (#14).
- `methods_snippets_EN.md`, `ndvi_extraction_methods_EN.md` — paste-ready English methods (#8).
- `CHANGES_vs_old.md`, `HANDOFF.md`.

## Integrity
No fabricated values/DOIs; every number traces to a CSV produced by code. Reproduction of published
metrics: max |Δ| = 0.000497 (3-dp rounding floor), 0 cells beyond rounding. Matched samples
throughout; cluster-aware inference primary. Outstanding items left as visible `# TODO` /
limitation (crop-specific NDVI mask; strict Scenario B; 4-year NDVI rolling-origin).
