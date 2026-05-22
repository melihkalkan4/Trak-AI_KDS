"""X-Modal -> Feature Predictor: derive harmonized stress class from NDVI vs DOY climatology.

This is the *third* modality in the 3-way consensus engine. Given the
site's unified parquet, we compute the NDVI z-score against the DOY
climatology (built from 2017-2024) and map it onto the harmonized 4-class
taxonomy via `visual_validation.config.feature_zscore_to_class`.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import (
    load_unified_features_with_era5, load_climatology,
)


_HARMONIZED_BADGE = {
    "healthy":        "🟢 Saglikli",
    "mild_stress":    "🟡 Hafif stres",
    "severe_stress": "🟠 Siddetli stres",
    "disease":        "🔴 Hastalik",
}


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    df = load_unified_features_with_era5(site_id, year)
    if df is None or df.empty:
        st.info(
            f"{site_id} {year} icin unified parquet yok. "
            f"`python -m prospective_validation.runners build_features --site {site_id} --year {year}`"
        )
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # ── Z-score predictor ────────────────────────────────────────────────────
    clim = load_climatology()
    try:
        from visual_validation.config import feature_zscore_to_class
    except Exception:                                                   # noqa: BLE001
        feature_zscore_to_class = None

    z_series = pd.Series(dtype=float, index=df.index)
    if not clim.empty and "NDVI_int" in df.columns:
        # Climatology parquet schema: doy, ndvi_mean, ndvi_std (sunflower DOY).
        doy_col = next((c for c in clim.columns if c.lower() in ("doy", "day_of_year")), None)
        mean_col = next((c for c in clim.columns if "mean" in c.lower()), None)
        std_col  = next((c for c in clim.columns if "std" in c.lower()), None)
        if doy_col and mean_col and std_col:
            df["doy"] = df["date"].dt.dayofyear
            cmap = clim.set_index(doy_col)
            df = df.merge(cmap[[mean_col, std_col]].rename(
                columns={mean_col: "_clim_mean", std_col: "_clim_std"}
            ), left_on="doy", right_index=True, how="left")
            # Guard against zero std → fall back to median σ ≈ 0.07.
            std_safe = df["_clim_std"].where(df["_clim_std"] > 1e-3, 0.07)
            z_series = (df["NDVI_int"] - df["_clim_mean"]) / std_safe

    last_z = float(z_series.dropna().iloc[-1]) if z_series.dropna().size else None
    last_ndvi = float(df["NDVI_int"].dropna().iloc[-1]) if df["NDVI_int"].dropna().size else None

    # ── Top status cards ─────────────────────────────────────────────────────
    cls = (feature_zscore_to_class(last_z)
           if (feature_zscore_to_class and last_z is not None) else None)
    cols = st.columns(4)
    cols[0].metric("Son NDVI", f"{last_ndvi:.3f}" if last_ndvi is not None else "—")
    cols[1].metric("Z-skor (vs DOY)", f"{last_z:+.2f}" if last_z is not None else "—")
    cols[2].metric("Tahmin sinifi", _HARMONIZED_BADGE.get(cls, "—") if cls else "—")
    cols[3].metric("Veri uzunlugu", f"{len(df):,} gun")

    # ── NDVI + climatology overlay ──────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["NDVI_int"], mode="lines",
        name="NDVI (Sentinel-2)", line=dict(color="#2ca02c", width=2),
    ))
    if "_clim_mean" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["_clim_mean"],
            mode="lines", name="DOY iklim ortalamasi",
            line=dict(color="#7f7f7f", dash="dot"),
        ))
        if "_clim_std" in df.columns:
            upper = df["_clim_mean"] + 2 * df["_clim_std"]
            lower = df["_clim_mean"] - 2 * df["_clim_std"]
            fig.add_trace(go.Scatter(
                x=df["date"], y=upper, mode="lines",
                line=dict(width=0), showlegend=False,
            ))
            fig.add_trace(go.Scatter(
                x=df["date"], y=lower, mode="lines",
                fill="tonexty", fillcolor="rgba(127,127,127,0.15)",
                line=dict(width=0), name="± 2σ baseline",
            ))
    fig.update_layout(
        height=320, margin=dict(t=10, b=30, l=55, r=30),
        yaxis=dict(title="NDVI", range=[0, 1]),
        xaxis_title="Tarih",
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Kaynak: `data/prospective/{year}/{site}_unified_features.parquet` (NDVI + ERA5) · "
        "İklim baseline: 2017-2024 DOY ortalamasi · "
        "Sinif mapping: `visual_validation.config.feature_zscore_to_class`"
    )

    # ── Raw feature snapshot ─────────────────────────────────────────────────
    pref_cols = [c for c in [
        "date", "NDVI_int", "NDVI_trend_7d", "EVI_int", "NDWI_int",
        "t2m_mean", "tp_sum", "drought_index_7d", "GDD_cum",
    ] if c in df.columns]
    with st.expander("📄 Son 60 gun (ham ozellikler)", expanded=False):
        st.dataframe(df[pref_cols].tail(60), use_container_width=True, hide_index=True)
