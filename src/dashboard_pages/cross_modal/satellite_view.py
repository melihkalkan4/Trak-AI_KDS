"""X-Modal -> Satellite: ResNet50 satellite CNN status + per-site consensus snapshots.

The satellite CNN (`models/visual/satellite_cnn_resnet50.pt`) is FROZEN once
trained. Until the Planet Education API key arrives we stand in with the
Sentinel-2 RGB fetcher used by FLOV. This tab reports the honest training/
data state and lists any per-site consensus snapshots already on disk.
"""
from __future__ import annotations

import json

import streamlit as st

from ..shared.session import get_active_site


def render() -> None:
    site = get_active_site()
    site_id = site.research_id or "EVR_01"
    st.markdown(f"### Uydu modeli & snapshot durumu — {site_id}")

    try:
        from visual_validation import config as _vv     # type: ignore
    except Exception as exc:                                            # noqa: BLE001
        st.error(f"visual_validation modulu yuklenemedi: {exc}")
        return

    # ── Model & API status ──────────────────────────────────────────────────
    cnn_path = _vv.SATELLITE_CNN_PATH
    metrics_path = _vv.SATELLITE_CNN_METRICS_PATH
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "ResNet50 modeli",
        "🟢 Hazir" if cnn_path.exists() else "🔴 Egitilmedi",
    )
    c2.metric(
        "Planet API",
        "🟢 Aktif" if _vv.PLANET_API_KEY_AVAILABLE else "🟡 Stand-in (S2 RGB)",
    )
    c3.metric(
        "Veri kaynagi",
        _vv.SATELLITE_STAND_IN_SOURCE,
    )

    if metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            with st.expander("📊 Model metrikleri"):
                st.json(metrics)
        except Exception:                                               # noqa: BLE001
            pass
    else:
        st.caption(
            "Egitim metrikleri henuz yok — model Planet Education tier "
            "ulastiktan sonra Colab uzerinde egitilecek."
        )

    st.markdown("---")

    # ── Per-site consensus snapshots (the satellite class is logged here) ──
    snap_dir = _vv.CONSENSUS_PREDICTIONS_DIR
    if not snap_dir.exists():
        st.info("Henuz konsensus snapshot dizini olusturulmadi.")
        return

    files = sorted(snap_dir.glob(f"{site_id}_*.json"))
    if not files:
        st.info(
            f"Bu saha icin uydu/konsensus snapshot yok.\n\n"
            f"Komut: `python scripts/run_cross_modal_validation.py "
            f"--site {site_id}`"
        )
        return

    st.markdown(f"### Son snapshot ({files[-1].name})")
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception as exc:                                            # noqa: BLE001
        st.error(f"Snapshot okunamadi: {exc}")
        return

    sat = data.get("satellite", {}) or data
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Tarih", str(data.get("date", sat.get("date", "—")))[:10])
    cc2.metric("Sinif", sat.get("class", sat.get("label", "—")))
    conf = sat.get("confidence", 0)
    cc3.metric("Guven", f"{float(conf):.0%}" if conf else "—")

    with st.expander("📄 Ham JSON"):
        st.json(data)

    if len(files) > 1:
        with st.expander(f"📁 Tum snapshot'lar ({len(files)})"):
            for p in files[-20:]:
                st.code(p.name, language="text")
