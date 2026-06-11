"""TRAK-AI KDS — Precision Agriculture Tema Sistemi (v3.0).

Konsept
-------
* **Dark mode**  : Deep forest (#0A1A0A) + vivid green (#66BB6A) + sunflower gold (#FFD54F)
* **Light mode** : Crisp white (#FFFFFF) + Trakya green (#2E7D32) + sunflower yellow (#F9A825)
* WCAG AA+ kontrast (min 4.5:1, ana metin 12:1+)
* Tüm Streamlit native widgetlar override edilmiştir
* Sidebar, KPI card, alert badge, dataframe, expander, plotly hepsi tema duyarlı
"""

from __future__ import annotations

from typing import Literal

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CSS — Precision Agriculture palette + comprehensive Streamlit overrides
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
<style>
    /* ═══════════════════════════════════════════════════════════════════
       TRAK-AI KDS — Precision Agriculture Theme v3.0
       Dark (default) + Light + System modları
       ═══════════════════════════════════════════════════════════════════ */

    /* ── Brand palette (constant across modes) ───────────────────────── */
    :root {
        --critical:        #C62828;
        --warning:         #E65100;
        --info-strong:     #1565C0;
        --success-strong:  #2E7D32;
    }

    /* ── LIGHT MODE (default fallback) ──────────────────────────────── */
    :root,
    :root[data-trakai-theme="light"] {
        /* Backgrounds */
        --bg-primary:      #FFFFFF;
        --bg-secondary:    #F1F8E9;
        --bg-card:         #FFFFFF;
        --bg-card-alt:     #F5F9F1;
        --bg-sidebar:      #E8F5E9;
        --bg-sidebar-alt:  #C8E6C9;
        --bg-hover:        #E0F2E1;
        --bg-muted:        #ECEFEA;

        /* Text */
        --text-primary:    #1B2A1B;
        --text-secondary:  #4A5E4A;
        --text-muted:      #6B7B6B;
        --text-on-accent:  #FFFFFF;

        /* Accents */
        --accent-green:    #2E7D32;
        --accent-green-2:  #4CAF50;
        --accent-yellow:   #F9A825;
        --accent-yellow-2: #FFD54F;
        --accent-blue:     #1565C0;

        /* Borders + shadows */
        --border:          #C8E6C9;
        --border-strong:   #A5D6A7;
        --shadow:          0 2px 8px rgba(46, 125, 50, 0.12);
        --shadow-hover:    0 6px 20px rgba(46, 125, 50, 0.20);
        --glow-critical:   rgba(198, 40, 40, 0.35);

        /* Semantic */
        --critical-text:   #B71C1C;
        --warning-text:    #E65100;
        --info-text:       #0D47A1;
        --success-text:    #1B5E20;
        --critical-bg:     #FFEBEE;
        --warning-bg:      #FFF3E0;
        --info-bg:         #E3F2FD;
        --success-bg:      #E8F5E9;

        /* KPI */
        --kpi-value:       #1B5E20;
        --kpi-border-gradient: linear-gradient(180deg, #2E7D32 0%, #F9A825 100%);
    }

    /* ── DARK MODE (system preference) ─────────────────────────────── */
    @media (prefers-color-scheme: dark) {
        :root:not([data-trakai-theme="light"]) {
            --bg-primary:      #0A1A0A;
            --bg-secondary:    #0F2010;
            --bg-card:         #162616;
            --bg-card-alt:     #1A2E1A;
            --bg-sidebar:      #0F1F0F;
            --bg-sidebar-alt:  #0A1606;
            --bg-hover:        #1F3520;
            --bg-muted:        #1A261A;

            --text-primary:    #E8F5E9;
            --text-secondary:  #A5D6A7;
            --text-muted:      #81C784;
            --text-on-accent:  #FFFFFF;

            --accent-green:    #66BB6A;
            --accent-green-2:  #4CAF50;
            --accent-yellow:   #FFD54F;
            --accent-yellow-2: #FFC107;
            --accent-blue:     #42A5F5;

            --border:          #1E3A1E;
            --border-strong:   #2E5E2E;
            --shadow:          0 2px 10px rgba(102, 187, 106, 0.10);
            --shadow-hover:    0 6px 22px rgba(102, 187, 106, 0.20);
            --glow-critical:   rgba(239, 154, 154, 0.45);

            --critical-text:   #FFB4B4;
            --warning-text:    #FFCC80;
            --info-text:       #90CAF9;
            --success-text:    #A5D6A7;
            --critical-bg:     #3A1717;
            --warning-bg:      #3D2A0F;
            --info-bg:         #102A43;
            --success-bg:      #1A3A1F;

            --kpi-value:       #A5D6A7;
            --kpi-border-gradient: linear-gradient(180deg, #66BB6A 0%, #FFD54F 100%);
        }
    }

    /* ── DARK MODE (explicit toggle) ───────────────────────────────── */
    :root[data-trakai-theme="dark"] {
        --bg-primary:      #0A1A0A;
        --bg-secondary:    #0F2010;
        --bg-card:         #162616;
        --bg-card-alt:     #1A2E1A;
        --bg-sidebar:      #0F1F0F;
        --bg-sidebar-alt:  #0A1606;
        --bg-hover:        #1F3520;
        --bg-muted:        #1A261A;

        --text-primary:    #E8F5E9;
        --text-secondary:  #A5D6A7;
        --text-muted:      #81C784;
        --text-on-accent:  #FFFFFF;

        --accent-green:    #66BB6A;
        --accent-green-2:  #4CAF50;
        --accent-yellow:   #FFD54F;
        --accent-yellow-2: #FFC107;
        --accent-blue:     #42A5F5;

        --border:          #1E3A1E;
        --border-strong:   #2E5E2E;
        --shadow:          0 2px 10px rgba(102, 187, 106, 0.10);
        --shadow-hover:    0 6px 22px rgba(102, 187, 106, 0.20);
        --glow-critical:   rgba(239, 154, 154, 0.45);

        --critical-text:   #FFB4B4;
        --warning-text:    #FFCC80;
        --info-text:       #90CAF9;
        --success-text:    #A5D6A7;
        --critical-bg:     #3A1717;
        --warning-bg:      #3D2A0F;
        --info-bg:         #102A43;
        --success-bg:      #1A3A1F;

        --kpi-value:       #A5D6A7;
        --kpi-border-gradient: linear-gradient(180deg, #66BB6A 0%, #FFD54F 100%);
    }

    /* ═══════════════════════════════════════════════════════════════════
       GLOBAL APP CHROME
       ═══════════════════════════════════════════════════════════════════ */

    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }
    .main .block-container, [data-testid="stMain"] {
        background-color: var(--bg-primary) !important;
        color: var(--text-primary) !important;
    }

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
    .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }
    h1 { border-bottom: 2px solid var(--accent-green); padding-bottom: 0.3rem; }

    .stMarkdown p, .stMarkdown li, .stMarkdown span:not([class*="badge"]) {
        color: var(--text-primary) !important;
    }
    .stMarkdown a {
        color: var(--accent-yellow) !important;
        text-decoration: none;
        border-bottom: 1px dotted var(--accent-yellow);
    }
    .stMarkdown a:hover { color: var(--accent-yellow-2) !important; }

    .stCaption, [data-testid="stCaptionContainer"], .caption,
    small, .stMarkdown small {
        color: var(--text-muted) !important;
        font-style: italic;
    }

    /* ═══════════════════════════════════════════════════════════════════
       SIDEBAR — sol menü tüm widgetları
       ═══════════════════════════════════════════════════════════════════ */

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-sidebar) 0%, var(--bg-sidebar-alt) 100%) !important;
        border-right: 1px solid var(--border) !important;
    }
    section[data-testid="stSidebar"] > div { background: transparent !important; }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p {
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] h1 { border-bottom: none; }

    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label,
    section[data-testid="stSidebar"] .stCheckbox label {
        color: var(--text-primary) !important;
    }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: var(--text-muted) !important;
    }
    section[data-testid="stSidebar"] hr,
    section[data-testid="stSidebar"] [data-testid="stDivider"] {
        border-color: var(--border) !important;
        background-color: var(--border) !important;
    }

    /* Sidebar radio item — active state */
    section[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) {
        background-color: var(--bg-hover) !important;
        border-radius: 6px;
    }
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 0.2rem;
    }

    /* ═══════════════════════════════════════════════════════════════════
       MAIN BANNER (Precision Agriculture branding)
       ═══════════════════════════════════════════════════════════════════ */

    .main-banner {
        background: linear-gradient(135deg,
            var(--accent-green) 0%,
            var(--accent-green-2) 45%,
            var(--accent-yellow) 100%);
        padding: 1.3rem 1.7rem;
        border-radius: 14px;
        color: #FFFFFF;
        margin-bottom: 1.3rem;
        box-shadow: 0 4px 16px rgba(46, 125, 50, 0.30);
        position: relative;
        overflow: hidden;
    }
    .main-banner::before {
        content: ""; position: absolute; top: -50%; right: -10%;
        width: 280px; height: 280px;
        background: radial-gradient(circle, rgba(255, 213, 79, 0.18) 0%, transparent 65%);
        pointer-events: none;
    }
    .main-banner h1 {
        margin: 0; font-size: 1.75rem; color: #FFFFFF !important;
        border-bottom: none; letter-spacing: -0.02em;
    }
    .main-banner p {
        margin: 0.35rem 0 0 0; opacity: 0.95; font-size: 0.97rem;
        color: #FFFFFF !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       KPI CARD — Gradient border + hover lift
       ═══════════════════════════════════════════════════════════════════ */

    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-left: 4px solid;
        border-image: var(--kpi-border-gradient) 1;
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.55rem;
        box-shadow: var(--shadow);
        color: var(--text-primary);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-hover);
    }
    .kpi-card .kpi-header {
        display: flex; align-items: center; gap: 0.5rem;
        margin-bottom: 0.35rem;
    }
    .kpi-card .kpi-icon { font-size: 1.15rem; line-height: 1; }
    .kpi-card .kpi-label {
        color: var(--text-muted);
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
    }
    .kpi-card .kpi-value {
        color: var(--kpi-value);
        font-size: 1.85rem;
        font-weight: 700;
        margin: 0.2rem 0 0.15rem 0;
        line-height: 1.1;
    }
    .kpi-card .kpi-delta { font-size: 0.82rem; font-weight: 500; }
    .kpi-card.kpi-small  .kpi-value { font-size: 1.45rem; }
    .kpi-card.kpi-large  .kpi-value { font-size: 2.2rem; }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — st.metric
       ═══════════════════════════════════════════════════════════════════ */

    [data-testid="stMetric"] {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-left: 4px solid;
        border-image: var(--kpi-border-gradient) 1 !important;
        border-radius: 10px !important;
        padding: 0.85rem 1.1rem !important;
        box-shadow: var(--shadow);
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
        color: var(--text-muted) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.75rem !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
        color: var(--kpi-value) !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricDelta"], [data-testid="stMetricDelta"] div {
        color: var(--text-muted) !important;
    }
    [data-testid="stMetricDelta"] svg { opacity: 0.9; }

    /* ═══════════════════════════════════════════════════════════════════
       ALERT BADGES — Glow ve gradient destekli
       ═══════════════════════════════════════════════════════════════════ */

    .alert-badge {
        padding: 0.3rem 0.85rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.78rem;
        color: #FFFFFF;
        display: inline-block;
        margin-right: 0.35rem;
        letter-spacing: 0.3px;
    }
    .alert-critical {
        background: var(--critical);
        color: #FFFFFF;
        box-shadow: 0 0 10px var(--glow-critical);
    }
    .alert-warning {
        background: var(--accent-yellow);
        color: #1B2A1B;
    }
    .alert-info {
        background: transparent;
        border: 1px solid var(--accent-blue);
        color: var(--accent-blue);
    }
    .alert-success {
        background: transparent;
        border: 1px solid var(--accent-green);
        color: var(--accent-green);
    }
    .alert-low {
        background: var(--bg-muted);
        color: var(--text-muted);
        border: 1px solid var(--border);
    }

    /* ═══════════════════════════════════════════════════════════════════
       GLOBAL ALERT BAR — Pulsing critical
       ═══════════════════════════════════════════════════════════════════ */

    .global-alert-bar {
        background: linear-gradient(90deg, var(--critical) 0%, #E53935 50%, var(--accent-yellow) 130%);
        color: #FFFFFF !important;
        padding: 0.75rem 1.4rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex; align-items: center; gap: 0.6rem;
        font-size: 0.96rem;
        font-weight: 500;
        animation: alert-pulse 2.4s ease-in-out infinite;
    }
    .global-alert-bar * { color: #FFFFFF !important; }
    @keyframes alert-pulse {
        0%, 100% { opacity: 1.00; box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.35); }
        50%      { opacity: 0.93; box-shadow: 0 0 0 6px rgba(255, 255, 255, 0); }
    }

    .global-info-bar {
        background: var(--bg-card);
        border-left: 4px solid var(--accent-green);
        color: var(--text-primary);
        padding: 0.65rem 1.1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.92rem;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — st.info / st.success / st.warning / st.error
       ═══════════════════════════════════════════════════════════════════ */

    div[data-testid="stAlert"] {
        border-radius: 10px !important;
        padding: 0.7rem 1.1rem !important;
        border: 1px solid transparent !important;
        font-weight: 500;
    }
    div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stAlert"] div, div[data-testid="stAlert"] span {
        color: inherit !important;
    }
    /* kind sınıfları */
    div[data-baseweb="notification"][kind="info"],
    .stAlert.st-emotion-cache-1c7y2kd {
        background-color: var(--info-bg) !important;
        color: var(--info-text) !important;
        border-color: var(--accent-blue) !important;
    }
    div[data-baseweb="notification"][kind="warning"], .stWarning {
        background-color: var(--warning-bg) !important;
        color: var(--warning-text) !important;
        border-color: var(--warning) !important;
    }
    div[data-baseweb="notification"][kind="success"], .stSuccess {
        background-color: var(--success-bg) !important;
        color: var(--success-text) !important;
        border-color: var(--accent-green) !important;
    }
    div[data-baseweb="notification"][kind="error"], .stError {
        background-color: var(--critical-bg) !important;
        color: var(--critical-text) !important;
        border-color: var(--critical) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — Tabs
       ═══════════════════════════════════════════════════════════════════ */

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent !important;
        border-bottom: 1px solid var(--border) !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--bg-muted) !important;
        color: var(--text-primary) !important;
        border-radius: 8px 8px 0 0 !important;
        padding: 0.5rem 1.05rem !important;
        font-weight: 500 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--bg-hover) !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--accent-green) !important;
        color: #FFFFFF !important;
    }
    .stTabs [aria-selected="true"] p { color: #FFFFFF !important; }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — DataFrame / Table
       ═══════════════════════════════════════════════════════════════════ */

    [data-testid="stDataFrame"], .stDataFrame, .stTable {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] thead tr th,
    .stDataFrame thead tr th, .stTable thead tr th {
        background-color: var(--accent-green) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        font-size: 0.78rem !important;
        border-bottom: 2px solid var(--border-strong) !important;
    }
    [data-testid="stDataFrame"] tbody tr td,
    .stDataFrame tbody tr td, .stTable tbody tr td {
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(even),
    .stDataFrame tbody tr:nth-child(even) {
        background-color: var(--bg-card-alt) !important;
    }
    /* Glide-data-grid (yeni Streamlit dataframe) */
    .glide-data-grid {
        --gdg-bg-cell: var(--bg-card) !important;
        --gdg-bg-cell-medium: var(--bg-card-alt) !important;
        --gdg-bg-header: var(--accent-green) !important;
        --gdg-text-dark: var(--text-primary) !important;
        --gdg-text-medium: var(--text-secondary) !important;
        --gdg-text-header: #FFFFFF !important;
        --gdg-border-color: var(--border) !important;
        --gdg-accent-color: var(--accent-yellow) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — Inputs (selectbox, text, number, etc.)
       ═══════════════════════════════════════════════════════════════════ */

    [data-baseweb="select"] > div, [data-baseweb="input"] input,
    .stSelectbox div[role="combobox"], .stTextInput input,
    .stNumberInput input, .stTextArea textarea, .stDateInput input {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border-color: var(--border) !important;
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label,
    .stTextArea label, .stDateInput label, .stMultiSelect label,
    .stRadio label, .stCheckbox label, .stSlider label,
    .stFileUploader label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="list"] {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
    }
    [data-baseweb="menu"] [role="option"] {
        color: var(--text-primary) !important;
    }
    [data-baseweb="menu"] [role="option"]:hover {
        background-color: var(--bg-hover) !important;
        color: var(--accent-green) !important;
    }

    .stRadio div[role="radiogroup"] label,
    .stCheckbox label, .stCheckbox > div {
        color: var(--text-primary) !important;
    }
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: var(--accent-green) !important;
    }
    .stSlider [data-baseweb="slider"] div[style*="background"] {
        background-color: var(--accent-yellow) !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — Buttons
       ═══════════════════════════════════════════════════════════════════ */

    .stButton button {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        transition: all 0.18s ease;
    }
    .stButton button:hover {
        background-color: var(--bg-hover) !important;
        border-color: var(--accent-green) !important;
        color: var(--accent-green) !important;
        transform: translateY(-1px);
        box-shadow: var(--shadow);
    }
    button[kind="primary"], .stButton button[type="primary"] {
        background-color: var(--accent-green) !important;
        color: #FFFFFF !important;
        border-color: var(--accent-green) !important;
    }
    button[kind="primary"]:hover {
        background-color: var(--accent-green-2) !important;
        color: #FFFFFF !important;
    }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — Expander, Code, Progress, Spinner
       ═══════════════════════════════════════════════════════════════════ */

    [data-testid="stExpander"] details, .streamlit-expanderHeader, .stExpander {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary,
    .streamlit-expanderHeader p,
    [data-testid="stExpanderToggleIcon"],
    .stExpander summary {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
    }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }

    .stCodeBlock, code, pre, [data-testid="stCode"] {
        background-color: var(--bg-muted) !important;
        color: var(--text-secondary) !important;
        border-radius: 6px !important;
        border: 1px solid var(--border);
    }
    .stCodeBlock pre, .stCodeBlock code {
        background-color: transparent !important;
        color: var(--text-secondary) !important;
    }

    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--accent-green), var(--accent-yellow)) !important;
    }
    .stProgress > div { background-color: var(--bg-muted) !important; }
    .stSpinner > div { color: var(--accent-green) !important; }

    /* ═══════════════════════════════════════════════════════════════════
       STREAMLIT NATIVE — Charts (Plotly + native)
       ═══════════════════════════════════════════════════════════════════ */

    .js-plotly-plot, .plotly, .plot-container {
        background-color: transparent !important;
    }
    .js-plotly-plot .plotly .modebar { background: transparent !important; }

    /* ═══════════════════════════════════════════════════════════════════
       WEATHER DAY CARDS
       ═══════════════════════════════════════════════════════════════════ */

    .weather-day-card {
        text-align: center; padding: 0.75rem 0.5rem;
        background: var(--bg-card); border-radius: 10px;
        border: 1px solid var(--border);
        color: var(--text-primary);
        box-shadow: var(--shadow);
        transition: transform 0.15s ease;
    }
    .weather-day-card:hover { transform: translateY(-2px); }
    .weather-day-card .day-name {
        font-size: 0.78rem; color: var(--text-muted); font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.3px;
    }
    .weather-day-card .day-icon { font-size: 1.85rem; margin: 0.25rem 0; }
    .weather-day-card .day-temp {
        font-weight: 700; color: var(--accent-green); font-size: 1.05rem;
    }
    .weather-day-card .day-prec {
        color: var(--accent-blue); font-size: 0.78rem; font-weight: 500;
    }

    /* ═══════════════════════════════════════════════════════════════════
       MISC — Divider, scrollbar, focus ring
       ═══════════════════════════════════════════════════════════════════ */

    hr, .stDivider, [data-testid="stDivider"] {
        border-color: var(--border) !important;
        background-color: var(--border) !important;
    }

    /* Custom scrollbar — sade ve tema duyarlı */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-muted); }
    ::-webkit-scrollbar-thumb {
        background: var(--border-strong);
        border-radius: 6px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent-green); }

    /* Focus ring (klavye erişilebilirliği) */
    *:focus-visible {
        outline: 2px solid var(--accent-yellow) !important;
        outline-offset: 2px;
    }
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# JS — data-trakai-theme attribute
# ─────────────────────────────────────────────────────────────────────────────

