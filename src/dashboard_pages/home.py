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

    # An alert is "active" if its forecast target_date is still in the future
    # (today or later); it is "resolved" once that date has passed — that's
    # when the historical NDVI/consensus outcome is known and the forecast
    # window closed. This is the same semantics FLOV uses operationally.
    import pandas as _pd
    _today = _pd.Timestamp.today().normalize()

    def _split_active_resolved(df: "_pd.DataFrame", date_col: str = "target_date"):
        """Return (active, resolved_last_30d) DataFrames keyed by target_date."""
        if df is None or df.empty or date_col not in df.columns:
            return _pd.DataFrame(), _pd.DataFrame()
        d = df.copy()
        d[date_col] = _pd.to_datetime(d[date_col], errors="coerce")
        d = d.dropna(subset=[date_col])
        active   = d[d[date_col] >= _today]
        cutoff   = _today - _pd.Timedelta(days=30)
        resolved = d[(d[date_col] <  _today) & (d[date_col] >= cutoff)]
        return active, resolved

    flov_active, flov_resolved = _split_active_resolved(flov_df)
    vv_active,   vv_resolved   = _split_active_resolved(vv_df)

    a1, a2, a3 = st.columns(3)
    n_flov = len(flov_active)
    n_xmod = len(vv_active)
    with a1:
        kpi_card("FLOV uyarilari", str(n_flov),
                 delta=None, delta_color="warning" if n_flov else "positive")
    with a2:
        kpi_card("X-Modal uyarilari", str(n_xmod),
                 delta=None, delta_color="warning" if n_xmod else "positive")
    with a3:
        kpi_card("Hava uyarilari", str(n_weather),
                 delta=None, delta_color="warning" if n_weather else "positive")

    # ── Resolved alerts (target_date passed within last 30 days) ───────────
    n_resolved_total = len(flov_resolved) + len(vv_resolved)
    _exp_label = (f"✅ Cozulmus Uyarilar — Son 30 Gun ({n_resolved_total})"
                  if n_resolved_total else
                  "✅ Cozulmus Uyarilar (Son 30 Gun)")

    with st.expander(_exp_label, expanded=False):
        rows: list[dict] = []
        # FLOV rows -> harmonized schema
        for _, r in flov_resolved.iterrows():
            rows.append({
                "Tarih":   r.get("target_date"),
                "Kaynak":  "FLOV",
                "Tip":     f"NDVI anomalisi ({r.get('direction', '?')})",
                "Onem":    str(r.get("severity", "")).upper(),
                "Mesaj":   r.get("message_tr") or r.get("message_en") or "",
            })
        # X-Modal (visual consensus) rows -> harmonized schema
        for _, r in vv_resolved.iterrows():
            rows.append({
                "Tarih":   r.get("target_date"),
                "Kaynak":  "X-Modal",
                "Tip":     r.get("flag") or r.get("agreement_type") or "consensus",
                "Onem":    str(r.get("severity", "")).upper(),
                "Mesaj":   r.get("message_tr") or r.get("message_en") or "",
            })

        if not rows:
            st.info(
                "Son 30 gunde cozulmus uyari yok. "
                "Bir uyari, tahmin hedef tarihi gectiginde otomatik "
                "**cozulmus** olarak isaretlenir (kaynak: `logs/alerts.jsonl`, "
                "`logs/visual_consensus_alerts.jsonl`)."
            )
        else:
            res_df = _pd.DataFrame(rows).sort_values("Tarih", ascending=False)
            st.caption(
                f"Son 30 gunde **{len(res_df)}** uyari cozuldu "
                f"(FLOV: {len(flov_resolved)} · X-Modal: {len(vv_resolved)})."
            )
            st.dataframe(
                res_df, hide_index=True, use_container_width=True,
                column_config={
                    "Tarih": st.column_config.DatetimeColumn(
                        "Tarih", format="DD MMM YYYY"),
                },
            )

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
