"""
Anomaly flagger — turns a `ConsensusResult` into an actionable alert.

The consensus engine already assigns a flag key (HIGH_CONF_OK,
INVESTIGATE, EARLY_WARNING, ...).  This module:

    1. Enriches the flag with phenology-stage context (flowering/grain-fill
       escalates severity per FLOV's alert policy).
    2. Builds a `ConsensusAlert` dataclass with bilingual EN/TR messages
       and a recommended action list.
    3. Persists alerts to a JSONL ledger that the dashboard can render.

It deliberately mirrors the FLOV alert-engine signature so the same
notifier / Streamlit panel can ingest both feeds.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .. import config
from .decision_engine import ConsensusResult


logger = logging.getLogger("trakai.visual.flagger")


# ---------------------------------------------------------------------------
# Severity matrix — flag × phenology_stage → severity
# ---------------------------------------------------------------------------
# Stages from FLOV's SUNFLOWER_PHENOLOGY: sowing, vegetative, flowering,
# grain_filling, maturity, fallow.  We escalate any non-OK flag during the
# yield-critical flowering and grain-filling windows.
_CRITICAL_STAGES = {"flowering", "grain_filling"}

_BASE_SEVERITY: dict[str, str] = {
    "HIGH_CONF_OK":      "INFO",
    "PARTIAL_AGREEMENT": "INFO",
    "SATELLITE_FALSE":   "LOW",
    "EARLY_WARNING":     "MEDIUM",
    "INVESTIGATE":       "MEDIUM",
    "EQUIPMENT_FAIL":    "MEDIUM",
    "HIGH_CONF_ALERT":   "HIGH",
    "NO_CONSENSUS":      "MEDIUM",
}

# Escalation when the field is in a yield-critical stage
_ESCALATE: dict[str, str] = {
    "INFO":   "INFO",
    "LOW":    "MEDIUM",
    "MEDIUM": "HIGH",
    "HIGH":   "CRITICAL",
}


# ---------------------------------------------------------------------------
# Action playbook — keyed by flag (plain English; UI may translate)
# ---------------------------------------------------------------------------
_ACTIONS: dict[str, list[str]] = {
    "HIGH_CONF_OK": [
        "No action required — continue routine monitoring.",
    ],
    "HIGH_CONF_ALERT": [
        "Dispatch field crew within 24 h for visual confirmation.",
        "Pull most recent rover photo and laboratory leaf sample.",
        "Notify agronomist; escalate to irrigation/spray decision board.",
    ],
    "EARLY_WARNING": [
        "Increase rover sampling cadence to daily for next 5 days.",
        "Inspect soil moisture probes; cross-check ERA5 vs in-situ.",
        "Pre-position irrigation resources in case anomaly persists.",
    ],
    "INVESTIGATE": [
        "Collect leaf samples from the affected parcel for laboratory ID.",
        "Quarantine adjacent rows until pathogen ID is returned.",
        "Schedule targeted fungicide evaluation with agronomist.",
    ],
    "SATELLITE_FALSE": [
        "Re-fetch cloud mask / atmospheric correction for the scene.",
        "Verify parcel polygon vs satellite pixel grid (off-by-one risk).",
        "If next pass repeats anomaly, re-classify with a clearer scene.",
    ],
    "EQUIPMENT_FAIL": [
        "Field crew: physically inspect ESP32 sensor enclosure.",
        "Re-run ERA5 fetch lineage check; rotate cdsapi key if stale.",
        "Hold automated irrigation triggers until sensor health restored.",
    ],
    "PARTIAL_AGREEMENT": [
        "Treat consensus as provisional; await next observation cycle.",
        "Flag for dashboard review at next stand-up.",
    ],
    "NO_CONSENSUS": [
        "Open incident ticket; route to model-ops on-call.",
        "Suspend autonomous actions for this parcel pending review.",
    ],
}

# Bilingual templates
_MSG_EN: dict[str, str] = {
    "HIGH_CONF_OK":      "All modalities confirm the field is healthy.",
    "HIGH_CONF_ALERT":   "Severe stress / disease confirmed across all modalities.",
    "EARLY_WARNING":     "Numerical features flag pre-symptomatic stress.",
    "INVESTIGATE":       "Field photo flags disease not yet visible elsewhere.",
    "SATELLITE_FALSE":   "Satellite stress signal NOT confirmed on the ground.",
    "EQUIPMENT_FAIL":    "Sensor signal anomalous; both vision modalities healthy.",
    "PARTIAL_AGREEMENT": "Modalities partially agree; treat with care.",
    "NO_CONSENSUS":      "Modalities disagree; consensus not reached.",
}
_MSG_TR: dict[str, str] = {
    "HIGH_CONF_OK":      "Tüm modaliteler tarlanın sağlıklı olduğunu doğruluyor.",
    "HIGH_CONF_ALERT":   "Tüm modaliteler ciddi stres / hastalık üzerinde uzlaştı.",
    "EARLY_WARNING":     "Sayısal göstergeler henüz görsel olarak belirgin olmayan stresi işaret ediyor.",
    "INVESTIGATE":       "Tarla fotoğrafı henüz uydudan görünmeyen hastalık işareti veriyor.",
    "SATELLITE_FALSE":   "Uydu stres sinyali yer doğrulamasıyla teyit edilmedi.",
    "EQUIPMENT_FAIL":    "Sensör verisi anormal; her iki görsel modalite sağlıklı.",
    "PARTIAL_AGREEMENT": "Modaliteler kısmen uzlaştı; dikkatle değerlendirin.",
    "NO_CONSENSUS":      "Modaliteler uzlaşamadı; ortak karar yok.",
}


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------
@dataclass
class ConsensusAlert:
    site_id: str
    target_date: str
    flag: str
    severity: str
    consensus_class: str
    confidence_bucket: str
    agreement_type: str
    phenology_stage: str
    message_en: str
    message_tr: str
    actions: list[str] = field(default_factory=list)
    modalities: dict[str, dict] = field(default_factory=dict)
    weighted_scores: dict[str, float] = field(default_factory=dict)
    generated_utc: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _stage_for(target_date: str) -> str:
    """Best-effort phenology stage lookup; tolerates missing FLOV anchor."""
    try:
        d = datetime.fromisoformat(target_date).date()
        return config.stage_for_doy(d.timetuple().tm_yday)
    except Exception:                                           # noqa: BLE001
        return "unknown"


def flag_consensus(result: ConsensusResult) -> ConsensusAlert:
    """Build a `ConsensusAlert` from a `ConsensusResult`."""
    flag = result.flag or "PARTIAL_AGREEMENT"
    stage = _stage_for(result.target_date)
    base = _BASE_SEVERITY.get(flag, "MEDIUM")
    severity = _ESCALATE[base] if stage in _CRITICAL_STAGES and base != "INFO" else base

    return ConsensusAlert(
        site_id=result.site_id,
        target_date=result.target_date,
        flag=flag,
        severity=severity,
        consensus_class=result.consensus_class,
        confidence_bucket=result.confidence_bucket,
        agreement_type=result.agreement_type,
        phenology_stage=stage,
        message_en=_MSG_EN.get(flag, "Consensus alert."),
        message_tr=_MSG_TR.get(flag, "Konsensüs uyarısı."),
        actions=list(_ACTIONS.get(flag, [])),
        modalities=dict(result.modalities),
        weighted_scores=dict(result.weighted_scores),
        generated_utc=datetime.now(timezone.utc).isoformat(),
    )


def generate_alert(result: ConsensusResult,
                   *, persist: bool = True,
                   path: Optional[Path] = None,
                   ) -> ConsensusAlert:
    """Convenience: build + (optionally) persist the alert to JSONL."""
    alert = flag_consensus(result)
    if persist:
        out = path or (config.LOGS_DIR / "visual_consensus_alerts.jsonl")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")
        logger.info("[flagger] %s/%s %s/%s -> %s",
                    alert.site_id, alert.target_date,
                    alert.flag, alert.severity, out)
    return alert


__all__ = [
    "ConsensusAlert",
    "flag_consensus",
    "generate_alert",
]
