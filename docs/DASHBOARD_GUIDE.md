# TRAK-AI KDS — Master Dashboard Guide

> **Entry point:** `streamlit run src/dashboard.py`
>
> Single unified Streamlit app replacing the 5 previously-disparate dashboards.

---

## Architecture

```
src/
├── dashboard.py                         # 8-tab router (≈140 lines)
└── dashboard_pages/
    ├── _legacy_pages.py                 # original 932-line farmer pages (preserved)
    ├── home.py                          # 🏠 Ana
    ├── settings.py                      # ⚙️ Settings (5 sub-tabs)
    ├── shared/
    │   ├── styling.py                   # brand theme + banner + alert bar CSS
    │   ├── session.py                   # dual site ID system (tarla_id ↔ EVR_xx)
    │   ├── components.py                # KPI card, badge, status indicators
    │   └── data_loaders.py              # @st.cache_data parquet/JSONL readers
    ├── flov_validation/                 # ✅ FLOV
    │   ├── live_metrics.py
    │   ├── alerts_panel.py
    │   ├── per_stage_analysis.py
    │   ├── yield_forecast.py
    │   └── integrity_audit.py
    ├── cross_modal/                     # 🔬 X-Modal
    │   ├── satellite_view.py
    │   ├── field_yolov8.py
    │   ├── feature_predictor.py
    │   ├── consensus_view.py
    │   └── annotation_tool.py
    └── weather/                         # 🌦️ Hava
        ├── current_conditions.py
        ├── historical_trends.py
        ├── climatology_comparison.py
        ├── forecast.py
        ├── weather_alerts.py
        ├── alert_rules.py
        └── data_sources/
            ├── openmeteo_client.py
            └── era5_loader.py
```

## 8 Top-Level Tabs

| Tab | Module | Description |
|---|---|---|
| 🏠 Ana | `home.py` | Snapshot of active site + alert roll-up + jump-to-tab |
| 🌿 Tarla Detay | `_legacy_pages.page_tarla` | NDVI, verim, fenoloji, sulama, SHAP |
| 🚜 Rover | `_legacy_pages.page_rover` | Mock simulation, model-vs-rover, harita |
| 💬 SCRAG | `_legacy_pages.page_chat` | RAG-grounded chat (FAISS + Ollama) |
| ✅ FLOV | `flov_validation/` | Frozen LSTM+XGB forward-looking validation |
| 🔬 X-Modal | `cross_modal/` | 3-way consensus: satellite · field · features |
| 🌦️ Hava | `weather/` | ERA5 history · DOY climatology · Open-Meteo 7-day |
| ⚙️ Settings | `settings.py` | API status, model integrity, audit logs |

## Dual Site Identification

Two coexisting site systems handled by `shared/session.get_active_site()`:

- **`tarla_id`** — DB integer (1, 2, 3) — farmer-facing pages.
- **`research_site`** — `EVR_01`, `EVR_02`, ... — FLOV / Cross-Modal / Weather.

Both selectors live in the sidebar; pages choose whichever they need.

## Cross-Page Navigation

Triggered by `shared.session.navigate_to(target, context=...)`. Wired today:

- FLOV alerts → SCRAG (`alerts_panel.py`)
- Weather alerts → SCRAG (`weather_alerts.py`)
- Home jump buttons → 4 deep tabs

## Caching Discipline

- `@st.cache_data(ttl=...)` for parquet/JSONL/csv loaders (60 s for logs, 300 s for parquet, 600 s for climatology).
- Resource singletons (FAISS vectorstore, YOLOv8 model) live behind `@st.cache_resource` in `_legacy_pages.py`.

## Required External Endpoints

- **Open-Meteo** (`api.open-meteo.com`) — free, no auth — current + 7-day forecast.
- **Ollama** (localhost) — LLM for SCRAG.
- **CDS / GEE** — not called by the dashboard; cron jobs produce parquet artefacts.

## Smoke Test

```bash
venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'src')
import dashboard_pages  # triggers package init
import dashboard_pages.home, dashboard_pages.settings
import dashboard_pages.flov_validation
import dashboard_pages.cross_modal
import dashboard_pages.weather
print('all good')
"
```

Then:

```bash
venv/Scripts/streamlit.exe run src/dashboard.py
```

## Legacy / Archive

- `dashboard/flov_dashboard.py` → moved to `archive/old_dashboards/flov_dashboard.py`.
- `dashboard/` directory kept with a `README.md` redirect.

## Migration Notes

- `st.set_page_config` is called **only** in `src/dashboard.py`. Sub-modules must not call it.
- `init_db()` is called **only** in the router. Legacy module no longer calls it.
- Path setup (`sys.path.insert`) is duplicated in both `src/dashboard.py` and `_legacy_pages.py` so each entry remains robust to import order.
