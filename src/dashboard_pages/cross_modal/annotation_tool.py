"""X-Modal → 🏷️ Annotation Tool: minimal in-app labeling for field photos.

Full port of `scripts/annotate_field_photos.py` is planned; this initial
version surfaces unlabeled photos and writes the chosen label back to
`data/visual_validation/field_labels.jsonl`.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st


_LABELS = [
    "saglikli_aycicegi",
    "saglikli_bugday",
    "kuraklik",
    "hastalik_mildiyo",
    "hastalik_pas",
    "yabanci_ot",
    "besin_eksigi",
    "diger",
]


def _photo_dirs() -> list[Path]:
    try:
        from visual_validation import config as _vv  # type: ignore
        return [_vv.FIELD_PHOTOS_DIR] if _vv.FIELD_PHOTOS_DIR.exists() else []
    except Exception:                                                # noqa: BLE001
        return []


def _labels_file() -> Path:
    try:
        from visual_validation import config as _vv  # type: ignore
        # config exposes VISUAL_DIR (= data/visual/); there is no DATA_DIR
        # attribute. Keep labels alongside ground-truth observations.
        return _vv.GROUND_TRUTH_DIR / "field_labels.jsonl"
    except Exception:                                                # noqa: BLE001
        return Path("data/visual/ground_truth_observations/field_labels.jsonl")


def render() -> None:
    st.markdown("### Saha foto etiketleme")
    dirs = _photo_dirs()
    if not dirs:
        st.info("Henuz saha fotografi yok (`data/visual_validation/field_photos/`).")
        return

    files = sorted(p for d in dirs for p in d.glob("*.jpg"))
    if not files:
        st.info("Bu dizinde .jpg dosyasi yok.")
        return

    labels_path = _labels_file()
    seen = set()
    if labels_path.exists():
        for line in labels_path.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line).get("image"))
            except Exception:                                       # noqa: BLE001
                continue

    todo = [p for p in files if p.name not in seen]
    if not todo:
        st.success(f"Tum {len(files)} foto etiketlendi.")
        return

    st.caption(f"Kalan: **{len(todo)}** / {len(files)} foto")
    current = todo[0]
    st.image(str(current), caption=current.name, use_container_width=True)

    label = st.selectbox("Etiket", _LABELS, key=f"lbl_{current.name}")
    if st.button("✅ Kaydet ve sonraki", use_container_width=True):
        labels_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "image": current.name,
            "label": label,
            "labeled_at": datetime.utcnow().isoformat() + "Z",
        }
        with labels_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        st.rerun()
