"""
TRAK-AI KDS — Top-level LLM engine (lazy + RAM-aware)
========================================================
Streamlit-friendly wrapper around the underlying Ollama client.

Key features:
- `@st.cache_resource` so the LLM bootstrap runs ONCE per session, not per rerun.
- Pre-flight RAM check (`psutil.virtual_memory`) picks the largest model that fits.
- Graceful fallback if no model fits OR Ollama is offline -> dashboards stay alive.
- Single entry point: `get_llm_engine()` returns `{"client_fn", "model", "available"}`
  or `None` when no LLM can be served.

The existing `src/cp4_rag/llm_engine.py` (full Tri-RAG pipeline) is left untouched;
this module just selects the model and exposes a thin `chat()` helper that the
dashboard's SCRAG page can call.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Optional

import requests

logger = logging.getLogger("trakai.llm")

# ── path setup so `from cp4_rag.config import ...` works when imported from any cwd
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_CP4_DIR = os.path.join(_SRC_DIR, "cp4_rag")
for _p in (_SRC_DIR, _CP4_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration: RAM requirements per model (rough, leave 500 MB safety)
# ─────────────────────────────────────────────────────────────────────────────

# Ordered largest -> smallest. The first one that *fits* AND is *installed*
# in the local Ollama daemon wins.
MODEL_CANDIDATES: list[tuple[str, float]] = [
    ("gemma3:4b",     3.0),
    ("gemma2:2b",     1.8),
    ("qwen2.5:1.5b",  1.2),
    ("phi3:mini",     2.5),
    ("llama3.2:1b",   1.0),
]

DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SAFETY_MARGIN_GB = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _available_ram_gb() -> Optional[float]:
    try:
        import psutil
    except ImportError:
        logger.debug("psutil not installed - skipping RAM check")
        return None
    try:
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:                                                  # noqa: BLE001
        return None


def _ollama_running(base_url: str = DEFAULT_OLLAMA_URL) -> bool:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:                                                  # noqa: BLE001
        return False


def _list_installed_models(base_url: str = DEFAULT_OLLAMA_URL) -> list[str]:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        if r.status_code == 200:
            return [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:                                                  # noqa: BLE001
        pass
    return []


def _pick_model() -> Optional[str]:
    """Return the largest candidate model that (a) fits in RAM and
    (b) is already installed in Ollama. None if nothing fits."""
    if not _ollama_running():
        logger.info("Ollama daemon not reachable at %s", DEFAULT_OLLAMA_URL)
        return None

    installed = set(_list_installed_models())
    if not installed:
        logger.info("Ollama running but no models pulled")
        return None

    ram_gb = _available_ram_gb()
    for model, need_gb in MODEL_CANDIDATES:
        if model not in installed:
            continue
        if ram_gb is None or ram_gb >= (need_gb + SAFETY_MARGIN_GB):
            logger.info("LLM selected: %s (need %.1f GB, have %.1f GB)",
                        model, need_gb,
                        ram_gb if ram_gb is not None else -1.0)
            return model
        logger.debug("Skipping %s: needs %.1f+ GB, only %.1f available",
                     model, need_gb, ram_gb)

    logger.warning("No installed Ollama model fits available RAM")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Streamlit-cached entry point
# ─────────────────────────────────────────────────────────────────────────────

def _build_engine() -> Optional[dict]:
    """Real bootstrap (no Streamlit dep so it can be unit-tested)."""
    model = _pick_model()
    if model is None:
        return None

    base_url = DEFAULT_OLLAMA_URL

    def chat(prompt: str, system_prompt: str = "",
             temperature: float = 0.3, num_ctx: int = 4096) -> dict:
        """Single-shot generation. Returns dict with answer + timing."""
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        }
        t0 = time.time()
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            return {
                "answer": data.get("response", "").strip(),
                "duration_sec": round(time.time() - t0, 2),
                "tokens": data.get("eval_count", 0),
                "model": model,
                "ok": True,
            }
        except Exception as exc:                                       # noqa: BLE001
            return {"answer": "", "duration_sec": round(time.time() - t0, 2),
                    "tokens": 0, "model": model, "ok": False,
                    "error": str(exc)}

    return {"model": model, "chat": chat, "base_url": base_url,
            "available": True}


def get_llm_engine() -> Optional[dict]:
    """Streamlit-cached LLM accessor. Safe to call from any page render.

    Returns:
      dict with keys {model, chat, base_url, available} on success,
      or None when no LLM can be served (Ollama down / no model fits).
    """
    try:
        import streamlit as st
    except ImportError:
        # Plain Python usage (CLI, tests)
        return _build_engine()

    @st.cache_resource(show_spinner=False)
    def _cached() -> Optional[dict]:
        return _build_engine()

    return _cached()


def llm_status_text() -> str:
    """One-line health string for sidebar / settings panel."""
    eng = get_llm_engine()
    if eng is None:
        if not _ollama_running():
            return "🔴 Ollama kapalı"
        return "🟡 Uygun model yok / RAM yetersiz"
    return f"🟢 {eng['model']}"


def check_ollama_connection(base_url: str = DEFAULT_OLLAMA_URL) -> bool:
    """Backwards-compatible alias used by shared/components.py."""
    return _ollama_running(base_url)


__all__ = [
    "get_llm_engine", "llm_status_text", "check_ollama_connection",
    "MODEL_CANDIDATES",
]
