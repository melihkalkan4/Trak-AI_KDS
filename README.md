# TRAK-AI KDS

**An offline-first Edge–Fog–Cloud decision-support system for precision agriculture in Trakya, Türkiye (winter wheat & sunflower).**

*Tarımsal Karar Destek Sistemi — Trakya'da buğday ve ayçiçeği için çevrimdışı-öncelikli Edge–Fog–Cloud karar destek sistemi.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
Release: **v1.0.0**

TRAK-AI acquires in-situ field data with a low-cost ESP32 rover, runs all inference, retrieval and
language generation locally on a laptop-class host, and uses the cloud only for cache-backed acquisition
of Earth-observation and reanalysis inputs — so the full decision loop runs on CPU-only hardware **without
a network connection once inputs are cached**. Its design is deliberately *honesty-aware*: where machine
learning does not demonstrably beat a transparent statistical baseline, the system says so and defers to
the baseline.

---

## Architecture

```
EDGE   ESP32-WROOM-32 rover — soil moisture (SEN0193), air temp/humidity (DHT22),
       obstacle (HC-SR04), GPS (NEO-6M), ESP32-CAM (JPEG capture) → MQTT telemetry
         │  (trakaia/rover/data)
FOG    Laptop host — NDVI forecasting (LSTM), layered yield estimation, YOLOv8 crop-health
       classification, Tri-RAG advisory + local LLM (Gemma-3-4B via Ollama), MQTT orchestrator
       with a human-in-the-loop approval queue, offline-first SQLite store, Streamlit dashboard
         │  (trakaia/kds/advisory, trakaia/db/pending)
CLOUD  Cache-backed acquisition only — Sentinel-2 (Google Earth Engine), ERA5-Land (Copernicus CDS),
       ISRIC SoilGrids. Optional at run time.
```

## Subsystems

| Path | Component | Notes |
|---|---|---|
| `src/cp1_etl/` | Multi-modal ETL & fusion | Sentinel-2 + ERA5-Land + SoilGrids → master feature matrix (cached) |
| `src/cp2_model/` | NDVI 7-day forecasting | LSTM / Conv-LSTM / Attention-LSTM / XGBoost race; residual-delta, 17 features |
| `src/cp25/`, `models/cp25/` | Layered yield estimation | Climate → +NDVI → +soil tiers; honest baselines (climatology, persistence) |
| `src/image_classifier.py` | YOLOv8s-cls crop health | 6 classes; runs at fog tier on the ESP32-CAM image |
| `src/cp4_rag/` | Tri-RAG advisory | FAISS (e5-small) + BM25 + merge-boost; local Gemma-3-4B via Ollama |
| `src/mqtt_orchestrator.py` | Fog orchestrator | Rule-based anomaly detection → RAG/LLM → advisory; approval queue |
| `src/database.py`, `data/trakai.db` | Offline-first store | SQLite (WAL); dashboards read, services write |
| `src/dashboard.py` | Streamlit dashboard | 9 tabs; reads only from the local DB |
| `src/cp3_edge/trak_ai_rover/` | Rover firmware | C++/PlatformIO for ESP32-WROOM-32 |

## Key results (verified)

- **NDVI forecast (R²):** wheat 0.752, sunflower 0.796 (stacked LSTM champion; full model race reported).
- **District yield (MAPE, cross-validated):** wheat 16.4 % (LOYO) / 10.6 % (LOILO); sunflower 17.8 % / 13.5 %.
  Under out-of-year (LOYO) validation **no ML configuration beats a climatology baseline for winter wheat**
  (which is therefore the operational default); a multimodal model does add skill for sunflower.
- **Crop-health classifier:** 94.9 % top-1. *The drought-stress class is flagged as overfit (100 % on only
  360 images) and needs augmentation.*
- **Advisory:** 17,065 chunks over 64 documents; retrieval 10/10; end-to-end latency **27.1 s on CPU**.
- **Forward validation:** on a real surveyed parcel the frozen NDVI forecaster **does not beat a naïve
  persistence baseline** (reported transparently, not softened).

## Status & honest disclosures

This is a research prototype. The following components are placeholders or stubs and are **not** operational
as designed — disclosed here for transparency:

- **ESP32-CAM on-device classifier is a placeholder** (byte-size heuristic). The rover captures and
  transmits images only; crop-health inference runs at the fog tier.
- **The satellite-CNN modality of the cross-modal consensus is an untrained stub**, so that validator runs
  as a **two-of-three** consensus (field image + numerical features).
- The NDVI inference path falls back to the last training window when no live imagery is supplied.
- The advisory context currently injects a fixed soil profile rather than a per-parcel one.
- The rover waypoints and the demonstration site coordinates are placeholders; the single field-surveyed
  parcel used for analysis is separate.

## Requirements & quick start

- Python 3.11+ (see `requirements.txt`), a local **Mosquitto** MQTT broker (`localhost:1883`), and
  **Ollama** with the `gemma3:4b` model for the advisory layer.
- Cloud acquisition (`src/cp1_etl/`) needs Google Earth Engine and Copernicus CDS credentials.

```bash
# 1. Initialise the offline database
python scripts/init_database.py

# 2. Launch the dashboard (offline-first; reads from data/trakai.db)
streamlit run src/dashboard.py

# 3. (Optional) Run the fog orchestrator for live rover telemetry
python src/mqtt_orchestrator.py

# 4. (Optional) Hardware-free integration test
python trakaia_full_test.py
```

## Data, companion paper & code

- **Dataset:** Mendeley Data, DOI [10.17632/f6d29w5zjk.1](https://doi.org/10.17632/f6d29w5zjk.1) (CC-BY-4.0).
- **Companion methods paper:** Kalkan, M., Çavdaroğlu, G.Ç. *Spatial skill is not temporal skill: a
  cross-validation audit of satellite-driven winter-wheat and sunflower yield prediction in Trakya, Türkiye*
  (under review, International Journal of Engineering and Geosciences).
- **Companion reproducibility code:** Zenodo, DOI
  [10.5281/zenodo.21308764](https://doi.org/10.5281/zenodo.21308764) (MIT).

## How to cite

If you use this software, please cite the companion article and this repository:

```
Kalkan, M., & Çavdaroğlu, G. Ç. (2026). TRAK-AI KDS: an offline-first Edge–Fog–Cloud decision-support
system for precision agriculture in Trakya, Türkiye (v1.0.0) [software].
https://github.com/melihkalkan4/Trak-AI_KDS
```

## Authors

- **Melih Kalkan** — Işık University, Department of Management Information Systems, İstanbul, Türkiye.
  ORCID [0009-0004-7719-5333](https://orcid.org/0009-0004-7719-5333).
- **Gülsüm Çiğdem Çavdaroğlu** — Işık University, Department of Management Information Systems, İstanbul,
  Türkiye. ORCID [0000-0002-4875-4800](https://orcid.org/0000-0002-4875-4800).

## License

Source code: **MIT** (see [LICENSE](LICENSE)). The accompanying dataset is CC-BY-4.0, and data derived from
Copernicus, NASA POWER, ISRIC SoilGrids, ESA WorldCover, SRTM and TÜİK retain their providers' terms — see
the LICENSE file for attribution requirements.
