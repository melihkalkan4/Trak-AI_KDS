"""FLOV → 📈 Per-Stage: validation metrics broken down by phenology stage."""
from __future__ import annotations

import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import load_flov_validation


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    _, _, per_stage = load_flov_validation(site_id, year)
    if per_stage is None or per_stage.empty:
        st.info(
            f"`{site_id}_{year}_validation_per_stage.csv` yok.\n\n"
            f"`python scripts/validate_evr01.py --site {site_id} --year {year}` calistirin."
        )
        return

    show = per_stage.copy()
    for c in ("R2", "MAE", "RMSE", "bias", "MAPE_pct"):
        if c in show.columns:
            show[c] = show[c].round(4)
    st.dataframe(show, use_container_width=True, hide_index=True)
