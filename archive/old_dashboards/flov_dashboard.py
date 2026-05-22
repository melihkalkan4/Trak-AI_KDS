"""
FLOV (Forward-Looking Operational Validation) — Streamlit dashboard.

Audience: thesis evaluator + farmer-validator (5 Evrenli sites).

Reads only the parquet/CSV artefacts that Phases 2/3/4 already produce —
this dashboard is a *viewer*.  It NEVER calls the GEE/CDS fetchers; pulling
fresh data is the cron job's responsibility (Phase 8).

Run:
    streamlit run dashboard/flov_dashboard.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from prospective_validation import alerts as alerts_mod
from prospective_validation import config

st.set_page_config(
    page_title="TRAK-AI · FLOV (Prospective Validation)",
    page_icon="🌻",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Cached loaders (Streamlit's @st.cache_data; cleared on file mtime change)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load_predictions(site_id: str, year: int) -> pd.DataFrame:
    p = config.REPORTS_DIR / f"{site_id}_{year}_predictions.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["prediction_date"] = pd.to_datetime(df["prediction_date"])
    df["target_date"]     = pd.to_datetime(df["target_date"])
    return df


@st.cache_data(show_spinner=False)
def _load_unified(site_id: str, year: int) -> pd.DataFrame:
    p = config.PROSPECTIVE_DIR / str(year) / f"{site_id}_unified_features.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def _load_validation(site_id: str, year: int) -> tuple[pd.DataFrame, dict | None, pd.DataFrame]:
    out_dir = config.REPORTS_DIR
    matched_csv = out_dir / f"{site_id}_{year}_validation.csv"
    per_stage_csv = out_dir / f"{site_id}_{year}_validation_per_stage.csv"
    summary_json = out_dir / f"{site_id}_{year}_validation_summary.json"
    matched = pd.read_csv(matched_csv, parse_dates=["target_date", "actual_date"]) \
        if matched_csv.exists() else pd.DataFrame()
    per_stage = pd.read_csv(per_stage_csv) if per_stage_csv.exists() else pd.DataFrame()
    summary = json.loads(summary_json.read_text(encoding="utf-8")) \
        if summary_json.exists() else None
    return matched, summary, per_stage


@st.cache_data(show_spinner=False)
def _load_climatology() -> pd.DataFrame:
    p = config.HISTORICAL_CLIMATOLOGY_DIR / "sunflower_doy_climatology.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("FLOV controls")
site_lookup = {f"{s.id} — {s.name}": s for s in config.EVRENLI_SITES}
site_label  = st.sidebar.selectbox("Tarla / Site", list(site_lookup.keys()), index=0)
site        = site_lookup[site_label]
year        = st.sidebar.selectbox("Yil / Year", [2025, 2026, 2024], index=0)
show_clim   = st.sidebar.checkbox("Klimatoloji bandi (DOY, ±1σ)", value=True)
show_alerts = st.sidebar.checkbox("Uyarilar (alerts)", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Alan: **{site.area_ha:.1f} ha**  \n"
    f"Sub-pixel risk: **{'YES' if site.subpixel_risk else 'no'}**  \n"
    f"Coords: ({site.lat:.4f}, {site.lon:.4f})"
)
if site.subpixel_risk:
    st.sidebar.warning(
        "Bu tarla 5 ha altinda — 30 m kenar tamponuyla S2 piksel saflarinin "
        "yarisindan azi guvenli. Tek-piksel gurultusu yuksek olabilir."
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🌻 TRAK-AI · FLOV")
st.caption(
    f"Forward-Looking Operational Validation — site **{site.id}** ({site.name}), year **{year}**"
)

predictions = _load_predictions(site.id, year)
unified     = _load_unified(site.id, year)
matched, summary, per_stage = _load_validation(site.id, year)
clim        = _load_climatology()

if predictions.empty:
    st.error(
        f"Henuz tahmin uretilmemis: `reports/prospective/{site.id}_{year}_predictions.parquet`\n\n"
        f"Once `python scripts/predict_evr01.py --site {site.id} --year {year}` calistirin."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Top KPI row
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tahmin satiri", f"{len(predictions):,}")
col1.caption(f"{predictions['prediction_date'].min().date()} → "
             f"{predictions['target_date'].max().date()}")

if summary:
    col2.metric("Kapsama (matched/total)",
                f"{summary['n_matched']}/{summary['n_predictions']}",
                delta=f"{summary['coverage_pct']:.1f}%")
    r2 = summary["overall_model"].get("R2")
    mae = summary["overall_model"].get("MAE")
    col3.metric("Model R²",  f"{r2:.3f}"  if r2  is not None else "—")
    col3.caption("Persistence vs model:")
    col4.metric("Model MAE", f"{mae:.4f}" if mae is not None else "—")
    naive_mae = summary["overall_naive_persistence"].get("MAE")
    if naive_mae is not None and mae is not None:
        col4.caption(f"Naive MAE: {naive_mae:.4f}  ({(naive_mae-mae)*1000:+.1f}×10⁻³)")
else:
    col2.metric("Kapsama", "—")
    col3.metric("R²", "—")
    col4.metric("MAE", "—")
    st.info(
        f"Validasyon dosyalari yok. `python scripts/validate_evr01.py --site {site.id} --year {year}` calistirin."
    )

# ---------------------------------------------------------------------------
# Main chart: NDVI predicted vs actual (vs climatology band)
# ---------------------------------------------------------------------------
st.subheader("NDVI: tahmin · gercek · klimatoloji")

import plotly.graph_objects as go

fig = go.Figure()

# Climatology band (DOY-based) — map onto the predictions' target_date window
if show_clim and not clim.empty and not predictions.empty:
    tmin = predictions["target_date"].min()
    tmax = predictions["target_date"].max()
    dr = pd.date_range(tmin, tmax, freq="D")
    cl = clim.set_index("doy").reindex(dr.dayofyear).reset_index(drop=True)
    cl["date"] = dr
    fig.add_traces([
        go.Scatter(
            x=cl["date"], y=cl["ndvi_mean"] + cl["ndvi_std"],
            mode="lines", line=dict(width=0), showlegend=False,
            hoverinfo="skip",
        ),
        go.Scatter(
            x=cl["date"], y=cl["ndvi_mean"] - cl["ndvi_std"],
            mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(120,160,80,0.18)",
            name="Klimatoloji ±1σ (DOY)", hoverinfo="skip",
        ),
        go.Scatter(
            x=cl["date"], y=cl["ndvi_mean"],
            mode="lines", line=dict(color="rgba(80,120,60,0.7)", dash="dot"),
            name="Klimatoloji (DOY ort.)",
        ),
    ])

# Actuals (if available — from unified parquet NDVI_int)
if not unified.empty and "NDVI_int" in unified.columns:
    fig.add_trace(go.Scatter(
        x=unified["date"], y=unified["NDVI_int"],
        mode="lines", line=dict(color="#3d8b3d", width=2),
        name="Gercek NDVI (NDVI_int)",
    ))

# Predictions
fig.add_trace(go.Scatter(
    x=predictions["target_date"], y=predictions["predicted_ndvi"],
    mode="lines+markers",
    line=dict(color="#1f77b4", width=2),
    marker=dict(size=4),
    name="Tahmin (t+7)",
))

# Matched-pair markers from validation, if any
if not matched.empty:
    fig.add_trace(go.Scatter(
        x=matched["actual_date"], y=matched["actual_ndvi"],
        mode="markers",
        marker=dict(color="#d62728", size=7, symbol="x"),
        name="Validasyon gercek (S2)",
    ))

fig.update_layout(
    height=460,
    yaxis_title="NDVI",
    xaxis_title="Tarih",
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.18),
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Per-phenological-stage metrics
# ---------------------------------------------------------------------------
if not per_stage.empty:
    st.subheader("Fenoloji asamasina gore validasyon")
    show = per_stage.copy()
    for c in ("R2", "MAE", "RMSE", "bias", "MAPE_pct"):
        if c in show.columns:
            show[c] = show[c].round(4)
    st.dataframe(show, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
if show_alerts:
    st.subheader("Uyarilar (alerts)")
    alerts = alerts_mod.evaluate(predictions, site=site)
    s = alerts_mod.summarize(alerts)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Toplam", s["total"])
    a2.metric("Kritik",  s.get("critical", 0))
    a3.metric("Uyari",   s.get("warn", 0))
    a4.metric("Bilgi",   s.get("info", 0))

    if alerts:
        df_a = alerts_mod.to_dataframe(alerts)
        # Compact view
        view = df_a[["target_date", "severity", "stage", "direction",
                     "predicted_ndvi", "climatology_ndvi", "anomaly",
                     "message_tr", "action_tr"]].copy()
        view = view.sort_values(["target_date", "severity"],
                                ascending=[True, True])
        st.dataframe(
            view,
            use_container_width=True, hide_index=True,
            column_config={
                "severity": st.column_config.SelectboxColumn(
                    "Severity", options=["info", "warn", "critical"]),
                "predicted_ndvi":   st.column_config.NumberColumn(format="%.3f"),
                "climatology_ndvi": st.column_config.NumberColumn(format="%.3f"),
                "anomaly":          st.column_config.NumberColumn(format="%+.3f"),
            },
        )
        st.download_button(
            "Uyarilari indir (CSV)",
            df_a.to_csv(index=False).encode("utf-8"),
            file_name=f"alerts_{site.id}_{year}.csv",
            mime="text/csv",
        )
    else:
        st.success("Bu pencerede esik asan anomali yok.")

# ---------------------------------------------------------------------------
# Yield panel (XGBoost, if a yield prediction file exists)
# ---------------------------------------------------------------------------
yield_path = config.REPORTS_DIR / f"{site.id}_{year}_yield.json"
if yield_path.exists():
    st.subheader("Verim tahmini (XGBoost)")
    y = json.loads(yield_path.read_text(encoding="utf-8"))
    yc1, yc2 = st.columns(2)
    yc1.metric("Tahmini verim (ton/ha)", f"{y.get('predicted_yield_t_ha', float('nan')):.2f}")
    yc2.metric("Model SHA256 (kisa)",    y.get("model_sha256_short", "—"))

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Donmuş model (LSTM NDVI + XGB verim) · 2017-2024 egitimi · "
    "tum cikti dosyalari `reports/prospective/` altinda. "
    "Bu panel sadece okur — yeniden egitim YOK."
)
