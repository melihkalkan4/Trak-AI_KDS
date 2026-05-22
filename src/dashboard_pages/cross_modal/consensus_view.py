"""X-Modal -> 3-Way Consensus: agreement matrix + Cohen/Fleiss Kappa.

If no consensus logs exist yet (typical before the first cron run), we
fall back to showing the engine configuration (modality weights, harmonized
taxonomy, decision flags) so the tab still conveys what the system will do
once snapshots start landing.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import (
    load_consensus_jsonl, load_consensus_alerts_jsonl,
    list_consensus_snapshots,
)


def _render_engine_config() -> None:
    """Show the consensus engine's static configuration as a placeholder."""
    try:
        from visual_validation import config as _vv  # type: ignore
    except Exception as exc:                                            # noqa: BLE001
        st.error(f"visual_validation modulu yuklenemedi: {exc}")
        return

    st.markdown("#### Konsensus motoru — yapilandirma")
    weights_df = pd.DataFrame(
        [(k, v) for k, v in _vv.MODALITY_WEIGHTS.items()],
        columns=["Modalite", "Agirlik"],
    )
    st.dataframe(weights_df, use_container_width=True, hide_index=True)

    st.markdown("#### Harmonize taxonomi (4 sinif)")
    st.code("\n".join(f"{i}: {lbl}" for i, lbl in enumerate(_vv.HARMONIZED_LABELS)),
            language="text")

    st.markdown("#### Karar bayraklari")
    flags_df = pd.DataFrame(
        [(k, v) for k, v in _vv.CONSENSUS_FLAGS.items()],
        columns=["Bayrak", "Aciklama"],
    )
    st.dataframe(flags_df, use_container_width=True, hide_index=True)


def render() -> None:
    site = get_active_site()
    site_id = site.research_id

    df = load_consensus_jsonl(site_id=site_id, n=500)
    if df is None or df.empty:
        st.info(
            f"Henuz konsensus karari log'lanmadi ({site_id or 'tum sahalar'}).\n\n"
            f"Komut: `python scripts/run_cross_modal_validation.py "
            f"--site {site_id or 'EVR_01'}`"
        )
        st.markdown("---")
        _render_engine_config()
        return

    st.markdown(f"### 3-yollu konsensus ({len(df)} kayit)")

    # Aggregate kappa metrics if columns are present.
    metric_cols = st.columns(4)
    metric_cols[0].metric("Toplam karar", len(df))
    if "cohen_kappa" in df.columns:
        mean_cohen = pd.to_numeric(df["cohen_kappa"], errors="coerce").mean()
        if pd.notna(mean_cohen):
            metric_cols[1].metric("Cohen κ (ort)", f"{mean_cohen:.3f}")
    if "fleiss_kappa" in df.columns:
        mean_fleiss = pd.to_numeric(df["fleiss_kappa"], errors="coerce").mean()
        if pd.notna(mean_fleiss):
            metric_cols[2].metric("Fleiss κ (ort)", f"{mean_fleiss:.3f}")
    if "agreement_score" in df.columns:
        mean_agree = pd.to_numeric(df["agreement_score"], errors="coerce").mean()
        if pd.notna(mean_agree):
            metric_cols[3].metric("Anlasma (ort)", f"{mean_agree:.2f}")

    keep = [c for c in ["timestamp", "site_id", "evrenli_id",
                        "decision", "agreement_score",
                        "cohen_kappa", "fleiss_kappa",
                        "satellite_class", "field_class", "features_class"]
            if c in df.columns]
    st.dataframe(df[keep] if keep else df, use_container_width=True, hide_index=True)

    # Alerts
    alerts = load_consensus_alerts_jsonl(site_id=site_id, n=200)
    if alerts is not None and not alerts.empty:
        st.markdown("### ⚠️ Konsensus uyarilari")
        st.dataframe(alerts, use_container_width=True, hide_index=True)

    # Snapshot files
    snaps = list_consensus_snapshots(site_id=site_id)
    if snaps:
        with st.expander(f"📁 Snapshot dosyalari ({len(snaps)})"):
            for p in snaps[-20:]:
                st.code(p.name, language="text")