def _theme_attr_script(theme: str) -> str:
    """Inject HTML attribute so CSS variables flip without Streamlit-rerun delay."""
    safe = "dark" if theme == "dark" else "light"
    return (
        "<script>"
        f"document.documentElement.setAttribute('data-trakai-theme', '{safe}');"
        "</script>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def apply_trakai_theme() -> None:
    """Inject CSS + sync the explicit theme choice from session state."""
    st.markdown(_CSS, unsafe_allow_html=True)
    theme = st.session_state.get("app_theme")
    if theme in ("light", "dark"):
        st.markdown(_theme_attr_script(theme), unsafe_allow_html=True)


def render_theme_toggle() -> None:
    """Sidebar widget: ☀️ Light / 🌙 Dark / 🖥️ System. Call inside `with st.sidebar:`."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Plotly template helper — chartlar tema duyarlı olsun
# ─────────────────────────────────────────────────────────────────────────────

def get_plotly_template() -> dict:
    """Return a plotly layout dict tuned to the active TRAK-AI theme.

    Usage::

        import plotly.graph_objects as go
        fig = go.Figure(...)
        fig.update_layout(**get_plotly_template())
    """
    theme = st.session_state.get("app_theme", "system")
    # If system, infer from media query (default = light unless dark hint present)
    is_dark = theme == "dark"
    if theme == "system":
        # Heuristic: assume light unless explicitly set
        is_dark = False

    if is_dark:
        return dict(
            paper_bgcolor="#162616",
            plot_bgcolor="#0F2010",
            font=dict(color="#E8F5E9", family="sans-serif"),
            xaxis=dict(gridcolor="#1E3A1E", linecolor="#2E5E2E",
                       tickfont=dict(color="#A5D6A7"), zerolinecolor="#2E5E2E"),
            yaxis=dict(gridcolor="#1E3A1E", linecolor="#2E5E2E",
                       tickfont=dict(color="#A5D6A7"), zerolinecolor="#2E5E2E"),
            legend=dict(bgcolor="rgba(22,38,22,0.85)", bordercolor="#1E3A1E",
                        borderwidth=1, font=dict(color="#E8F5E9")),
            colorway=["#66BB6A", "#FFD54F", "#42A5F5", "#FF8A65", "#BA68C8",
                      "#4DD0E1", "#FFB74D", "#81C784"],
            margin=dict(l=50, r=20, t=40, b=50),
        )
    else:
        return dict(
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#F8FBF6",
            font=dict(color="#1B2A1B", family="sans-serif"),
            xaxis=dict(gridcolor="#C8E6C9", linecolor="#A5D6A7",
                       tickfont=dict(color="#4A5E4A"), zerolinecolor="#A5D6A7"),
            yaxis=dict(gridcolor="#C8E6C9", linecolor="#A5D6A7",
                       tickfont=dict(color="#4A5E4A"), zerolinecolor="#A5D6A7"),
            legend=dict(bgcolor="rgba(255,255,255,0.92)", bordercolor="#C8E6C9",
                        borderwidth=1, font=dict(color="#1B2A1B")),
            colorway=["#2E7D32", "#F9A825", "#1565C0", "#E64A19", "#7B1FA2",
                      "#00838F", "#EF6C00", "#558B2F"],
            margin=dict(l=50, r=20, t=40, b=50),
        )


__all__ = [
    "apply_trakai_theme", "render_main_banner", "render_theme_toggle",
    "get_plotly_template",
]
