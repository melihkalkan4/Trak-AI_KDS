"""
Three-way consensus decision engine.

Inputs: independent harmonized-class predictions from up to three modalities:
    - satellite  (ResNet50 / PlanetScope or S2 stand-in)   -- optional
    - field      (YOLOv8 / ESP32-CAM)                       -- optional
    - features   (LSTM + climatology z-score)               -- optional

Output: a `ConsensusResult` with the decided class, confidence bucket,
agreement-type label, a Fleiss-κ-style raters table, and a flag from
`anomaly_flagger`.  When one modality is missing the engine downgrades
gracefully (dual-vote 2-way, or single-modality "TRUST_AVAILABLE").
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .. import config


logger = logging.getLogger("trakai.visual.consensus")


# ---------------------------------------------------------------------------
# Lightweight prediction container — any modality can produce one of these
# without depending on the heavyweight ML libs.
# ---------------------------------------------------------------------------
@dataclass
class ModalityPrediction:
    modality: str                  # "satellite" | "field" | "features"
    harmonized_class: str          # one of HARMONIZED_LABELS
    confidence: float              # in (0, 1]
    source: str = ""               # human-readable source/model description
    raw: Optional[dict] = None     # original payload, for the audit trail


@dataclass
class ConsensusResult:
    site_id: str
    target_date: str
    modalities: dict[str, dict] = field(default_factory=dict)
    consensus_class: str = ""
    confidence_bucket: str = "LOW"
    agreement_type: str = ""           # "UNANIMOUS" | "MAJORITY" | "TIE" | "DISAGREE" | "SINGLE"
    flag: str = ""                     # CONSENSUS_FLAGS key
    weighted_scores: dict[str, float] = field(default_factory=dict)
    narrative: str = ""
    n_modalities: int = 0
    generated_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
class ConsensusDecisionEngine:
    """Stateless — call .decide(...) per (site, date) with whatever preds you have."""

    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = dict(weights or config.MODALITY_WEIGHTS)

    # -------------------------------------------------------------------
    @staticmethod
    def _rebalance(weights: dict[str, float], available: set[str]) -> dict[str, float]:
        """Drop missing modalities and renormalise."""
        kept = {k: v for k, v in weights.items() if k in available and v > 0}
        s = sum(kept.values()) or 1.0
        return {k: v / s for k, v in kept.items()}

    # -------------------------------------------------------------------
    def decide(
        self,
        site_id: str,
        target_date: str,
        *,
        satellite: Optional[ModalityPrediction] = None,
        field_pred: Optional[ModalityPrediction] = None,
        features:  Optional[ModalityPrediction] = None,
    ) -> ConsensusResult:
        preds: dict[str, ModalityPrediction] = {}
        if satellite is not None:
            preds["satellite"] = satellite
        if field_pred is not None:
            preds["field"] = field_pred
        if features is not None:
            preds["features"] = features

        # Carry payloads forward
        result = ConsensusResult(
            site_id=site_id,
            target_date=target_date,
            modalities={k: {
                "class": p.harmonized_class,
                "confidence": float(p.confidence),
                "source": p.source,
            } for k, p in preds.items()},
            n_modalities=len(preds),
            generated_utc=datetime.now(timezone.utc).isoformat(),
        )

        if not preds:
            result.consensus_class = "unknown"
            result.agreement_type = "NONE"
            result.flag = "EQUIPMENT_FAIL"
            result.narrative = "No modality reported a prediction for this site/date."
            return result

        # Single-modality fast path
        if len(preds) == 1:
            only = next(iter(preds.values()))
            result.consensus_class = only.harmonized_class
            result.confidence_bucket = self._bucket(only.confidence)
            result.agreement_type = "SINGLE"
            result.flag = self._flag_single(only)
            result.narrative = (
                f"Only the {only.modality} modality reported "
                f"({only.harmonized_class} @ conf={only.confidence:.2f}). "
                "Treat the decision as provisional."
            )
            return result

        # Weighted vote
        w = self._rebalance(self.weights, set(preds.keys()))
        scores: dict[str, float] = {l: 0.0 for l in config.HARMONIZED_LABELS}
        for name, p in preds.items():
            scores[p.harmonized_class] += w[name] * float(p.confidence)
        result.weighted_scores = scores
        consensus_class = max(scores, key=lambda k: scores[k])
        result.consensus_class = consensus_class

        # Agreement type
        votes = [p.harmonized_class for p in preds.values()]
        counts = Counter(votes)
        n = len(preds)
        top_count = counts.most_common(1)[0][1]
        if top_count == n:
            result.agreement_type = "UNANIMOUS"
        elif top_count >= (n // 2) + 1:
            result.agreement_type = "MAJORITY"
        elif top_count == 1 and n > 1:
            result.agreement_type = "DISAGREE"
        else:
            result.agreement_type = "TIE"

        # Confidence bucket — combine agreement + weighted score
        top_score = scores[consensus_class]
        sum_score = sum(scores.values()) or 1.0
        rel = top_score / sum_score
        if result.agreement_type == "UNANIMOUS" and rel >= 0.66:
            result.confidence_bucket = "HIGH"
        elif result.agreement_type in {"MAJORITY", "UNANIMOUS"} and rel >= 0.50:
            result.confidence_bucket = "MEDIUM"
        else:
            result.confidence_bucket = "LOW"

        # Flag + narrative
        result.flag, result.narrative = self._flag_and_narrative(preds, result)
        return result

    # -------------------------------------------------------------------
    @staticmethod
    def _bucket(conf: float) -> str:
        if conf >= 0.85:
            return "HIGH"
        if conf >= 0.6:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _flag_single(p: ModalityPrediction) -> str:
        if p.harmonized_class == "healthy":
            return "PARTIAL_AGREEMENT"
        return "INVESTIGATE"

    # -------------------------------------------------------------------
    def _flag_and_narrative(
        self,
        preds: dict[str, ModalityPrediction],
        result: ConsensusResult,
    ) -> tuple[str, str]:
        classes = {k: p.harmonized_class for k, p in preds.items()}
        unique = set(classes.values())

        # All agree
        if len(unique) == 1:
            klass = next(iter(unique))
            if klass == "healthy":
                return "HIGH_CONF_OK", (
                    f"All {len(preds)} modalities agree the field is healthy."
                )
            if klass in {"severe_stress", "disease"}:
                return "HIGH_CONF_ALERT", (
                    f"All {len(preds)} modalities agree the field shows {klass}. "
                    "Recommend immediate action."
                )
            return "PARTIAL_AGREEMENT", (
                f"All {len(preds)} modalities agree on {klass}."
            )

        # Specific disagreement patterns (3-way only)
        sat = classes.get("satellite")
        fld = classes.get("field")
        ftr = classes.get("features")

        # Field detects disease while satellite + features show healthy/mild
        if fld == "disease" and (sat in {"healthy", "mild_stress"}
                                 or ftr in {"healthy", "mild_stress"}):
            return "INVESTIGATE", (
                "Field photo classifier flags disease while satellite / feature "
                "modalities show healthy or mild signal. Possible early-stage "
                "localised disease — recommend site visit and laboratory confirmation."
            )

        # Features alone show severe anomaly
        if ftr in {"severe_stress"} and sat in {"healthy", "mild_stress"} \
                and fld in {"healthy", "mild_stress"}:
            return "EARLY_WARNING", (
                "Numerical features (NDVI anomaly) detect stress that vision "
                "modalities have not yet picked up. Likely early-stage drought "
                "or pre-symptomatic deficiency — monitor closely."
            )

        # Satellite shouts stress, others say fine
        if sat in {"mild_stress", "severe_stress"} and \
                fld == "healthy" and ftr == "healthy":
            return "SATELLITE_FALSE", (
                "Satellite stress signal is not confirmed by field or feature "
                "modalities. Possible illumination/atmospheric artefact or "
                "wrong-parcel pixel attribution."
            )

        # Features broken, others healthy
        if ftr in {"severe_stress"} and fld == "healthy" and sat == "healthy":
            return "EQUIPMENT_FAIL", (
                "Sensor-derived features look anomalous while both vision "
                "modalities agree the field is healthy. Check ESP32 sensor "
                "calibration and ERA5 fetch lineage."
            )

        # Generic 2-vs-1
        return "PARTIAL_AGREEMENT", (
            f"Modalities disagree (classes: {classes}). "
            f"Consensus class assigned by weighted score; treat with care."
        )

    # -------------------------------------------------------------------
    def persist(self, result: ConsensusResult,
                path: Path = config.CONSENSUS_LOG) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        return path


__all__ = ["ConsensusDecisionEngine", "ConsensusResult", "ModalityPrediction"]
