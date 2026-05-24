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
    /* ═══════════════════════════════════════════════════════════════════
       TRAK-AI KDS — Comprehensive Theme System
       v2.0 (2026-05-23) — Streamlit native widget coverage
       Tüm st.* bileşenleri light/dark uyumlu yapan kapsamlı CSS.
       ═══════════════════════════════════════════════════════════════════ */

    /* ── Brand palette (constant) ─────────────────────────────────────── */
    :root {
        --primary:       #2E7D32;
        --primary-dark:  #1B5E20;
        --primary-light: #66BB6A;
        --secondary:     #FFA000;
        --accent:        #1976D2;
        --critical:      #C62828;
        --warning:       #F57C00;
        --info:          #1976D2;
        --success:       #388E3C;
    }

    /* ── Light mode (default) ─────────────────────────────────────────── */
    :root {
        --bg:                #FFFFFF;
        --bg-secondary:      #F5F7F4;
        --surface:           #FFFFFF;
        --surface-alt:       #F5F7F4;
        --surface-muted:     #ECEFEA;
        --surface-tab:       #EFEDE9;
        --surface-hover:     #E8F1E5;
        --border:            #D0D7D2;
        --border-strong:     #A8B5AC;
        --text:              #1F2A24;
        --text-muted:        #4A5550;
        --text-soft:         #6B7670;
        --link:              #1976D2;
        --shadow:            0 2px 8px rgba(0,0,0,0.08);
        --kpi-value:         #1B5E20;
        --sidebar-bg-1:      #F8F9FA;
        --sidebar-bg-2:      #E9ECEF;
        --sidebar-text:      #1F2A24;
        --banner-shadow:     rgba(46,125,50,0.20);
        --info-bg:           #E3F2FD;
        --info-text:         #0D47A1;
        --warning-bg:        #FFF3E0;
        --warning-text:      #E65100;
        --success-bg:        #E8F5E9;
        --success-text:      #1B5E20;
        --error-bg:          #FFEBEE;
        --error-text:        #B71C1C;
    }

    /* ── Dark mode (system preference) ────────────────────────────────── */
    @media (prefers-color-scheme: dark) {
        :root:not([data-trakai-theme="light"]) {
            --bg:             #0E1410;
            --bg-secondary:   #16201A;
            --surface:        #1B2520;
            --surface-alt:    #25312B;
            --surface-muted:  #2E3A33;
            --surface-tab:    #2A332D;
            --surface-hover:  #2F3D34;
            --border:         #3A4842;
            --border-strong:  #586A5F;
            --text:           #ECF3ED;
            --text-muted:     #C2CFC7;
            --text-soft:      #95A39B;
            --link:           #64B5F6;
            --shadow:         0 2px 10px rgba(0,0,0,0.40);
            --kpi-value:      #A5D6A7;
            --sidebar-bg-1:   #1A211D;
            --sidebar-bg-2:   #11160F;
            --sidebar-text:   #ECF3ED;
            --banner-shadow:  rgba(0,0,0,0.45);
            --info-bg:        #102A43;
            --info-text:      #BCDFFF;
            --warning-bg:     #3D2A0F;
            --warning-text:   #FFD7A0;
            --success-bg:     #1A3A1F;
            --success-text:   #B8E2BB;
            --error-bg:       #3A1717;
            --error-text:     #FFB4B4;
        }
    }

    /* ── Dark mode (explicit toggle overrides system) ─────────────────── */
    :root[data-trakai-theme="dark"] {
        --bg:             #0E1410;
        --bg-secondary:   #16201A;
        --surface:        #1B2520;
        --surface-alt:    #25312B;
        --surface-muted:  #2E3A33;
        --surface-tab:    #2A332D;
        --surface-hover:  #2F3D34;
        --border:         #3A4842;
        --border-strong:  #586A5F;
        --text:           #ECF3ED;
        --text-muted:     #C2CFC7;
        --text-soft:      #95A39B;
        --link:           #64B5F6;
        --shadow:         0 2px 10px rgba(0,0,0,0.40);
        --kpi-value:      #A5D6A7;
        --sidebar-bg-1:   #1A211D;
        --sidebar-bg-2:   #11160F;
        --sidebar-text:   #ECF3ED;
        --banner-shadow:  rgba(0,0,0,0.45);
        --info-bg:        #102A43;
        --info-text:      #BCDFFF;
        --warning-bg:     #3D2A0F;
        --warning-text:   #FFD7A0;
        --success-bg:     #1A3A1F;
        --success-text:   #B8E2BB;
        --error-bg:       #3A1717;
        --error-text:     #FFB4B4;
    }

    /* ── Light mode (explicit toggle wins on dark OS) ─────────────────── */
    :root[data-trakai-theme="light"] {
        --bg:             #FFFFFF;
        --bg-secondary:   #F5F7F4;
        --surface:        #FFFFFF;
        --surface-alt:    #F5F7F4;
        --surface-muted:  #ECEFEA;
        --surface-tab:    #EFEDE9;
        --surface-hover:  #E8F1E5;
        --border:         #D0D7D2;
        --border-strong:  #A8B5AC;
        --text:           #1F2A24;
        --text-muted:     #4A5550;
        --text-soft:      #6B7670;
        --link:           #1976D2;
        --shadow:         0 2px 8px rgba(0,0,0,0.08);
        --kpi-value:      #1B5E20;
        --sidebar-bg-1:   #F8F9FA;
        --sidebar-bg-2:   #E9ECEF;
        --sidebar-text:   #1F2A24;
        --banner-shadow:  rgba(46,125,50,0.20);
        --info-bg:        #E3F2FD;
        --info-text:      #0D47A1;
        --warning-bg:     #FFF3E0;
        --warning-text:   #E65100;
        --success-bg:     #E8F5E9;
        --success-text:   #1B5E20;
        --error-bg:       #FFEBEE;
        --error-text:     #B71C1C;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE WIDGET OVERRIDES
       — Tüm st.* bileşenlerini CSS değişkenlerine bağla
       ═══════════════════════════════════════════════════════════════════ */

    /* Global body + main area */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }
    .main .block-container, [data-testid="stMain"] {
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }

    /* Headings — koyu modda %100 görünür */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: var(--text) !important;
    }

    /* Markdown paragraph + list */
    .stMarkdown p, .stMarkdown li, .stMarkdown span:not([class*="badge"]) {
        color: var(--text) !important;
    }
    .stMarkdown a { color: var(--link) !important; }

    /* Caption — gri ton bg'ye uyumlu */
    .stCaption, [data-testid="stCaptionContainer"], .caption,
    small, .stMarkdown small {
        color: var(--text-muted) !important;
    }

    /* ── st.metric ────────────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        box-shadow: var(--shadow);
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
        color: var(--text-muted) !important;
        font-weight: 500 !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
        color: var(--kpi-value) !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] div {
        color: var(--text-muted) !important;
    }
    /* Delta pozitif/negatif renkleri — Streamlit kendi rengini kullanır,
       sadece görünürlüğü garanti et */
    [data-testid="stMetricDelta"] svg { opacity: 0.9; }

    /* ── st.info / st.success / st.warning / st.error ─────────────────── */
    div[data-testid="stAlert"] {
        border-radius: 8px !important;
        padding: 0.7rem 1rem !important;
        border: 1px solid transparent !important;
    }
    /* Info (mavi tonlar) */
    div[data-testid="stAlert"][data-baseweb="notification"],
    div[role="alert"][data-baseweb="notification"] {
        background-color: var(--info-bg) !important;
        color: var(--info-text) !important;
    }
    div[data-testid="stAlert"] [data-testid="stAlertContentInfo"],
    div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"] div, div[data-testid="stAlert"] span {
        color: inherit !important;
    }
    /* Streamlit kind sınıfları */
    div.stAlert.st-emotion-cache-1c7y2kd, /* info */
    div[data-baseweb="notification"][kind="info"] {
        background-color: var(--info-bg) !important;
        color: var(--info-text) !important;
    }
    /* Warning */
    div[data-baseweb="notification"][kind="warning"],
    .stWarning {
        background-color: var(--warning-bg) !important;
        color: var(--warning-text) !important;
    }
    /* Success */
    div[data-baseweb="notification"][kind="success"],
    .stSuccess {
        background-color: var(--success-bg) !important;
        color: var(--success-text) !important;
    }
    /* Error */
    div[data-baseweb="notification"][kind="error"],
    .stError {
        background-color: var(--error-bg) !important;
        color: var(--error-text) !important;
    }

    /* ── DataFrame / Tables ───────────────────────────────────────────── */
    [data-testid="stDataFrame"], .stDataFrame, .stTable {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    [data-testid="stDataFrame"] thead tr th,
    .stDataFrame thead tr th, .stTable thead tr th {
        background-color: var(--surface-muted) !important;
        color: var(--text) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid var(--border-strong) !important;
    }
    [data-testid="stDataFrame"] tbody tr td,
    .stDataFrame tbody tr td, .stTable tbody tr td {
        color: var(--text) !important;
        border-color: var(--border) !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(even),
    .stDataFrame tbody tr:nth-child(even) {
        background-color: var(--surface-alt) !important;
    }
    /* Glide-data-grid (Streamlit yeni dataframe) */
    .glide-data-grid {
        --gdg-bg-cell: var(--surface) !important;
        --gdg-bg-cell-medium: var(--surface-alt) !important;
        --gdg-bg-header: var(--surface-muted) !important;
        --gdg-text-dark: var(--text) !important;
        --gdg-text-medium: var(--text-muted) !important;
        --gdg-text-header: var(--text) !important;
        --gdg-border-color: var(--border) !important;
    }

    /* ── Inputs: selectbox, multiselect, text_input, number_input ─────── */
    [data-baseweb="select"] > div, [data-baseweb="input"] input,
    .stSelectbox div[role="combobox"], .stTextInput input,
    .stNumberInput input, .stTextArea textarea, .stDateInput input {
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border-color: var(--border) !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label,
    .stTextArea label, .stDateInput label, .stMultiSelect label,
    .stRadio label, .stCheckbox label, .stSlider label,
    .stFileUploader label {
        color: var(--text) !important;
        font-weight: 500 !important;
    }
    /* Selectbox dropdown listesi */
    [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="list"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    [data-baseweb="menu"] [role="option"] {
        color: var(--text) !important;
    }
    [data-baseweb="menu"] [role="option"]:hover {
        background-color: var(--surface-hover) !important;
    }

    /* Radio + Checkbox text */
    .stRadio div[role="radiogroup"] label,
    .stCheckbox label, .stCheckbox > div {
        color: var(--text) !important;
    }
    .stRadio div[role="radiogroup"] label > div:last-child,
    .stCheckbox label > span {
        color: var(--text) !important;
    }

    /* Slider */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: var(--primary) !important;
    }
    .stSlider [data-baseweb="slider"] div[style*="background"] {
        background-color: var(--primary-light) !important;
    }

    /* ── Buttons ──────────────────────────────────────────────────────── */
    .stButton button, button[kind="primary"], button[kind="secondary"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        font-weight: 500 !important;
    }
    .stButton button:hover, button[kind="primary"]:hover, button[kind="secondary"]:hover {
        background-color: var(--surface-hover) !important;
        border-color: var(--primary) !important;
        color: var(--text) !important;
    }
    button[kind="primary"], .stButton button[type="primary"] {
        background-color: var(--primary) !important;
        color: #FFFFFF !important;
        border-color: var(--primary) !important;
    }
    button[kind="primary"]:hover {
        background-color: var(--primary-dark) !important;
        color: #FFFFFF !important;
    }

    /* ── Expander ─────────────────────────────────────────────────────── */
    [data-testid="stExpander"] details, .streamlit-expanderHeader, .stExpander {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary, .streamlit-expanderHeader p,
    [data-testid="stExpanderToggleIcon"], .stExpander summary {
        color: var(--text) !important;
        font-weight: 500 !important;
    }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }

    /* ── Code blocks ──────────────────────────────────────────────────── */
    .stCodeBlock, code, pre, [data-testid="stCode"] {
        background-color: var(--surface-muted) !important;
        color: var(--text) !important;
        border-radius: 6px !important;
    }
    .stCodeBlock pre, .stCodeBlock code {
        background-color: transparent !important;
        color: var(--text) !important;
    }

    /* ── Tabs ─────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent !important;
        border-bottom: 1px solid var(--border) !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--surface-tab) !important;
        color: var(--text) !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--surface-hover) !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary) !important;
        color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] p {
        color: #FFFFFF !important;
    }

    /* ── Sidebar (CRITICAL — Streamlit sidebar tüm widgetlar) ─────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-bg-1) 0%, var(--sidebar-bg-2) 100%) !important;
    }
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] * {
        color: var(--sidebar-text);
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: var(--text-muted) !important;
    }

    /* ── Progress bar ─────────────────────────────────────────────────── */
    .stProgress > div > div > div {
        background-color: var(--primary) !important;
    }
    .stProgress > div {
        background-color: var(--surface-muted) !important;
    }

    /* ── Spinner ──────────────────────────────────────────────────────── */
    .stSpinner > div { color: var(--primary) !important; }

    /* ── Plotly chart background (transparent) ────────────────────────── */
    .js-plotly-plot, .plotly, .plot-container {
        background-color: transparent !important;
    }
    .js-plotly-plot .plotly .modebar { background: transparent !important; }

    /* ── Divider ──────────────────────────────────────────────────────── */
    hr, .stDivider, [data-testid="stDivider"] {
        border-color: var(--border) !important;
        background-color: var(--border) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       TRAK-AI CUSTOM COMPONENTS (önceki versiyondan korunan)
       ═══════════════════════════════════════════════════════════════════ */

    /* Banner */
    .main-banner {
        background: linear-gradient(135deg, #2E7D32 0%, #558B2F 50%, #FFA000 100%);
        padding: 1.2rem 1.6rem;
        border-radius: 12px;
        color: #FFFFFF;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px var(--banner-shadow);
    }
    .main-banner h1 { margin: 0; font-size: 1.7rem; color: #FFFFFF !important; }
    .main-banner p  { margin: 0.3rem 0 0 0; opacity: 0.95; font-size: 0.95rem; color: #FFFFFF !important; }

    /* KPI card (custom HTML) */
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
    .kpi-card .kpi-delta { font-size: 0.80rem; color: var(--text-muted); }

    /* Alert badges */
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

    /* Global alert bar */
    .global-alert-bar {
        background: linear-gradient(90deg, #C62828, #E53935);
        color: #FFFFFF !important;
        padding: 0.7rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 0.95rem;
    }
    .global-alert-bar * { color: #FFFFFF !important; }

    /* Weather day cards */
    .weather-day-card {
        text-align: center; padding: 0.7rem 0.4rem;
        background: var(--surface-alt); border-radius: 8px;
        border: 1px solid var(--border);
        color: var(--text);
    }
    .weather-day-card .day-name { font-size: 0.78rem; color: var(--text-muted); }
    .weather-day-card .day-icon { font-size: 1.7rem; margin: 0.2rem 0; }
    .weather-day-card .day-temp { font-weight: 600; color: var(--text); }
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
