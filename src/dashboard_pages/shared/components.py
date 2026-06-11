"""Reusable Streamlit widgets — KPI cards, alert badges, system status."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st


logger = logging.getLogger("trakai.dashboard.components")


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
def kpi_card(label: str,
             value: str,
             delta: Optional[str] = None,
             delta_color: str = "normal",
             icon: Optional[str] = None,
             size: str = "medium") -> None:
    """Tema duyarlı KPI card — Precision Agriculture stili.

    Args:
        label: Üst label (UPPERCASE küçük yazı).
        value: Ana sayı / değer.
        delta: Opsiyonel delta etiketi (ör. "+12 dün").
        delta_color: ``positive`` | ``negative`` | ``warning`` | ``normal``.
        icon: Opsiyonel emoji ikonu (ör. ``🌾``).
        size: ``small`` | ``medium`` (default) | ``large``.
    """
    color_map = {
        "normal":   "var(--text-muted)",
        "positive": "var(--success-text)",
        "negative": "var(--critical-text)",
        "warning":  "var(--warning-text)",
    }
    arrow_map = {
        "positive": "▲",
        "negative": "▼",
        "warning":  "⚠",
        "normal":   "→",
    }
    color = color_map.get(delta_color, color_map["normal"])
    arrow = arrow_map.get(delta_color, arrow_map["normal"])
    delta_html = (
        f'<div class="kpi-delta" style="color:{color}">{arrow} {delta}</div>'
        if delta else ""
    )
    icon_html = (
        f'<span class="kpi-icon">{icon}</span>' if icon else ""
    )
    size_class = f" kpi-{size}" if size in ("small", "large") else ""
    st.markdown(
        f'<div class="kpi-card{size_class}">'
        f'<div class="kpi-header">{icon_html}'
        f'<div class="kpi-label">{label}</div></div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def alert_badge_html(severity: str, text: str) -> str:
    css = {
        "CRITICAL": "alert-critical",
        "HIGH":     "alert-critical",
        "WARNING":  "alert-warning",
        "MEDIUM":   "alert-warning",
        "INFO":     "alert-info",
        "LOW":      "alert-low",
        "OK":       "alert-success",
    }.get(severity.upper(), "alert-info")
    return f'<span class="alert-badge {css}">{text}</span>'


# ---------------------------------------------------------------------------
# Global notification bar (top of every page)
# ---------------------------------------------------------------------------
def render_global_alert_bar() -> None:
    """Render a top banner when CRITICAL alerts are open anywhere in the system."""
    try:
        from prospective_validation import config as _flov  # type: ignore
        flov_alerts = _flov.LOGS_DIR / "alerts.jsonl"
    except Exception:                                           # noqa: BLE001
        flov_alerts = Path("logs/alerts.jsonl")
    try:
        from visual_validation import config as _vv          # type: ignore
        vv_alerts = _vv.LOGS_DIR / "visual_consensus_alerts.jsonl"
        weather_alerts = _vv.LOGS_DIR / "weather_alerts.jsonl"
    except Exception:                                           # noqa: BLE001
        vv_alerts = Path("logs/visual_consensus_alerts.jsonl")
        weather_alerts = Path("logs/weather_alerts.jsonl")

    n_critical = 0
    for p in (flov_alerts, vv_alerts, weather_alerts):
        n_critical += _count_critical_in_jsonl(p)

    if n_critical == 0:
        return

    st.markdown(
        f'<div class="global-alert-bar">'
        f'🚨 <strong>{n_critical} aktif kritik uyarı</strong> &nbsp;·&nbsp; '
        f'FLOV / Cross-Modal / Hava sekmelerinden inceleyin.'
        f'</div>',
        unsafe_allow_html=True,
    )


def _count_critical_in_jsonl(p: Path) -> int:
    if not p.exists():
        return 0
    n = 0
    try:
        for line in p.read_text(encoding="utf-8").splitlines()[-200:]:
            s = line.upper()
            if '"SEVERITY":' in s and ('"CRITICAL"' in s or '"HIGH"' in s):
                n += 1
    except Exception:                                           # noqa: BLE001
        return 0
    return n


# ---------------------------------------------------------------------------
# System status indicator strip — sidebar bottom
# ---------------------------------------------------------------------------
def system_status_indicators() -> None:
    """Probe key subsystems and render coloured emoji badges."""
    items: list[tuple[str, bool, str]] = []

    # Ollama / LLM
    ollama_ok = False
    try:
        from llm_engine import check_ollama_connection  # type: ignore
        ollama_ok = bool(check_ollama_connection())
    except Exception:                                           # noqa: BLE001
        pass
    items.append(("Ollama", ollama_ok, "LLM (Ollama)"))

    # FAISS
    faiss_ok = False
    try:
        from build_index import load_faiss_index  # type: ignore
        _f = load_faiss_index()
        faiss_ok = _f is not None and _f[0] is not None
    except Exception:                                           # noqa: BLE001
        pass
    items.append(("FAISS", faiss_ok, "RAG (FAISS)"))

    # YOLOv8
    yolo_ok = False
    try:
        from image_classifier import classifier as _img_clf  # type: ignore
        yolo_ok = _img_clf is not None and _img_clf.model is not None
    except Exception:                                           # noqa: BLE001
        pass
    items.append(("YOLOv8", yolo_ok, "Field vision"))

    # DB
    db_ok = False
    try:
        from database import get_tarlalar  # type: ignore
        db_ok = get_tarlalar() is not None
    except Exception:                                           # noqa: BLE001
        pass
    items.append(("DB", db_ok, "SQLite"))

    # FLOV reports present
    flov_ok = False
    try:
        from prospective_validation import config as _flov  # type: ignore
        flov_ok = any(_flov.REPORTS_DIR.glob("*_predictions.parquet"))
    except Exception:                                           # noqa: BLE001
        pass
    items.append(("FLOV", flov_ok, "Predictions"))

    for short, ok, _tip in items:
        st.markdown(f"- {short} {'🟢' if ok else '🔴'}")


# ---------------------------------------------------------------------------
# Convenience: format a timestamp for display
# ---------------------------------------------------------------------------
def fmt_ts(ts: Optional[str]) -> str:
    if not ts:
        return "—"
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d.strftime("%d %b %Y %H:%M")
    except Exception:                                           # noqa: BLE001
        return str(ts)


# ---------------------------------------------------------------------------
# Demo-mode badge — academic honesty about fallbacks
# ---------------------------------------------------------------------------
def demo_mode_badge(reason: str = "", *, inline: bool = False) -> None:
    """Render a visible "🧪 Demo Modu" badge with an optional reason.

    Use this anywhere the system silently falls back to a heuristic or
    feature-derived stub (e.g. YOLO model missing, LLM offline, mock
    sensor data). Surfacing this keeps academic / demo integrity.
    """
    text = "🧪 Demo Modu"
    if reason:
        text += f" — {reason}"
    # Tema duyarlı: CSS değişkenlerini kullan → hem light hem dark'ta okunabilir
    style = (
        "display:inline-block;padding:3px 12px;border-radius:8px;"
        "background:var(--warning-bg);color:var(--warning-text);"
        "border:1px solid var(--accent-yellow);"
        "font-size:0.78rem;font-weight:600;letter-spacing:0.2px;"
    )
    if inline:
        return f'<span style="{style}">{text}</span>'  # type: ignore[return-value]
    st.markdown(
        f'<div style="margin:4px 0;"><span style="{style}">{text}</span></div>',
        unsafe_allow_html=True,
    )
    return None


__all__ = [
    "kpi_card", "alert_badge_html",
    "render_global_alert_bar", "system_status_indicators",
    "demo_mode_badge",
    "fmt_ts",
]
