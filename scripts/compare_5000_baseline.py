#!/usr/bin/env python3
"""BASELINE vs CANDIDATE architecture comparison harness (PHASE 1 PART K).

Freezes a BASELINE (lexical-only retrieval over the catalog) and a CANDIDATE (the 5,000-disease
embedding + lexical + safety-recall retrieval architecture), measures both on the SAME synthetic
labeled eval set, and runs the multi-metric promotion gate. Dependency-free (uses the deterministic
retrieval paths + the synthetic eval builder).

Emits a JSON report to docs/evaluation or stdout. This measures the retrieval PLUMBING on synthetic
data — REAL clinical superiority is NOT VERIFIED (no real patient data). The gate output shows the
governance decision (PROMOTE / SHADOW / REJECT) the registry would enforce.

Usage: python scripts/compare_5000_baseline.py [--json] [--n 250]
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _stub_nova_agent():
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    if "nova_agent" not in sys.modules:
        pkg = types.ModuleType("nova_agent")
        pkg.__path__ = [str(_ROOT / "nova_agent")]
        sys.modules["nova_agent"] = pkg


def _metrics_for(retriever, catalog, n, seed):
    """Build synthetic eval cases and compute the MetricSet fields we can measure from retrieval."""
    from learning.retrieval.eval_synthetic import build_eval_cases
    from learning.retrieval.metrics import recall_at_k, critical_recall_at_k, critical_miss_rate
    from learning.baseline import MetricSet

    cases = build_eval_cases(catalog, retriever, n=n, top_k=200, seed=seed)
    r = recall_at_k(cases, ks=(20, 50, 100))
    cr = critical_recall_at_k(cases, ks=(5, 20, 100))
    # top-k "accuracy" here == recall at small k (retrieval Top-1/3/5 presence).
    r_small = recall_at_k(cases, ks=(1, 3, 5, 10))
    # per-specialty recall@100
    by_spec_hits: dict = {}
    by_spec_tot: dict = {}
    from learning.retrieval.metrics import _rank_of
    for c in cases:
        # specialty derived from the true concept's category (looked up in catalog)
        concept = catalog.get_condition(c.true_concept_id) if hasattr(catalog, "get_condition") else None
        spec = (getattr(concept, "category", "") or "unknown")
        by_spec_tot[spec] = by_spec_tot.get(spec, 0) + 1
        if _rank_of(c.ranked_concept_ids, c.true_concept_id) <= 100:
            by_spec_hits[spec] = by_spec_hits.get(spec, 0) + 1
    per_spec = {s: by_spec_hits.get(s, 0) / by_spec_tot[s] for s in by_spec_tot}
    return MetricSet(
        top_1=r_small["recall@1"], top_3=r_small["recall@3"], top_5=r_small["recall@5"],
        top_10=r_small["recall@10"],
        recall_at_20=r["recall@20"], recall_at_50=r["recall@50"], recall_at_100=r["recall@100"],
        critical_recall_at_5=cr["critical_recall@5"], critical_recall_at_20=cr["critical_recall@20"],
        critical_recall_at_100=cr["critical_recall@100"],
        critical_miss_rate=critical_miss_rate(cases, k=100),
        per_specialty_recall_at_100=per_spec,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args(argv)

    _stub_nova_agent()
    from nova_agent.ontology.registry import build_catalog
    from learning.retrieval.index import DiseaseIndex
    from learning.retrieval.retriever import Retriever
    from learning.baseline import compare

    catalog = build_catalog()
    index = DiseaseIndex().build(catalog.all_concepts())

    # BASELINE: lexical-only (no embedding index fusion) — simulate by an index-less retriever that
    # relies on the catalog lexical search. We approximate by disabling embedding contribution:
    # a retriever whose index is EMPTY falls back to lexical fusion only.
    baseline_retriever = Retriever(DiseaseIndex().build([]), catalog=catalog)
    # CANDIDATE: full embedding + lexical fusion over the 5,000+ index.
    candidate_retriever = Retriever(index, catalog=catalog)

    baseline = _metrics_for(baseline_retriever, catalog, args.n, args.seed)
    candidate = _metrics_for(candidate_retriever, catalog, args.n, args.seed)
    result = compare(baseline, candidate)

    report = {
        "note": ("Synthetic retrieval-plumbing comparison; REAL clinical superiority NOT VERIFIED "
                 "(no real patient data). Gate decision shows what the registry would enforce."),
        "n": args.n,
        "comparison": result.as_dict(),
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("BASELINE (lexical-only) vs CANDIDATE (embedding+lexical, 5,000+ index)")
        print(f"  decision: {result.decision}")
        for k in ("recall_at_100", "critical_recall_at_100", "critical_miss_rate", "top_5"):
            print(f"  {k:24s} base={getattr(baseline,k):.4f}  cand={getattr(candidate,k):.4f}")
        print("  reasons:", result.reasons[:3])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
