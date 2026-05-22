"""
Cross-modal validator — orchestrator that ties the three modalities into
a single per-(site, date) consensus run.

Behaviour:

    * Reads whatever modalities are available *right now* (1, 2, or 3).
      The satellite modality is auto-skipped when its weight file is
      missing — the engine falls back to 2-of-3 voting (field + features)
      without code changes.

    * For each (site, target_date):
        1. Try to pull a satellite chip + ResNet50 prediction.
        2. Reuse the latest YOLOv8 prediction for the site from the JSONL
           audit, or accept one passed in via `field_payload`.
        3. Reuse the FLOV LSTM prediction via `MultiModalFeaturePredictor`.
        4. Call `ConsensusDecisionEngine.decide(...)`.
        5. Run `anomaly_flagger.generate_alert(...)`.
        6. Persist consensus + alert to JSONL.

    * `validate_batch(site_id, date_range)` loops over a window — used
      by `scripts/run_cross_modal_validation.py` and the dashboard.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Optional

from .. import config
from ..consensus.decision_engine import (
    ConsensusDecisionEngine, ConsensusResult, ModalityPrediction,
)
from ..consensus.anomaly_flagger import generate_alert, ConsensusAlert
from ..models.feature_predictor import MultiModalFeaturePredictor
from ..models.satellite_cnn import load_predictor as load_satellite
from ..api_clients.sentinel2_imagery import fetch_rgb_chip, fetch_rgb_chip_stub


logger = logging.getLogger("trakai.visual.orchestrator")


# ---------------------------------------------------------------------------
@dataclass
class CrossModalRun:
    site_id: str
    target_date: str
    consensus: dict
    alert: dict
    available_modalities: list[str]
    skipped_modalities: list[str]
    generated_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
class CrossModalValidator:
    """Stateful only insofar as the underlying frozen wrappers cache models."""

    def __init__(self,
                 *,
                 use_stub_satellite_chip: bool = True,
                 weights: Optional[dict[str, float]] = None):
        self.engine = ConsensusDecisionEngine(weights=weights)
        self.feature_pred = MultiModalFeaturePredictor()
        self.satellite_pred = load_satellite()        # may be None if no weights yet
        self.use_stub_satellite_chip = use_stub_satellite_chip
        self._yolo_cache: dict[str, dict] = {}

    # -------------------------------------------------------------------
    # Modality fetchers
    # -------------------------------------------------------------------
    def _satellite(self, site_id: str, target: date) -> Optional[ModalityPrediction]:
        if self.satellite_pred is None:
            return None
        chip = fetch_rgb_chip(site_id, target) or (
            fetch_rgb_chip_stub(site_id, target) if self.use_stub_satellite_chip else None
        )
        if chip is None:
            return None
        pred = self.satellite_pred.predict(chip.asset_path)
        if pred is None:
            return None
        return ModalityPrediction(
            modality="satellite",
            harmonized_class=pred.harmonized_class,
            confidence=pred.confidence,
            source=pred.source,
            raw=pred.to_dict(),
        )

    def _field_from_payload(self, payload: dict) -> Optional[ModalityPrediction]:
        if not payload:
            return None
        cls = payload.get("harmonized_class")
        conf = payload.get("confidence")
        if not cls or conf is None:
            return None
        return ModalityPrediction(
            modality="field",
            harmonized_class=cls,
            confidence=float(conf),
            source=payload.get("source", "yolov8s-cls"),
            raw=payload,
        )

    def _field_from_log(self, site_id: str, target: date) -> Optional[ModalityPrediction]:
        """Pull the latest YOLOv8 audit row for this site on/before `target`."""
        log = config.LOGS_DIR / "visual_field_yolov8.jsonl"
        if not log.exists():
            return None
        best = None
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except Exception:                                   # noqa: BLE001
                continue
            if row.get("site_id") and row["site_id"] != site_id:
                continue
            ts = row.get("timestamp_utc") or row.get("timestamp")
            if not ts:
                continue
            try:
                rd = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
            except Exception:                                   # noqa: BLE001
                continue
            if rd <= target and (best is None or rd > best[0]):
                best = (rd, row)
        if best is None:
            return None
        return self._field_from_payload(best[1])

    def _features(self, site_id: str, target: date) -> Optional[ModalityPrediction]:
        try:
            fp = self.feature_pred.predict(site_id, target)
        except Exception:                                       # noqa: BLE001
            logger.exception("[orchestrator] feature predict failed for %s @ %s",
                             site_id, target)
            return None
        if fp is None:
            return None
        return ModalityPrediction(
            modality="features",
            harmonized_class=fp.harmonized_class,
            confidence=fp.confidence,
            source=fp.source,
            raw=fp.to_dict(),
        )

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------
    def validate_one(self,
                     site_id: str,
                     target: date,
                     *,
                     field_payload: Optional[dict] = None,
                     ) -> CrossModalRun:
        sat = self._satellite(site_id, target)
        fld = (self._field_from_payload(field_payload)
               if field_payload else self._field_from_log(site_id, target))
        ftr = self._features(site_id, target)

        result: ConsensusResult = self.engine.decide(
            site_id, target.isoformat(),
            satellite=sat, field_pred=fld, features=ftr,
        )
        self.engine.persist(result)
        alert: ConsensusAlert = generate_alert(result)

        present = [n for n, p in
                   (("satellite", sat), ("field", fld), ("features", ftr)) if p]
        skipped = [n for n, p in
                   (("satellite", sat), ("field", fld), ("features", ftr)) if not p]

        run = CrossModalRun(
            site_id=site_id,
            target_date=target.isoformat(),
            consensus=result.to_dict(),
            alert=alert.to_dict(),
            available_modalities=present,
            skipped_modalities=skipped,
            generated_utc=datetime.now(timezone.utc).isoformat(),
        )

        out = config.CONSENSUS_PREDICTIONS_DIR / f"{site_id}_{target.isoformat()}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2),
                       encoding="utf-8")
        logger.info("[orchestrator] %s @ %s -> %s (%s)",
                    site_id, target, result.consensus_class, result.flag)
        return run

    # -------------------------------------------------------------------
    def validate_batch(self,
                       site_id: str,
                       start: date,
                       end: date,
                       *,
                       step_days: int = 5,
                       ) -> list[CrossModalRun]:
        runs: list[CrossModalRun] = []
        d = start
        while d <= end:
            runs.append(self.validate_one(site_id, d))
            d += timedelta(days=step_days)
        return runs


__all__ = ["CrossModalValidator", "CrossModalRun"]
