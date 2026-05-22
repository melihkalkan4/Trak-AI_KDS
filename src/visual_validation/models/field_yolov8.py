"""
Modality 2: Field-vision YOLOv8 frozen wrapper.

Wraps the existing `models/crop_health_best.pt` YOLOv8s-cls model.  This
module NEVER retrains — it only loads, hashes, and infers.  Output is
normalised into the harmonized 4-class taxonomy so the consensus engine
gets uniform inputs across modalities.

Two ingestion modes:
    1. Per-file:    predict(image_path) → dict
    2. Per-folder:  predict_folder(dir) → DataFrame
    3. MQTT hook:   integrate with existing src/mqtt_orchestrator.py via
                    handle_mqtt_payload(payload) — no new listener needed.

Integrity: SHA-256 of the .pt file is computed at load-time and exposed
as `model_sha256`.  The orchestrator/dashboard can use this for the
frozen-model contract.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd

from .. import config


logger = logging.getLogger("trakai.visual.yolov8")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class YoloPrediction:
    image_path: Optional[str]
    predicted_class: str           # raw YOLOv8 class name (Turkish)
    harmonized_class: str          # one of HARMONIZED_LABELS
    confidence: float              # top-1 prob
    all_probabilities: dict        # raw → prob
    model_sha256: str
    timestamp_utc: str
    source: str = "yolov8s-cls"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Frozen wrapper
# ---------------------------------------------------------------------------
def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class FieldYOLOv8Predictor:
    """Frozen YOLOv8s-cls wrapper.  Loads once, infers many."""

    def __init__(self, model_path: Path = config.YOLOV8_MODEL_PATH):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"YOLOv8 model not found: {self.model_path}.  "
                f"Place crop_health_best.pt under models/ or override model_path.",
            )
        self.model_sha256 = _sha256_of(self.model_path)
        self.class_names = config.YOLOV8_CLASS_NAMES
        self._model = None             # lazy — saves ~3 s import time when only hash is needed
        logger.info("FieldYOLOv8Predictor initialised; sha256=%s",
                    self.model_sha256[:16])

    # -------------------------------------------------------------------
    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
        except ImportError as e:                                # pragma: no cover
            raise RuntimeError(
                "ultralytics not installed — `pip install ultralytics`.",
            ) from e
        self._model = YOLO(str(self.model_path))
        # YOLOv8-cls exposes class names via model.names (alphabetical)
        loaded = tuple(self._model.names[i] for i in sorted(self._model.names))
        if loaded != self.class_names:
            logger.warning(
                "YOLOv8 model.names %s differs from config.YOLOV8_CLASS_NAMES %s — "
                "harmonization will use the *config* mapping.",
                loaded, self.class_names,
            )

    # -------------------------------------------------------------------
    def predict(self, image_path: str | Path) -> YoloPrediction:
        """Run a single-image classification."""
        self._ensure_loaded()
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(image_path)

        results = self._model.predict(source=str(path), verbose=False)
        r = results[0]
        # Top-1
        top_idx = int(r.probs.top1)
        top_conf = float(r.probs.top1conf)
        raw_class = self.class_names[top_idx]

        # All-class dict — useful for downstream calibration / SHAP plots
        probs = r.probs.data.tolist()
        all_probs = {name: float(p) for name, p in zip(self.class_names, probs)}

        harmonized = config.YOLOV8_TO_HARMONIZED.get(raw_class, "healthy")

        return YoloPrediction(
            image_path=str(path),
            predicted_class=raw_class,
            harmonized_class=harmonized,
            confidence=top_conf,
            all_probabilities=all_probs,
            model_sha256=self.model_sha256,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )

    # -------------------------------------------------------------------
    def predict_folder(
        self,
        folder: str | Path,
        *,
        patterns: Iterable[str] = ("*.jpg", "*.jpeg", "*.png"),
    ) -> pd.DataFrame:
        """Run inference over every image in `folder`; return tidy DataFrame."""
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(folder)
        files: list[Path] = []
        for p in patterns:
            files.extend(sorted(folder.rglob(p)))
        if not files:
            logger.warning("predict_folder: no images under %s", folder)
            return pd.DataFrame(columns=[
                "image_path", "predicted_class", "harmonized_class",
                "confidence", "timestamp_utc",
            ])
        rows = []
        for f in files:
            try:
                pred = self.predict(f)
                rows.append(pred.to_dict())
            except Exception as e:                              # noqa: BLE001
                logger.exception("predict_folder: failed on %s — %s", f, e)
        df = pd.DataFrame(rows)
        if not df.empty:
            df["image_path"] = df["image_path"].astype(str)
        return df

    # -------------------------------------------------------------------
    def predict_from_base64(self, b64_jpeg: str) -> YoloPrediction:
        """
        Decode a base64 JPEG (e.g. from MQTT) → PIL → temp file → predict.

        We round-trip through disk because Ultralytics' YOLO API is
        path-oriented and that gives us a reproducible source field.
        """
        self._ensure_loaded()
        try:
            from PIL import Image
        except ImportError as e:                                # pragma: no cover
            raise RuntimeError("Pillow not installed.") from e
        raw = base64.b64decode(b64_jpeg)
        img = Image.open(io.BytesIO(raw))
        # Save to a deterministic, time-stamped path for the audit trail
        out_dir = config.FIELD_PHOTOS_DIR / "mqtt_inbox"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%f")
        out = out_dir / f"frame_{ts}.jpg"
        img.convert("RGB").save(out, "JPEG", quality=90)
        return self.predict(out)

    # -------------------------------------------------------------------
    def handle_mqtt_payload(self, payload: dict) -> Optional[YoloPrediction]:
        """
        Hook for src/mqtt_orchestrator.on_message — call this with the
        decoded JSON payload.  Returns None when payload has no image.
        Caller is responsible for re-publishing the result if desired.
        """
        b64 = payload.get("image")
        if not b64:
            return None
        try:
            return self.predict_from_base64(b64)
        except Exception:                                       # noqa: BLE001
            logger.exception("handle_mqtt_payload: inference failed")
            return None


__all__ = ["FieldYOLOv8Predictor", "YoloPrediction"]
