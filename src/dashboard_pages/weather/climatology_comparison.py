"""Weather → 🔄 Climatology: this season vs DOY ±1σ baseline."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import load_climatology
from .data_sources.era5_loader import load_era5_history


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    clim = load_climatology()
    cur = load_era5_history(site_id, year)
    if clim is None or clim.empty:
        st.info("DOY klimatoloji parqueti yok.")
        return
    if cur is None or cur.empty:
        st.info("Bu yil icin ERA5 verisi yok.")
        return

    cur = cur.copy()
    cur["doy"] = pd.to_datetime(cur["date"]).dt.dayofyear
    merged = cur.merge(clim, on="doy", how="left", suffixes=("", "_clim"))

    fig = go.Figure()
    if "ndvi_mean" in merged.columns:
        fig.add_traces([
            go.Scatter(x=merged["date"],
                       y=merged["ndvi_mean"] + merged["ndvi_std"],
                       mode="lines", line=dict(width=0),
                       showlegend=False, hoverinfo="skip"),
            go.Scatter(x=merged["date"],
                       y=merged["ndvi_mean"] - merged["ndvi_std"],
                       mode="lines", line=dict(width=0),
                       fill="tonexty", fillcolor="rgba(120,160,80,0.18)",
                       name="DOY NDVI ±1σ", hoverinfo="skip"),
        ])
    st.caption("NDVI klimatoloji bandı + bu seninkilerin ERA5 sıcaklık eğrisi:")
    if "t2m_mean" in merged.columns:
        fig.add_trace(go.Scatter(x=merged["date"], y=merged["t2m_mean"],
                                 mode="lines", name="T ort. (bu yil)",
                                 line=dict(color="#d62728")))
    fig.update_layout(height=380,
                      legend=dict(orientation="h", y=1.05),
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
