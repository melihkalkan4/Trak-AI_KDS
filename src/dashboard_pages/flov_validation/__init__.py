"""FLOV (Forward-Looking Operational Validation) tab — 5 sub-tabs."""

import streamlit as st


def render() -> None:
    st.title("✅ FLOV — Forward-Looking Operational Validation")
    st.caption("Donmuş LSTM + XGBoost · 2017-2024 eğitimi · prospektif validasyon")

    tabs = st.tabs([
        "📊 Live Metrics",
        "🚨 Active Alerts",
        "📈 Per-Stage",
        "🌾 Yield Forecast",
        "🔒 Integrity Audit",
    ])

    with tabs[0]:
        from .live_metrics import render as r; r()
    with tabs[1]:
        from .alerts_panel import render as r; r()
    with tabs[2]:
        from .per_stage_analysis import render as r; r()
    with tabs[3]:
        from .yield_forecast import render as r; r()
    with tabs[4]:
        from .integrity_audit import render as r; r()
