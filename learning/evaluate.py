"""Ranker evaluation metrics (dependency-free).

Computes the metrics the promotion gate cares about, most importantly `critical_recall` — the
fraction of cases where a critical/red-flag true label is kept in the top-K of the ranked list.
Also top-k accuracy and mean reciprocal rank. No numpy needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from learning.schemas import RankerOutput


@dataclass(frozen=True)
class EvalCase:
    output: RankerOutput
    true_concept_id: str
    true_is_critical: bool


def _rank_of(output: RankerOutput, concept_id: str) -> int:
    for r in output.ranked:
        if r.concept_id == concept_id:
            return r.rank
    return 10 ** 9  # not present


def evaluate(cases: Sequence[EvalCase], k: int = 5) -> Dict[str, float]:
    if not cases:
        return {"n": 0.0, "top_k_accuracy": 0.0, "mrr": 0.0, "critical_recall": 1.0}
    topk_hits = 0
    mrr = 0.0
    crit_total = 0
    crit_hits = 0
    for c in cases:
        rank = _rank_of(c.output, c.true_concept_id)
        if rank <= k:
            topk_hits += 1
        if rank < 10 ** 9:
            mrr += 1.0 / rank
        if c.true_is_critical:
            crit_total += 1
            if rank <= k:
                crit_hits += 1
    return {
        "n": float(len(cases)),
        "top_k_accuracy": topk_hits / len(cases),
        "mrr": mrr / len(cases),
        # If there are no critical cases, recall is vacuously 1.0 (nothing missed).
        "critical_recall": (crit_hits / crit_total) if crit_total else 1.0,
        "k": float(k),
    }
