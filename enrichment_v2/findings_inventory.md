# FINDINGS INVENTORY (Step 0) — source map for FINDINGS_REPORT.md

> **READ-ONLY compilation.** This file maps every planned report section to the **real artifacts**
> that already exist on disk. No analysis was run; no number was computed here. In Step 1 every value
> in `FINDINGS_REPORT.md` will be pulled from the files listed below and cited by path. Anything not
> found in any artifact will be written `[NOT IN ARTIFACTS]`, never invented.
> Rollback = delete `findings_inventory.md` (and later `FINDINGS_REPORT.md` + `findings_assets/`).

Crop labels everywhere: `bugday` = winter wheat, `aycicegi` = oilseed sunflower.

---

## PART A — ARTIFACT INVENTORY (path · what it holds)

### A1. enrichment_v2 — primary (crop-specific) result set
| Path | Holds |
|---|---|
| `enrichment_v2/ADVISOR_REPORT.md` | **PRIMARY narrative.** Crop-specific LOYO-vs-matched-climatology SS table + year-clustered CIs (lines 20–35); per-crop effective/ineffective RS list (12–14); crop-mask TÜİK validation r=0.954 wheat / 0.615 sunflower (line 17); tier A–D defs (18); all-cropland comparison note incl. "sunflower D SS +0.109" (38); honest limitations (40–41). |
| `enrichment_v2/outputs/advisor_master_ledger.csv` | Crop×tier×model×CV ledger: r2, rmse, baseline_rmse_matched, skill_score, ss_ci_low/high_clustered. n=213 wheat / 209 sunflower. **Source for §4 SS numbers.** |
| `enrichment_v2/outputs/advisor_tier_{A,B,C,D}_{bugday,aycicegi}.csv` (8 files) | Per-tier feature matrices actually fed to models (target + features). |
| `enrichment_v2/outputs/advisor_gap.csv` | Crop-specific ΔR² = R²_LOILO − R²_LOYO per crop×tier×model, with CI + year sign-rank p. **Source for §6 (crop-specific gap).** |
| `enrichment_v2/outputs/advisor_rolling.csv` | Crop×tier rolling-origin forward skill vs climatology (n_test_years, rolling_mean_skill). **§8.** |
| `enrichment_v2/outputs/advisor_ablation.csv` | Per-tier ΔR² vs tier A, by model×CV (enrichment ladder). **§7/§8.** |
| `enrichment_v2/outputs/advisor_selection_report.csv` | Per crop×tier feature → group → importance → status(selected/dropped_collinear). **§7.** |
| `enrichment_v2/outputs/advisor_percrop_rs_list.csv` | Per crop: effective_RS_indices, ineffective_RS_indices, selected_RS_features. **§7.** |
| `enrichment_v2/outputs/advisor_selected_features.json` | Verbatim selected-feature lists per crop×tier. **§14 appendix.** |
| `enrichment_v2/outputs/tables/advisor_table2_temporal.csv` | Formatted crop-specific temporal-performance table. **§4.** |
| `enrichment_v2/outputs/tables/advisor_table3_gap.csv` | Formatted crop-specific gap table ("persists = True"). **§6.** |

