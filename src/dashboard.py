"""
TRAK-AI KDS — Master Dashboard (unified router)
================================================
8 sekme: 🏠 Ana | 🌿 Tarla Detay | 🚜 Rover | 💬 SCRAG |
         ✅ FLOV | 🔬 X-Modal | 🌦️ Hava | ⚙️ Settings

Calistirma:
    streamlit run src/dashboard.py

This is the single entry point for the entire DSS. Page rendering logic
lives under `src/dashboard_pages/<page>/__init__.py` (and `_legacy_pages.py`
for the original farmer-facing surface).
"""
from __future__ import annotations

import os
import sys
import logging

# ── Path Kurulumu ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_CP2_DIR = os.path.join(PROJECT_ROOT, "src", "cp2_model")
_CP4_DIR = os.path.join(PROJECT_ROOT, "src", "cp4_rag")
for _p in [_SRC_DIR, _CP2_DIR, _CP4_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st

# ── Streamlit page config (must be the very first Streamlit call) ────────────
st.set_page_config(
    page_title="TRAK-AIA KDS",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB init (single point of truth — legacy module no longer calls it) ──────
try:
    from database import init_db
    init_db()
except Exception as exc:                                            # noqa: BLE001
    st.error(f"Veritabani baslatma hatasi: {exc}")


# ── Auto-ensure tarla_tahminler is populated (first-launch convenience) ──
def _auto_ensure_predictions() -> None:
    """If tarla_tahminler is empty for any active tarla, run the crop-aware
    pipeline once. Cached via session state so it runs at most once per
    Streamlit session."""
    if st.session_state.get("_auto_predict_done"):
        return
    try:
        import sqlite3
        from pathlib import Path
        db = Path(PROJECT_ROOT) / "data" / "trakai.db"
        if not db.exists():
            return
        con = sqlite3.connect(db)
        try:
            missing = con.execute("""
                SELECT t.id FROM tarla t
                LEFT JOIN tarla_tahminler tt ON tt.tarla_id = t.id
                WHERE tt.id IS NULL
            """).fetchall()
        finally:
            con.close()
        if not missing:
            st.session_state["_auto_predict_done"] = True
            return

        st.toast(f"{len(missing)} tarla için tahmin hesaplanıyor...",
                 icon="⚙️")
        import subprocess
        subprocess.run(
            [sys.executable,
             str(Path(PROJECT_ROOT) / "scripts" / "predict_all_tarlalar.py")],
            cwd=PROJECT_ROOT, capture_output=True, timeout=300,
        )
        st.session_state["_auto_predict_done"] = True
    except Exception as exc:                                        # noqa: BLE001
        logging.getLogger("trakai.dashboard").warning(
            "auto-predict failed: %s", exc)


_auto_ensure_predictions()

# ── Shared utilities ─────────────────────────────────────────────────────────
from dashboard_pages.shared.styling import (
    apply_trakai_theme, render_main_banner, render_theme_toggle,
)
from dashboard_pages.shared.session import init_session_state, get_active_site
from dashboard_pages.shared.components import (
    render_global_alert_bar, system_status_indicators,
)

logger = logging.getLogger("trakai.dashboard")


# ── Page registry ────────────────────────────────────────────────────────────
# Each entry: (label, lazy renderer that returns a callable).
# Lazy import keeps cold-start fast and avoids cascading import errors.
def _legacy_render(page_fn_name: str):
    def _runner():
        from dashboard_pages import _legacy_pages as legacy   # type: ignore
        site = get_active_site()
        if site.tarla is None:
            st.error("Tarla bulunamadi. Veritabanini kontrol edin.")
            return
        getattr(legacy, page_fn_name)(site.db_tarla_id, site.tarla)
    return _runner


def _module_render(module_path: str):
    def _runner():
        mod = __import__(module_path, fromlist=["render"])
        mod.render()
    return _runner


PAGES: dict[str, callable] = {
    "🏠 Ana":         _module_render("dashboard_pages.home"),
    "🌿 Tarla Detay": _legacy_render("page_tarla"),
    "🚜 Rover":       _legacy_render("page_rover"),
    "💬 SCRAG":       _legacy_render("page_chat"),
    "✅ FLOV":        _module_render("dashboard_pages.flov_validation"),
    "🔬 X-Modal":     _module_render("dashboard_pages.cross_modal"),
    "🌦️ Hava":        _module_render("dashboard_pages.weather"),
    "⚙️ Settings":    _module_render("dashboard_pages.settings"),
}


# ── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar() -> str:
    """Render unified sidebar: brand, site selectors, status, navigation."""
    with st.sidebar:
        st.markdown("# 🌾 TRAK-AIA KDS")
        st.caption("TUBiTAK 2209-A • Trakya Universitesi • 2026")

        # Theme toggle (sistem / aydınlık / karanlık)
        render_theme_toggle()

        st.divider()

        # ── Single tarla selector (research_code bridges to FLOV/EVR_xx) ─────
        try:
            from database import get_tarlalar
            tarlalar = get_tarlalar() or []
            if tarlalar:
                def _lbl(t: dict) -> str:
                    rc = t.get("research_code")
                    tag = f" [{rc}]" if rc else ""
                    crop = t.get("aktif_urun") or "?"
                    return f"{t['isim']}{tag} ({crop})"
                labels = {t["id"]: _lbl(t) for t in tarlalar}
                st.selectbox(
                    "Tarla",
                    options=list(labels.keys()),
                    format_func=lambda x: labels[x],
                    key="tarla_id",
                )
            else:
                st.warning("DB'de tarla yok. `python src/database.py --reset` cagirin.")
        except Exception as exc:                                    # noqa: BLE001
            st.caption(f"DB tarla listesi yok ({exc})")

        # ── Research year (for FLOV/cross-modal artefact lookup) ─────────────
        st.number_input("Yil", min_value=2024, max_value=2030, step=1,
                        key="research_year")

        st.divider()

        # ── Navigation ───────────────────────────────────────────────────────
        nav_target = st.session_state.get("nav_target")
        nav_options = list(PAGES.keys())
        default_idx = nav_options.index(nav_target) if nav_target in nav_options else 0
        page = st.radio("Sayfa", nav_options, index=default_idx,
                        label_visibility="collapsed", key="active_page")
        # Clear cross-page jump target after consumption.
        if nav_target:
            st.session_state["nav_target"] = None

        st.divider()
        st.markdown("**Sistem Durumu**")
        system_status_indicators()

    return page


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    apply_trakai_theme()
    init_session_state()

    page = render_sidebar()

    # Global alert bar (CRITICAL across FLOV / X-Modal / Weather).
    render_global_alert_bar()

    # Light banner per top-level tab.
    subtitle_map = {
        "🏠 Ana":         "Cok kaynakli karar destek sistemi",
        "🌿 Tarla Detay": "Bitki sagligi, verim, fenoloji",
        "🚜 Rover":       "Alan robotu telemetri ve anomali",
        "💬 SCRAG":       "Bilgi tabanli tarim asistani",
        "✅ FLOV":        "Forward-looking validation",
        "🔬 X-Modal":     "Saha · Uydu · Ozellik 3-yollu konsensus",
        "🌦️ Hava":        "ERA5 + Open-Meteo + climatology",
        "⚙️ Settings":    "API durumu, model integrity, audit",
    }
    render_main_banner(page.split(" ", 1)[-1] if " " in page else page,
                       subtitle_map.get(page, ""))

    # Dispatch.
    runner = PAGES.get(page)
    if runner is None:
        st.error(f"Bilinmeyen sayfa: {page}")
        return
    try:
        runner()
    except Exception as exc:                                        # noqa: BLE001
        logger.exception("Page render failed: %s", page)
        st.error(f"Sayfa yuklenemedi: {exc}")
        with st.expander("Hata detayi"):
            import traceback
            st.code(traceback.format_exc(), language="python")


if __name__ == "__main__":
    main()
