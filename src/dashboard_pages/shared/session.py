"""Cross-page session state + navigation helpers (offline-first, unified).

After the v3 schema refactor there is ONE site identifier: the DB `tarla_id`.
Every tarla row carries a `research_code` (e.g. 'EVR_01') that bridges to FLOV
and prospective_validation artefacts. Pages that previously consumed
`research_site` should now read `ActiveSite.research_code`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import streamlit as st


logger = logging.getLogger("trakai.dashboard.session")


_DEFAULTS = {
    "tarla_id": 1,
    "research_year": 2025,
    "chat_history": [],
    "rag_sources": {},
    "scrag_context": None,
    "nav_target": None,
    "auto_scroll_to": None,
}


def init_session_state() -> None:
    """Idempotently seed session state defaults."""
    for k, v in _DEFAULTS.items():
        st.session_state.setdefault(k, v)


@dataclass
class ActiveSite:
    db_tarla_id: Optional[int]
    tarla: Optional[dict]       # full row from `database.get_tarla(tarla_id)`
    research: Optional[object]  # `prospective_validation.config.Site` (or None)

    # ── derived identifiers ────────────────────────────────────────────────
    @property
    def research_code(self) -> Optional[str]:
        """EVR_xx bridge code, sourced from the DB row."""
        if self.tarla and self.tarla.get("research_code"):
            return self.tarla["research_code"]
        if self.research is not None:
            return getattr(self.research, "id", None)
        return None

    # legacy alias — many pages still call `.research_id`
    @property
    def research_id(self) -> Optional[str]:
        return self.research_code

    @property
    def name(self) -> str:
        if self.tarla and "isim" in self.tarla:
            return self.tarla["isim"]
        if self.research is not None:
            return getattr(self.research, "name", str(self.research_code))
        return self.research_code or f"#{self.db_tarla_id}"

    @property
    def lat(self) -> Optional[float]:
        if self.tarla and self.tarla.get("konum_lat") is not None:
            return float(self.tarla["konum_lat"])
        if self.research is not None and hasattr(self.research, "lat"):
            return float(self.research.lat)
        return None

    @property
    def lon(self) -> Optional[float]:
        if self.tarla and self.tarla.get("konum_lon") is not None:
            return float(self.tarla["konum_lon"])
        if self.research is not None and hasattr(self.research, "lon"):
            return float(self.research.lon)
        return None


def get_active_site() -> ActiveSite:
    """Resolve the active site from the single source of truth (DB tarla)."""
    db_id = st.session_state.get("tarla_id")

    tarla = None
    try:
        from database import get_tarla  # type: ignore[import-not-found]
        if db_id is not None:
            tarla = get_tarla(db_id)
    except Exception:                                           # noqa: BLE001
        tarla = None

    # Look up the matching FLOV Site by research_code, if the DB row has one
    research = None
    rcode = tarla.get("research_code") if tarla else None
    if rcode:
        try:
            from prospective_validation import config as _flov  # type: ignore
            for s in _flov.EVRENLI_SITES:
                if getattr(s, "id", None) == rcode:
                    research = s
                    break
        except Exception:                                       # noqa: BLE001
            research = None

    return ActiveSite(db_tarla_id=db_id, tarla=tarla, research=research)


def navigate_to(page: str, context: Optional[dict] = None) -> None:
    """Programmatic cross-tab navigation. Sidebar radio observes `nav_target`.

    NB: Streamlit prefers a widget's persisted ``key`` value over a fresh
    ``index=`` argument on re-render — so writing only ``nav_target`` is not
    enough.  We also force-set ``active_page`` (the sidebar radio's key) so
    the new page wins on the next rerun.
    """
    st.session_state["nav_target"] = page
    st.session_state["active_page"] = page
    if context:
        st.session_state["scrag_context"] = context
    st.rerun()


__all__ = ["init_session_state", "get_active_site", "ActiveSite", "navigate_to"]
