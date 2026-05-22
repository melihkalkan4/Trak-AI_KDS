"""3-way consensus engine, agreement metrics, anomaly flagger."""

from .decision_engine import (
    ConsensusDecisionEngine,
    ConsensusResult,
    ModalityPrediction,
)
from .agreement_metrics import (
    cohens_kappa,
    fleiss_kappa,
    confusion_matrix,
    pairwise_kappa_table,
    disagreement_patterns,
    interpret_kappa,
    to_fleiss_matrix,
    AgreementSummary,
    summarise,
)
from .anomaly_flagger import (
    ConsensusAlert,
    flag_consensus,
    generate_alert,
)

__all__ = [
    "ConsensusDecisionEngine", "ConsensusResult", "ModalityPrediction",
    "cohens_kappa", "fleiss_kappa", "confusion_matrix",
    "pairwise_kappa_table", "disagreement_patterns", "interpret_kappa",
    "to_fleiss_matrix", "AgreementSummary", "summarise",
    "ConsensusAlert", "flag_consensus", "generate_alert",
]
