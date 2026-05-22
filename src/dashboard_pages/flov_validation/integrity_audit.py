"""FLOV → 🔒 Integrity Audit: SHA-256 ledger + reproducibility caption."""
from __future__ import annotations

import streamlit as st

from ..shared.data_loaders import load_integrity_ledger


def render() -> None:
    st.markdown("### Model Integrity Ledger (SHA-256)")
    df = load_integrity_ledger(n=200)
    if df is None or df.empty:
        st.info("model_integrity.jsonl bos veya yok.")
        return
    cols = [c for c in ["timestamp", "model_name", "sha256", "status", "loader"]
            if c in df.columns]
    st.dataframe(df[cols] if cols else df, use_container_width=True, hide_index=True)
    st.caption(
        "Donmuş model (LSTM NDVI + XGB verim) · 2017-2024 egitimi · "
        "her yukleme SHA-256 ile dogrulanir · yeniden egitim yok."
    )
