# SUMMARY — Paper 1 generation

**Paper:** "Spatial skill is not temporal skill" — an honest cross-validation audit of
satellite-driven winter-wheat & sunflower yield prediction in Trakya. Target: *Computers and
Electronics in Agriculture* (Q1). Branch: `paper1`. All outputs in `paper1_generalization/` (57 files).

## What was produced
- **Analysis** (`analysis/`): per_sample_predictions (30,557 rows, all CV regimes — regenerated &
  fidelity-verified), bootstrap_ci, generalization_gap (+per_model), baseline_superiority,
  ablation_per_model, morans_i, prospective_overall, fidelity_check, recomputed_aggregate_metrics,
  + **`prospective_real/`** (real-coords FLOV: summary JSON, predictions, matched, per-stage, audit)
  + prospective_overall_real, prospective_placeholder_vs_real.
- **Tables** (`tables/`): T1 master results, T2 matched-sample ablation, T3 per-stage NDVI,
  T4 feature importance, + rendered `tables.md`.
- **Figures** (`figures/`): F1–F6 (PDF + 300-dpi PNG) + `figure_manifest.md`.
- **Manuscript** (`manuscript/`): `paper1.md` (full structural draft) + `paper1_elsarticle.tex` skeleton.
- **References** (`refs/`): `references.bib` (anchor works, all VERIFY) + `citation_todo.md`.
- **Reproduction** (`repro/`): `repro_common.py` + 10 numbered scripts + `run_all.py` +
  `README.md` + `requirements_full_venv.txt`.
- **Docs** (`docs/`, PRIMARY): `WRITING_DOSSIER.md`, `methods_as_implemented.md`,
  `results_narrative.md`, `numbers_ledger.md`, `work_log.md`.
- **Logs** (`logs/`): `artifact_manifest.md`, `decisions.md`, `integrity_audit.md`, this SUMMARY.

## Headline honest findings (all traceable; see numbers_ledger.md)
1. No ML model beats climatology for wheat under LOYO (best SS −0.172 [−0.238,−0.109]); sunflower
   multimodal does (SS +0.224 [+0.167,+0.276]).
2. Large spatial>temporal generalization gap (wheat-A ΔR²=+0.639 [+0.545,+0.735], p=6e−26;
   significant for all crops/tiers/models).
3. NDVI value is crop-specific; the wheat "NDVI harm" (naïve −0.444) is a sample-size artifact
   (matched ΔNDVI ≈ +0.039); sunflower matched ΔNDVI = +0.431.
4. On the farmer's REAL surveyed parcel (0.62 ha), the frozen forward NDVI forecaster does not beat
   naïve persistence in any season (2025 R²=0.78 vs 0.91; 2026 partial −1.32 vs 0.49; Wilcoxon
   p=1.000); late-season per-stage skill unstable (maturity R²=−13.7).
5. Wheat residuals spatially autocorrelated (Moran's I +0.257, p=0.008); sunflower not.

## Reproduction fidelity
Recompute vs published thesis cp25 tables: **92/92 checks pass, max |Δ| = 0.0**; per-sample
champion predictions match to 0.0. → the regenerated LOILO/Spatiotemporal predictions are faithful.
`run_all.py` reproduces everything end-to-end (~6–8 min) with the pinned venv.

## Numbers: point-estimate vs 95% CI
- **CI'd (iid + cluster bootstrap):** baseline skill scores; generalization-gap ΔR²; LOYO/LOILO
  R²/RMSE/MAE/MAPE/bias.
- **Point estimate only:** per-stage FLOV R² (single site/season, small per-stage n); Moran's I
  (analytic p, no CI on I); ablation tier R² (point CV values; gap CIs available separately);
  Spatiotemporal summary R².
- **Honesty flag:** temporal skill is fragile — year-cluster CIs are wide (e.g. best sunflower LOYO
  R² cluster CI [−0.145, +0.506]); state this in the paper.

## Real-world input status (was blocked — now UNBLOCKED for EVR_01)
- ✅ **Real parcel coordinates supplied (2026-06-20)** — 4 GPS corners → 0.62 ha field near Vize.
  EVR_01 prospective section **re-validated live** (GEE+CDS, frozen inference) on true geometry via
  `repro/11_prospective_real_coords.py`. The placeholder-coordinate blocker is RESOLVED for EVR_01.
- **Result is robust at real coords:** the frozen NDVI forecaster still does NOT beat naïve
  persistence (2025 model R²=0.78 vs 0.91; 2026 partial model R²=−1.32 vs 0.49; Wilcoxon p=1.000
  in all windows). Placeholder coords were mildly optimistic → the finding is not an artifact.
- Remaining caveats (single small 0.62 ha field/subpixel, satellite ground truth, 2026 partial,
  EVR_02–05 still placeholder) reported in the manuscript; out of scope: more years/regions.
- Core LOYO/LOILO/Spatiotemporal + Moran's I analysis is **independent** of site coords (uses the
  real 29-district `ilce_coords.csv`).

## Outstanding for the human author
- Resolve all `[VERIFY]` citations (`refs/citation_todo.md`); confirm every bib DOI/details.
- Confirm author roles (CRediT), TÜBİTAK 2209-A grant id, advisor full name/affiliation.
- Optional: add a SHAP beeswarm (figs available in `reports/cp25/fig_shap_summary_*`).

## Status
Analysis, figures, tables, docs, manuscript draft, references skeleton, reproduction pipeline, and
integrity audit are COMPLETE and internally consistent. The `docs/` package is self-sufficient for
writing the final manuscript.
