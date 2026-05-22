# FLOV — Forward-Looking Operational Validation

**Module:** `src/prospective_validation/`
**Frozen models:** 2017-2024 sunflower champions (LSTM + XGBoost)
**Validation period:** 2025-01-01 → present, 2026-04-01 → 2026-10-31

## 1. Why "Forward-Looking"

Backtesting on the same years the model was trained on can only certify
*in-sample* skill. The Forward-Looking Operational Validation (FLOV)
phase evaluates the **frozen** 2017-2024 champion against data the model
has never seen, in the same operational loop a farmer would use it in:

1. New satellite + reanalysis data arrive day-by-day.
2. A *frozen* artefact (hash-locked) consumes those features.
3. Predictions are written to disk and time-stamped.
4. As cloud-free Sentinel-2 overpasses arrive, the predictions are
   compared against ground truth — no re-tuning, no re-fitting, no
   look-ahead.

This is the only validation discipline that produces metrics one can
honestly report as "the model achieves X on truly held-out data".

## 2. Frozen-Artefact Contract

The validation pipeline NEVER re-trains, re-tunes, or modifies any model
file. Integrity is enforced by a SHA-256 ledger
(`logs/model_integrity.jsonl`) that is append-only and re-checked at
every load. The runtime artefacts under contract are:

| Role | File | SHA-256 (first 16) |
|---|---|---|
| LSTM champion (NDVI) | `src/cp2_model/model_lstm_sunflower.keras` | `43ef61b5a70f16cd…` |
| Scaler (NDVI) | `src/cp2_model/scaler_sunflower.pkl` | `1212fc5081366 8f5…` |
| XGBoost champion (yield) | `src/cp2_model/model_xgb_sunflower.pkl` | `9cc638a6a9519022…` |
| Yield scaler | `src/cp2_model/yield_scaler_sunflower.pkl` | `53e405f78848b6d8…` |
| Yield XGB feature set | `src/cp2_model/yield_xgb_sunflower.pkl` | `1b8f2a14404f87ad…` |
| Feature names (LSTM) | `src/cp2_model/feature_names.json` | `8d1948d9824fb54c…` |
| Feature names (XGB) | `src/cp2_model/xgb_feature_names_sunflower.json` | `62724be6ab8fc698…` |
| DOY climatology | `data/historical/climatology/sunflower_doy_climatology.parquet` | `3cd26360ff416fc3…` |

Any drift in any of these files trips a `RuntimeError` at import time.
The full ledger lives in `logs/model_integrity.jsonl`.

## 3. Inputs (the frozen feature contract)

The LSTM consumes a `(T=30, F=17)` window of MinMax-scaled features:

```
NDVI_int, EVI_int, NDWI_int, NDVI_trend_7d,
t2m_mean, t2m_max, t2m_min, tp_sum, ssr_sum,
GDD, GDD_cum, evaporation_mm, drought_index_7d,
temp_amplitude, dew_depression,
sin_doy, cos_doy
```

Feature engineering uses **`preprocessing_cp2.load_and_clean` +
`engineer_features` verbatim** (zero-drift design — we write a temp CSV
that matches the training-era schema and call the training pipeline's
own functions). The 30-day window is required by the trained Keras
architecture; the 7-day forecast horizon (`t+7`) is hard-coded in
training as well.

The XGBoost yield head consumes a *season-level* feature vector summarising
the full crop cycle (peak NDVI, cumulative GDD, total precipitation, etc.).
See `src/cp2_model/build_yield_features.py`.

## 4. Pilot Sites

5 placeholder sites in Vize/Evrenli (NW Türkiye), to be replaced with
real parcel coordinates before deployment. Each site is encoded as a
`Site(id, name, lat, lon, owner, area_da)` dataclass and rasterised to
a square polygon with a **30 m inward buffer** for Sentinel-2 pixel
purity. Sites under 5 ha (e.g. `EVR_01` at 1.25 ha) are flagged with
`subpixel_risk=True` and the dashboard renders a warning banner.

## 5. The Two-Layered Climatology

We use *two* baselines for narrative reporting:

1. **Residual layer (native)** — the LSTM itself outputs a residual
   on top of the last observed NDVI, scaled by `tanh(δ) × 0.30`. This
   is what the model *actually does* on each forward pass.
2. **DOY climatology layer (narrative)** — a separate parquet, built
   from the 2017-2024 master matrix's *raw* (cloud-free, NaN-tolerant)
   NDVI grouped by day-of-year, smoothed with a centred 7-day rolling
   window. This is what we anchor the user-facing "is today
   anomalous?" question against.

