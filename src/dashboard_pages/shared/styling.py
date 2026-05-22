"""TRAK-AI brand theme + reusable HTML chrome (banner, alert bar).

Theme-aware: respects both
    * explicit user toggle (sidebar) via the `app_theme` session-state key
      ("light" | "dark"), applied as `data-trakai-theme` on the <html> root, and
    * system preference via `@media (prefers-color-scheme: dark)`.

All surface colors flow through CSS variables; no hardcoded white/grey
backgrounds remain so cards and chrome adapt cleanly to dark mode.
"""

from __future__ import annotations

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CSS — uses cascading variable overrides for light/dark
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
    /* ── Brand palette (constant) ─────────────────────────────────────── */
    :root {
        --primary:       #2E7D32;
        --primary-dark:  #1B5E20;
        --secondary:     #FFA000;
        --accent:        #1976D2;
        --critical:      #C62828;
        --warning:       #F57C00;
        --info:          #1976D2;
        --success:       #388E3C;
    }

    /* ── Light mode surface variables (default) ───────────────────────── */
    :root {
        --surface:           #FFFFFF;
        --surface-alt:       #F5F7F4;
        --surface-muted:     #ECEFEA;
        --surface-tab:       #EFEDE9;
        --border:            #E0E0E0;
        --text:              #1F2A24;
        --text-muted:        #5E6B62;
        --shadow:            0 2px 8px rgba(0,0,0,0.08);
        --kpi-value:         var(--primary-dark);
        --sidebar-bg-1:      #F8F9FA;
        --sidebar-bg-2:      #E9ECEF;
        --banner-shadow:     rgba(46,125,50,0.20);
    }

    /* ── Dark mode surface variables (system preference) ──────────────── */
    @media (prefers-color-scheme: dark) {
        :root:not([data-trakai-theme="light"]) {
            --surface:        #1B2520;
            --surface-alt:    #25312B;
            --surface-muted:  #2E3A33;
            --surface-tab:    #2A332D;
            --border:         #3A4842;
            --text:           #E8EFE9;
            --text-muted:     #A6B3AC;
            --shadow:         0 2px 10px rgba(0,0,0,0.40);
            --kpi-value:      #A5D6A7;
            --sidebar-bg-1:   #1A211D;
            --sidebar-bg-2:   #11160F;
            --banner-shadow:  rgba(0,0,0,0.45);
        }
    }

    /* ── Dark mode override (explicit user toggle wins over system) ───── */
    :root[data-trakai-theme="dark"] {
        --surface:        #1B2520;
        --surface-alt:    #25312B;
        --surface-muted:  #2E3A33;
        --surface-tab:    #2A332D;
        --border:         #3A4842;
        --text:           #E8EFE9;
        --text-muted:     #A6B3AC;
        --shadow:         0 2px 10px rgba(0,0,0,0.40);
        --kpi-value:      #A5D6A7;
        --sidebar-bg-1:   #1A211D;
        --sidebar-bg-2:   #11160F;
        --banner-shadow:  rgba(0,0,0,0.45);
    }

    /* ── Force light when user explicitly chose light even on dark OS ── */
    :root[data-trakai-theme="light"] {
        --surface:        #FFFFFF;
        --surface-alt:    #F5F7F4;
        --surface-muted:  #ECEFEA;
        --surface-tab:    #EFEDE9;
        --border:         #E0E0E0;
        --text:           #1F2A24;
        --text-muted:     #5E6B62;
        --shadow:         0 2px 8px rgba(0,0,0,0.08);
        --kpi-value:      var(--primary-dark);
        --sidebar-bg-1:   #F8F9FA;
        --sidebar-bg-2:   #E9ECEF;
        --banner-shadow:  rgba(46,125,50,0.20);
    }

    /* ── Banner ───────────────────────────────────────────────────────── */
    .main-banner {
        background: linear-gradient(135deg, #2E7D32 0%, #558B2F 50%, #FFA000 100%);
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        color: #FFFFFF;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px var(--banner-shadow);
    }
    .main-banner h1 { margin: 0; font-size: 1.7rem; }
    .main-banner p  { margin: 0.3rem 0 0 0; opacity: 0.9; font-size: 0.95rem; }

    /* ── KPI card ─────────────────────────────────────────────────────── */
    .kpi-card {
        background: var(--surface);
        border-radius: 10px;
        padding: 1.0rem 1.2rem;
        box-shadow: var(--shadow);
        border-left: 4px solid var(--primary);
        margin-bottom: 0.5rem;
        color: var(--text);
    }
    .kpi-card .kpi-label { color: var(--text-muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-card .kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--kpi-value); margin: 0.25rem 0; }
    .kpi-card .kpi-delta { font-size: 0.80rem; }

    /* ── Alert badges (constant on color, work on any bg) ─────────────── */
    .alert-badge {
        padding: 0.20rem 0.65rem; border-radius: 6px;
        font-weight: 600; font-size: 0.80rem; color: #FFFFFF;
        display: inline-block; margin-right: 0.3rem;
    }
    .alert-critical { background: var(--critical); }
    .alert-warning  { background: var(--warning);  }
    .alert-info     { background: var(--info);     }
    .alert-success  { background: var(--success);  }
    .alert-low      { background: #757575; }

    /* ── Global alert bar ─────────────────────────────────────────────── */
    .global-alert-bar {
        background: linear-gradient(90deg, #C62828, #E53935);
        color: #FFFFFF;
        padding: 0.7rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 0.95rem;
    }

    /* ── Sidebar ──────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-bg-1) 0%, var(--sidebar-bg-2) 100%);
    }

    /* ── Tabs ─────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        background: var(--surface-tab);
        color: var(--text);
        border-radius: 8px 8px 0 0;
        padding: 0.4rem 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--primary); color: #FFFFFF;
    }

    /* ── Weather day cards ────────────────────────────────────────────── */
    .weather-day-card {
        text-align: center; padding: 0.7rem 0.4rem;
        background: var(--surface-alt); border-radius: 8px;
        border: 1px solid var(--border);
        color: var(--text);
    }
    .weather-day-card .day-name { font-size: 0.78rem; color: var(--text-muted); }
    .weather-day-card .day-icon { font-size: 1.7rem; margin: 0.2rem 0; }
    .weather-day-card .day-temp { font-weight: 600; }
    .weather-day-card .day-prec { color: var(--accent); font-size: 0.78rem; }
</style>
"""


# JS snippet: applies the `data-trakai-theme` attribute on <html> so
# CSS variables flip immediately without Streamlit-rerun glitches.
def _theme_attr_script(theme: str) -> str:
    safe = "dark" if theme == "dark" else "light"
    return (
        "<script>"
        f"document.documentElement.setAttribute('data-trakai-theme', '{safe}');"
        "</script>"
    )


def apply_trakai_theme() -> None:
    """Inject CSS + sync the explicit theme choice from session state."""
    st.markdown(_CSS, unsafe_allow_html=True)
    theme = st.session_state.get("app_theme")
    if theme in ("light", "dark"):
        st.markdown(_theme_attr_script(theme), unsafe_allow_html=True)


def render_theme_toggle() -> None:
    """Sidebar widget: light / dark / system. Call from inside `with st.sidebar:`."""
    options = ["🖥️ Sistem", "☀️ Aydınlık", "🌙 Karanlık"]
    current = st.session_state.get("app_theme", "system")
    idx = {"system": 0, "light": 1, "dark": 2}.get(current, 0)
    choice = st.radio(
        "Tema",
        options,
        index=idx,
        horizontal=True,
        key="_theme_radio",
        label_visibility="collapsed",
    )
    new_value = {options[0]: "system", options[1]: "light", options[2]: "dark"}[choice]
    if new_value != current:
        st.session_state["app_theme"] = new_value
        st.rerun()


def render_main_banner(title: str, subtitle: str = "") -> None:
    sub = f'<p>{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="main-banner"><h1>🌾 {title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


__all__ = ["apply_trakai_theme", "render_main_banner", "render_theme_toggle"]
