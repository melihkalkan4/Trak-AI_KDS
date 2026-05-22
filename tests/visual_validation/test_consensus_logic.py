"""ConsensusDecisionEngine path coverage."""

from visual_validation.consensus.decision_engine import (
    ConsensusDecisionEngine, ModalityPrediction,
)


def _eng():
    return ConsensusDecisionEngine()


def _mp(mod, klass, conf):
    return ModalityPrediction(modality=mod, harmonized_class=klass, confidence=conf)


def test_no_modalities_returns_equipment_fail():
    r = _eng().decide("EVR_01", "2026-05-22")
    assert r.consensus_class == "unknown"
    assert r.flag == "EQUIPMENT_FAIL"


def test_single_modality_path():
    r = _eng().decide("EVR_01", "2026-05-22",
                      features=_mp("features", "mild_stress", 0.7))
    assert r.agreement_type == "SINGLE"
    assert r.consensus_class == "mild_stress"
    assert r.n_modalities == 1


def test_unanimous_healthy_high_conf():
    e = _eng()
    r = e.decide("EVR_01", "2026-05-22",
                 satellite=_mp("satellite", "healthy", 0.9),
                 field_pred=_mp("field", "healthy", 0.9),
                 features=_mp("features", "healthy", 0.9))
    assert r.agreement_type == "UNANIMOUS"
    assert r.consensus_class == "healthy"
    assert r.flag == "HIGH_CONF_OK"
    assert r.confidence_bucket == "HIGH"


def test_field_disease_triggers_investigate():
    r = _eng().decide("EVR_01", "2026-05-22",
                      satellite=_mp("satellite", "healthy", 0.8),
                      field_pred=_mp("field", "disease", 0.85),
                      features=_mp("features", "healthy", 0.7))
    assert r.flag == "INVESTIGATE"


def test_feature_early_warning():
    r = _eng().decide("EVR_01", "2026-05-22",
                      satellite=_mp("satellite", "healthy", 0.8),
                      field_pred=_mp("field", "healthy", 0.8),
                      features=_mp("features", "severe_stress", 0.9))
    assert r.flag == "EARLY_WARNING"


def test_satellite_false_pattern():
    r = _eng().decide("EVR_01", "2026-05-22",
                      satellite=_mp("satellite", "severe_stress", 0.85),
                      field_pred=_mp("field", "healthy", 0.85),
                      features=_mp("features", "healthy", 0.85))
    assert r.flag == "SATELLITE_FALSE"


def test_features_severe_others_healthy_resolves_to_early_warning():
    # Per decision_engine ordering, features-severe with healthy vision
    # is classified as EARLY_WARNING (pre-symptomatic stress) rather
    # than EQUIPMENT_FAIL — the early-warning branch matches first.
    r = _eng().decide("EVR_01", "2026-05-22",
                      satellite=_mp("satellite", "healthy", 0.85),
                      field_pred=_mp("field", "healthy", 0.85),
                      features=_mp("features", "severe_stress", 0.85))
    assert r.flag == "EARLY_WARNING"


def test_two_way_majority_when_one_missing():
    r = _eng().decide("EVR_01", "2026-05-22",
                      field_pred=_mp("field", "mild_stress", 0.9),
                      features=_mp("features", "mild_stress", 0.9))
    assert r.agreement_type == "UNANIMOUS"
    assert r.consensus_class == "mild_stress"
    assert r.n_modalities == 2


def test_weights_renormalised_when_missing():
    e = _eng()
    w = e._rebalance(e.weights, {"field", "features"})
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert "satellite" not in w
