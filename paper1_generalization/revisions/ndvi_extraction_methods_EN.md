# Sentinel-2 NDVI extraction — methods as implemented (#8, #9)

> Read directly from source (`src/cp25/03b_fetch_ilce_ndvi.py`, `src/cp1_etl/mod_s2_gee.py`,
> `src/prospective_validation/*`). No pre-processing detail is invented. Paste-ready English.

## 1. District-level NDVI (the 2004–2025 panel; tiers B and C)
*Source: `src/cp25/03b_fetch_ilce_ndvi.py`.*

- **Platform/collection:** Google Earth Engine, `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2 Level-2A,
  surface reflectance, harmonised).
- **Region of interest:** each district represented by its centroid with an **adaptive circular
  buffer (5–8 km)**; mountainous/forested districts use the smaller buffer (cropland is sparse there).
- **Cropland mask:** **ESA WorldCover v200 (2021), class "Map" == 40 (cropland).** ⚠️ This is a
  **generic cropland mask, NOT crop-specific** — wheat and sunflower pixels are **not** separated.
  Both crops therefore draw on the **same district-level cropland NDVI aggregate**; the two crops are
  distinguished only downstream by the phenological-window feature extraction and by their TÜİK yields.
- **Cloud masking:** s2cloudless (`COPERNICUS/S2_CLOUD_PROBABILITY`) with probability **< 30 %**;
  a QA60 bitmask fallback (bits 10 = cloud, 11 = cirrus) is applied when the cloud-probability join
  fails. A pre-filter of `CLOUDY_PIXEL_PERCENTAGE < 80` is applied at scene level.
- **Index:** `NDVI = (B8 − B4) / (B8 + B4)`.
- **Compositing:** **16-day median** composites over the season (client-side loop over windows).
- **Spatial reduction:** `reduceRegion` **mean** (plus p25/p75 and a cropland pixel count) at
  **scale = 30 m** (Sentinel-2 native is 10 m; 30 m used for the district aggregate).
- **Phenological-window features** (used in tiers B/C) are derived from this district NDVI series:
  `ndvi_max, ndvi_mean_season, ndvi_integral, ndvi_flowering, ndvi_grain_fill, ndvi_spring_slope,
  greenness_days`.

**Limitations to state in the paper (#8):**
1. No crop-type map ⇒ no wheat/sunflower pixel separation (generic cropland only).
2. District-aggregate NDVI (5–8 km buffer), not field-level, for the panel.
3. A crop-specific re-extraction would require an external crop-type/parcel map for 2004–2025,
   which is **not available**; this is flagged as a limitation and future work (no crop mask was
   fabricated). GEE access exists, but a credible crop-specific mask does not.

## 2. Parcel-level NDVI (the 0.62 ha prospective field; FLOV)
*Source: `src/cp1_etl/mod_s2_gee.py` (called by `src/prospective_validation/fetchers/sentinel2.py`).*

- **Collection:** `COPERNICUS/S2_SR_HARMONIZED`, scene filter `CLOUDY_PIXEL_PERCENTAGE < 70`.
- **Masking/scaling:** `eemont` `.maskClouds()` + `.scaleAndOffset()`; indices `NDVI, EVI, NDWI`
  via `.spectralIndices(...)`.
- **ROI:** the **real surveyed parcel polygon** (4 GPS corners → 0.62 ha; 10 m inward buffer for
  pixel purity, ~3129 m² ≈ 31 S2 pixels; small-field/subpixel-flagged).
- **Spatial reduction:** `reduceRegion` **mean** at **scale = 10 m** (native), one value per date.
- **Temporal handling:** per-date values where a cloud-free observation exists (dates with no valid
  NDVI are skipped = raw "gold standard"); a linearly **interpolated** daily `NDVI_int` is also
  produced for coverage. Headline metrics use the **raw** S2 series; `NDVI_int` is reported for
  comparability with the original placeholder run.

## 3. Parcel "what is one observation?" (#9)
*Source: `src/prospective_validation/frozen_model_predictor.py`, `feature_builder.py`, `config.py`.*

- **Input window:** T = 30 days of 17 MinMax-scaled features (NDVI_int, EVI_int, NDWI_int, NDVI
  7-day trend, ERA5 t2m/tp/ssr/GDD/etc., sin/cos DOY).
- **Forecast horizon:** **t + 7 days** (hard-coded in training and inference).
- **Output:** NDVI residual update `ndvi_hat = last_observed + tanh(δ) × 0.30`, inverse-scaled.
- **An observation** in the validation = one (prediction_date → target_date = +7 d) pair, matched to
  the nearest cloud-free actual within ±2 days. Per-stage grouping is by `target_date` day-of-year
  against the sunflower phenology calendar.
- **Training period:** 2017–2024 (sunflower); the 2025/2026 parcel data are fully out-of-sample
  (frozen, hash-locked model; no re-fit, no look-ahead).
- **Phenology stages (DOY):** pre_season 1–104, emergence 105–130, vegetative 131–170,
  flowering 171–200, grain_fill 201–240, maturity 241–280, post_harvest 281–366.
