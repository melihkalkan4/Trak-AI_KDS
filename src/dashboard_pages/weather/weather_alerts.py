"""Weather → ⚠️ Hava Uyarıları: rule-engine over Open-Meteo daily."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ..shared.session import get_active_site, navigate_to
from .alert_rules import evaluate_forecast, summarize
from .data_sources.openmeteo_client import fetch_forecast


def _alerts_log_path() -> Path:
    try:
        from visual_validation import config as _vv  # type: ignore
        return _vv.LOGS_DIR / "weather_alerts.jsonl"
    except Exception:                                                # noqa: BLE001
        return Path("logs/weather_alerts.jsonl")


def render() -> None:
    site = get_active_site()
    if site.lat is None or site.lon is None:
        st.warning("Aktif sahanin koordinati yok.")
        return

    data = fetch_forecast(site.lat, site.lon, days=7)
    if not data or "daily" not in data:
        st.error("Open-Meteo daily yaniti yok.")
        return

    alerts = evaluate_forecast(data["daily"])
    s = summarize(alerts)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam", s.get("total", 0))
    c2.metric("CRITICAL", s.get("CRITICAL", 0))
    c3.metric("WARNING", s.get("WARNING", 0))
    c4.metric("INFO", s.get("INFO", 0))

    if not alerts:
        st.success("Onumuzdeki 7 gunde esik asan hava olayi yok.")
        return

    df = pd.DataFrame([a.as_dict() for a in alerts])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Persist for the global alert bar
    try:
        path = _alerts_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for a in alerts:
                f.write(json.dumps(
                    {"site_id": site.research_id, **a.as_dict()},
                    ensure_ascii=False) + "\n")
    except Exception:                                                # noqa: BLE001
        pass

    if st.button("💬 SCRAG'a sor (hava uyarisi)", use_container_width=True):
        ctx = {"from": "Weather alerts",
               "site_id": site.research_id,
               "n_alerts": int(len(alerts))}
        navigate_to("💬 SCRAG", context=ctx)
