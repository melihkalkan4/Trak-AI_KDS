# A0 — DATA INVENTORY (read-only audit)

> Read-only audit. Nothing modified; this file + later audit artifacts live ONLY in
> `enrichment_v2/audit/`. Rollback = delete `enrichment_v2/audit/`. Every number below is from a
> real file/code read; unreadable/missing items are marked NOT FOUND. Measurements of value ranges
> (B1–B9) are deferred to A1 — this A0 covers artifact inventory + per-index cleaning-step mapping.

## 0. HEADLINE FINDING (answers the #1 open question, from code — `enrichment_v2/code/ev2_common.py:s2_index_image`)
**The |value|≤1 clamp / denominator handling is applied ONLY to EVI and EVI2. NDVI, NDRE, CIre,
NDWI, GNDVI, OSAVI have NO clamp and NO explicit denominator guard.** The cloud mask (s2cloudless
prob<30%) and the cropland mask ARE applied to all 8 indices. Verified line-by-line:

| # | Index | Formula (reflectance) | Denominator | Cloud+crop mask | Clamp / guard | Blow-up risk |
|---|---|---|---|---|---|---|
| NDVI | L101 | (B8−B4)/(B8+B4) | B8+B4 (sum≥0) | YES | **NONE** | low (bounded unless denom≈0) |
| EVI | L102–103 | 2.5(B8−B4)/(B8+6B4−7.5B2+1) | blue-band poly (can →0/neg) | YES | **|≤1| clamp, L111** | GUARDED |
| EVI2 | L104 | 2.5(B8−B4)/(B8+2.4B4+1) | B8+2.4B4+1 | YES | **|≤1| clamp, L112** | GUARDED |
| NDRE | L105 | (B8−B5)/(B8+B5) | B8+B5 (sum) | YES | **NONE** | low–med (red-edge B5 can be small) |
| **CIre** | L106 | (B7/B5)−1 | **B5 alone (ratio)** | YES | **NONE** | **HIGH — unbounded ratio; same failure mode as the old EVI bug** |
| NDWI | L107 | (B8−B11)/(B8+B11) | B8+B11 (sum) | YES | **NONE** | low |
| GNDVI | L108 | (B8−B3)/(B8+B3) | B8+B3 (sum) | YES | **NONE** | low |
| OSAVI | L109 | (B8−B4)/(B8+B4+0.16) | B8+B4+0.16 | YES | +0.16 soft-guard (denom≠0) | lowest |

- Normalized-difference indices (NDVI/NDRE/NDWI/GNDVI) are mathematically in [−1,1] **only if** both
  bands ≥0 and denominator >0; with no guard they CAN go non-finite/extreme where both bands ≈0
  (deep shadow / water / fill). **CIre is the genuine gap** (ratio with the red-edge denominator,
  no bound, no guard) — A1 must measure its max and non-finite count.
- Clamp stage: server-side in GEE **before** the median composite + reduceRegions (so only post-clamp
  district aggregates are saved; see §3).
- Same `s2_index_image()` is reused by T2 (`indices_*.csv`), the crop-specific extraction
  (`p2_cropmask_indices.py` → `crop_specific_indices_*.csv`, NDVI/NDRE/EVI) and the plains test
  (`p7_test_plains.py`) → the clamp gap is identical everywhere.

## 1. Masking / cleaning steps by stage (from code)
- **Cloud mask:** `img.updateMask(prob.lt(30))` (s2cloudless `COPERNICUS/S2_CLOUD_PROBABILITY`), L98 —
  applied to the scene before all index math → all 8 indices. (cp25/03b also used s2cloudless<30 + QA60 fallback.)
- **Cropland+built-up:** `cropland_mask()` = WorldCover `Map==40` AND NOT `Map==50`, applied to the
  composite (L118) → all indices restricted to cropland, built-up excluded.
- **EVI/EVI2 clamp:** L111–112 only (see §0).
- **Compositing:** per-window **median** of the masked per-scene index images.
- **Reduction:** `reduceRegions` over district/plain polygons @30 m, reducer = mean/median/stdDev/P10/P90;
  CV=std/mean and range=P90−P10 derived client-side.
- **Soil (`t3_soil.py`):** SoilGrids depth-weighted 0–30 cm, ISRIC d_factors (clay/sand/silt/soc/phh2o/cfvo÷10,
  cec÷10, bdod÷100, nitrogen÷100); AWC via Saxton–Rawls (2006). No range clamp.
