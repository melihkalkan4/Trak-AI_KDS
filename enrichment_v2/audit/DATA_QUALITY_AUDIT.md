# DATA QUALITY AUDIT — TRAK-AI (READ-ONLY)

> Read-only audit. Nothing modified; all outputs in `enrichment_v2/audit/`. Rollback = delete that
> folder. Every number is measured from a real file (scripts: `code/audit_a1.py`,
> `code/audit_raw_sample.py`). Companion files: `feature_summary.csv`, `flagged_records.csv`,
> `raw_sample_anomaly_rates.csv`, `collinear_pairs.csv`, `INVENTORY.md`.

## EXECUTIVE SUMMARY — verdict per feature family
| Family | Verdict | One-line |
|---|---|---|
| Spectral indices | **FLAGS (code GAP, no garbage in outputs)** | clamp/guard only on EVI/EVI2; CIre/NDRE/NDWI/GNDVI/OSAVI unguarded — but measured out-of-bounds = **0** in saved aggregates AND in raw clamp-disabled pixels (masking+median suppress the failure mode) |
| Climate | **CLEAN** | precip/GDD/temp/aridity all plausible; **no 12.5× precip bug** (raw annual 307–965 mm, mean 594) |
| Soil | **CLEAN** | all in physical range; texture sums = 100%; AWC 0.138–0.154 |
| Topography | **CLEAN** | elevation 39–442 m, slope 2.3–5.6°, north/eastness ∈ [−1,1], TWI 7.8–9.4 |
| Target (yield) | **CLEAN** | wheat 147–589, sunflower 52–372 kg/da; no zeros/neg/>5×IQR outliers |
| Anomaly z | **CLEAN** | max|z| = 2.47; no |z|>5, no non-finite |
| Coverage | **FLAGS** | 25.1% NaN in index location-metrics (window-years with no cloud-free S2); 29 districts, 0 dup |
| Structural | **NOTE** | 0 constant features; 217 collinear pairs |r|>0.98 (expected; informational) |

## ⭐ #1 QUESTION ANSWERED — clamp / denominator-guard coverage
**From code (`ev2_common.py:s2_index_image`, verified line-by-line): the |value|≤1 clamp is applied
ONLY to EVI (L111) and EVI2 (L112). NDVI, NDRE, CIre, NDWI, GNDVI, OSAVI have NO clamp and NO explicit
denominator guard.** Cloud mask (s2cloudless<30%) and cropland mask ARE applied to all 8 indices.
- **CIre = (B7/B5)−1** is the genuine gap: a ratio with the red-edge denominator, unbounded, unguarded —
  the same failure mode that produced the old EVI≈4.47e9.
- **However, measured impact = none in this pipeline.** Across 4 sampled districts (Demirköy 761,
  Kofçaz 11 888, Pehlivanköy 9 478, Hayrabolu 113 232 cropland px), with the clamp DISABLED, every
  index has **0 out-of-bounds pixels** at the cropland-median-composite level; CIre max 5.09–7.86
  (legitimate high canopy, not a blow-up). The cloud+cropland mask + per-window median composite
  remove the deep-shadow/water/fill pixels where denominators collapse, so the gap does not manifest
  as garbage. (`raw_sample_anomaly_rates.csv`.)
- The one place raw values DO exceed bounds: **raw EVI at 30 m, Hayrabolu = 36 / 1 246 884 px (0.003%),
  max 1.019** — i.e. the clamp IS doing real, if tiny, work; the gap matters only for EVI-type
  denominators, and only EVI/EVI2 are guarded.
- **Recommendation (no fix applied — audit only):** add the same `|value|≤1` guard (and a non-finite
  drop) to NDRE/NDWI/GNDVI/OSAVI and a sane upper bound to CIre, for robustness against future,
  less-masked ROIs. Today's saved features are clean; this is preventive.

## B1 — index range (saved post-clamp aggregates, both crops, n=464 district-window-years)
| index | clamp | min | max | mean | NaN% | nonfinite | OOB | extreme>1e3 |
|---|---|---|---|---|---|---|---|---|
| NDVI | N | −0.340 | 0.910 | 0.417 | 25.1 | 0 (only NaN) | 0 | 0 |
| EVI | Y | −0.105 | 0.855 | 0.294 | 25.1 | 0 | 0 | 0 |
| EVI2 | Y | −0.098 | 0.793 | 0.274 | 25.1 | 0 | 0 | 0 |
| NDRE | N | −0.379 | 0.754 | 0.276 | 25.1 | 0 | 0 | 0 |
| **CIre** | **N** | −0.485 | **5.781** | 0.936 | 25.1 | 0 | 0 (within [−1,10]) | 0 |
| NDWI | N | −0.316 | 0.754 | 0.023 | 25.1 | 0 | 0 | 0 |
| GNDVI | N | −0.340 | 0.840 | 0.471 | 25.1 | 0 | 0 | 0 |
| OSAVI | N | −0.152 | 0.705 | 0.295 | 25.1 | 0 | 0 | 0 |
(“nonfinite” counts only NaN here; there are 0 inf/−inf and 0 |value|>1e3.)

