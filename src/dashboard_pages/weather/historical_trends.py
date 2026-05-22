"""Weather → 📈 Geçmiş Hava (ERA5): cached daily series for current site/year."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from ..shared.session import get_active_site
from .data_sources.era5_loader import load_era5_history


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    df = load_era5_history(site_id, year)
    if df is None or df.empty:
        st.info(f"{site_id} {year} icin ERA5 unified parquet yok.")
        return

    # ERA5 unified parquet exposes t2m_{mean,max,min} + tp_sum directly.
    fig = go.Figure()
    if "t2m_max" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["t2m_max"],
                                 mode="lines", name="T max",
                                 line=dict(color="#d62728")))
    if "t2m_min" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["t2m_min"],
                                 mode="lines", name="T min",
                                 line=dict(color="#1f77b4")))
    if "t2m_mean" in df.columns:
        fig.add_trace(go.Scatter(x=df["date"], y=df["t2m_mean"],
                                 mode="lines", name="T mean",
                                 line=dict(color="#7f7f7f", dash="dot")))
    if "tp_sum" in df.columns:
        # ERA5-Land tp_sum on disk uses the legacy sum-of-accumulated-hourlies
        # scale (~12.5x daily total). Display in realistic mm so the y-axis
        # is meaningful. Cap per-day at 80 mm (climatology max for NW TR).
        tp_display = (df["tp_sum"] / 12.5).clip(lower=0, upper=80)
        fig.add_trace(go.Bar(x=df["date"], y=tp_display,
                             name="Yagis (mm)", marker_color="#aec7e8",
                             yaxis="y2", opacity=0.55))
    fig.update_layout(
        height=420,
        yaxis=dict(title="Sicaklik (°C)"),
        yaxis2=dict(title="Yagis (mm)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("📄 Ham veri"):
        st.dataframe(df.tail(60), use_container_width=True, hide_index=True)
