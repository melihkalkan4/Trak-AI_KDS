# DATA BUNDLE — all data we worked with (consolidated by copy)

Self-contained copy of every dataset used and produced across this work. **Copies only — every
original file is untouched** (read-only sources copied here for convenience; rollback = delete
`enrichment_v2/`). Rebuild/refresh with `enrichment_v2/code/make_data_bundle.sh` (idempotent).
The bulky raw GEE API cache (`data/cache/api/`, multi-GB binary) is intentionally EXCLUDED.

Size ≈ 49 MB · ~285 files.

## 01_inputs_used/ — read-only source data the analysis consumed
- `tuik/` — TÜİK district yields (`tuik_ilce_yields_clean.csv`, **`tuik_ilce_yields_full_referans.csv`**
  = comprehensive: verim_kg_da + uretim_ton, 2004–2025, Edirne/Kırklareli/Tekirdağ + İstanbul-Thrace),
  `ilce_coords.csv`, yield stats/trends.
- `calibration/` — `calibration_features_layer{A,B,C}.csv` (model inputs), holdout/train splits,
  `master_feature_matrix_2017_2024.csv`, `soil_ilce.csv`.
- `climate_daily_nasapower/` — 29 districts' daily NASA POWER (2004–2025) — basis of the LSTM monthly sequences.
- `yield/` — derived yield matrices.
- `admin_shapefiles/` — Türkiye admin boundaries (adm0/1/2 + line) from the user-provided zip.
- `cp25_published_results/` — the thesis/Paper-1 published CSVs we reproduced & compared to
  (master_comparison, baselines, layer_a/b/c results, loocv predictions, per-stage, perm importance).
- `prospective_parcel/` — EVR_01 prospective FLOV artifacts.
- `advisor_todo/` — advisor's to-do (PDF + extracted text).

## 02_outputs_enrichment_v2/ — what we produced (RS enrichment + advisor to-do)
- `outputs/` — district cropland geometries; multi-index distribution metrics (T2); soil+AWC (T3);
  topography (T4); anomalies (T5); tiers A–D (T6); selection (T7); CV ledgers/gap/ablation/rolling (T8);
  crop-specific masked indices + crop-area validation (advisor p2); advisor tiers + per-crop RS lists
  (p3/p4); LSTM yield results (p6); two-plains test (p7); result tables.
- `REPORT.md`, `ADVISOR_REPORT.md`, `PLAN.md`, `README.md`, `POST_RESTART_VERIFICATION.txt`,
  `checksums_before.txt`, `checksums_after.txt`.

## 03_outputs_paper1/ — Paper-1 + referee-revision deliverables
- `analysis/`, `tables/`, `figures/`, `docs/` (WRITING_DOSSIER etc.), `manuscript/`, `refs/`,
  `revisions/` (the [P] referee-revision artifacts), `logs/`.

## Notes
- Crop labels: `bugday` = winter wheat, `aycicegi`/`aycicegi_yaglik` = oilseed sunflower.
- The LSTM yield outputs (`lstm_yield_*.csv`) are added by re-running `make_data_bundle.sh` once the
  p6 job completes (it was still running when this bundle was first built).
- Integrity: no original artifact was modified to build this bundle (pure copy).
