"""FLOV → 🌾 Yield Forecast: XGBoost ton/ha prediction + model SHA256."""
from __future__ import annotations

import json

import streamlit as st

from ..shared.session import get_active_site


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    year = int(st.session_state.get("research_year", 2025))

    try:
        from prospective_validation import config as _flov  # type: ignore
        yield_path = _flov.REPORTS_DIR / f"{site_id}_{year}_yield.json"
    except Exception as exc:                                        # noqa: BLE001
        st.error(f"FLOV config yuklenemedi: {exc}")
        return

    if not yield_path.exists():
        st.info(
            f"`{yield_path.name}` yok.\n\n"
            f"`python scripts/predict_yield.py --site {site_id} --year {year}` calistirin."
        )
        return

    y = json.loads(yield_path.read_text(encoding="utf-8"))
    c1, c2 = st.columns(2)
    c1.metric(
        "Tahmini verim (ton/ha)",
        f"{y.get('predicted_yield_t_ha', float('nan')):.2f}",
    )
    c2.metric("Model SHA256 (kisa)", y.get("model_sha256_short", "—"))
    with st.expander("📄 Ham JSON"):
        st.json(y)