Anomaly = `predicted_ndvi − climatology(doy)`. Both layers are exposed
in the predictions parquet as `predicted_ndvi`, `last_observed_ndvi`,
`climatology_ndvi`, `anomaly_vs_climatology`.

## 6. Walk-Forward Inference

For each day `t` where a 30-day input window can be assembled:

```
window = features.iloc[t-30 : t]                  # (30, 17)
scaled = scaler.transform(window.ffill().bfill()) # MinMax (frozen)
out    = lstm.predict(scaled[None, ...])          # delta_t+7
ndvi_hat_scaled = scaled[-1, NDVI_IDX] + tanh(out) * 0.30
ndvi_hat        = scaler.inverse_transform(...)
```

No state is carried between calls — the pipeline is purely stateless.
Predictions are persisted as
`reports/prospective/<site>_<year>_predictions.parquet`.

## 7. Actuals (Ground Truth)

Three strategies are supported (`src/prospective_validation/actuals.py`):

| Strategy | Source | Notes |
|---|---|---|
| `from_unified_features` | Phase 2 parquet (`NDVI_int`) | Daily, *interpolated*. Coverage 100 % but weaker truth on cloudy days. |
| `from_master_matrix(use_raw=True)` | 2017-2024 master CSV (raw `NDVI`) | NaN on cloudy days — **gold standard** for metrics. |
| `from_sentinel2_fetch` | Direct GEE pull | Same as above, but fresh; cloud-free overpasses only. |

The thesis report should rely on the `s2` or `master` (`use_raw=True`)
sources. The `unified` source is used for the live dashboard for
*coverage*, not for headline metrics.

## 8. Matching Strategy

Predictions are joined to actuals via `pd.merge_asof` with a
nearest-day tolerance (`±N` days, default 2):

* `tolerance_days = 0` — strict day-of join (only daily/interpolated
  sources qualify)
* `tolerance_days ≥ 1` — nearest-day join within ±N days of
  `target_date` (correct semantics for raw S2, which arrives every ~5
  days when cloud-free)

The matched DataFrame records `actual_date`, `days_to_actual`, and
both model and persistence error magnitudes.

## 9. Metrics

`compute_metrics(predicted, actual)` returns `n, R², MAE, RMSE, bias,
MAPE_pct` (all in numpy, no sklearn dependency for auditability).

The thesis report includes a **persistence baseline** —
`naïve_pred = last_observed_ndvi`. This is the standard agronomic
benchmark; any model that fails to beat persistence on R² *and* MAE is
not contributing operational value.

**Wilcoxon signed-rank (one-sided)** tests
H₀: median |model − actual| ≥ median |persistence − actual|
against H₁: model errors are smaller. We report W and `p_value`.

Per-stage breakdown groups by sunflower phenology (see `config.SUNFLOWER_PHENOLOGY`):
`pre_season, emergence, vegetative, flowering, grain_fill, maturity, post_harvest`.

## 10. Alerts

`src/prospective_validation/alerts.py` translates the residual-anomaly
signal into farmer-facing messages (Turkish primary, English secondary).
Severity is anomaly-magnitude × phenology-criticality:

| `|anomaly|` (NDVI units) | base severity | uplifted in flowering / grain_fill |
|---|---|---|
| `≥ 0.20` | critical | critical |
| `≥ 0.10` | warn | critical |
| `≥ 0.05` | info | info |

Alerts persist append-only to `logs/alerts.jsonl`. The dashboard
renders them with stage-aware action recommendations.

## 11. Reproducibility & Audit

* **Hash-based file cache** — every GEE / CDS / SoilGrids fetch is
  keyed by a SHA-256 of canonical-JSON parameters
  (`data/cache/api/<source>/<hash>.bin`). Same query → cache hit.
* **API audit trail** — every external request is logged to
  `logs/api_audit.jsonl` with `cache_hit`, `latency_s`,
  `response_sha256`, and an `extra` dict.
* **Loguru logging** — 100 MB rotation, 90-day retention, zip
  compression (`logs/flov.log`).
* **No retraining ever** — the integrity ledger is the contract.

See `docs/REPRODUCIBILITY.md` for the canonical environment versions
and a step-by-step build recipe.

## 12. References (project-internal)

* Training: `src/cp2_model/train_models_cp2.py`
* Frozen preprocessing: `src/cp2_model/preprocessing_cp2.py`
* Yield inference: `src/cp2_model/inference_yield.py`
* Phenology constants: `src/prospective_validation/config.py`
* Validator: `src/prospective_validation/live_validator.py`
* Metrics: `src/prospective_validation/metrics.py`
* Dashboard: `dashboard/flov_dashboard.py`
