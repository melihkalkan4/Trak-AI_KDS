# Mock Data Audit — FLOV pipeline & broader KDS

**Audit date:** 2026-05-22
**Scope:** Identify every site in the codebase where simulated /
placeholder / fallback data feeds a user-visible decision, and grade
whether it blocks the FLOV thesis claim.

The FLOV thesis claim is: *"a frozen 2017-2024 sunflower champion
delivers measurable skill on truly held-out 2025-2026 data at five
Vize/Evrenli sites."*  Anything that touches the inputs or outputs of
that loop is in-scope.

## 1. Verdict summary

| Layer | Mock data present? | Blocks FLOV thesis? |
|---|---|---|
| **FLOV inference & validation** (`src/prospective_validation/*`) | **No, except site coords** | **Coords-only blocker** (see §2) |
| Frozen model artefacts | No | No (hash-locked) |
| Climatology baseline | No | No (built from real 2017-2024 master CSV) |
| Sentinel-2 fetcher | No (real GEE) | No |
| ERA5 fetcher | No (real CDS) | No |
| SoilGrids fetcher | No (real GEE) | No |
| Alerts engine | No | No |
| Streamlit FLOV dashboard | No (reads only real artefacts) | No |
| **Broader KDS demo app** (`src/dashboard.py` + `src/database.py`) | **Yes, extensively** | **No** (out-of-scope; demo only) |
| Image classifier | Yes, fallback | No (out-of-scope) |
| Rover MQTT | Yes, test publisher | No (out-of-scope) |

## 2. Blocker: pilot site coordinates

**File:** `src/prospective_validation/config.py:101-107`

```python
EVRENLI_SITES: Final[tuple[Site, ...]] = (
    Site("EVR_01", "Kendi tarlam",  41.045, 27.205, "self",       12.5),
    Site("EVR_02", "Komşu tarla 1", 41.048, 27.210, "neighbor_1",  8.0),
    Site("EVR_03", "Komşu tarla 2", 41.043, 27.198, "neighbor_2", 15.0),
    Site("EVR_04", "Komşu tarla 3", 41.050, 27.215, "neighbor_3", 10.0),
    Site("EVR_05", "Komşu tarla 4", 41.040, 27.200, "neighbor_4",  7.5),
)
```

**Status:** PLACEHOLDER coordinates — they are physically reasonable
points near Vize/Evrenli (NW Türkiye), but they are NOT the actual
parcel centroids of the 5 farmer plots.

**Why it's a blocker:** The 2025/2026 prospective metrics are
reported *per site* in the validation summary and dashboard.  If the
coordinates are off by tens of metres, the 30 m inward buffer plus
S2 10 m pixel grid can shift which actual pixels enter the
"cloud-free overpass" timeseries, mostly affecting `EVR_01` (1.25 ha,
already sub-pixel-flagged).

**How to unblock:** Replace the 5 tuples with real `lat`, `lon`, and
`area_da` values measured from the farmer parcel polygons (KML / GeoJSON
from the field walk). No other code in the FLOV pipeline needs to
change — the `Site` dataclass and `geometry.site_polygon_coords` already
consume those three fields.

**Optional improvement (not blocking):** swap the square-approximation
in `geometry.py` for the true parcel polygon (Shapely) once the
field-walk produces vector boundaries. The current square is correct
to within ±3 m of the real parcel for the placeholder areas.

## 3. Mock data OUTSIDE FLOV (not a thesis blocker)

These are part of the broader TRAK-AI KDS Streamlit demo app, which is
a separate code path from `src/prospective_validation/*`. They exist
so that the demo runs end-to-end before real backend services are
provisioned; they DO NOT touch the FLOV pipeline.

### 3.1 `src/database.py` — demo DB seeder
| Function | What it generates |
|---|---|
| `_MOCK_TARLALAR` (line 144) | 4 demo field rows |
| `_generate_mock_weather` (line 371) | Synthetic 20-Mar → 20-May-2026 weather log |
| `_generate_mock_scans` (line 469) | Fake rover scan history |
| `_MOCK_TAHMINLER` (line 583) | Static "last prediction" cards |

Versioned by `MOCK_VERSION = "2"`; bumping it wipes and re-seeds.
These should be replaced by real Postgres rows once the operational
backend is live, but they are clearly labelled and isolated.

### 3.2 `src/image_classifier.py` — YOLO fallback
Falls back to `_mock_result()` when:
* `ultralytics` is not installed
* the trained YOLO checkpoint is missing
* model loading raises

The fallback returns a `random.choices`-weighted label with a
confidence in `[0.65, 0.95]` and tags the result `mock=True`. The
orchestrator (`mqtt_orchestrator.py:320`) appends `[MOCK]` to its log
line so downstream consumers cannot accidentally treat the synthetic
result as truth.

### 3.3 `src/mqtt_test_publisher.py` — rover stub
Test-only publisher that emits synthetic rover MQTT payloads to
exercise `mqtt_orchestrator.py`. Never imported by the FLOV pipeline.

### 3.4 `src/dashboard.py` — KDS demo
Renders the mock DB rows. The `YOLOv8 ⚠️ MOCK` banner (line 181) and
the "Mock Veri Paneli" sub-page (line 543) explicitly disclose this to
the demo user.

## 4. Action items

Priority is "FLOV thesis publish-readiness" only.

| # | Action | File | Owner |
|---|---|---|---|
| 1 | **Replace placeholder lat/lon/area_da** with real parcel measurements | `src/prospective_validation/config.py:101-107` | Field walk |
| 2 | Optional: swap square polygon for true parcel boundary (Shapely) | `src/prospective_validation/geometry.py` | Phase 6+ |
| 3 | Re-run the integrity ledger after any coord change (lat/lon do not enter the LSTM tensor, so model hashes stay stable; only the audit will note a code diff) | n/a | automatic |

**Nothing else in the FLOV pipeline uses mock data.** The thesis
report can cite this audit document and proceed with the 2025-2026
prospective numbers as soon as the field-walk coordinates land.

## 5. How to re-run this audit

```bash
# Show every mock / placeholder hit in the FLOV module
grep -nrEi "(mock|fake|dummy|simulate|placeholder|random\.|np\.random)" \
     src/prospective_validation/

# And in the broader src/ for completeness
grep -lEi "(mock|fake|dummy|simulate|placeholder|random\.|np\.random)" \
     -r src/
```
