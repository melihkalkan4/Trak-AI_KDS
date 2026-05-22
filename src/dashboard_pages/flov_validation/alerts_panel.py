"""FLOV → 🚨 Active Alerts: severity counts + actionable table + CSV export."""
from __future__ import annotations

import streamlit as st

from ..shared.session import get_active_site, navigate_to
from ..shared.data_loaders import load_flov_predictions


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    predictions = load_flov_predictions(site_id, year)
    if predictions.empty:
        st.info("Tahmin yok — uyari yok.")
        return

    try:
        from prospective_validation import alerts as alerts_mod  # type: ignore
        from prospective_validation import config as _flov        # type: ignore
        site_obj = next((s for s in _flov.EVRENLI_SITES
                         if getattr(s, "id", None) == site_id), None)
    except Exception as exc:                                        # noqa: BLE001
        st.error(f"Alerts modulu yuklenemedi: {exc}")
        return

    alerts = alerts_mod.evaluate(predictions, site=site_obj)
    s = alerts_mod.summarize(alerts)
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Toplam", s.get("total", 0))
    a2.metric("Kritik", s.get("critical", 0))
    a3.metric("Uyari", s.get("warn", 0))
    a4.metric("Bilgi", s.get("info", 0))

    if not alerts:
        st.success("Bu pencerede esik asan anomali yok.")
        return

    df_a = alerts_mod.to_dataframe(alerts)
    cols = [c for c in ["target_date", "severity", "stage", "direction",
                        "predicted_ndvi", "climatology_ndvi", "anomaly",
                        "message_tr", "action_tr"] if c in df_a.columns]
    view = df_a[cols].sort_values(["target_date", "severity"], ascending=[True, True])
    st.dataframe(
        view, use_container_width=True, hide_index=True,
        column_config={
            "severity": st.column_config.SelectboxColumn(
                "Severity", options=["info", "warn", "critical"]),
            "predicted_ndvi":   st.column_config.NumberColumn(format="%.3f"),
            "climatology_ndvi": st.column_config.NumberColumn(format="%.3f"),
            "anomaly":          st.column_config.NumberColumn(format="%+.3f"),
        },
    )

    c1, c2 = st.columns(2)
    c1.download_button(
        "📥 Uyarilari indir (CSV)",
        df_a.to_csv(index=False).encode("utf-8"),
        file_name=f"alerts_{site_id}_{year}.csv",
        mime="text/csv",
    )
    if c2.button("💬 SCRAG'a sor (kritik uyari)", use_container_width=True):
        critical = view[view["severity"] == "critical"]
        ctx = {
            "from": "FLOV alerts",
            "site_id": site_id,
            "n_critical": int(len(critical)),
            "first_message": (critical["message_tr"].iloc[0]
                              if len(critical) and "message_tr" in critical
                              else ""),
        }
        navigate_to("💬 SCRAG", context=ctx)
