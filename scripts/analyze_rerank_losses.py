"""Rerank-loss analysis (Round M): for every concept RETRIEVED by Stage 1 but removed before the
Rerank Top-25, record why it lost.

Per dropped candidate: retrieval rank/score, rerank score, which signal-typed sub-queries retrieved it
(matched evidence channels: chief_complaint / symptom / objective_finding / history_risk / medication /
imaging / code), curation depth (specificity proxy), dangerous/urgency flags, the patient's recorded
pertinent negatives, and the competing survivors (the 5 weakest kept + the 25th-ranked score).

DEVELOPMENT CASES ONLY -- refuses any blind module. Mock LLM, synthetic data.

    NOVA_COMPETITION_RETRIEVAL=1 python scripts/analyze_rerank_losses.py \
        --case-module evaluation.generalization_dev_cases_round_m --case-var ROUND_M_CASES \
        --cases RoundM_098,RoundM_099 --output /tmp/rerank_losses.json --truth-only
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import nova_agent.retrieval_pipeline as rp  # noqa: E402
from evaluation.simulator import PatientSimulator  # noqa: E402
from nova_agent.diagnosis_normalizer import same_diagnosis  # noqa: E402
from nova_agent.llm_client import MockLLMClient  # noqa: E402
from nova_agent.orchestrator import DoctorAgent  # noqa: E402


def analyze_case(case, *, truth_only: bool):
    agent = DoctorAgent(llm_client=MockLLMClient())
    state = agent.new_case(case.case_id, case.chief_complaint, case.demographics)
    sim = PatientSimulator(case)
    turns = []
    while state.remaining_turns:
        channels = {}
        captured = {}
        orig_rrf, orig_rerank, orig_retrieve = rp._rrf_fuse, rp.lightweight_rerank, rp.retrieve_high_recall

        def rrf(lists, top_k):
            for signal, hits in lists:
                for rank, hit in enumerate(hits, 1):
                    channels.setdefault(hit.concept.concept_id, []).append({"signal": signal, "rank": rank})
            return orig_rrf(lists, top_k)

        def retrieve(*a, **kw):
            result = orig_retrieve(*a, **kw)
            captured["retrieved"] = list(result)
            return result

        def rerank(retrieved, **kw):
            kept = orig_rerank(retrieved, **kw)
            captured["scored"] = {c.concept.concept_id: round(rp._rerank_score(c, rank), 4) for rank, c in enumerate(retrieved, 1)}
            captured["kept"] = {c.concept.concept_id for c in kept}
            return kept

        with patch.object(rp, "_rrf_fuse", rrf), patch.object(rp, "retrieve_high_recall", retrieve), \
                patch.object(rp, "lightweight_rerank", rerank):
            action, _, _ = agent.decide(state)
        retrieved = captured.get("retrieved", [])
        if retrieved:
            kept = captured["kept"]
            scores = captured["scored"]
            ordered_kept = sorted((c for c in retrieved if c.concept.concept_id in kept), key=lambda c: -scores[c.concept.concept_id])
            floor = scores[ordered_kept[-1].concept.concept_id] if ordered_kept else None
            dropped = []
            for rank, c in enumerate(retrieved, 1):
                cid = c.concept.concept_id
                if cid in kept:
                    continue
                is_truth = same_diagnosis(c.concept.canonical_name, case.ground_truth_diagnosis)
                if truth_only and not is_truth:
                    continue
                dropped.append(dict(
                    concept=c.concept.canonical_name, is_truth=is_truth, retrieval_rank=rank,
                    retrieval_score=round(c.match_score, 4), match_kind=c.match_kind, rerank_score=scores[cid],
                    gap_to_top25_floor=round(floor - scores[cid], 4) if floor is not None else None,
                    channels=channels.get(cid, []), curation=c.concept.curation_status,
                    dangerous=bool(c.concept.dangerous), urgency=c.concept.urgency,
                    typical_feature_count=len(getattr(c.concept, "typical_features", []) or [])))
            turns.append(dict(turn=state.turn_count + 1, retrieved=len(retrieved), kept=len(kept), top25_floor=floor,
                              weakest_survivors=[dict(concept=c.concept.canonical_name, rerank_score=scores[c.concept.concept_id],
                                                      match_kind=c.match_kind, curation=c.concept.curation_status)
                                                 for c in ordered_kept[-5:]],
                              dropped=dropped, pertinent_negatives=list(state.pertinent_negatives)))
        agent.observe(state, action, sim.respond(action))
        if action.action_type == "DIAGNOSE":
            break
    return dict(case_id=case.case_id, truth=case.ground_truth_diagnosis, turns=turns)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case-module", default="evaluation.generalization_dev_cases_round_m")
    p.add_argument("--case-var", default="ROUND_M_CASES")
    p.add_argument("--cases", help="comma-separated development case IDs")
    p.add_argument("--output", required=True)
    p.add_argument("--truth-only", action="store_true", help="record only the ground-truth concept when it is dropped")
    args = p.parse_args()
    if "blind" in args.case_module:
        raise SystemExit("refusing to analyze a blind module")
    cases = getattr(importlib.import_module(args.case_module), args.case_var)
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c.case_id in wanted]
    results = [analyze_case(c, truth_only=args.truth_only) for c in cases if c.scoring_expected]
    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    truth_lost = sum(any(d["is_truth"] for t in r["turns"] for d in t["dropped"]) for r in results)
    print(f"cases={len(results)} cases_where_truth_was_retrieved_then_dropped={truth_lost}")


if __name__ == "__main__":
    main()
