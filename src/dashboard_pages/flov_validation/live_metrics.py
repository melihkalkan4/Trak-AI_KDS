"""FLOV → 📊 Live Metrics: KPI row + NDVI chart with climatology band."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import (
    load_flov_predictions, load_flov_unified, load_flov_validation,
    load_climatology,
)


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    predictions = load_flov_predictions(site_id, year)
    unified = load_flov_unified(site_id, year)
    matched, summary, _ = load_flov_validation(site_id, year)
    clim = load_climatology()

    if predictions.empty:
        st.error(
            f"`{site_id}_{year}_predictions.parquet` bulunamadi.\n\n"
            f"Once `python scripts/predict_evr01.py --site {site_id} --year {year}` calistirin."
        )
        return

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tahmin satiri", f"{len(predictions):,}")
    c1.caption(f"{predictions['prediction_date'].min().date()} → "
               f"{predictions['target_date'].max().date()}")
    if summary:
        c2.metric("Kapsama (matched/total)",
                  f"{summary.get('n_matched', 0)}/{summary.get('n_predictions', 0)}",
                  delta=f"{summary.get('coverage_pct', 0):.1f}%")
        r2 = summary.get("overall_model", {}).get("R2")
        mae = summary.get("overall_model", {}).get("MAE")
        c3.metric("Model R²", f"{r2:.3f}" if r2 is not None else "—")
        c4.metric("Model MAE", f"{mae:.4f}" if mae is not None else "—")
        naive_mae = summary.get("overall_naive_persistence", {}).get("MAE")
        if naive_mae is not None and mae is not None:
            c4.caption(f"Naive MAE: {naive_mae:.4f} ({(naive_mae - mae) * 1000:+.1f}×10⁻³)")
    else:
        c2.metric("Kapsama", "—")
        c3.metric("R²", "—")
        c4.metric("MAE", "—")

    # NDVI chart
    st.subheader("NDVI: tahmin · gercek · klimatoloji")
    fig = go.Figure()

    show_clim = st.checkbox("Klimatoloji bandi (DOY ±1σ)", value=True, key="flov_show_clim")
    if show_clim and not clim.empty:
        tmin = predictions["target_date"].min()
        tmax = predictions["target_date"].max()
        dr = pd.date_range(tmin, tmax, freq="D")
        cl = clim.set_index("doy").reindex(dr.dayofyear).reset_index(drop=True)
        cl["date"] = dr
        fig.add_traces([
            go.Scatter(x=cl["date"], y=cl["ndvi_mean"] + cl["ndvi_std"],
                       mode="lines", line=dict(width=0), showlegend=False,
                       hoverinfo="skip"),
            go.Scatter(x=cl["date"], y=cl["ndvi_mean"] - cl["ndvi_std"],
                       mode="lines", line=dict(width=0),
                       fill="tonexty", fillcolor="rgba(120,160,80,0.18)",
                       name="Klimatoloji ±1σ (DOY)", hoverinfo="skip"),
            go.Scatter(x=cl["date"], y=cl["ndvi_mean"],
                       mode="lines",
                       line=dict(color="rgba(80,120,60,0.7)", dash="dot"),
                       name="Klimatoloji (DOY ort.)"),
        ])

    if not unified.empty and "NDVI_int" in unified.columns:
        fig.add_trace(go.Scatter(
            x=unified["date"], y=unified["NDVI_int"],
            mode="lines", line=dict(color="#3d8b3d", width=2),
            name="Gercek NDVI (NDVI_int)",
        ))
    fig.add_trace(go.Scatter(
        x=predictions["target_date"], y=predictions["predicted_ndvi"],
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2), marker=dict(size=4),
        name="Tahmin (t+7)",
    ))
    if not matched.empty:
        fig.add_trace(go.Scatter(
            x=matched["actual_date"], y=matched["actual_ndvi"],
            mode="markers",
            marker=dict(color="#d62728", size=7, symbol="x"),
            name="Validasyon gercek (S2)",
        ))
    fig.update_layout(
        height=460, yaxis_title="NDVI", xaxis_title="Tarih",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.18),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
