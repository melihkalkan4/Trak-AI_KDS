"""
Streamlit annotation UI for ESP32 field photos.

Walks the inbox folder, shows each photo, lets the annotator pick a
harmonized label, and writes the result to a CSV ledger that the
YOLOv8 evaluation notebook (07_*.ipynb) can join against.

Run:
    streamlit run scripts/annotate_field_photos.py
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _bootstrap() -> None:
    here = Path(__file__).resolve()
    root = here.parent.parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> None:
    _bootstrap()
    import streamlit as st
    from visual_validation import config

    config.ensure_dirs()
    st.set_page_config(page_title="TRAK-AI Field-photo annotator", layout="wide")
    st.title("ESP32-CAM photo annotator")
    st.caption("Assign harmonized labels; the YOLOv8 evaluator joins on filename.")

    inbox = st.sidebar.text_input(
        "Photo folder",
        value=str(config.FIELD_PHOTOS_DIR / "mqtt_inbox"),
    )
    out_csv = st.sidebar.text_input(
        "Annotation CSV",
        value=str(config.GROUND_TRUTH_DIR / "field_photo_labels.csv"),
    )
    annotator = st.sidebar.text_input("Annotator initials", value="ME")
    folder = Path(inbox)
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not folder.exists():
        st.warning(f"Folder {folder} does not exist yet.")
        return

    files = sorted([p for p in folder.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])
    if not files:
        st.info("No photos in the inbox folder.")
        return

    # Existing labels
    already: set[str] = set()
    if out_path.exists():
        with out_path.open("r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                already.add(row.get("image_path", ""))

    unlabelled = [f for f in files if str(f) not in already]
    st.write(f"**{len(unlabelled)} unlabelled** / {len(files)} total")

    idx = st.number_input("Index", 0, max(0, len(unlabelled) - 1), 0)
    if not unlabelled:
        st.success("All photos labelled.")
        return
    target = unlabelled[int(idx)]
    st.image(str(target), caption=target.name, width=512)

    label = st.radio("Harmonized class", list(config.HARMONIZED_LABELS), horizontal=True)
    notes = st.text_input("Notes (optional)", value="")
    if st.button("Save"):
        new = not out_path.exists()
        with out_path.open("a", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["image_path", "harmonized_class", "annotator",
                            "annotated_utc", "notes"])
            w.writerow([str(target), label, annotator,
                        datetime.now(timezone.utc).isoformat(), notes])
        st.success(f"Saved {target.name} -> {label}")
        st.rerun()


if __name__ == "__main__":
    main()