## B2 — distribution-metric consistency
- P10 ≤ median ≤ P90 violations: **0**. std<0: **0**. range<0: **0**.
- **CV instability (REAL flag):** CV = std/mean explodes where the index mean ≈ 0. **NDWI max|CV| = 708**
  (NDWI mean ≈ 0.023), CIre max|CV| = 25.5; **465 non-finite CV cells** across indices (mean≈0).
  → the `*_cv` features for low-mean indices (esp. NDWI) are unstable and should be dropped/guarded.

## B3 — climate (CLEAN; the 12.5× precip bug is NOT present)
- season precip 85.5–879.5 mm (mean 365); winter 74–613; flowering 0–121; grain-fill 0–129 — all plausible.
- GDD 1938–4716; aridity 0.1–1.1; flowering t2m 13.9–29.8 °C. OOB = 0 for all.
- RAW daily annual precip (29 districts): 307–965 mm, mean **594 mm** (Trakya ≈ 550–640). No 10–12× scale error.

## B4 — soil (CLEAN)
pH 6.58–7.31; SOC 15.9–26.8; CEC 21.8–27.4; bulk density 1.357–1.444; cfvo 8.8–15.7; **AWC 0.138–0.154**;
clay 30.5–38.1, sand 26.2–35.0, silt 33.4–41.8. clay+sand+silt = 100.0 for all 29 (0 rows off >5%).

## B5 — topography (CLEAN)
elevation 39.2–441.7 m; slope 2.29–5.57°; northness −0.241–0.070; eastness −0.118–0.105; TWI 7.80–9.40. OOB=0.

## B6 — yield + anomaly (CLEAN)
- wheat verim 147–589 kg/da (mean 385, n=652); sunflower 52–372 (mean 206, n=641). 0 zeros/negatives; 0 >5×IQR outliers.
- anomaly z: 225 z-columns, max|z| = 2.47, |z|>5 = 0, non-finite = 0.

## B7 — coverage (FLAG: missingness)
- **25.1% NaN** in index location-metrics — district-window-years with no cloud-free S2 behind the
  median composite (esp. greenup/winter windows). Not garbage, but a real completeness gap; per-composite
  cloud-free observation COUNT is not persisted, so insufficient-obs cannot be audited from saved files.
- 29 Trakya districts present in both crops; 0 duplicate district-year rows.

## B8 — structural
- Constant / zero-variance index features: **0**.
- |r|>0.98 collinear index-feature pairs: **217** (`collinear_pairs.csv`) — expected (mean≈median,
  range≈P90−P10, indices intercorrelated); informational, handled downstream by T7 selection.
- Spatial support note: indices/soil/topo use admin-polygon cropland (this work); the original Paper-1
  district NDVI used adaptive point-buffers — different support, not directly comparable per-cell.

## PRIORITISED ANOMALIES (real garbage vs benign)
**REAL / actionable:**
1. **Clamp-guard code GAP** for CIre/NDRE/NDWI/GNDVI/OSAVI (CIre highest risk). Today: 0 garbage in
   outputs (masking+median protect it), but unguarded → preventive guard recommended.
2. **NDWI `_cv` (and low-mean-index CV) instability** — max|CV|=708, 465 non-finite CV cells. Drop/guard CV for NDWI.
3. **25.1% NaN** in index features (cloud-free-coverage gaps) — affects model completeness, not value validity.
4. **Raw EVI >1 in 0.003% px** — confirms the EVI clamp is necessary and is working (removes them).

**BENIGN:**
- CIre max 5.78 / 7.86 = legitimate dense-canopy values, not blow-ups.
- 217 collinear pairs — inherent to distribution metrics of correlated indices.
- (Admin reorg Tekirdağ Merkez↔Süleymanpaşa: documented elsewhere; not a data-value error.)

## BOTTOM LINE
The enriched feature set is, as saved, **free of impossible/garbage values** (0 out-of-bounds across
all families; no 12.5× precip recurrence; no EVI blow-up recurrence). The single substantive code-level
risk — that the EVI/EVI2 clamp was **not** extended to CIre/NDRE/NDWI/GNDVI/OSAVI — is confirmed, but it
is currently masked by the cloud/cropland/median pipeline (measured raw OOB = 0). The actionable
follow-ups are: extend the guard (preventive), and drop/guard the unstable low-mean CV features (NDWI).
