#!/usr/bin/env python3
"""Development-only evaluation under the PRELIMINARY-ROUND rules (organizer briefing 2026-10-06).

Runs synthetic development cases through competition.adapter.NovaCompetitionAgent with
preliminary=True and the deterministic MOCK model (never the fixed competition model):
  * no TEST action; vital signs are handed over with the first statement;
  * SAY text must be <= 30 characters; DIAGNOSE must carry an S/O/A/P note and ONE primary diagnosis;
  * the simulated patient answers from the case's scripted answer for the internal key the agent
    asked (free text is not parsed), the examiner from the scripted examination results.

Reports accuracy, critical recall, turns, SAY compliance and note completeness, and (with
--compare) the same cases under the unrestricted development rules so the cost of losing TEST is
visible. Synthetic data, mock LLM, no expert adjudication: NOT the official score.

  NOVA_COMPETITION_RETRIEVAL=1 python scripts/evaluate_preliminary_rules.py \
      --case-module evaluation.generalization_dev_cases_round_m --case-var ROUND_M_CASES --compare
"""
from __future__ import annotations

import argparse
import importlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from competition.adapter import NovaCompetitionAgent  # noqa: E402
from evaluation.simulator import run_case  # noqa: E402
from nova_agent.diagnosis_normalizer import same_diagnosis  # noqa: E402
from nova_agent.llm_client import MockLLMClient  # noqa: E402
from nova_agent.orchestrator import DoctorAgent  # noqa: E402
from nova_agent.preliminary import SAY_MAX_CHARS  # noqa: E402


def run_preliminary_case(case) -> dict:
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    obs = {"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics, "vital_signs": case.exam_results.get("vital_signs")}
    turns = says = exams = 0
    over_limit = 0
    tests = 0
    while True:
        action = agent.act(obs)
        kind = action["action_type"]
        if kind == "DIAGNOSE":
            soap = action.get("soap") or {}
            return dict(case_id=case.case_id, scored=case.scoring_expected, critical=case.critical,
                        truth=case.ground_truth_diagnosis, final=action.get("primary_diagnosis"),
                        key=action["metadata"].get("key"), turns=turns, says=says, exams=exams,
                        tests=tests, say_over_limit=over_limit,
                        soap_complete=all(soap.get(k, "").strip() for k in "SOAP"),
                        correct=bool(same_diagnosis(action["metadata"].get("key", ""), case.ground_truth_diagnosis)
                                     or same_diagnosis(action.get("primary_diagnosis") or "", case.ground_truth_diagnosis)
                                     or any(same_diagnosis(part.strip(" ()"), case.ground_truth_diagnosis)
                                            for part in (action.get("primary_diagnosis") or "").replace("(", "|").split("|"))))
        turns += 1
        pending = agent._pending_actions[case.case_id]
        if kind == "SAY":
            says += 1
            over_limit += len(action["content"]) > SAY_MAX_CHARS
            reply = case.answers.get(pending.key, case.default_answer) if pending.key != "explanation" else "네, 알겠습니다."
            obs = {"case_id": case.case_id, "observation_type": "say_response", "content": reply}
        elif kind == "EXAM":
            exams += 1
            obs = {"case_id": case.case_id, "observation_type": "exam_result",
                   "content": case.exam_results.get(pending.key, case.default_exam_result)}
        else:  # TEST would be a rule violation
            tests += 1
            obs = {"case_id": case.case_id, "observation_type": "test_result",
                   "content": case.test_results.get(pending.key, case.default_test_result)}


def summarize(rows: list) -> dict:
    scored = [r for r in rows if r["scored"]]
    crit = [r for r in scored if r["critical"]]
    return dict(cases=len(rows), scored=len(scored),
                accuracy=sum(r["correct"] for r in scored) / max(1, len(scored)),
                critical_recall=(sum(r["correct"] for r in crit) / len(crit)) if crit else None,
                mean_turns=statistics.mean(r["turns"] for r in rows),
                max_turns=max(r["turns"] for r in rows),
                tests_requested=sum(r["tests"] for r in rows),
                say_over_30_chars=sum(r["say_over_limit"] for r in rows),
                soap_complete=sum(r["soap_complete"] for r in rows),
                cases_over_50_turns=sum(r["turns"] > 50 for r in rows))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--case-module", default="evaluation.generalization_dev_cases_round_m")
    p.add_argument("--case-var", default="ROUND_M_CASES")
    p.add_argument("--cases", help="comma-separated case ids")
    p.add_argument("--compare", action="store_true", help="also run the unrestricted development rules")
    p.add_argument("--output")
    args = p.parse_args()
    if "blind" in args.case_module:
        raise SystemExit("refusing to evaluate a blind module")
    cases = getattr(importlib.import_module(args.case_module), args.case_var)
    if args.cases:
        cases = [c for c in cases if c.case_id in set(args.cases.split(","))]
    rows = [run_preliminary_case(c) for c in cases]
    out = {"preliminary_rules": summarize(rows)}
    if args.compare:
        agent = DoctorAgent(llm_client=MockLLMClient())
        dev = [run_case(agent, c) for c in cases]
        scored = [r for r in dev if r.scoring_expected]
        crit = [r for r in scored if r.critical]
        out["unrestricted_development_rules"] = dict(
            scored=len(scored), accuracy=sum(r.correct for r in scored) / max(1, len(scored)),
            critical_recall=(sum(r.correct for r in crit) / len(crit)) if crit else None,
            mean_turns=statistics.mean(r.turns for r in dev), tests_requested=sum(r.test_count for r in dev))
    out["limitation"] = "synthetic development cases, deterministic mock model, no expert adjudication; not the official score"
    print(json.dumps(out, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps({**out, "cases": rows}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
