"""Cohen's + Fleiss' Kappa correctness on hand-checked examples."""

import math

from visual_validation.consensus import agreement_metrics as am


def test_cohens_kappa_perfect_agreement():
    a = ["healthy"] * 5 + ["disease"] * 5
    assert am.cohens_kappa(a, a) == 1.0


def test_cohens_kappa_all_disagree_negative():
    a = ["healthy"] * 5 + ["disease"] * 5
    b = ["disease"] * 5 + ["healthy"] * 5
    k = am.cohens_kappa(a, b)
    assert k < 0.0


def test_fleiss_kappa_perfect_agreement():
    # 3 subjects, 3 raters, all agree on healthy
    mat = [[3, 0, 0, 0], [3, 0, 0, 0], [3, 0, 0, 0]]
    k = am.fleiss_kappa(mat)
    # Degenerate (no marginal variability) — kappa returns NaN
    assert math.isnan(k)


def test_fleiss_kappa_with_variability_positive():
    # 3 subjects, 3 raters, mostly agree
    mat = [
        [3, 0, 0, 0],   # all healthy
        [0, 3, 0, 0],   # all mild
        [2, 1, 0, 0],   # 2 healthy, 1 mild
    ]
    k = am.fleiss_kappa(mat)
    assert not math.isnan(k)
    assert k > 0.0


def test_to_fleiss_matrix_filters_incomplete_records():
    records = [
        {"satellite": "healthy", "field": "healthy", "features": "healthy"},
        {"satellite": None,      "field": "disease", "features": "healthy"},  # dropped
        {"satellite": "mild_stress", "field": "mild_stress", "features": "mild_stress"},
    ]
    mat, kept = am.to_fleiss_matrix(records)
    assert len(mat) == 2
    assert len(kept) == 2


def test_pairwise_kappa_table_returns_three_rows():
    records = [
        {"satellite": "healthy", "field": "healthy", "features": "healthy"},
        {"satellite": "disease", "field": "disease", "features": "mild_stress"},
        {"satellite": "mild_stress", "field": "mild_stress", "features": "mild_stress"},
    ]
    rows = am.pairwise_kappa_table(records)
    assert len(rows) == 3
    pairs = {(r["modality_a"], r["modality_b"]) for r in rows}
    assert pairs == {("satellite", "field"),
                     ("satellite", "features"),
                     ("field", "features")}


def test_interpret_kappa_buckets():
    assert am.interpret_kappa(-0.1) == "poor (worse than chance)"
    assert am.interpret_kappa(0.1)  == "slight"
    assert am.interpret_kappa(0.3)  == "fair"
    assert am.interpret_kappa(0.5)  == "moderate"
    assert am.interpret_kappa(0.7)  == "substantial"
    assert am.interpret_kappa(0.9)  == "almost perfect"