### A2. enrichment_v2 — methodological comparison (all-cropland 8-index) result set
| Path | Holds |
|---|---|
| `enrichment_v2/REPORT.md` | **COMPARISON narrative.** Integrity; what was extracted; "spatial≠temporal persists (T8)"; crop-specific index value; T7 selection; data-quality notes; conclusion. |
| `enrichment_v2/outputs/master_ledger_v2.csv` | All-cropland crop×tier×model×CV ledger (adds mae vs advisor ledger). **Source for §5.** |
| `enrichment_v2/outputs/gap_v2.csv` | All-cropland ΔR² gap (same schema as advisor_gap). **§6.** |
| `enrichment_v2/outputs/ablation_v2.csv` | All-cropland enrichment ablation ΔR² vs A. **§7.** |
| `enrichment_v2/outputs/rolling_origin_v2.csv` | All-cropland rolling-origin forward skill. **§8.** |
| `enrichment_v2/outputs/selected_features.json` | All-cropland selected features per crop×tier. **§14.** |
| `enrichment_v2/outputs/t7_selection_report.csv`, `t7_ratio.csv` | All-cropland T7 selection detail + selected/total ratio. **§7.** |
| `enrichment_v2/outputs/tables/table2_temporal_performance_v2.csv` | Formatted all-cropland temporal table. **§5.** |
| `enrichment_v2/outputs/tables/table3_generalization_gap_v2.csv` | Formatted all-cropland gap table. **§6.** |
| `enrichment_v2/outputs/tables/table4_ablation_v2.csv` | Formatted ablation. **§7.** |
| `enrichment_v2/outputs/tables/table6_selected_features_v2.csv` | Formatted selected features. **§7/§14.** |
| `enrichment_v2/outputs/tables/table7_rolling_origin_v2.csv` | Formatted rolling-origin. **§8.** |
| `enrichment_v2/outputs/tables/table8_enrichment_value_v2.csv` | ΔSS by enrichment ladder A→D. **§7.** |

### A3. enrichment_v2 — feature-enrichment inputs (data layer)
| Path | Holds |
|---|---|
| `enrichment_v2/outputs/tables/rs_variable_inventory.csv` (18 rows) | RS variable inventory: thesis-NDVI vars vs NEW indices. **§3.** |
| `enrichment_v2/outputs/tables/phenological_metrics.csv` (8 rows) | Phenological distribution metrics (mean/median/std/CV/P10/P90/range) per window. **§3.** |
| `enrichment_v2/outputs/tables/crop_masking_windows.csv` (7 rows) | Crop-specific phenology windows. **§3.** |
| `enrichment_v2/outputs/tables/tier_definitions.csv` | Tier A–D definitions. **§2/§3.** |
| `enrichment_v2/outputs/crop_classified_area.csv` | Per-district-year wheat/sunflower classified ha (basis of TÜİK r-validation). **§3.** |
| `enrichment_v2/outputs/indices_{bugday,aycicegi}.csv` | All-cropland 8-index × 3-window × 7-metric district aggregates. **§3.** |
| `enrichment_v2/outputs/crop_specific_indices_{bugday,aycicegi}.csv` | Crop-masked NDVI/NDRE/EVI × 3-window × 7-metric. **§3.** |
| `enrichment_v2/outputs/soil_features.csv` (29×31) | SoilGrids 0–30 cm 9 props + AWC (Saxton–Rawls). **§3.** |
| `enrichment_v2/outputs/topo_features.csv` (29×8) | elevation/slope/northness/eastness/TWI. **§3.** |
| `enrichment_v2/outputs/anomaly_{bugday,aycicegi}.csv` | Per-district z-scores + yield_z. **§3.** |
| `enrichment_v2/outputs/feature_groups.json` | Feature→group mapping. **§3/§14.** |
| `enrichment_v2/outputs/t2_evi_clamp_diagnostic.csv` | EVI clamp impact counts (representative window/crop). **§10.** |

### A4. enrichment_v2 — yield LSTM
| Path | Holds |
|---|---|
| `enrichment_v2/outputs/lstm_yield_results.csv` | Monthly-climate-sequence LSTM: crop×CV r2, rmse, mae, SS_vs_clim, cp25_layerA_r2, delta_vs_layerA. **§8.** |
| `enrichment_v2/outputs/lstm_yield_persample.csv` | Per-sample LSTM predictions. **§8 support.** |

