# Multi-Modal Visual Validation — Methodology

**Subsystem:** `src/visual_validation/`
**Status:** Phase 1-8 scaffold complete; satellite ResNet50 awaits Planet Education API key
**Companion doc:** `docs/FLOV_METHODOLOGY.md` (the upstream LSTM+XGBoost pipeline)

---

## 1. Purpose

The TRAK-AI DSS already exposes a single-modality FLOV (LSTM + XGBoost on
NDVI/EVI/NDWI features).  This subsystem adds **two more independent
observation channels** and a 3-way consensus engine so the operator can
distinguish:

- a true crop stress event (all modalities agree),
- a satellite artefact (cloud/atmosphere) that the ground denies,
- an equipment failure (sensor drift while vision agrees on healthy),
- a pre-symptomatic anomaly (features see it before vision does), and
- a localised disease outbreak (field photo flags disease before the
  satellite or features can).

## 2. The three modalities

| # | Modality | Model | Status | Output |
|---|----------|-------|--------|--------|
| 1 | PlanetScope (3 m RGB) / Sentinel-2 stand-in | ResNet50 transfer-learning | **NEW** — trained on Colab | 3 classes |
| 2 | ESP32-CAM field photos | YOLOv8s-cls `crop_health_best.pt` | **FROZEN** | 6 raw classes |
| 3 | Numerical features | LSTM + XGBoost (FLOV champion) | **FROZEN** | NDVI scalar → z-score |

YOLOv8 and the LSTM+XGBoost are **never** retrained inside this
subsystem — they are wrapped, hashed (SHA-256), and only inferred.

## 3. Harmonized 4-class taxonomy

Every modality output is mapped to one of four canonical labels before
the consensus engine ever sees it.

```
healthy | mild_stress | severe_stress | disease
```

Mapping tables live in `src/visual_validation/config.py`:

- `YOLOV8_TO_HARMONIZED`  (Turkish raw labels → harmonized)
- `SATELLITE_TO_HARMONIZED`  (3-class — disease is NOT a satellite class)
- `feature_zscore_to_class(z)`  (z >= -1 → healthy, -2 <= z < -1 → mild,
  z < -2 → severe)

### Why "disease" is field-only

Leaf-scale disease lesions are smaller than a 3 m PlanetScope pixel and
have no characteristic NDVI signature in the early days.  Letting only
the field modality emit "disease" prevents a confusing 3-way DISAGREE
on incipient disease events.

## 4. Consensus algorithm

Implemented in `src/visual_validation/consensus/decision_engine.py`.

1. Collect 1-3 `ModalityPrediction` objects (each carrying harmonized
   class + confidence).
2. **Single-modality fast path** if only one is present — flag the
   result as `SINGLE`, mark provisional.
3. **Weighted vote** otherwise:
   `score(label) = Σ w_modality × confidence_modality`
   Default weights: `satellite=0.30, field=0.40, features=0.30`
   (re-normalised when a modality is missing).
4. **Agreement type**: UNANIMOUS / MAJORITY / TIE / DISAGREE / SINGLE.
5. **Confidence bucket** (`HIGH` / `MEDIUM` / `LOW`) — combines the
   normalised top score with the agreement type.
6. **Flag** (one of the eight `CONSENSUS_FLAGS` keys) — chosen by an
   explicit if-ladder over the modality-class combinations, including
   the named patterns: `EARLY_WARNING`, `INVESTIGATE`,
   `SATELLITE_FALSE`, `EQUIPMENT_FAIL`.

## 5. Agreement metrics

`src/visual_validation/consensus/agreement_metrics.py`:

- **Cohen's Kappa** (`cohens_kappa`) for every pairwise modality combo
  over the records where both modalities reported.
- **Fleiss' Kappa** (`fleiss_kappa`) for the 3-way agreement matrix
  (only records where all three modalities are present).
- **Confusion matrix** (`confusion_matrix`) per pair.
- **Disagreement patterns** (`disagreement_patterns`) — top class-pairs
  that disagree most.
- **Interpretation** via Landis & Koch (1977) bands.

These metrics drive the rolling re-calibration check that re-tunes
`MODALITY_WEIGHTS` once enough labelled observations are collected.

## 6. Anomaly flagger → operator alert

