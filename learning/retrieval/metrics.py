"""Retrieval evaluation metrics (dependency-free).

For a high-recall retriever the primary goal is RECALL@K (is the true diagnosis anywhere in the
Top-K candidate pool?), NOT Top-1 accuracy — Top-1 is the reranker/LLM's job downstream. We report
Recall@{20,50,100,200} overall and, separately and more importantly, CRITICAL Recall@{20,50,100}
(recall restricted to must-not-miss diagnoses). A critical miss is the metric that gates promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence


@dataclass
class EvalCase:
    """One labeled retrieval eval case: the ranked candidate concept_ids the retriever returned,
    the true concept_id, and whether the true diagnosis is critical/must-not-miss."""

    case_id: str
    ranked_concept_ids: List[str]
    true_concept_id: str
    is_critical: bool = False


def _rank_of(ranked: Sequence[str], target: str) -> int:
    for i, cid in enumerate(ranked, 1):
        if cid == target:
            return i
    return 10 ** 9


def recall_at_k(cases: Sequence[EvalCase], ks: Sequence[int] = (20, 50, 100, 200)) -> Dict[str, float]:
    if not cases:
        return {f"recall@{k}": 0.0 for k in ks}
    out: Dict[str, float] = {}
    for k in ks:
        hits = sum(1 for c in cases if _rank_of(c.ranked_concept_ids, c.true_concept_id) <= k)
        out[f"recall@{k}"] = hits / len(cases)
    return out


def critical_recall_at_k(cases: Sequence[EvalCase], ks: Sequence[int] = (20, 50, 100)) -> Dict[str, float]:
    crit = [c for c in cases if c.is_critical]
    if not crit:
        # vacuously perfect if there are no critical cases (nothing to miss)
        return {f"critical_recall@{k}": 1.0 for k in ks}
    out: Dict[str, float] = {}
    for k in ks:
        hits = sum(1 for c in crit if _rank_of(c.ranked_concept_ids, c.true_concept_id) <= k)
        out[f"critical_recall@{k}"] = hits / len(crit)
    return out


def critical_miss_rate(cases: Sequence[EvalCase], k: int = 100) -> float:
    """Fraction of CRITICAL cases whose true dx is NOT in the Top-k pool (the safety-gating metric)."""
    crit = [c for c in cases if c.is_critical]
    if not crit:
        return 0.0
    misses = sum(1 for c in crit if _rank_of(c.ranked_concept_ids, c.true_concept_id) > k)
    return misses / len(crit)


def evaluate(cases: Sequence[EvalCase]) -> Dict[str, float]:
    m: Dict[str, float] = {"n": float(len(cases))}
    m.update(recall_at_k(cases))
    m.update(critical_recall_at_k(cases))
    m["critical_miss_rate@100"] = critical_miss_rate(cases, k=100)
    return m
