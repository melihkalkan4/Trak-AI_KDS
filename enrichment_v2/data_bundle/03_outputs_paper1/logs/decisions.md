# Decisions Log — Paper 1

Chronological record of every decision/assumption, with rationale. Append-only.

---

### 2026-06-20 — Phase 0

**D-01 · Isolation.** No `papers/` dir exists → created `paper1_generalization/` at repo
root with subdirs analysis/figures/tables/manuscript/refs/repro/logs/docs. Created git
branch `paper1` off `main`. All outputs go ONLY inside `paper1_generalization/`. No tracked
file outside this folder will be modified. (Pre-existing uncommitted changes in working tree —
data/trakai.db, logs/*.jsonl, src/cp4_rag/* — predate this task and are left untouched; not
committed.)

**D-02 · Environment = existing repo venv (not a fresh one).** Rationale: the master prompt
asks for an isolated venv "so as not to pollute global." The repo's own `venv/` (Python 3.13.2)
is already isolated from global Python AND contains the **exact package versions that produced
the original results** (numpy 2.4.3, sklearn 1.8.0, xgboost 3.2.0, …). A fresh venv could pull
different versions and break bit-for-bit reproduction of the published metrics (GPR/XGBoost are
version-sensitive). Reproduction fidelity > a redundant second venv. I will NOT install new
packages (all needed ones present). Versions frozen to `repro/requirements_full_venv.txt`.

**D-03 · "Recompute-or-report" hierarchy adopted.** For every number: (1) recompute from
per-sample artifacts if available; (2) else regenerate per-sample via deterministic inference
re-run of the EXISTING pipeline (no retrain); (3) else report point estimate only and mark
"CI not computable". No fabricated/placeholder numbers ever.

**D-04 · LOILO / Spatiotemporal per-sample predictions via deterministic inference re-run.**
Only LOYO per-sample predictions are persisted on disk. To run the formal generalization-gap
test (paired LOYO-vs-LOILO) and bootstrap LOILO CIs, per-sample LOILO/Spatiotemporal
predictions are needed. The original scripts (`src/cp25/05,06,07`) compute these out-of-fold
predictions internally (deterministic, SEED=42) but discard all but LOYO. Decision: in a script
**inside my folder**, import the original modules' helper functions (`_make_model`, `_cv_predict`,
feature lists, imputation) WITHOUT calling their `main()` (so nothing writes to the original
locations), and regenerate the discarded per-sample predictions. This is squarely the
"deterministic inference re-run to obtain per-sample predictions" the prompt explicitly permits;
it is NOT retraining (identical features, hyperparameters, seed). **Fidelity gate:** my
recomputed aggregate metrics MUST match the published `05/06/07_*_results.csv` to ≥3 decimals,
else I stop and report. This faithfulness is verifiable precisely because the pipeline is
deterministic.

**D-05 · Frozen-model rule scope.** The "frozen champion" protected by the FLOV contract is the
**prospective LSTM+XGBoost artifact** (hash-locked in `logs/model_integrity.jsonl`), validated
forward on 2025/2026. I do not touch it. The cp25 CV evaluation re-runs (D-04) concern the
retrospective generalization study and reproduce an evaluation, not the frozen prospective
artifact. Precedent: the thesis itself re-ran per-fold fits for the existing LOILO MAPE bootstrap
(`reports/cp25/13_*`, "07_layer_c_full.py birebir", seed=42).

**D-06 · Bootstrap CIs primarily from existing LOYO per-sample predictions.** Cleanest, touches
no model. 5000 resamples, fixed seed (12345). Paired bootstrap used for ΔR² gap CIs (resample
observations, recompute both LOYO and LOILO metrics on the same resample).

**D-07 · Matched-sample ablation.** Naive Layer A→B comparison conflates feature change with
sample change (A n=589 vs B n=213). For an honest NDVI marginal-value test I will additionally
evaluate climate-only models on the NDVI-available subset (the Layer B/C rows), giving a
matched-n A vs B vs C ablation. Deterministic inference re-run on existing data; no retrain.

**D-08 · Coordinates.** Core LOYO/LOILO/Spatiotemporal + Moran's I use the REAL
`data/external/tuik/ilce_coords.csv` (29 districts). The 5 EVR prospective sites use
placeholder/approximate coordinates (config.py L105-109; FLOV §4). Per prompt rule 6, the core
paper is built coordinate-independent; the prospective section is reported WITH an explicit
placeholder-coordinate limitation. Not a blocker.

**D-09 · Crop naming.** Internal labels `bugday` (wheat) and `aycicegi`/`aycicegi_yaglik`
(oilseed sunflower) map to manuscript "winter wheat" and "sunflower". n and metrics kept per
internal label to preserve traceability.

**D-10 · Primary prospective season = 2025.** 2026 is mid-season (as of 2026-06-20 only
pre_season/emergence/vegetative present, small n) → reported as in-progress/partial. 2025 is the
complete forward season carrying the senescence-collapse finding.

**D-11 · No master-data STOP needed.** Core input `data/processed/master_feature_matrix_2017_2024.csv`
and the calibration feature matrices were found and verified. No STOP&ASK condition triggered.

### 2026-06-20 — Phase 1–6 (later)

**D-12 · Faithful replication over importlib.** Rather than import the digit-prefixed cp25 modules
(risking accidental writes via their `main()`), `repro/repro_common.py` re-implements the exact
Layer A/B/C logic (feature lists, model configs, imputation, `_cv_predict`, `_block_groups`) from
verified source. Faithfulness is proven by the fidelity gate (recompute = published, max |Δ|=0.0)
and per-sample champion cross-check (|Δ|=0.0). This is self-contained and write-safe.

**D-13 · Fidelity gate PASSED.** 92/92 checks, global max |Δ| = 0.0; champion per-sample |Δ|=0.0.
⇒ regenerated LOILO/Spatiotemporal per-sample predictions are faithful → safe basis for gap test
and CIs.

**D-14 · Vectorized bootstrap.** Initial loop-based bootstrap (1.6M sklearn calls) was too slow;
replaced with fully vectorized numpy bootstraps (observation via (n_boot×n) indexing; cluster via
per-group sufficient statistics). Results are mathematically identical; runtime 02 dropped to ~9 s.

**D-15 · Matched-sample ablation insight.** The matched ablation revealed the thesis's H2 "NDVI
hurts wheat" (naïve ΔR²=−0.444) is largely a sample-size artifact (A_full n=589 R²=−0.092 vs
A_matched n=213 R²=−0.575). Matched NDVI effect ≈ +0.039. Reported as a methodological-honesty
contribution, not a contradiction of the thesis (which did not run the matched comparison).

**D-16 · Bootstrap CI dual-method.** Report iid (primary, comparable to literature/thesis Görev-13)
AND year/district cluster (sensitivity) because the district-year panel is non-iid; cluster CIs are
wide and disclosed (temporal skill fragile with ~22 years).

**D-17 · Isolation verified via git.** `git diff --name-only HEAD` shows only the 9 tracked files
that were already modified at session start (none touched by me); all 57 new files are under
`paper1_generalization/`. Frozen prospective model untouched. No commit made (not requested).

### 2026-06-20 — Phase 7 (UNBLOCK: real parcel coordinates supplied by user)

**D-18 · Real-coordinate prospective re-validation.** The user supplied 4 real surveyed parcel
corners for EVR_01 ("Kendi tarlam"):
`(41.531790,27.861590),(41.531521,27.862092),(41.530694,27.861425),(41.530760,27.860755)`.
Centroid 41.531191, 27.861465; area **0.62 ha (6.2 da)** (shoelace); ~50 km from the placeholder
(41.045, 27.205). This unblocks the FLOV prospective section.
- **How run:** `repro/11_prospective_real_coords.py` re-runs the REAL FLOV chain
  (`build_unified_features` → frozen `predict_ndvi_series` → `LiveValidator`) on the true polygon.
  Live S2 (GEE service account) + ERA5 (CDS) confirmed working in-session (GEE: 10 S2 scenes near
  field; CDS client OK). Frozen LSTM loaded with integrity hash `43ef61b5…` (matches FLOV contract)
  — inference only, NO retraining.
- **True polygon:** built from the 4 corners (shapely), 10 m inward buffer (one S2 pixel; full
  30 m was too aggressive for 0.62 ha), used area ≈ 3129 m² (~31 S2 pixels). `subpixel_risk=True`
  (small field) — disclosed.
- **Isolation:** `config.AUDIT_FILE`/`LOG_FILE` redirected into `analysis/prospective_real/`;
  `configure_logging()` NOT called (so `logs/flov.log` untouched); `build_unified_features(save=False)`
  (so `data/prospective/` not overwritten); outputs written only under my folder; distinct site id
  `EVR01R` (no collision with original EVR_01 artifacts); `geometry.site_polygon_coords`
  **monkeypatched at runtime** (no source edit) to return the true polygon. API cache
  (`data/cache/api/`, UNTRACKED) receives additive new entries for the new location — acceptable
  (not a tracked-file modification).
- **Actuals:** raw S2 (gold standard, FLOV §7) as primary + unified NDVI_int (matches original
  method) for comparability. tolerance_days=2 (as original).
- **Cost:** ERA5 ≈ 6 min/CDS-month → full 2025 (12 mo) + 2026 (Jan–today) ≈ ~2 h; per-month cache
  makes it resumable. Run in background.
- **No fabrication:** if any month/fetch fails, coverage is reported as-is; numbers come only from
  the actual run. If the run cannot complete, the placeholder-limitation stays and this is reported.

**D-19 · Real-coords run COMPLETE (exit 0) — finding robust.** 17 ERA5 CDS months fetched; outputs
in `analysis/prospective_real/`. Result: frozen NDVI forecaster does **not** beat naive persistence
at the real parcel in any window (2025 model R²=0.78 vs persistence 0.91; 2026 partial model
R²=−1.32 vs 0.49; Wilcoxon p=1.000 throughout). Placeholder coords were mildly optimistic
(2026 model R² 0.703→−1.32) → the honest finding is NOT a placeholder artifact and is stronger at
the true site. Per-stage late-season skill unstable (maturity R²=−13.7; MAE stays ~0.05 → R²
ill-posed at low-variance stages, reported honestly). Isolation re-verified via git: still only the
9 pre-existing tracked-file modifications; audit/log redirected to my folder; no EVR01R file in
`data/prospective/`; frozen model inference-only (hash `43ef61b5…`). Updated all docs/manuscript/
tables/figures/logs accordingly; placeholder-coordinate limitation removed for EVR_01 (replaced by
single-small-field/subpixel/partial-2026 caveats). EVR_02–05 left placeholder (not re-run).
