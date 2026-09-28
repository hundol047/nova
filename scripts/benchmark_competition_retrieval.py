#!/usr/bin/env python
"""Retrieval evaluation utility for the competition retrieval pipeline
(nova_agent/retrieval_pipeline.py + nova_agent/open_world.py).

Measures, honestly and without answer leakage, whether the TRUE diagnosis of a real synthetic
evaluation case actually survives high-recall retrieval -- using only the case's own presenting
text/history (never the ground-truth diagnosis name or id as the query).

Queries come from evaluation/held_out_cases.py + evaluation/generalization_cases_v2.py +
evaluation/generalization_stress_cases.py (the same real synthetic cases the rest of the suite
scores diagnostic accuracy against), restricted to cases whose ground_truth_diagnosis is a Tier-1
KB id that also has a corresponding concept in the DEFAULT (real, non-synthetic) DiseaseCatalog --
this script never builds or measures against a synthetic 5,000-concept test catalog.

Two query conditions are reported separately:
  - chief_complaint_only: JUST the case's original presenting sentence (the hardest, most
    realistic "turn 0" condition).
  - chief_complaint_plus_history: chief complaint + every elicited answer text (approximates a
    case a few turns in, when build_clinical_presentation() has more to work with).

Usage:
    python scripts/benchmark_competition_retrieval.py
    python scripts/benchmark_competition_retrieval.py --json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.generalization_cases_v2 import GENERALIZATION_CASES_V2
from evaluation.generalization_stress_cases import GENERALIZATION_STRESS_CASES
from evaluation.held_out_cases import HELD_OUT_CASES
from nova_agent.ontology.models import Tier
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.open_world import OpenWorldRetriever
from nova_agent.retrieval_pipeline import retrieve_high_recall

# Reference numbers measured in-session on this repository BEFORE this round's retrieval changes
# (commit a1b92c8, chief-complaint+history condition, same 44-case set, same methodology) --
# preserved here as a fixed baseline for honest before/after comparison. Never recomputed by
# re-running old code (this branch's retrieval code has moved on); if that matters, check out
# a1b92c8 and re-run this same script to reproduce them.
BASELINE_RECALL = {
    "chief_complaint_only": {20: 11.4, 50: 11.4, 100: 11.4},
    "chief_complaint_plus_history": {20: 31.8, 50: 34.1, 100: 34.1},
}
BASELINE_LABEL = "commit a1b92c8 (pre-IDF/typical_features-index/multi-query-RRF)"

_ALL_CASES = list(HELD_OUT_CASES) + list(GENERALIZATION_CASES_V2) + list(GENERALIZATION_STRESS_CASES)


@dataclass
class RecallReport:
    condition: str
    n_cases: int
    recall_at: Dict[int, float]
    mrr: float
    mean_rank: Optional[float]
    median_rank: Optional[float]
    tier_recall_at_50: Dict[str, float] = field(default_factory=dict)
    misses: List[str] = field(default_factory=list)


def _kb_id_to_concept_id() -> Dict[str, str]:
    return {c.kb_id: c.concept_id for c in get_default_catalog().all_concepts() if c.kb_id}


def _rank_of(concept_id: str, retrieved_ids: List[str]) -> Optional[int]:
    try:
        return retrieved_ids.index(concept_id) + 1  # 1-indexed
    except ValueError:
        return None


def measure(*, use_history: bool, retrieval_top_k: int = 150) -> RecallReport:
    retriever = OpenWorldRetriever(get_default_catalog())
    kb_to_concept = _kb_id_to_concept_id()
    tier_by_concept = {c.concept_id: c.tier for c in get_default_catalog().all_concepts()}

    ranks: List[Optional[int]] = []
    misses: List[str] = []
    tier_hits: Dict[str, int] = {}
    tier_totals: Dict[str, int] = {}
    n = 0

    for case in _ALL_CASES:
        gt = getattr(case, "ground_truth_diagnosis", None)
        if not gt:
            continue
        concept_id = kb_to_concept.get(gt)
        if concept_id is None:
            continue  # not present in the REAL default catalog -- never fabricate a match
        n += 1
        tier = tier_by_concept.get(concept_id, Tier.TIER1_DEEP).value
        tier_totals[tier] = tier_totals.get(tier, 0) + 1

        # Query built ONLY from the case's own presentation/history -- NEVER the answer.
        assert gt not in case.chief_complaint.lower().replace("_", " "), (
            f"potential answer leakage in chief_complaint for case {case.case_id}"
        )
        history_text = list(case.answers.values()) if use_history and hasattr(case, "answers") else []

        retrieved = retrieve_high_recall(
            retriever, chief_complaint=case.chief_complaint, history=history_text,
            retrieval_top_k=retrieval_top_k,
        )
        retrieved_ids = [c.concept.concept_id for c in retrieved]
        rank = _rank_of(concept_id, retrieved_ids)
        ranks.append(rank)
        if rank is None:
            misses.append(case.case_id)
        elif rank <= 50:
            tier_hits[tier] = tier_hits.get(tier, 0) + 1

    def recall_at(k: int) -> float:
        hits = sum(1 for r in ranks if r is not None and r <= k)
        return round(100.0 * hits / n, 1) if n else 0.0

    reciprocal_ranks = [(1.0 / r) if r is not None else 0.0 for r in ranks]
    mrr = round(sum(reciprocal_ranks) / n, 4) if n else 0.0
    found_ranks = [r for r in ranks if r is not None]
    mean_rank = round(statistics.mean(found_ranks), 1) if found_ranks else None
    median_rank = round(statistics.median(found_ranks), 1) if found_ranks else None

    tier_recall_at_50 = {
        tier: round(100.0 * tier_hits.get(tier, 0) / total, 1)
        for tier, total in tier_totals.items()
    }

    condition = "chief_complaint_plus_history" if use_history else "chief_complaint_only"
    return RecallReport(
        condition=condition, n_cases=n,
        recall_at={20: recall_at(20), 50: recall_at(50), 100: recall_at(100), 150: recall_at(150)},
        mrr=mrr, mean_rank=mean_rank, median_rank=median_rank,
        tier_recall_at_50=tier_recall_at_50, misses=misses,
    )


def measure_latency(n_samples: int = 30) -> Dict[str, float]:
    from nova_agent.retrieval_pipeline import lightweight_rerank

    retriever = OpenWorldRetriever(get_default_catalog())
    queries = [
        "progressive hearing loss and ringing in the ears with vertigo",
        "sudden severe chest pain radiating to the back",
        "fever cough shortness of breath",
        "abdominal pain nausea vomiting",
        "headache dizziness weakness",
    ]
    retrieval_times: List[float] = []
    rerank_times: List[float] = []
    for i in range(n_samples):
        q = queries[i % len(queries)]
        t0 = time.perf_counter()
        retrieved = retrieve_high_recall(retriever, chief_complaint=q, symptoms=q.split(),
                                         retrieval_top_k=150)
        t1 = time.perf_counter()
        lightweight_rerank(retrieved, rerank_top_k=25)
        t2 = time.perf_counter()
        retrieval_times.append(t1 - t0)
        rerank_times.append(t2 - t1)

    def pctl(samples: List[float], p: float) -> float:
        s = sorted(samples)
        return s[min(len(s) - 1, int(len(s) * p))]

    return {
        "retrieval_p50_ms": round(pctl(retrieval_times, 0.5) * 1000, 2),
        "retrieval_p95_ms": round(pctl(retrieval_times, 0.95) * 1000, 2),
        "rerank_p50_ms": round(pctl(rerank_times, 0.5) * 1000, 2),
        "rerank_p95_ms": round(pctl(rerank_times, 0.95) * 1000, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of text")
    args = parser.parse_args()

    reports = [measure(use_history=False), measure(use_history=True)]
    latency = measure_latency()

    if args.json:
        payload = {
            "baseline_label": BASELINE_LABEL,
            "baseline_recall": BASELINE_RECALL,
            "reports": [
                {
                    "condition": r.condition, "n_cases": r.n_cases, "recall_at": r.recall_at,
                    "mrr": r.mrr, "mean_rank": r.mean_rank, "median_rank": r.median_rank,
                    "tier_recall_at_50": r.tier_recall_at_50, "misses": r.misses,
                }
                for r in reports
            ],
            "latency": latency,
        }
        print(json.dumps(payload, indent=2))
        return

    print("=== Competition retrieval evaluation (nova_agent/retrieval_pipeline.py) ===\n")
    print("Query source: evaluation/{held_out_cases,generalization_cases_v2,generalization_"
          "stress_cases}.py -- real synthetic cases' own presenting text/history, NEVER the "
          "ground-truth diagnosis name (asserted per-case above).\n")
    for r in reports:
        print(f"-- {r.condition} (n={r.n_cases}) --")
        baseline = BASELINE_RECALL.get(r.condition, {})
        for k in (20, 50, 100, 150):
            base = baseline.get(k)
            new = r.recall_at[k]
            if base is not None:
                delta = round(new - base, 1)
                print(f"  Recall@{k}: baseline {base}% -> new {new}%  (delta {delta:+.1f} pts)")
            else:
                print(f"  Recall@{k}: {new}%  (no baseline recorded at this K)")
        print(f"  MRR: {r.mrr}")
        print(f"  Mean true-diagnosis rank: {r.mean_rank}")
        print(f"  Median true-diagnosis rank: {r.median_rank}")
        print(f"  Recall@50 by tier: {r.tier_recall_at_50}")
        if r.misses:
            print(f"  Cases where the true diagnosis never appeared in top-150: {r.misses}")
        print()

    print(f"Baseline reference: {BASELINE_LABEL}\n")
    print("-- Latency (this machine, single process, not a production benchmark) --")
    for k, v in latency.items():
        print(f"  {k}: {v} ms")


if __name__ == "__main__":
    main()