### A5. enrichment_v2 — two-plains (örnek alan) independent test
| Path | Holds |
|---|---|
| `enrichment_v2/outputs/plains_test_summary.csv` (16 rows) | Ahmetbey & Müsellim ovas, 8-yr per-year cropland/wheat/sunflower ha + peak NDVI/NDRE/EVI. **§13/appendix (extra validation).** |
| `enrichment_v2/outputs/plains_geometry.json` | The two plain polygons + areas. |

### A6. Data-quality audit (READ-ONLY audit deliverables)
| Path | Holds |
|---|---|
| `enrichment_v2/audit/DATA_QUALITY_AUDIT.md` | Per-family verdicts; clamp-coverage answer; B1–B8 measured ranges; prioritised anomalies; bottom line. **§10.** |
| `enrichment_v2/audit/INVENTORY.md` | A0 artifact inventory + per-index cleaning-step mapping (clamp only EVI/EVI2). **§10.** |
| `enrichment_v2/audit/feature_summary.csv` | Per-feature min/max/mean/NaN%/nonfinite/OOB verdict. **§10.** |
| `enrichment_v2/audit/flagged_records.csv` | OOB records (empty = 0 garbage). **§10.** |
| `enrichment_v2/audit/raw_sample_anomaly_rates.csv` (32 rows) | Clamp-disabled per-pixel OOB rates, 4 districts × 8 indices. **§10.** |
| `enrichment_v2/audit/collinear_pairs.csv` (217) | \|r\|>0.98 collinear index-feature pairs (by-design). **§10/§14.** |

### A7. Integrity
| Path | Holds |
|---|---|
| `enrichment_v2/checksums_before.txt` / `checksums_after.txt` | SHA256 of protected artifacts before/after (byte-identity check). **§10.** |
| `enrichment_v2/POST_RESTART_VERIFICATION.txt` | Post-restart non-destruction verification. **§10.** |
| `enrichment_v2/PLAN.md`, `README.md` | Design recap, contract, manifest. **§2/§13.** |

### A8. Original Paper-1 baseline (pre-enrichment; point-buffer spatial support)
| Path | Holds |
|---|---|
| `paper1_generalization/analysis/baseline_superiority.csv` | LOYO SS vs B0 climatology per layer×crop×model + CI + Wilcoxon. **Sunflower LC gpr SS = +0.224 [+0.167,+0.276]; wheat 0/16 beat B0.** **§9.** |
| `paper1_generalization/analysis/generalization_gap.csv` | Original ΔR² (LOILO−LOYO), fixed-model + CI + Wilcoxon. **Wheat·A +0.639; sunflower·A +0.580.** **§6/§9.** |
| `paper1_generalization/analysis/generalization_gap_per_model.csv` | Per-model gap consistency. **§6.** |
| `paper1_generalization/docs/numbers_ledger.md` | Master ledger of every Paper-1 number → source → claim (A1–A4 champions, B1–B7 baseline superiority, C1–C6 gap). **§9.** |
| `paper1_generalization/analysis/bootstrap_ci.csv`, `ablation_per_model.csv`, `morans_i.csv`, `recomputed_aggregate_metrics.csv`, `fidelity_check.csv` | Bootstrap CIs, ablation, Moran's I, fidelity gate (max\|Δ\|=0). **§9/§12.** |
| `paper1_generalization/tables/T1_master_results.csv … T4_feature_importance.csv` | Published Paper-1 result tables. **§9.** |
| `paper1_generalization/manuscript/paper1.md`, `paper1_elsarticle.tex` | The existing manuscript (design/methods/claims to align with). **§2/§12/§13.** |
| `paper1_generalization/docs/{WRITING_DOSSIER,methods_as_implemented,results_narrative,work_log}.md` | Writing dossier + methods-as-implemented + narrative. **§2/§12.** |

