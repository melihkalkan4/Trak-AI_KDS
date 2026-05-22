"""
Modality 1: Satellite stress classifier (ResNet50, to be trained on Colab).

This skeleton is callable today even though the weight file is not yet
present — the public surface (`load_predictor`, `SatelliteStressClassifier`)
is stable so the consensus engine can be wired now.  Training itself
happens in `notebooks/06_satellite_cnn_training.ipynb` and produces a
state-dict at `config.SATELLITE_CNN_PATH`.

Output schema mirrors the YOLOv8 wrapper so the consensus engine treats
all three modalities uniformly.

Important: the satellite CNN is 3-class (no "disease"); leaf-scale disease
is the field modality's exclusive responsibility.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .. import config


logger = logging.getLogger("trakai.visual.satcnn")


# ---------------------------------------------------------------------------
@dataclass
class SatellitePrediction:
    image_path: Optional[str]
    predicted_class: str          # raw 3-class output
    harmonized_class: str         # mapped via SATELLITE_TO_HARMONIZED
    confidence: float
    all_probabilities: dict
    model_sha256: str
    timestamp_utc: str
    source: str = "resnet50-stress"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
def _sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class SatelliteStressClassifier:
    """
    ResNet50 stress classifier — frozen at inference.

    The weight file is OPTIONAL at construction time so the orchestrator
    can detect "no model yet" gracefully (returns None instead of raising).
    """

    def __init__(self,
                 model_path: Path = config.SATELLITE_CNN_PATH,
                 class_names=config.SATELLITE_CLASS_NAMES,
                 device: Optional[str] = None):
        self.model_path = Path(model_path)
        self.class_names = tuple(class_names)
        self.device = device or "cpu"
        self._model = None
        self.model_sha256 = ""
        self.available = self.model_path.exists()
        if self.available:
            self.model_sha256 = _sha256_of(self.model_path)
            logger.info("SatelliteStressClassifier ready; sha256=%s",
                        self.model_sha256[:16])
        else:
            logger.info("SatelliteStressClassifier stub — no weights at %s yet.",
                        self.model_path)

    # -------------------------------------------------------------------
    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not self.available:
            raise RuntimeError(
                f"ResNet50 weights not found at {self.model_path}. "
                "Train the model in notebooks/06_satellite_cnn_training.ipynb "
                "or wait for the Planet Education key to land."
            )
        try:
            import torch
            from torchvision.models import resnet50
        except ImportError as e:
            raise RuntimeError(
                "torch / torchvision not installed.  Run on Colab or "
                "`pip install torch torchvision` on a GPU box.",
            ) from e
        model = resnet50(weights=None)
        # Replace final FC with our 3-class head (matches training notebook)
        import torch.nn as nn
        in_feats = model.fc.in_features
        model.fc = nn.Linear(in_feats, len(self.class_names))
        sd = torch.load(self.model_path, map_location=self.device)
        if isinstance(sd, dict) and "state_dict" in sd:
            sd = sd["state_dict"]
        model.load_state_dict(sd, strict=False)
        model.eval()
        self._model = model.to(self.device)
        self._torch = torch

    # -------------------------------------------------------------------
    @staticmethod
    def _preprocess(img_path: Path):
        from torchvision import transforms
        from PIL import Image
        tf = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
        img = Image.open(img_path).convert("RGB")
        return tf(img).unsqueeze(0)

    # -------------------------------------------------------------------
    def predict(self, image_path: str | Path) -> Optional[SatellitePrediction]:
        if not self.available:
            return None
        self._ensure_loaded()
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(image_path)

        x = self._preprocess(path).to(self.device)
        with self._torch.no_grad():
            logits = self._model(x)
            probs = self._torch.nn.functional.softmax(logits, dim=1)[0].cpu().tolist()
        top_idx = max(range(len(probs)), key=lambda i: probs[i])
        raw_class = self.class_names[top_idx]
        all_probs = {n: float(p) for n, p in zip(self.class_names, probs)}
        harmonized = config.SATELLITE_TO_HARMONIZED.get(raw_class, raw_class)

        return SatellitePrediction(
            image_path=str(path),
            predicted_class=raw_class,
            harmonized_class=harmonized,
            confidence=float(probs[top_idx]),
            all_probabilities=all_probs,
            model_sha256=self.model_sha256,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
def load_predictor(strict: bool = False) -> Optional[SatelliteStressClassifier]:
    """
    Convenience constructor.  When `strict=False` returns None if the
    weight file is absent (used by the orchestrator's 2-of-3 fallback).
    """
    c = SatelliteStressClassifier()
    if not c.available and strict:
        raise RuntimeError("Satellite CNN weights are not available yet.")
    return c if c.available else None


__all__ = ["SatelliteStressClassifier", "SatellitePrediction", "load_predictor"]
