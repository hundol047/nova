"""Deep clinical reranker (PHASE 1 PART G).

Narrows the broad Top-100~200 retrieval pool to a focused Top-20~30 for the LLM, using patient +
disease embeddings plus clinical evidence signals (supporting/contradictory evidence, objective
findings, temporal relation, risk factors, safety flags). A dependency-free deterministic reranker
runs everywhere; a torch reranker is optional (same interface, loaded lazily).

Non-negotiable: a safety_mandatory candidate is NEVER dropped by reranking, regardless of score
(Safety > ML). Reranking only re-orders and truncates NON-mandatory tail candidates.
"""

from learning.rerank.reranker import (
    Reranker,
    RerankInput,
    RerankedCandidate,
    RerankResult,
)
from learning.rerank.hard_negatives import MIMIC_PAIRS, hard_negatives_for

__all__ = [
    "Reranker", "RerankInput", "RerankedCandidate", "RerankResult",
    "MIMIC_PAIRS", "hard_negatives_for",
]
