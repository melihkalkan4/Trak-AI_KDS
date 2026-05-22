# Reproducibility — FLOV pipeline

This document is the canonical "how to rebuild and verify the
Forward-Looking Operational Validation pipeline from a clean checkout"
recipe. If anything in the codebase contradicts this file, **the code
wins** — please open an issue.

## 1. Environment

Captured 2026-05-22 from the active project venv:

| component | version |
|---|---|
| OS | Windows 11 (Home Single Language 10.0.26200) |
| Python | 3.13.2 |
| TensorFlow | 2.21.0 |
| Keras | 3.13.2 |
| NumPy | 2.4.3 |
| pandas | 3.0.1 |
| SciPy | 1.17.1 |
| scikit-learn | 1.8.0 |
| XGBoost | 3.2.0 |
| Streamlit | 1.57.0 |
| Plotly | 6.7.0 |
| loguru | 0.7.3 |
| pyarrow | 24.0.0 |
| earthengine-api | 1.7.17 |
| eemont | 2025.7.1 |
| cdsapi | (installed, version metadata not exposed) |

> The frozen-artefact contract was generated on this exact environment.
> If you bump TensorFlow or Keras, the `.keras` archive may still load,
> but the integrity ledger will keep guaranteeing the *file* did not
> change — not that the framework's numerical outputs are bit-identical.

## 2. Frozen artefact hashes (SHA-256)

These are the values committed in `logs/model_integrity.jsonl` at the
time of writing. Any deviation aborts the validation pipeline at load:

```
lstm_champion_sunflower      43ef61b5a70f16cd935818c0c7a19da70cc08ec4417b16cecc20f03b6c26c361
xgb_yield_sunflower          9cc638a6a9519022b04759ceb067fdcc085f9dab4c02229d30c1a7816a4b9a45
scaler_sunflower             1212fc50813668f5d4387c3ac3b303f033443ce34806f51a76375ea51041126d
yield_xgb_sunflower          1b8f2a14404f87adeb0bad67dc6307228e4959e4405f16cd9400e197d273ee1b
yield_scaler_sunflower       53e405f78848b6d8b68116db01ac90c8b718dbee6f38b2ae11f541b8c2821dae
feature_names                8d1948d9824fb54c9b04c886851343577a37a2e5be0f9ac6782fdb50642fc168
xgb_feature_names_sunf       62724be6ab8fc698e30641bf4000860c65cc403e7bef83f2572d4eeaee75ece4
sunflower_doy_climatology    3cd26360ff416fc3cd5d98f78a75be2b7fc143fde930f7721221109366531c16
```

## 3. Secrets / credentials

| service | location | how to obtain |
|---|---|---|
| Google Earth Engine | `keys/trak-ai-kds-d3e5e5b6e168.json` | service-account JSON; required for S2 and SoilGrids fetchers |
| Copernicus CDS | `~/.cdsapirc` | run `python scripts/setup_cds_credentials.py` once |

The CDS endpoint is the *beta* URL: `https://cds-beta.climate.copernicus.eu/api`.

## 4. Build / verify recipe

```bash
# 1. Create venv (Windows)
py -3.13 -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt

# 2. Configure CDS once
./venv/Scripts/python.exe scripts/setup_cds_credentials.py

# 3. Verify the frozen-model contract (no fetch, no predict — just hashes)
./venv/Scripts/python.exe scripts/phase1_health_check.py

# 4. Build / refresh the DOY climatology baseline (idempotent)
./venv/Scripts/python.exe scripts/build_climatology.py

# 5. Fetch the prospective window for site EVR_01, year 2025
./venv/Scripts/python.exe scripts/fetch_evr01_2025.py

# 6. Run the frozen LSTM in walk-forward mode
./venv/Scripts/python.exe scripts/predict_evr01.py --site EVR_01 --year 2025

# 7. Validate predictions vs actuals
./venv/Scripts/python.exe scripts/validate_evr01.py --site EVR_01 --year 2025 \
    --source unified --tolerance-days 2

# 8. View results
./venv/Scripts/python.exe scripts/run_flov_dashboard.py
```

The smoke-test path (no network, no CDS, no GEE) used during the
component-level tests is:

```bash
./venv/Scripts/python.exe scripts/predict_evr01.py --plumbing
./venv/Scripts/python.exe scripts/smoke_validate_2024.py
```

These run entirely off the 2017-2024 master CSV and the
`X_sunflower.npy` training tensor; useful for CI and for verifying that
a new venv reproduces the published numbers within ±1 ULP.