### A9. Original Paper-1 referee-revision artifacts (point-buffer support)
| Path | Holds |
|---|---|
| `paper1_generalization/revisions/master_ledger.csv`, `master_ledger_summary.csv` | Revision master ledger. |
| `paper1_generalization/revisions/rolling_origin_results.csv`, `rolling_origin_summary.csv` | Forward-in-time (original support). **§8.** |
| `paper1_generalization/revisions/staged_forecast_results.csv` | Staged-issuance forecast (original support only). **§8 (flag: not re-run for admin-polygon enrichment).** |
| `paper1_generalization/revisions/ablation_matched_by_algorithm.csv`, `ablation_by_algorithm_summary.csv` | Per-algorithm matched ablation. **§8.** |
| `paper1_generalization/revisions/clustered_inference.csv`, `iid_inference_supplementary.csv` | Cluster-aware vs iid inference. **§9/§12.** |
| `paper1_generalization/revisions/spatiotemporal_blocks.csv` (+membership) | Spatiotemporal block CV. **§2/§9.** |
| `paper1_generalization/revisions/morans_i_sensitivity.csv` | Moran's I sensitivity. **§9.** |
| `paper1_generalization/revisions/permutation_importance_foldwise.csv` | Fold-wise permutation importance. **§7.** |
| `paper1_generalization/revisions/parcel_per_stage.csv` (+reconciliation) | Prospective parcel per-stage. **§9.** |
| `paper1_generalization/revisions/hyperparameter_protocol.csv` | Fixed-hyperparameter protocol. **§2.** |

---

## PART B — REPORT SECTION → SOURCE MAP (1–14)

| § | Section | Primary source(s) | Status |
|---|---|---|---|
| 1 | Executive summary | synthesized from §4 (`ADVISOR_REPORT.md`, `advisor_master_ledger.csv`), §6 (`advisor_gap.csv`,`generalization_gap.csv`), §10 (`audit/DATA_QUALITY_AUDIT.md`, checksums) | ✅ all present |
| 2 | Study design recap | `README.md`, `PLAN.md`, `paper1_generalization/docs/numbers_ledger.md`, `revisions/hyperparameter_protocol.csv`, `revisions/spatiotemporal_blocks.csv`; n from `advisor_master_ledger.csv` | ✅ |
| 3 | Data & feature enrichment | `tables/rs_variable_inventory.csv`, `phenological_metrics.csv`, `crop_masking_windows.csv`, `tier_definitions.csv`, `crop_classified_area.csv`, `soil_features.csv`, `topo_features.csv`, `anomaly_*.csv`; TÜİK r from `ADVISOR_REPORT.md:17` | ✅ — **CAVEAT:** the validation **r=0.954/0.615 scalars live only in `ADVISOR_REPORT.md` prose**; the per-year areas behind them are in `crop_classified_area.csv` but the correlation coefficient itself is not persisted in a standalone CSV. Will cite prose + underlying CSV. |
| 4 | **PRIMARY results — crop-specific** | `ADVISOR_REPORT.md:20–35`, `advisor_master_ledger.csv`, `tables/advisor_table2_temporal.csv` | ✅ |
| 5 | COMPARISON — all-cropland | `REPORT.md`, `master_ledger_v2.csv`, `tables/table2_temporal_performance_v2.csv` | ✅ — the "sunflower D +0.109" headline-guard number is in `ADVISOR_REPORT.md:38`; will cross-check exact value in `master_ledger_v2.csv` (tier D aycicegi LOYO). |
| 6 | **Headline gap (ΔR²)** | crop-specific `advisor_gap.csv` + `tables/advisor_table3_gap.csv`; all-cropland `gap_v2.csv` + `tables/table3_generalization_gap_v2.csv`; original `paper1_generalization/analysis/generalization_gap.csv` (+0.639 wheat·A / +0.580 sunflower·A) + `numbers_ledger.md` C1–C6 | ✅ |
| 7 | Per-crop index findings | `advisor_percrop_rs_list.csv`, `advisor_selection_report.csv`, `advisor_selected_features.json`, `selected_features.json`, `t7_selection_report.csv`, `tables/table6_selected_features_v2.csv`, `tables/table8_enrichment_value_v2.csv`, `advisor_ablation.csv`/`ablation_v2.csv` | ✅ |
| 8 | Forward-in-time & ablation | `advisor_rolling.csv` + `tables/table7_rolling_origin_v2.csv` + `rolling_origin_v2.csv`; `advisor_ablation.csv`/`ablation_v2.csv`/`tables/table4_ablation_v2.csv`; LSTM `lstm_yield_results.csv`; staged `revisions/staged_forecast_results.csv` | ✅ — **FLAG:** rolling-origin & ablation exist for BOTH supports; **staged-issuance exists only for the original point-buffer Paper-1** (`revisions/`), NOT re-run on admin-polygon enrichment. Will state this explicitly, not blend. |
| 9 | Comparison to original Paper-1 | `paper1_generalization/analysis/baseline_superiority.csv` (sunflower LC gpr +0.224), `numbers_ledger.md`, `manuscript/paper1.md`; vs crop-specific `advisor_master_ledger.csv` | ✅ — will state spatial-support change (point-buffer → admin polygon) ⇒ numbers NOT cell-for-cell comparable. |
| 10 | Data-quality & integrity | `audit/DATA_QUALITY_AUDIT.md`, `feature_summary.csv`, `flagged_records.csv`, `raw_sample_anomaly_rates.csv`, `collinear_pairs.csv`, `INVENTORY.md`; `checksums_before.txt`==`checksums_after.txt`; `POST_RESTART_VERIFICATION.txt` | ✅ |
| 11 | Honest limitations | `ADVISOR_REPORT.md:40–41`, `audit/DATA_QUALITY_AUDIT.md` (NDWI CV, clamp gap, 25.1% NaN), crop-mask r=0.615 | ✅ |
| 12 | Scientific interpretation | synthesized from `REPORT.md` Conclusion, `numbers_ledger.md`, `docs/WRITING_DOSSIER.md`, `docs/results_narrative.md` | ✅ (interpretive prose; grounded in cited numbers, no new computation) |
| 13 | Open decisions & next steps | synthesized from `PLAN.md`, `ADVISOR_REPORT.md`, audit action items; plains extra-validation `plains_test_summary.csv` | ✅ — **CAVEAT:** advisor ORCID/email = `[NOT IN ARTIFACTS]` (not on disk). |
| 14 | Appendix — source index + feature lists | this file; `advisor_selected_features.json`, `selected_features.json`; `collinear_pairs.csv` | ✅ |

