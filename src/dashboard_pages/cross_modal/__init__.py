"""Cross-modal validation tab — 5 sub-tabs."""

import streamlit as st


def render() -> None:
    st.title("🔬 Cross-Modal Validation")
    st.caption("3-yollu konsensüs: PlanetScope/S2 · YOLOv8 · LSTM+XGB")

    tabs = st.tabs([
        "🛰️ Satellite",
        "📷 Field (YOLOv8)",
        "📊 Feature Predictor",
        "🤝 3-Way Consensus",
        "🏷️ Annotation Tool",
    ])

    with tabs[0]:
        from .satellite_view import render as r; r()
    with tabs[1]:
        from .field_yolov8 import render as r; r()
    with tabs[2]:
        from .feature_predictor import render as r; r()
    with tabs[3]:
        from .consensus_view import render as r; r()
    with tabs[4]:
        from .annotation_tool import render as r; r()
