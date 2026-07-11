<!--
============================================================================
DATA IN BRIEF MANUSCRIPT — WORKING DRAFT (English manuscript text)
Prepared following the official Data in Brief article template v.19 (Dec 2024).
All numeric values verified cell-by-cell against the deposit files in
mendeley_package/ on 2026-07-11. Citation tags: [V] verified, [P] provisional,
[N] needs check, [D] DOI missing. Remove tags on final pass (keep only content).
Bracketed ALL-CAPS placeholders mark values the author must supply/confirm.
============================================================================
-->

# A cross-validation-ready district-year dataset of satellite, climate, soil and in-situ features for winter-wheat and sunflower yield modelling in Trakya, Türkiye

<!-- Title check: contains "dataset"; differs from the Mendeley dataset title
("Spatial skill is not temporal skill — TRAK-AI crop-yield cross-validation
audit (Trakya, Türkiye)") and from the related-article title. [V] -->

**Authors**

Melih Kalkan ^a,\*^ [V], Gülsüm Çiğdem Çavdaroğlu ^a^ [V]

^a^ Işık University, Department of Management Information Systems, İstanbul, Türkiye [V]
<!-- [DEĞER DOĞRULANACAK: full postal street address + postal code of the
Department, as required by the DiB template "full postal address of each
author's institution"] -->

\* Corresponding author.
E-mail address: melihkalkan4@outlook.com (M. Kalkan) [V — matches the IJEG submission on DergiPark]
<!-- [N] DiB template requests an *institutional* e-mail address; substitute an
@isikun.edu.tr address here if one is available. Twitter/X handle: optional,
omit if none. -->

ORCID: M. Kalkan 0009-0004-7719-5333 [V]; G. Ç. Çavdaroğlu 0000-0002-4875-4800 [V]

---

## Keywords

crop yield forecasting; leave-one-year-out validation; spatial autocorrelation; vegetation indices; reanalysis climate data; pedotransfer available water capacity; generalization gap; agricultural panel data

---

## Abstract

<!-- 100–500 words; describes collection, dataset and reuse potential; no
conclusions/interpretations; avoids "study/results/conclusions"; differs from
the repository description. Current length ≈ 250 words. -->

This data article documents a derived, analysis-ready panel assembled to interrogate how cross-validation design shapes apparent skill in satellite-driven crop-yield modelling across Trakya (the European part of Türkiye). The panel covers 29 districts of the Edirne, Kırklareli and Tekirdağ provinces for winter wheat and oilseed sunflower. A climate tier spans 1165 district-years over 2004–2025; tiers that carry Sentinel-2 vegetation information and SoilGrids soil information span the 2017–2024 satellite era. Predictors were derived by district-level zonal aggregation over a phenology-classified cropland mask: multi-temporal Sentinel-2 spectral indices summarised by seven distribution statistics across greenup, peak, grain-fill and harvest windows; NASA POWER (MERRA-2) growing-season climate descriptors; and ISRIC SoilGrids 2.0 soil properties with a Saxton–Rawls available-water-capacity estimate. District yield targets were curated from TÜİK official statistics. The deposit ships not only the feature matrices and target but also the complete feature-selection log, the leave-one-year-out (temporal) and leave-one-district-out (spatial) fold assignments, per-sample out-of-fold predictions for every layer × crop × model, and in-situ records from a field-surveyed 0.62 ha winter-wheat parcel near Vize together with auxiliary monitoring sites. A column-level data dictionary, integrity checksums, and a single dependency-light script that regenerates the headline derived tables from the shipped inputs accompany the files. Because temporal and spatial folds are held on identical observations, the data enable paired comparison of forecasting-relevant against interpolation-relevant skill without a Google Earth Engine account, and support reuse in benchmarking, meta-analysis of validation practice, and teaching of honest model evaluation.

---

## Specifications Table

<!-- Every row mandatory; left column text is fixed by the template. Values
cross-checked against the deposit and the Mendeley record on 2026-07-11. -->

| | |
|---|---|
| **Subject** | Earth and Environmental Sciences [V — DiB dropdown option "Earth & Environmental Sciences"] |
| **Specific subject area** | Agricultural remote sensing; satellite-, climate- and soil-based crop-yield modelling and cross-validation benchmarking. [V] |
| **Type of data** | Table (CSV); JSON configuration; Python script. Processed / analysed / derived (secondary data). [V] |
| **How data were acquired** | Sentinel-2 L2A spectral indices and phenology-window statistics extracted in Google Earth Engine over an ESA WorldCover cropland mask; NASA POWER (MERRA-2) climate variables; ISRIC SoilGrids 2.0 soil properties with a Saxton–Rawls available-water-capacity transform; SRTM topography (documented, not modelled); TÜİK district crop statistics. District-level zonal aggregation; cross-validation with scikit-learn `LeaveOneGroupOut`. [V] |
| **Data format** | Raw (curated TÜİK statistics); Analysed; Derived. Filtered. [V] |
| **Description of data collection** | Predictors were aggregated to the district (ilçe) level over crop-classified pixels for each crop-year; yields were curated from TÜİK. Feature tiers add information progressively (climate → +Sentinel-2 → +soil). Temporal (leave-one-year-out) and spatial (leave-one-district-out) folds share identical observations per tier. [V] |
| **Data source location** | Institution: Işık University. Region: Trakya — Edirne, Kırklareli and Tekirdağ provinces, Türkiye. Country: Türkiye. Field-surveyed parcel EVR_01 centroid: 41.531191 N, 27.861465 E (near Vize, Kırklareli). Primary data sources: Copernicus Sentinel-2 (ESA); NASA POWER / MERRA-2 (NASA); ISRIC SoilGrids 2.0; ESA WorldCover; NASA/USGS SRTM; TÜİK / TurkStat. [V] |
| **Data accessibility** | Repository name: Mendeley Data. Data identification number (reserved DOI): 10.17632/f6d29w5zjk.1. Direct URL to data: https://data.mendeley.com/datasets/f6d29w5zjk/1. Licence: CC-BY-4.0. [DEĞER DOĞRULANACAK: the deposit is in moderation/draft at the time of writing; the DOI and URL must resolve and provide anonymous reviewer access before submission.] [P] |
| **Related research article** | None. [V — see note below] |

<!-- RELATED-ARTICLE NOTE (do not print in the cell): the associated manuscript
"Spatial skill is not temporal skill: a cross-validation audit of satellite-
driven winter-wheat and sunflower yield prediction in Trakya, Türkiye"
(Kalkan & Çavdaroğlu) is under review at the International Journal of Engineering
and Geosciences (DergiPark ID 1992083; submitted 2026-07-11, status "New
Submission"). The DiB template requires the related research article to be "at
least accepted for publication"; because it is not yet accepted, this row reads
"None". On acceptance, move the article to this row and make it the first
reference. -->

---

## Value of the Data

<!-- 3–6 bullets, each ≤150 words; why valuable + how reusable; no conclusions. -->

- The deposit pairs **temporal (leave-one-year-out) and spatial (leave-one-district-out) cross-validation folds computed on identical observations**, so a reuser can quantify how much apparent yield-model skill is attributable to spatial interpolation rather than genuine forecasting. This paired design is rarely published alongside the underlying features, making the dataset directly usable for benchmarking cross-validation practice.

- Because the deposit ships **per-sample out-of-fold predictions for every layer × crop × model × fold scheme**, any reported metric (R², RMSE, MAE, MAPE, skill score) can be recomputed and audited without rerunning the models, and alternative aggregations or statistical tests can be applied to the same predictions.

- The predictors are delivered as **extracted, district-level values with a full column dictionary**, letting researchers without a Google Earth Engine account, cloud credits, or petabyte-scale imagery reproduce and extend a satellite-plus-climate-plus-soil yield analysis over a full 22-year window.

- The **field-surveyed 0.62 ha parcel (EVR_01)** with real GPS corners and daily feature series provides a rare in-situ anchor for district-scale remote-sensing yield work in Türkiye, supporting scale-transfer and forecaster-versus-persistence studies at the sub-field level.

- The curated **TÜİK district panel of winter-wheat and sunflower yields, planted area and production (2004–2025)** is a reusable reference for agricultural-economics and food-security work on Trakya, one of Türkiye's principal grain and oilseed regions.

---

## Background

<!-- ≤200 words; motivation/context; if related to an original article, briefly
say how the data article adds value; no interpretation. -->

Satellite-driven crop-yield models are frequently reported with strong accuracy, yet the headline number depends heavily on how the data are split for validation: random or spatial folds let a model exploit structure shared between neighbouring locations in the same year, whereas holding out entire years tests the forward, forecasting-relevant skill an operational system actually needs. This deposit was compiled to make that distinction inspectable and reusable. It assembles, for two contrasting crops across Trakya, the full chain from district-level predictors to fold assignments to per-sample predictions, so that temporal and spatial validation can be compared on the same observations. The data underpin the associated manuscript (currently under review), which audits the spatial-versus-temporal generalization gap; the data article adds value by releasing the extracted features, selection logs, folds, predictions and in-situ records in a self-contained, Earth-Engine-free form that lets others reproduce every reported figure and repurpose the panel for their own validation, benchmarking or teaching needs.

---

## Data Description

The deposit is a single archive that unpacks into six numbered data folders plus documentation. Every column of every CSV is described in `data_dictionary.csv` (file, column, dtype, non-null %, value range/example, description). Table 1 lists the files with their dimensions; the paragraphs that follow describe each folder.

**Table 1.** File inventory of the deposit (rows exclude the header). Column counts are as shipped.

| Folder / file | Rows | Cols | Content |
|---|---|---|---|
| `01_main_panel/calibration_features_layerA.csv` | 1165 | 20 | Climate tier: target + 14 climate features; 29 districts, 2004–2025 |
| `01_main_panel/calibration_features_layerB.csv` | 422 | 27 | Tier A + 7 Sentinel-2 NDVI features; 2017–2024 |
| `01_main_panel/calibration_features_layerC.csv` | 422 | 45 | Tier B + SoilGrids soil (clay/sand/silt/pH/SOC/AWC × 3 depths) |
| `02_crop_specific_layer/crop_specific_indices_{wheat,sunflower}.csv` | 232 each | 67 | NDVI/NDRE/EVI × phenology window × 7 distribution metrics |
| `02_crop_specific_layer/spectral_indices8_distribution_{wheat,sunflower}.csv` | 232 each | 172 | 8 indices × phenology window × 7 distribution metrics |
| `02_crop_specific_layer/anomaly_zscores_{wheat,sunflower}.csv` | 232 each | 173 | Per-district z-scores of the 8-index metrics + `yield_z` |
| `02_crop_specific_layer/crop_classified_area_ha.csv` | 232 | 6 | Phenology-classified wheat/sunflower area (ha) per district-year |
| `02_crop_specific_layer/soilgrids_awc_features.csv` | 29 | 31 | Per-district SoilGrids 0–30 cm properties + Saxton–Rawls AWC |
| `02_crop_specific_layer/topography_documented_NOT_modelled.csv` | 29 | 8 | SRTM elevation/slope/aspect/TWI — documented, **not** modelled |
| `03_feature_selection/feature_selection_report.csv` | 314 | 6 | Retained and dropped features per crop × tier |
| `03_feature_selection/selected_features_by_tier.json` | — | — | Final retained feature sets, both crops × tiers A/B/C/D |
| `04_folds_and_predictions/per_sample_predictions_main.csv` | 30557 | 11 | Out-of-fold `y_true`/`y_pred`/`abs_error` per layer × crop × CV × model |
| `04_folds_and_predictions/lstm_yield_persample.csv` | 2330 | 6 | Monthly-climate yield-LSTM per-sample predictions |
| `04_folds_and_predictions/aggregate_metrics_recomputed.csv` | 92 | 11 | Recomputed R²/RMSE/MAE/MAPE/bias/skill score |
| `05_field_insitu/EVR01_parcel_coordinates.csv` | 5 | 6 | Four surveyed GPS corners + centroid, 0.62 ha |
| `05_field_insitu/EVR_daily_features_{2025,2026}.csv` | 1825 / 685 | 21 | Daily climate + index features per site (`surveyed` flag) |
| `05_field_insitu/EVR01_parcel_{2025,2026}_validation_per_stage.csv` | 7 / 3 | 7 | Frozen NDVI forecaster vs persistence, by phenology stage |
| `05_field_insitu/consensus_predictions.csv` | 20 | 6 | Multimodal consensus predictions (site-coded) |
| `06_tuik_reference/tuik_ilce_crop_yields_2004_2025.csv` | 1428 | 10 | TÜİK district yield (kg/da), planted/harvested area, production |
| `data_dictionary.csv` | 1073 | 6 | Column-by-column dictionary for every CSV |
| `CHECKSUMS.sha256`, `LICENSE`, `README.md`, `regenerate_tables.py` | — | — | Integrity hashes, licence + source terms, guide, regeneration script |

*`01_main_panel/`* holds the modelled feature matrices with the yield target `verim_kg_da` (kg per decare, TÜİK). Three nested tiers add information progressively: tier A carries 14 growing-season climate descriptors over the full 2004–2025 window (1165 district-years); tier B adds seven Sentinel-2 NDVI phenology features and is therefore restricted to the 2017–2024 satellite era (422 district-years: 213 winter-wheat and 209 sunflower); tier C further adds SoilGrids soil properties. Keys (`ilce_id`, `ilce`, `il`, `year`, `crop`) are common to all files.

*`02_crop_specific_layer/`* holds the crop-masked robustness layer for 2017–2024 (29 districts × 8 years = 232 district-years per crop). It contains eight vegetation indices (NDVI, EVI, EVI2, NDRE, CIre, NDWI, GNDVI, OSAVI) summarised by seven distribution metrics (mean, median, standard deviation, p10, p90, coefficient of variation, range) within phenology windows (greenup, peak, grain-fill for wheat, harvest), their per-district anomaly z-scores, the phenology-classified crop area used for mask validation, per-district SoilGrids properties with a Saxton–Rawls available-water-capacity estimate, and SRTM topographic covariates that are documented but deliberately not used in any modelled tier.

*`03_feature_selection/`* documents the complete per-crop, per-tier selection, listing both retained and dropped features (with group and importance) and the final retained sets.

*`04_folds_and_predictions/`* is the reproducibility core: out-of-fold predictions for every layer × crop × cross-validation regime × model, the yield-LSTM per-sample predictions, and a recomputed aggregate-metrics table.

*`05_field_insitu/`* contains the in-situ data. `EVR_01` is a field-surveyed 0.62 ha winter-wheat parcel near Vize (Kırklareli) whose four real GPS corners and centroid (41.531191 N, 27.861465 E) are published; auxiliary sites `EVR_02`–`EVR_05` are included as daily feature series with `surveyed = False` and their coordinates deliberately withheld (not ground-truthed). Per-stage validation files compare a frozen NDVI forecaster against a persistence baseline.

*`06_tuik_reference/`* redistributes TÜİK district crop yields, planted/harvested area and production for 2004–2025 in a curated, study-scoped form.

---

## Experimental Design, Materials and Methods

<!-- No character limit; describe acquisition and processing fully; include code
references; no interpretation. -->

**Study area and units.** The analysis unit is the district-year (`ilçe` × calendar year). Twenty-nine districts of Trakya — spanning the provinces of Edirne, Kırklareli and Tekirdağ — were included for winter wheat (`bugday`) and oilseed sunflower (`aycicegi_yaglik`). District boundaries follow TÜİK administrative codes (`ilce_id`, range 1163–2096).

**Yield targets.** District yields (kg per decare), planted and harvested area, and production were curated from TÜİK (TurkStat) official statistics for 2004–2025 and shipped in `06_tuik_reference/tuik_ilce_crop_yields_2004_2025.csv`. The modelled target `verim_kg_da` corresponds to the `bugday` and `aycicegi_yaglik` records.

**Cropland mask.** For each crop-year, cropland pixels were identified from a phenology-based classification within the ESA WorldCover cropland extent, and the classified area was validated against TÜİK planted area (see below). Zonal statistics for all predictors were computed over the crop-classified pixels only.

**Sentinel-2 predictors.** Multi-temporal Sentinel-2 L2A surface-reflectance imagery (2017–2024) was processed in Google Earth Engine. Eight vegetation indices (NDVI, EVI, EVI2, NDRE, CIre, NDWI, GNDVI, OSAVI) were computed and summarised within phenology windows (greenup, peak, grain-fill, harvest) by seven distribution metrics (mean, median, standard deviation, p10, p90, coefficient of variation, range), yielding the crop-specific tables in `02_crop_specific_layer/`. A compact NDVI feature set (peak, seasonal mean, integral, flowering, grain-fill, spring slope, greenness days) enters the tier-B main panel. The raster extraction code lives in the associated code repository (see Code availability); the deposit ships the extracted district-level values so that no Earth Engine account is required.

**Climate predictors.** Growing-season climate descriptors — cumulative and phenology-window growing-degree-days, vernalization days, seasonal/winter/flowering/grain-fill precipitation sums, an aridity index, heat-stress days, flowering-window temperature means and maxima, a diurnal temperature range, and seasonal/flowering shortwave radiation — were derived from NASA POWER (MERRA-2) daily data and are carried in tier A.

**Soil predictors.** ISRIC SoilGrids 2.0 properties (clay, sand, silt, pH in H₂O, soil organic carbon, cation-exchange capacity, bulk density, nitrogen, coarse fragments) were extracted per district; plant-available water capacity (`awc_0_30`) was derived with the Saxton–Rawls pedotransfer functions. Tier C carries these at three depth intervals (0–5, 5–15, 15–30 cm); the per-district 0–30 cm aggregates are in `soilgrids_awc_features.csv`.

**Topography.** SRTM-derived elevation, slope, aspect (northness/eastness) and a topographic wetness index are provided in `topography_documented_NOT_modelled.csv` for documentation; they are **not** used in any modelled tier.

**Feature tiers and selection.** Predictors were organised into nested tiers (A = 14 climate features; B = 21, adding Sentinel-2; C = 27, adding soil) to isolate the marginal contribution of each modality. A per-crop, per-tier feature selection was applied; retained and dropped features are logged in `03_feature_selection/feature_selection_report.csv`, and the final retained sets (tiers A–D) are in `selected_features_by_tier.json`.

**Cross-validation regimes.** Out-of-fold predictions were generated with scikit-learn `LeaveOneGroupOut` under three regimes that share the same observations per tier: leave-one-year-out (LOYO; groups = year) as a temporal / forecasting analogue; leave-one-district-out (LOILO; groups = district) as a spatial / interpolation analogue; and a spatiotemporal blocking scheme (five year-blocks × five KMeans latitude/longitude clusters). Because LOYO and LOILO share observations, paired tests are possible.

**Models and baselines.** Six learners (fixed seed 42) were evaluated — partial least squares, ElasticNet, random forest, XGBoost, Gaussian-process regression (Matérn ν = 2.5), and a Layer-C stacking ensemble — alongside baselines: B0 climatology (leave-one-year-out per-district mean), B1 year-trend, B2 persistence, and B3 climate-proxy. A skill score SS = 1 − MSE_model / MSE_B0 places accuracy on a common scale. A separate monthly-climate yield-LSTM produced the per-sample predictions in `lstm_yield_persample.csv`.

**Mask validation.** The phenology-classified crop area was validated against TÜİK planted area by Pearson correlation on the 27-district × 8-year intersection with matched TÜİK area (n = 216 district-years): r = 0.954 (wheat) and r = 0.615 (sunflower). `regenerate_tables.py` recomputes these from the shipped files.

**In-situ field campaign.** The EVR_01 parcel (0.62 ha, winter wheat, near Vize) was surveyed with GPS corner coordinates. Daily climate-and-index feature series for EVR_01 and auxiliary monitoring sites are provided for the 2025 and 2026 seasons; per-stage validation files compare a frozen NDVI forecaster with a persistence baseline across phenology stages.

**Reproducibility.** `regenerate_tables.py` rebuilds the headline derived tables (crop-mask validation; climate-tier spatial-minus-temporal gap) from the shipped inputs with no network or Earth Engine access and checks them against the published invariants; `CHECKSUMS.sha256` provides integrity hashes for every file. The full modelling and raster-extraction code is in the associated repository (Code availability).

---

## Limitations

<!-- ≤200 words; limitations of the DATA (not of analysis/interpretation);
write "None"/"Not applicable" if none. -->

The analysis unit is the administrative district; the panel therefore carries no within-district spatial detail, and the only field-scale ground truth is the single EVR_01 parcel (auxiliary sites `EVR_02`–`EVR_05` are not field-surveyed and their coordinates are withheld). Sentinel-2 tiers are limited to 2017 onward, so the climate tier (2004–2025) and the vegetation/soil tiers (2017–2024) cover different windows and observation counts; the small number of years constrains leave-one-year-out folds. District yields are TÜİK reported statistics rather than measured plot yields. Climate features are from NASA POWER (MERRA-2); the associated manuscript notes a difference between MERRA-2 and ERA5-Land as an alternative source. Topographic covariates are provided for documentation only and are not part of any modelled tier. The deposit contains derived district-level values, not the raw Sentinel-2 imagery, which remains accessible through the code repository and Copernicus.

---

## Ethics Statement

The authors have read and follow the ethical requirements for publication in Data in Brief and confirm that the current work does not involve human subjects, animal experiments, or any data collected from social media platforms. The in-situ field records contain no farmer-identifying or landholding-ownership information. [V]

---

## CRediT Author Statement

**Melih Kalkan:** Conceptualization, Methodology, Software, Formal analysis, Data curation, Writing – original draft, Visualization. **Gülsüm Çiğdem Çavdaroğlu:** Supervision, Writing – review and editing. [V — mirrors the CRediT block in the associated manuscript]

---

## Acknowledgements

This work was carried out within a TÜBİTAK 2209-A University Students Research Projects support programme. [DEĞER DOĞRULANACAK: TÜBİTAK 2209-A application/grant number and support period.] The authors acknowledge the data providers ESA/Copernicus, ISRIC and TÜİK. Climate data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program. This dataset contains modified Copernicus Sentinel data (2017–2024). [P]

<!-- If the programme provided no numbered grant, replace with the standard
sentence: "This research did not receive any specific grant from funding
agencies in the public, commercial, or not-for-profit sectors." -->

---

## Declaration of Competing Interests

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper. [V]

---

## Declaration of Generative AI and AI-assisted Technologies in the Manuscript Preparation Process

<!-- Include only if AI tools were used in preparing the manuscript; delete
otherwise. Suggested wording if applicable: -->

During the preparation of this work the author(s) used [NAME OF TOOL] in order to [REASON, e.g. draft and copy-edit descriptive text and tabulate the file inventory]. After using this tool, the author(s) reviewed and edited the content as needed and take(s) full responsibility for the content of the publication. [N — confirm whether to include and which tool(s) to name]

---

## References

<!-- Max 20; numbered [n]; the dataset itself cited with a [dataset] tag; the
associated research article cited (as "submitted" — NOT "in press", which would
imply acceptance). DOIs marked [P] must be verified on the final pass. -->

1. M. Kalkan, G. Ç. Çavdaroğlu, Spatial skill is not temporal skill: a cross-validation audit of satellite-driven winter-wheat and sunflower yield prediction in Trakya, Türkiye, International Journal of Engineering and Geosciences (2026), manuscript submitted for publication (DergiPark ID 1992083). [V — status verified: under review; upgrade to first "In Press" citation on acceptance]

2. [dataset] M. Kalkan, G. Ç. Çavdaroğlu, Spatial skill is not temporal skill — TRAK-AI crop-yield cross-validation audit (Trakya, Türkiye), Mendeley Data, V1 (2026). DOI: 10.17632/f6d29w5zjk.1. [P — DOI resolves on publication]

3. D. Zanaga, R. Van De Kerchove, W. De Keersmaecker, D. Daems, C. Brockmann, G. Kirches, J. Wevers, O. Cartus, M. Santoro, S. Fritz, M. Lesiv, M. Herold, N.-E. Tsendbazar, P. Xu, F. Ramoino, O. Arino, ESA WorldCover 10 m 2021 v200, Zenodo (2022). DOI: 10.5281/zenodo.7254221. [V]

4. L. Poggio, L. M. de Sousa, N. H. Batjes, G. B. M. Heuvelink, B. Kempen, E. Ribeiro, D. Rossiter, SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty, SOIL 7 (2021) 217–240. DOI: 10.5194/soil-7-217-2021. [V]

5. K. E. Saxton, W. J. Rawls, Soil water characteristic estimates by texture and organic matter for hydrologic solutions, Soil Science Society of America Journal 70 (2006) 1569–1578. DOI: 10.2136/sssaj2005.0117. [V]

6. R. Gelaro, W. McCarty, M. J. Suárez, R. Todling, A. Molod, L. Takacs, et al., The Modern-Era Retrospective Analysis for Research and Applications, Version 2 (MERRA-2), Journal of Climate 30 (2017) 5419–5454. DOI: 10.1175/JCLI-D-16-0758.1. [V]

7. A. H. Sparks, nasapower: a NASA POWER global meteorology, surface solar energy and climatology data client for R, Journal of Open Source Software 3 (2018) 1035. DOI: 10.21105/joss.01035. [V]

8. M. Drusch, U. Del Bello, S. Carlier, O. Colin, V. Fernandez, F. Gascon, B. Hoersch, C. Isola, P. Laberinti, P. Martimort, A. Meygret, F. Spoto, O. Sy, F. Marchese, P. Bargellini, Sentinel-2: ESA's optical high-resolution mission for GMES operational services, Remote Sensing of Environment 120 (2012) 25–36. DOI: 10.1016/j.rse.2011.11.026. [V — DOI/lead authors/pages verified; spot-check the full 15-author string on ScienceDirect before submission] [N]

9. N. Gorelick, M. Hancher, M. Dixon, S. Ilyushchenko, D. Thau, R. Moore, Google Earth Engine: planetary-scale geospatial analysis for everyone, Remote Sensing of Environment 202 (2017) 18–27. DOI: 10.1016/j.rse.2017.06.031. [V]

10. Turkish Statistical Institute (TÜİK / TurkStat), Crop production statistics by district, https://www.tuik.gov.tr/ [N — add access date]. [P]

<!-- NASA POWER note: POWER has no single peer-reviewed dataset DOI (it aggregates
MERRA-2 meteorology + CERES/SRB solar). Cite the nasapower access tool [7] and
MERRA-2 [6], and include the POWER acknowledgement text in the Acknowledgements:
"These data were obtained from the NASA Langley Research Center (LaRC) POWER
Project funded through the NASA Earth Science/Applied Science Program." -->


<!-- Data-provider attributions (per LICENSE): "Contains modified Copernicus
Sentinel data [2017–2024]"; NASA POWER (CC-BY-4.0); ISRIC SoilGrids (CC-BY-4.0);
"© ESA WorldCover project 2021"; SRTM (public domain, NASA/USGS); TÜİK. -->
