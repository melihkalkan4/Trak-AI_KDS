"""🏠 Ana — Landing page.

Aggregates a high-level snapshot across all subsystems:
    * Active site card (DB tarla + research EVR_xx)
    * Critical alerts summary (FLOV + Cross-Modal + Weather)
    * Quick KPIs (NDVI, last rover scan, forecast snippet)
    * Jump-to-tab buttons
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from .shared.session import get_active_site, navigate_to
from .shared.components import kpi_card, fmt_ts
from .shared.data_loaders import (
    load_flov_predictions, load_flov_alerts_jsonl,
    load_consensus_alerts_jsonl,
)


def render() -> None:
    site = get_active_site()
    st.subheader(f"Aktif Saha: {site.name}")

    # ── Site card ────────────────────────────────────────────────────────────
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        if site.tarla:
            c1.metric("DB Tarla", site.tarla.get("isim", "—"))
            c2.metric("Urun", site.tarla.get("aktif_urun", "—"))
            c3.metric("Alan", f"{site.tarla.get('alan_dekar', '?')} da")
            _ekim = site.tarla.get("ekim_tarihi") or "—"
            c4.metric("Ekim", str(_ekim)[:10])
        else:
            c1.info("DB tarla secilmedi")
        if site.research is not None:
            st.caption(
                f"Arastirma kodu: **{site.research_id}** · "
                f"lat={site.lat}, lon={site.lon}"
            )

    # ── Alerts roll-up ───────────────────────────────────────────────────────
    st.markdown("### ⚠️ Aktif Uyarilar (ozet)")
    try:
        flov_df = load_flov_alerts_jsonl(site_id=site.research_id, n=200)
    except Exception:                                               # noqa: BLE001
        flov_df = None
    try:
        vv_df = load_consensus_alerts_jsonl(site_id=site.research_id, n=200)
    except Exception:                                               # noqa: BLE001
        vv_df = None

    # Weather alerts: evaluated live for the active site (7-day Open-Meteo).
    n_weather = 0
    try:
        from .weather.alert_rules import evaluate_forecast
        from .weather.data_sources.openmeteo_client import fetch_forecast
        if site.lat is not None and site.lon is not None:
            wdata = fetch_forecast(site.lat, site.lon, days=7)
            if wdata and "daily" in wdata:
                n_weather = len(evaluate_forecast(wdata["daily"]))
    except Exception:                                                   # noqa: BLE001
        n_weather = 0

    a1, a2, a3 = st.columns(3)
    n_flov = 0 if flov_df is None or flov_df.empty else len(flov_df)
    n_xmod = 0 if vv_df is None or vv_df.empty else len(vv_df)
    with a1:
        kpi_card("FLOV uyarilari", str(n_flov),
                 delta=None, delta_color="warning" if n_flov else "positive")
    with a2:
        kpi_card("X-Modal uyarilari", str(n_xmod),
                 delta=None, delta_color="warning" if n_xmod else "positive")
    with a3:
        kpi_card("Hava uyarilari", str(n_weather),
                 delta=None, delta_color="warning" if n_weather else "positive")

    # ── Latest FLOV prediction snapshot ──────────────────────────────────────
    st.markdown("### 📈 Son FLOV tahmini")
    try:
        df = load_flov_predictions(
            site_id=site.research_id or "EVR_01",
            year=int(st.session_state.get("research_year", 2025)),
        )
    except Exception:                                               # noqa: BLE001
        df = None

    if df is None or df.empty:
        st.info("Bu saha icin FLOV tahmini bulunamadi.")
    else:
        last = df.sort_values("prediction_date").iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Son tahmin tarihi", fmt_ts(str(last.get("prediction_date"))))
        c2.metric("Hedef tarih", fmt_ts(str(last.get("target_date"))))
        c3.metric("Tahmin NDVI",
                  f"{last.get('predicted_ndvi', float('nan')):.3f}"
                  if "predicted_ndvi" in last else "—")

    # ── Quick navigation ─────────────────────────────────────────────────────
    st.markdown("### 🚀 Hizli Erisim")
    nav_cols = st.columns(4)
    targets = [
        ("🌿 Tarla Detay", nav_cols[0]),
        ("✅ FLOV",        nav_cols[1]),
        ("🔬 X-Modal",     nav_cols[2]),
        ("🌦️ Hava",        nav_cols[3]),
    ]
    for label, col in targets:
        if col.button(label, use_container_width=True, key=f"home_nav_{label}"):
            navigate_to(label)

    st.caption(f"Son guncelleme: {datetime.now().strftime('%d %b %Y %H:%M')}")
