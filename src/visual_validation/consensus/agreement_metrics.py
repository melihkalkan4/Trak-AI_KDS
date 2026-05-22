"""
Inter-rater agreement metrics for the 3-way modality consensus.

Provides:
    - cohens_kappa(a, b)                — pairwise (2-rater) Kappa
    - fleiss_kappa(ratings_matrix)       — N-rater (>=3) Kappa
    - confusion_matrix(a, b)             — per-class cross-tab
    - pairwise_kappa_table(records)      — all-modality pairs
    - disagreement_patterns(records)     — which class-pairs disagree most
    - summarise(records)                 — single-call all-of-the-above

`records` is a list[dict] where each dict carries at least three keys —
"satellite", "field", "features" — each containing a harmonized class
label (or None when the modality didn't report for that observation).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Iterable, Optional, Sequence

from .. import config


# ---------------------------------------------------------------------------
# Pairwise — Cohen's Kappa
# ---------------------------------------------------------------------------
def cohens_kappa(a: Sequence[str], b: Sequence[str],
                 labels: Optional[Sequence[str]] = None) -> float:
    """
    Cohen's Kappa for two raters over the same N items.

    Returns NaN when the inputs are empty or fully constant (degenerate).
    """
    if len(a) != len(b):
        raise ValueError(f"Length mismatch: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        return float("nan")

    labs = list(labels or config.HARMONIZED_LABELS)
    idx = {l: i for i, l in enumerate(labs)}
    k = len(labs)

    # Confusion matrix
    cm = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        if x in idx and y in idx:
            cm[idx[x]][idx[y]] += 1

    total = sum(sum(r) for r in cm)
    if total == 0:
        return float("nan")

    p_o = sum(cm[i][i] for i in range(k)) / total
    row_marg = [sum(cm[i]) / total for i in range(k)]
    col_marg = [sum(cm[r][c] for r in range(k)) / total for c in range(k)]
    p_e = sum(row_marg[i] * col_marg[i] for i in range(k))

    if p_e >= 1.0:
        return float("nan")
    return (p_o - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# N-rater — Fleiss' Kappa
# ---------------------------------------------------------------------------
def fleiss_kappa(ratings_matrix: list[list[int]]) -> float:
    """
    Fleiss' Kappa for N subjects × k categories.

    `ratings_matrix[i][j]` = how many raters gave subject i category j.
    Row sums must be constant (= number of raters n).  NaN on degenerate
    input.

    Reference: Fleiss (1971), "Measuring nominal scale agreement among
    many raters", Psychological Bulletin 76(5):378-382.
    """
    N = len(ratings_matrix)
    if N == 0:
        return float("nan")
    k = len(ratings_matrix[0])
    if k == 0:
        return float("nan")
    n = sum(ratings_matrix[0])
    if n < 2:
        return float("nan")
    for row in ratings_matrix:
        if sum(row) != n:
            raise ValueError("Inconsistent rater counts across subjects.")

    # P_j = proportion of all assignments to category j
    total_assignments = N * n
    P_j = [sum(ratings_matrix[i][j] for i in range(N)) / total_assignments
           for j in range(k)]

    # P_i = extent of agreement on subject i
    P_i = []
    for i in range(N):
        s = sum(ratings_matrix[i][j] ** 2 for j in range(k))
        P_i.append((s - n) / (n * (n - 1)))

    P_bar = sum(P_i) / N
    P_e = sum(p * p for p in P_j)

    if P_e >= 1.0:
        return float("nan")
    return (P_bar - P_e) / (1.0 - P_e)


# ---------------------------------------------------------------------------
# Helper — build a Fleiss matrix from per-observation modality dicts
# ---------------------------------------------------------------------------
def to_fleiss_matrix(records: Iterable[dict],
                     modalities: Sequence[str] = ("satellite", "field", "features"),
                     labels: Optional[Sequence[str]] = None,
                     ) -> tuple[list[list[int]], list[dict]]:
    """
    Turn a list of {modality -> class} dicts into a Fleiss-compatible
    matrix.  Only records where ALL `modalities` are present are kept
    (Fleiss requires a constant number of raters per subject).

    Returns (matrix, kept_records).
    """
    labs = list(labels or config.HARMONIZED_LABELS)
    idx = {l: i for i, l in enumerate(labs)}
    matrix: list[list[int]] = []
    kept: list[dict] = []
    for rec in records:
        votes = [rec.get(m) for m in modalities]
        if any(v is None for v in votes):
            continue
        if any(v not in idx for v in votes):
            continue
        row = [0] * len(labs)
        for v in votes:
            row[idx[v]] += 1
        matrix.append(row)
        kept.append(rec)
    return matrix, kept


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------
def confusion_matrix(a: Sequence[str], b: Sequence[str],
                     labels: Optional[Sequence[str]] = None) -> dict:
    """
    Return {"labels": [...], "matrix": [[..]], "row_sums": [..], "col_sums": [..]}
    Rows are modality A; cols are modality B.
    """
    labs = list(labels or config.HARMONIZED_LABELS)
    idx = {l: i for i, l in enumerate(labs)}
    k = len(labs)
    m = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        if x in idx and y in idx:
            m[idx[x]][idx[y]] += 1
    return {
        "labels": labs,
        "matrix": m,
        "row_sums": [sum(r) for r in m],
        "col_sums": [sum(m[r][c] for r in range(k)) for c in range(k)],
    }


# ---------------------------------------------------------------------------
# Pairwise table across all modality pairs
# ---------------------------------------------------------------------------
def pairwise_kappa_table(records: Iterable[dict],
                         modalities: Sequence[str] = ("satellite", "field", "features"),
                         ) -> list[dict]:
    """
    For each (m1, m2) modality pair, compute Cohen's Kappa over the records
    where BOTH modalities reported.  Returns a list of dicts that's easy to
    render as a Streamlit / pandas table.
    """
    recs = list(records)
    rows = []
    for m1, m2 in combinations(modalities, 2):
        a = [r[m1] for r in recs if r.get(m1) and r.get(m2)]
        b = [r[m2] for r in recs if r.get(m1) and r.get(m2)]
        k = cohens_kappa(a, b)
        rows.append({
            "modality_a": m1,
            "modality_b": m2,
            "n_pairs": len(a),
            "cohens_kappa": None if math.isnan(k) else float(k),
            "interpretation": interpret_kappa(k),
        })
    return rows


# ---------------------------------------------------------------------------
# Disagreement patterns
# ---------------------------------------------------------------------------
def disagreement_patterns(records: Iterable[dict],
                          modalities: Sequence[str] = ("satellite", "field", "features"),
                          top_n: int = 10) -> list[dict]:
    """
    Find which (class_modality_a, class_modality_b) pairs disagree most
    often.  Returns the top-N rows sorted by frequency desc.
    """
    cnt: Counter = Counter()
    for r in records:
        for m1, m2 in combinations(modalities, 2):
            c1, c2 = r.get(m1), r.get(m2)
            if not c1 or not c2 or c1 == c2:
                continue
            cnt[(m1, c1, m2, c2)] += 1
    rows = []
    for (m1, c1, m2, c2), n in cnt.most_common(top_n):
        rows.append({
            "modality_a": m1, "class_a": c1,
            "modality_b": m2, "class_b": c2,
            "count": n,
        })
    return rows


# ---------------------------------------------------------------------------
# Landis & Koch (1977) Kappa interpretation
# ---------------------------------------------------------------------------
def interpret_kappa(k: float) -> str:
    if k is None or (isinstance(k, float) and math.isnan(k)):
        return "n/a"
    if k < 0.0:
        return "poor (worse than chance)"
    if k < 0.20:
        return "slight"
    if k < 0.40:
        return "fair"
    if k < 0.60:
        return "moderate"
    if k < 0.80:
        return "substantial"
    return "almost perfect"


# ---------------------------------------------------------------------------
# One-call summariser
# ---------------------------------------------------------------------------
@dataclass
class AgreementSummary:
    n_records_total: int
    n_records_all_three: int
    pairwise_kappa: list[dict]
    fleiss_kappa: Optional[float]
    fleiss_interpretation: str
    disagreement_top: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def summarise(records: Iterable[dict],
              modalities: Sequence[str] = ("satellite", "field", "features"),
              ) -> AgreementSummary:
    recs = list(records)
    matrix, kept = to_fleiss_matrix(recs, modalities)
    fk = fleiss_kappa(matrix) if matrix else float("nan")
    return AgreementSummary(
        n_records_total=len(recs),
        n_records_all_three=len(kept),
        pairwise_kappa=pairwise_kappa_table(recs, modalities),
        fleiss_kappa=None if math.isnan(fk) else float(fk),
        fleiss_interpretation=interpret_kappa(fk),
        disagreement_top=disagreement_patterns(recs, modalities),
    )


__all__ = [
    "cohens_kappa", "fleiss_kappa",
    "confusion_matrix", "to_fleiss_matrix",
    "pairwise_kappa_table", "disagreement_patterns",
    "interpret_kappa",
    "AgreementSummary", "summarise",
]
