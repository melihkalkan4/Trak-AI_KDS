"""Weather → 🌡️ Şu Anki Durum (Open-Meteo current)."""
from __future__ import annotations

import streamlit as st

from ..shared.session import get_active_site
from .data_sources.openmeteo_client import fetch_forecast


def render() -> None:
    site = get_active_site()
    if site.lat is None or site.lon is None:
        st.warning("Aktif sahanin koordinati yok.")
        return

    data = fetch_forecast(site.lat, site.lon, days=1)
    if not data or "current" not in data:
        st.error("Open-Meteo yaniti alinamadi.")
        return

    cur = data["current"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sicaklik", f"{cur.get('temperature_2m', '?')}°C")
    c2.metric("Nem", f"%{cur.get('relative_humidity_2m', '?')}")
    c3.metric("Ruzgar", f"{cur.get('wind_speed_10m', 0):.0f} km/s")
    c4.metric("Yagis (1s)", f"{cur.get('precipitation', 0):.1f} mm")

    c5, c6 = st.columns(2)
    c5.metric("Toprak Nemi (0-1cm)",
              f"{cur.get('soil_moisture_0_to_1cm', 0):.2f} m³/m³"
              if cur.get("soil_moisture_0_to_1cm") is not None else "—")
    c6.metric("Hava kodu", str(cur.get("weather_code", "—")))

    st.caption(f"Kaynak: Open-Meteo · {cur.get('time', '—')} · "
               f"lat={site.lat:.4f}, lon={site.lon:.4f}")
