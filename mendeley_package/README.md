# TRAK-AI — data deposit for *"Spatial skill is not temporal skill"*

Derived-data deposit accompanying the manuscript:

> Kalkan, M., & Çavdaroğlu, G. Ç. (2026). **Spatial skill is not temporal skill: a cross-validation
> audit of satellite-driven winter-wheat and sunflower yield prediction in Trakya, Türkiye.**
> *International Journal of Engineering and Geosciences (IJEG).*

**Reserved DOI:** `[Mendeley Data reserved DOI — inserted on deposit, e.g. 10.17632/XXXXXXX.1]`
**Code:** see the Code Availability Statement in the article (GitHub; Zenodo code DOI if minted).
**Licence:** CC-BY-4.0 (see `LICENSE`; third-party source terms listed there — Copernicus / NASA
POWER / SoilGrids / ESA WorldCover / SRTM / TÜİK).

This deposit lets a reader **reproduce every reported result** without a Google Earth Engine account:
it ships the extracted/derived values, the fold assignments and per-sample predictions, the in-situ
field data, and a single script (`regenerate_tables.py`) that rebuilds the headline derived tables
from these inputs. The Sentinel-2 extraction itself (Earth Engine) lives in the code repository.

---

## Scope

| Layer | Coverage |
|---|---|
| Main panel (paper Sections 3–4) | **1165 district-years**, 29 districts, **2004–2025** (climate tier); NDVI-bearing tiers 2017–2025 |
| Crop-specific robustness layer (Section 4.9) | **27 districts × 8 years (2017–2024) × 2 crops**; 213 wheat + 209 sunflower district-years enter the models |
| Crops | winter wheat (`bugday`), oilseed sunflower (`aycicegi` / `aycicegi_yaglik`) |
| In-situ | EVR_01 field-surveyed 0.62 ha parcel (real GPS) + auxiliary monitoring sites |

---

## Directory structure

```
01_main_panel/                 Modelled feature matrices + target (TÜİK yield)
  calibration_features_layerA.csv   climate tier (14 features), 1165 dy
  calibration_features_layerB.csv   +Sentinel-2 NDVI (21), NDVI era
  calibration_features_layerC.csv   +soil (27), NDVI era
02_crop_specific_layer/        Crop-masked 8-index robustness layer (2017–2024)
  spectral_indices8_distribution_{wheat,sunflower}.csv   8 indices × 7 distribution metrics × windows
  crop_specific_indices_{wheat,sunflower}.csv            NDVI/NDRE/EVI crop-window summaries
  soilgrids_awc_features.csv                             9 SoilGrids props + Saxton–Rawls AWC
  topography_documented_NOT_modelled.csv                 SRTM elevation/slope/TWI — documented, NOT modelled
  crop_classified_area_ha.csv                            phenology-classified wheat/sunflower area (ha)
  anomaly_zscores_{wheat,sunflower}.csv                  per-district z-scores + yield_z
03_feature_selection/          Complete per-crop × per-tier selection (retained AND dropped)
  feature_selection_report.csv                           feature, group, importance, status
  selected_features_by_tier.json                         final retained sets, all tiers × both crops
04_folds_and_predictions/      Reproduce every metric
  per_sample_predictions_main.csv                        layer×crop×cv(=fold scheme)×model, y_true/y_pred/abs_error
  lstm_yield_persample.csv                               monthly-climate yield-LSTM per-sample predictions
  aggregate_metrics_recomputed.csv                       recomputed R²/RMSE/… (fidelity check)
05_field_insitu/               In-situ field data (most valuable part)
  EVR01_parcel_coordinates.csv                           real surveyed 4 GPS corners + centroid, 0.62 ha
  EVR_daily_features_{2025,2026}.csv                     daily climate+index features per site
  EVR01_parcel_{2025,2026}_validation_per_stage.csv      frozen NDVI forecaster vs persistence, by stage
  consensus_predictions.csv                              multimodal consensus predictions (site-coded)
06_tuik_reference/             TÜİK official statistics (curated, public)
  tuik_ilce_crop_yields_2004_2025.csv                    district yield (kg/da) + production (t) + planted area
data_dictionary.csv            column-by-column: file, column, dtype, non-null %, range/example, description
CHECKSUMS.sha256               integrity hashes for every file
regenerate_tables.py           rebuilds the headline derived tables from the inputs above
LICENSE                        CC-BY-4.0 + third-party source attributions
```

---

## In-situ / field data (privacy note)

`EVR_01` is the **field-surveyed 0.62 ha winter-wheat parcel near Vize (Kırklareli)**; its four real
GPS corner coordinates are published in `EVR01_parcel_coordinates.csv` (centroid 41.5312 N, 27.8615 E),
consistent with the manuscript. `EVR_02`–`EVR_05` are **auxiliary monitoring sites that were NOT
field-surveyed**; their daily feature series are included for completeness with `surveyed = False`, and
**their coordinates are deliberately not published** (not ground-truthed — no fabricated locations). The
field records contain **no farmer-identifying or landholding-ownership information** (verified).

## TÜİK data

`06_tuik_reference/` redistributes TÜİK district crop yields and planted area in a curated, study-scoped
form for reproducibility. These are publicly accessible Turkish official statistics; TÜİK is attributed
(see `LICENSE`). This follows the "curated public data" route; the article's Data Availability Statement
notes the deposit will be released on publication.

## Verify these invariants (from the shipped files)

- mask validation (crop_classified_area vs TÜİK planted area, Pearson): **r = 0.954 wheat, 0.615
  sunflower, n = 216** (27 districts × 8 years).
- main panel: **1165 district-years, 29 districts, 2004–2025**.
- feature tiers: A = 14, B = 21, C = 27 features (main); crop-specific A→B→C→D.
- crop-specific tier D: wheat skill **−0.014** (gap **+0.572**), sunflower **−0.004** (gap **+0.600**).
- climate-tier spatial-minus-temporal gap: **+0.639 wheat, +0.580 sunflower**.

`python regenerate_tables.py` recomputes the mask-validation correlation and the main-panel skill
metrics from the shipped raw files and checks them against these values.

## How to cite

Cite **both** the article (above) and this dataset (DOI in the header). Attribute the third-party
sources as listed in `LICENSE`.
