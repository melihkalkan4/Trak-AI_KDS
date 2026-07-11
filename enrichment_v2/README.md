# enrichment_v2 — remote-sensing feature enrichment (non-destructive audit add-on)

Extends the TRAK-AI "Paper 1" cross-validation audit IN PLACE but **non-destructively**: the existing
thesis/Paper-1 artifacts are byte-for-byte unchanged (verified). All new code/data/outputs live ONLY
here. Branch: `feature/rs-enrichment-v2`.

## Start here
- **`REPORT.md`** — findings + integrity (checksum before==after) + data-quality notes.
- **`PLAN.md`** — task→code map, district source/CRS, central-district correspondences.
- **`outputs/tables/table2..8_*_v2.csv`** — audited result tables (Paper-1 equivalents).

## Run order (each writes only under enrichment_v2/)
```
code/t1_cropland_geometries.py   # admin polygons (from the provided zip) → district cropland; built-up excluded
code/t2_indices.py               # 8 indices × {mean,median,std,P10,P90,CV,range}, crop windows, 2017–24 (GEE)
code/t3_soil.py                  # SoilGrids 9 props 0–30 cm + AWC (Saxton–Rawls 2006)
code/t4_topography.py            # SRTM elevation/slope/northness/eastness + TWI
code/t5_anomaly.py               # per-district z-scores of metrics + yield
code/t6_assemble.py              # tiers A–D (matched n=213/209)
code/t7_select.py                # per-crop selection (collinearity + fold-importance + count cap)
code/t8_eval.py                  # 4 CV regimes × tiers × models; matched SS + clustered CI + gap + rolling-origin + ablation
code/t9_report.py                # tables 2–8 + REPORT.md + checksum verification
```
Harness is COPIED into `code/harness.py` + `code/harness_clusters.py` (faithful cp25 CV/model +
cluster-aware bootstrap), outputs redirected here. Env = repo venv (Python 3.13). GEE service-account
key in `keys/`; SoilGrids/DEM/MERIT via GEE; admin polygons from
`Downloads/Turkey - Administrative Levels.zip`.

## Integrity / rollback
- `checksums_before.txt` (T0) == `checksums_after.txt` (T9) — **145 protected artifacts, 0 changed**
  (per-path SHA256; `diff` is empty). data/trakai.db, models, *_results.csv, fig_*.png, feature_names.json,
  master_ledger*, paper1_generalization/* — all untouched.
- **Rollback** = delete `enrichment_v2/` + `git branch -D feature/rs-enrichment-v2`.

## Headline findings (audited; honest)
- Spatial≫temporal generalization gap **persists** with the richer feature set.
- Temporal (LOYO) skill vs matched climatology improves with enrichment for BOTH crops, but only
  **sunflower tier D** robustly beats climatology (year-clustered 95% CI [+0.033, +0.161]); **winter
  wheat tier D** is marginally positive (+0.057) with CI **including zero** [−0.054, +0.155].
- A multi-index set (red-edge CIre/NDRE, water NDWI, EVI/EVI2 — clamped |≤1|) lifts wheat more than
  single NDVI did (ΔSS B−A ≈ +0.21), narrowing but not erasing the crop asymmetry.
- Limitations: generic (non-crop-specific) cropland mask; NDVI era 2017–24 (8 yrs); few rolling-origin
  test years; district-aggregate features.