## 5. Output layout

```
data/
  cache/api/                 # hash-keyed pickle cache (idempotent)
  historical/climatology/    # DOY baseline parquet
  prospective/<year>/<site>_unified_features.parquet
reports/
  prospective/<site>_<year>_predictions.parquet
  prospective/<site>_<year>_predictions.csv
  prospective/<site>_<year>_validation.csv
  prospective/<site>_<year>_validation_per_stage.csv
  prospective/<site>_<year>_validation_summary.json
logs/
  flov.log                   # 100 MB rotation, zipped after roll
  api_audit.jsonl            # one line per external request
  model_integrity.jsonl      # append-only artefact ledger
  alerts.jsonl               # append-only alert journal
```

## 6. Audit checks anyone can run

```bash
# How many CDS / GEE calls did we make and how long did they take?
jq -r '. | "\(.ts_utc) \(.source) \(.status) \(.latency_s)s cache=\(.cache_hit)"' logs/api_audit.jsonl

# Did the frozen artefacts drift at any point?
jq -r '. | "\(.role) \(.status) \(.sha256[0:16])"' logs/model_integrity.jsonl | sort -u

# What alerts has the model raised this season?
jq -r '. | "\(.target_date) \(.severity) \(.stage) anom=\(.anomaly)"' logs/alerts.jsonl
```

(`jq` is not a hard dependency — `pandas.read_json(..., lines=True)`
works equivalently.)

## 7. Limitations of the current numbers

* **2024 smoke (`smoke_validate_2024.py`)** runs on the *training era*.
  R² ≈ 0.62 vs persistence R² ≈ 0.57 here is plumbing evidence only —
  it proves the validator runs end-to-end. It is **not** a held-out
  performance claim.
* **2025 prospective run** is the genuine held-out test. It requires
  the ERA5 fetch to finish (Jan 2025 onward). Numbers are written to
  the `*_validation_summary.json` and surfaced verbatim in the
  dashboard / thesis tables.
* **Pilot site coordinates are placeholders** until Phase 6's farmer
  ground-truthing. The integrity contract is unaffected (lat/lon do
  not enter the LSTM input vector), but per-site metrics will refresh
  once real coords land in `EVRENLI_SITES`.

## 8. Multi-Modal Visual Validation — frozen + new artefacts

Companion methodology: [`docs/MULTIMODAL_VALIDATION_METHODOLOGY.md`](MULTIMODAL_VALIDATION_METHODOLOGY.md).

| role | path | status | hash policy |
|---|---|---|---|
| YOLOv8s-cls field classifier | `models/crop_health_best.pt` | FROZEN | SHA-256 computed at load (`FieldYOLOv8Predictor.model_sha256`); the existing FLOV integrity ledger appends a row whenever the wrapper loads. |
| ResNet50 satellite stress classifier | `models/visual/satellite_cnn_resnet50.pt` | NEW — pending Planet Education key | Trained in `notebooks/06_satellite_cnn_training.ipynb`; the notebook writes `satellite_cnn_metrics.json` with `model_sha256`. Record that hash here when the file lands. |
| LSTM + XGBoost (reused via FLOV) | `models/*` (see §2) | FROZEN | Same SHA-256 contract as the rest of FLOV. |

### Visual pipeline rebuild recipe

```bash
# 1. Wrapper smoke (no network, no Planet key needed)
python -c "from visual_validation.models.field_yolov8 import FieldYOLOv8Predictor; print(FieldYOLOv8Predictor().model_sha256[:16])"

# 2. Run cross-modal validator over a window (2-of-3 fallback if no Planet/ResNet)
python scripts/run_cross_modal_validation.py --site EVR_01 \
    --start 2026-05-01 --end 2026-05-22 --step 5

# 3. Inspect results
ls data/visual/consensus_predictions/
tail -n 5 logs/visual_consensus.jsonl
tail -n 5 logs/visual_consensus_alerts.jsonl

# 4. Annotate field photos for the YOLOv8 evaluator
streamlit run scripts/annotate_field_photos.py
```

### New audit streams

```
logs/visual_field_yolov8.jsonl        # one row per YOLOv8 inference
logs/s2_chip_audit.jsonl              # one row per Sentinel-2 chip fetch
logs/planet_api_status.jsonl          # Planet API stub heartbeat
logs/visual_consensus.jsonl           # one row per (site, date) consensus
logs/visual_consensus_alerts.jsonl    # one row per alert raised
data/visual/consensus_predictions/<site>_<date>.json  # per-decision snapshot
```