### Items that will be written `[NOT IN ARTIFACTS]` (located nowhere on disk)
1. Advisor ORCID / email (§13).
2. Any cell-for-cell crop-specific-vs-original comparison on identical spatial support (§9) — impossible by construction (support changed point-buffer → admin polygon); will be described, not tabulated as a diff.

### Distinctions to enforce in Step 1 (per contract)
- **PRIMARY = crop-specific** (`ADVISOR_REPORT.md` / `advisor_*`); **COMPARISON = all-cropland** (`REPORT.md` / `*_v2`). The better-looking all-cropland sunflower-D **+0.109** must NEVER stand as the headline over the crop-specific **−0.004**.
- **REAL findings** (gap persists; neither crop robustly beats climatology under crop-specific LOYO) vs **BENIGN notes** (217 collinear pairs by-design; Tekirdağ↔Süleymanpaşa admin reorg; CIre max 5.78 = real dense canopy).
- Original-support results (`paper1_generalization/`) vs new admin-polygon results (`enrichment_v2/`) kept clearly separate; staged-issuance only exists for the former.

---

**STEP 0 COMPLETE — STOP.** Awaiting **"devam"** to compile `enrichment_v2/FINDINGS_REPORT.md` from exactly these sources.
Integrity so far: only this one new file (`findings_inventory.md`) created; nothing existing read-modified. Rollback = delete it.
