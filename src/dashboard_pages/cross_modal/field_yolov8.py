"""X-Modal -> Field (YOLOv8): audit log + ad-hoc upload & classify.

Before the rover starts streaming photos there is no audit log. To make
this tab useful from day one, we surface the YOLOv8 model status and let
the operator drop a photo in the browser for an immediate prediction.
"""
from __future__ import annotations

import io
from pathlib import Path

import streamlit as st

from ..shared.session import get_active_site
from ..shared.data_loaders import load_yolov8_audit_jsonl


@st.cache_resource(show_spinner=False)
def _get_classifier():
    """Lazy-load the YOLOv8 classifier wrapper from src/image_classifier.py."""
    try:
        from image_classifier import classifier as _img_clf            # type: ignore
        return _img_clf
    except Exception:                                                  # noqa: BLE001
        return None


def render() -> None:
    site = get_active_site()
    site_id = site.research_id

    # ── Model status ─────────────────────────────────────────────────────────
    try:
        from visual_validation import config as _vv                     # type: ignore
        model_path = _vv.YOLOV8_MODEL_PATH
        class_names = _vv.YOLOV8_CLASS_NAMES
        photos_dir: Path = _vv.FIELD_PHOTOS_DIR
    except Exception:                                                   # noqa: BLE001
        model_path = Path("models/crop_health_best.pt")
        class_names = ()
        photos_dir = Path("data/visual/field_photos")

    clf = _get_classifier()
    n_photos = (sum(1 for _ in photos_dir.glob("*.jpg"))
                if photos_dir.exists() else 0)

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "YOLOv8 modeli",
        "🟢 Yuklu" if (clf is not None and getattr(clf, "model", None)) else "🔴 Yuklenemedi",
    )
    c2.metric("Sinif sayisi", len(class_names) or "—")
    c3.metric("Saha fotografi (disk)", n_photos)

    if class_names:
        with st.expander("📚 Siniflar"):
            st.code("\n".join(f"{i}: {c}" for i, c in enumerate(class_names)),
                    language="text")

    st.markdown("---")

    # ── Ad-hoc classify ──────────────────────────────────────────────────────
    st.markdown("### 📷 Hizli siniflama")
    if clf is None or getattr(clf, "model", None) is None:
        st.warning(
            f"YOLOv8 modeli bulunamadi: `{model_path}`. "
            "image_classifier modulunu kontrol edin."
        )
    else:
        upl = st.file_uploader(
            "Bir tarla fotografi yukleyin (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            key="xmod_yolov8_upload",
        )
        if upl is not None:
            img_bytes = upl.read()
            st.image(io.BytesIO(img_bytes), caption=upl.name,
                     use_container_width=True)
            try:
                # image_classifier.classifier exposes .classify(image_path|bytes)
                # → {"sinif": ..., "guven": ...} (see src/image_classifier.py).
                tmp = Path("logs/_xmod_tmp_upload.jpg")
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(img_bytes)
                result = clf.classify_file(str(tmp))
                cls = result.get("sinif") or result.get("class") or "?"
                conf = (result.get("guven") or result.get("confidence") or 0)
                conf = float(conf) * (100 if conf <= 1 else 1)
                badge = "🟢" if cls in ("saglikli_bugday", "saglikli_aycicegi") else "🔴"
                st.success(f"{badge} **{cls}** — guven: %{conf:.0f}")
                with st.expander("📄 Ham sonuc"):
                    st.json(result)
            except Exception as exc:                                    # noqa: BLE001
                st.error(f"Siniflama hatasi: {exc}")

    st.markdown("---")

    # ── Audit log (only if cron / mqtt orchestrator has written it) ─────────
    df = load_yolov8_audit_jsonl(site_id=site_id, n=300)
    if df is None or df.empty:
        st.info(
            "Saha tahmin log'u henuz yok (`logs/visual_field_yolov8.jsonl`). "
            "MQTT orchestrator rover ile baglaninca otomatik dolacak."
        )
        return

    st.markdown(f"### Saha tahmin gecmisi (son {len(df)})")
    keep = [c for c in ["timestamp", "site_id", "evrenli_id", "image",
                        "predicted_class", "confidence", "n_detections"]
            if c in df.columns]
    st.dataframe(df[keep] if keep else df, use_container_width=True, hide_index=True)