- **Topo (`t4_topography.py`):** SRTM elevation + ee.Terrain slope/aspect→north/eastness; TWI via MERIT upa. No clamp.
- **Climate (`src/cp25/03_fetch_ilce_climate.py` + `04_seasonal_features.py`):** NASA POWER daily →
  seasonal/window aggregates. Earlier 12.5× precip bug reportedly fixed — **A1 must measure precip totals**.

## 2. Artifact inventory (path · rows · cols · dtypes · stage)
### Spectral indices — CLEANED (post-clamp aggregates); RAW pre-clamp NOT persisted
| file | rows | cols | stage |
|---|---|---|---|
| `enrichment_v2/outputs/indices_{bugday,aycicegi}.csv` | 232 | 172 | 8 idx × 3 win × 7 metric, post-clamp district aggregates |
| `enrichment_v2/outputs/crop_specific_indices_{bugday,aycicegi}.csv` | 232 | 67 | NDVI/NDRE/EVI × 3 win × 7 metric, crop-masked |
| `enrichment_v2/outputs/plains_test_summary.csv` | 16 | 18 | 2 plains × 8 yr peak NDVI/EVI/NDRE |
| `enrichment_v2/outputs/t2_evi_clamp_diagnostic.csv` | 2 | 6 | **EVI clamp impact counts** (representative window/crop) |
- ⚠️ **Raw, pre-clamp per-pixel/per-scene index values are NOT saved** (clamp is server-side pre-composite).
  Only the EVI clamp DIAGNOSTIC counts exist (one representative window per crop: wheat 67,662 px @
  2017 peak; sunflower 2,037 px @ 2017 peak). A1 can OPTIONALLY re-extract a small sample with all
  clamps DISABLED (into audit/) to quantify the true per-index raw anomaly rate — esp. for CIre.

### Climate
| file | rows | cols | stage |
|---|---|---|---|
| `data/processed/openmeteo_ilce/nasapower_ilce_*.csv` (×29) | 8036 (daily) | 9 | RAW daily NASA POWER 2004–2025 (T2M_MAX/MIN/T2M, PRECTOTCORR, ALLSKY_SFC_SW_DWN, GWETROOT, WS10M, RH2M) |
| `data/processed/calibration_features_layerA.csv` | 1165 | 20 | CLEANED seasonal climate features + target (Paper-1) |

### Soil / Topography
| file | rows | cols | stage |
|---|---|---|---|
| `data/processed/soil_ilce.csv` | 29 | 23 | original SoilGrids (Paper-1) |
| `enrichment_v2/outputs/soil_features.csv` | 29 | 31 | enriched 0–30 cm + AWC |
| `enrichment_v2/outputs/topo_features.csv` | 29 | 8 | elevation/slope/northness/eastness/TWI |

### Target (yield) / Anomaly / Paper-1 matrices
| file | rows | cols | stage |
|---|---|---|---|
| `data/external/tuik/tuik_ilce_yields_clean.csv` | 1165 | 10 | TÜİK yields 3 provinces (verim_kg_da, uretim_ton) |
| `data/external/tuik/tuik_ilce_yields_full_referans.csv` | 1428 | 10 | TÜİK yields 4 provinces (+İstanbul-Thrace) |
| `enrichment_v2/outputs/anomaly_{bugday,aycicegi}.csv` | 232 | 173 | per-district z-scores + yield_z |
| `data/processed/calibration_features_layer{A,B,C}.csv` | 1165/422/422 | 20/27/45 | original Paper-1 feature matrices |
- TÜİK files DO carry `verim_kg_da` + `uretim_ton` (yield present). All `float64` numeric except id/name/crop strings.
- `reports/cp25/*_results.csv` (×3): published metric tables (not features) — comparison references.

## 3. Coverage gaps to carry into A1
- RAW pre-clamp index values not persisted → A1 reports this + optional disabled-clamp sample re-extraction.
- Per-scene cloud-free observation COUNT behind each composite is not saved → cannot directly audit
  "insufficient obs" per window (B7) from saved files; would need re-extraction.
- Index files cover 2017–2024 only (Sentinel-2 era); climate/yield 2004–2025.

## 4. A1 plan (after "devam")
Run B1–B9 on the rawest available representation (the post-clamp aggregates for indices, plus the
clamp diagnostic + an optional disabled-clamp sample for CIre/NDRE/NDWI/GNDVI/OSAVI), and the
raw daily climate / soil / topo / yield files. Produce DATA_QUALITY_AUDIT.md, feature_summary.csv,
flagged_records.csv (+ raw_sample_anomaly_rates.csv if re-extraction is run).
