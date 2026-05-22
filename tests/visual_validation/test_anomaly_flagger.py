"""ConsensusAlert severity/escalation logic."""

from visual_validation.consensus.decision_engine import (
    ConsensusDecisionEngine, ModalityPrediction,
)
from visual_validation.consensus.anomaly_flagger import flag_consensus


def _decide(flag_seed, target_date="2026-05-22"):
    """Build a ConsensusResult that exercises a given flag."""
    e = ConsensusDecisionEngine()
    if flag_seed == "HIGH_CONF_OK":
        return e.decide("EVR_01", target_date,
                        satellite=ModalityPrediction("satellite", "healthy", 0.9),
                        field_pred=ModalityPrediction("field", "healthy", 0.9),
                        features=ModalityPrediction("features", "healthy", 0.9))
    if flag_seed == "INVESTIGATE":
        return e.decide("EVR_01", target_date,
                        satellite=ModalityPrediction("satellite", "healthy", 0.85),
                        field_pred=ModalityPrediction("field", "disease", 0.9),
                        features=ModalityPrediction("features", "healthy", 0.85))
    if flag_seed == "EARLY_WARNING":
        return e.decide("EVR_01", target_date,
                        satellite=ModalityPrediction("satellite", "healthy", 0.85),
                        field_pred=ModalityPrediction("field", "healthy", 0.85),
                        features=ModalityPrediction("features", "severe_stress", 0.9))
    raise ValueError(flag_seed)


def test_high_conf_ok_severity_info():
    r = _decide("HIGH_CONF_OK")
    alert = flag_consensus(r)
    assert alert.flag == "HIGH_CONF_OK"
    assert alert.severity == "INFO"
    assert alert.message_en
    assert alert.message_tr
    assert alert.actions


def test_investigate_has_actions():
    r = _decide("INVESTIGATE")
    alert = flag_consensus(r)
    assert alert.flag == "INVESTIGATE"
    assert alert.severity in {"MEDIUM", "HIGH"}        # escalates in flowering
    assert any("laborat" in a.lower() or "fungicide" in a.lower()
               for a in alert.actions)


def test_phenology_stage_field_populated():
    r = _decide("EARLY_WARNING")
    alert = flag_consensus(r)
    assert alert.phenology_stage           # not empty
    assert alert.flag == "EARLY_WARNING"
