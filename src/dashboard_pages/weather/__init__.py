"""Weather (Hava Durumu) tab — 5 sub-tabs + Open-Meteo + ERA5."""

import streamlit as st


def render() -> None:
    site_label = st.session_state.get("research_site", "EVR_01")
    st.title(f"🌦️ Hava Durumu — {site_label}")
    st.caption("ERA5 geçmiş · DOY klimatoloji · Open-Meteo 7-gün tahmin")

    tabs = st.tabs([
        "🌡️ Şu Anki Durum",
        "📈 Geçmiş Hava (ERA5)",
        "🔄 Climatology",
        "🔮 7-Gün Tahmin",
        "⚠️ Hava Uyarıları",
    ])

    with tabs[0]:
        from .current_conditions import render as r; r()
    with tabs[1]:
        from .historical_trends import render as r; r()
    with tabs[2]:
        from .climatology_comparison import render as r; r()
    with tabs[3]:
        from .forecast import render as r; r()
    with tabs[4]:
        from .weather_alerts import render as r; r()