`src/visual_validation/consensus/anomaly_flagger.py` turns a
`ConsensusResult` into a `ConsensusAlert` with:

- bilingual EN/TR messages,
- a recommended action list,
- a severity that is **escalated one step** when the field is in
  `flowering` or `grain_filling` (mirrors FLOV's stage-aware policy).

Alerts are appended to `logs/visual_consensus_alerts.jsonl`.

## 7. ESP32-CAM integration

The orchestrator at `src/mqtt_orchestrator.py` already subscribes to the
combined rover payload (`trakaia/rover/data`).  We do **not** duplicate
that listener.  Instead, the existing `on_message` should call:

```python
from visual_validation.api_clients.esp32_cam_listener import (
    publish_field_prediction_from_payload,
)
publish_field_prediction_from_payload(payload, mqtt_client)
```

That helper:

1. Decodes the base64 JPEG.
2. Runs `FieldYOLOv8Predictor.predict_from_base64(...)`.
3. Saves the photo + writes a JSONL audit row to
   `logs/visual_field_yolov8.jsonl`.
4. Optionally re-publishes the harmonized result on
   `trakaia/visual/field` so other clients can subscribe.

## 8. The satellite gap (Planet Education API)

The Planet API key application is pending.  In the interim:

- `api_clients.planet_client.PlanetClient` raises `NotImplementedError`
  on every network call (the public surface stays stable).
- `api_clients.sentinel2_imagery.fetch_rgb_chip(...)` pulls Sentinel-2
  L2A RGB thumbs via Google Earth Engine.
- `fetch_rgb_chip_stub(...)` makes a labelled synthetic chip for CI.
- The orchestrator (`CrossModalValidator`) auto-detects missing weights
  via `models.satellite_cnn.load_predictor()` and falls back to 2-of-3
  voting without code changes.

When the key arrives:

1. Replace the stubbed search/download in `planet_client.py`.
2. Train ResNet50 in `notebooks/06_satellite_cnn_training.ipynb`.
3. Drop `satellite_cnn_resnet50.pt` into `models/visual/`.
4. The pipeline starts emitting the satellite vote automatically.

## 9. Audit trails

| Stream | Location |
|--------|----------|
| Field YOLOv8 inferences | `logs/visual_field_yolov8.jsonl` |
| Satellite chip fetches | `logs/s2_chip_audit.jsonl` |
| Planet API status pings | `logs/planet_api_status.jsonl` |
| Per-(site,date) consensus | `logs/visual_consensus.jsonl` |
| Alerts | `logs/visual_consensus_alerts.jsonl` |
| Per-(site,date) snapshot | `data/visual/consensus_predictions/<site>_<date>.json` |

Each row carries the model SHA-256 the prediction was produced by, the
modality source string, and the UTC timestamp.

## 10. Mock/synthetic data audit

The only intentional synthetic input is `fetch_rgb_chip_stub(...)` (a
flat grey chip with a small green blob) which exists for CI.  Stubs are
labelled `source: "stub"` on the chip and `source: "synthetic"` in the
audit trail; no operator-facing dashboard ever displays them as real
observations.  The Planet client is a hard `NotImplementedError` —
there are no mock Planet payloads anywhere in the codebase.

## 11. How to run

End-to-end batch (no Planet key needed):
```
python scripts/run_cross_modal_validation.py \
    --site EVR_01 --start 2026-05-01 --end 2026-05-22 --step 5
```

Field-photo annotation UI:
```
streamlit run scripts/annotate_field_photos.py
```

Notebooks (run from `notebooks/`):
- `06_satellite_cnn_training.ipynb`     (Colab — when chips & key are ready)
- `07_field_photo_yolov8_eval.ipynb`     (read-only YOLOv8 evaluation)
- `08_cross_modal_consensus_analysis.ipynb` (Cohen + Fleiss + flag dist.)

## 12. Limitations

- ResNet50 weights are not produced yet → the satellite vote is
  optional today.  The 2-way (field + features) fallback retains all
  flag semantics except `SATELLITE_FALSE` (impossible without sat).
- Disease is field-only by design — outbreaks that escape the rover's
  imaging swath will not be caught until the rover revisits the parcel.
- The climatology `σ_NDVI` fallback (0.07) is used when the DOY table
  has gaps; document this in REPRODUCIBILITY when re-running.
