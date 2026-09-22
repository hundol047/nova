"""Real-LLM evaluation harness (spec section 3): `python -m evaluation.real_llm_benchmark`.

Unlike evaluation/benchmark.py (which defaults to the offline, deterministic `mock` provider and
is what's used for tuning/held-out accuracy in CI), this harness is meant to be pointed at an
ACTUAL LLM endpoint -- set NOVA_LLM_PROVIDER (competition/openai_compatible/local/anthropic) and
its endpoint/model/key env vars before running, or pass --provider to override just for this run.

If no real provider is configured, this still runs (useful to validate the harness's own plumbing
end to end -- JSON parsing, metric collection, resume logic), but prints a loud, impossible-to-miss
disclaimer that the results are NOT a real-LLM evaluation, and every metric in the saved JSON is
tagged with `provider_is_real: false`.

Token usage is recorded ONLY when the endpoint's response actually reports it (spec: null, never
an estimated number presented as if it were real).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from nova_agent.config import get_config
from nova_agent.llm_client import MockLLMClient, get_llm_client
from nova_agent.orchestrator import DoctorAgent

from evaluation.cases import SyntheticCase
from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.simulator import CaseResult, PatientSimulator


def run_one_case(agent: DoctorAgent, case: SyntheticCase, timeout_seconds: Optional[float]) -> tuple:
    """Runs one case, returning (CaseResult, wall_seconds, timed_out: bool). A soft, between-turn
    timeout: does not preempt a single hung network call (each real client's own
    NOVA_LLM_TIMEOUT_SECONDS covers that), only stops issuing further turns once the case's total
    wall time exceeds the budget."""
    from nova_agent.diagnosis_normalizer import same_diagnosis
    from nova_agent.knowledge.retrieval import disease_by_id
    from nova_agent.state import PatientState

    state: PatientState = agent.new_case(case.case_id, case.chief_complaint, case.demographics)
    simulator = PatientSimulator(case)
    start = time.perf_counter()

    seen_keys: List[tuple] = []
    duplicate_actions = malformed_turns = ask_count = exam_count = test_count = 0
    tests_performed: List[str] = []
    failed_to_diagnose = True
    timed_out = False

    for _ in range(state.max_turns):
        if timeout_seconds is not None and (time.perf_counter() - start) > timeout_seconds:
            timed_out = True
            break
        action, llm_output, _differential = agent.decide(state)
        if llm_output is None:
            malformed_turns += 1
        key_sig = (action.action_type, action.key)
        if action.action_type != "DIAGNOSE" and key_sig in seen_keys:
            duplicate_actions += 1
        seen_keys.append(key_sig)
        if action.action_type == "TEST":
            tests_performed.append(action.key)
            test_count += 1
        elif action.action_type == "ASK":
            ask_count += 1
        elif action.action_type == "EXAM":
            exam_count += 1
        result_text = simulator.respond(action)
        agent.observe(state, action, result_text)
        if action.action_type == "DIAGNOSE":
            failed_to_diagnose = False
            break

    gt_entry = disease_by_id(case.ground_truth_diagnosis)
    relevant_tests = set(gt_entry.get("discriminating_tests", [])) if gt_entry else set()
    unnecessary_tests = sum(1 for t in tests_performed if t not in relevant_tests)
    correct = bool(state.final_diagnosis) and same_diagnosis(state.final_diagnosis, case.ground_truth_diagnosis)

    result = CaseResult(
        case_id=case.case_id, category=case.category, scoring_expected=case.scoring_expected,
        ground_truth=case.ground_truth_diagnosis, final_diagnosis=state.final_diagnosis,
        correct=correct, turns=state.turn_count, ask_count=ask_count, exam_count=exam_count,
        test_count=test_count, duplicate_actions=duplicate_actions, unnecessary_tests=unnecessary_tests,
        critical=case.critical, critical_miss=case.critical and not correct, malformed_turns=malformed_turns,
        failed_to_diagnose=failed_to_diagnose,
        llm_call_count=state.llm_call_count, llm_success_count=state.llm_success_count,
        llm_failure_count=state.llm_failure_count, llm_fallback_count=state.llm_fallback_count,
    )
    wall_seconds = time.perf_counter() - start
    return result, wall_seconds, timed_out, state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default=None,
                         help="Override NOVA_LLM_PROVIDER for this run only (e.g. competition, "
                              "openai_compatible, anthropic). Defaults to whatever is already configured.")
    parser.add_argument("--cases", default=None,
                         help="Comma-separated case_ids to run (default: all held-out cases).")
    parser.add_argument("--max-cases", type=int, default=None, help="Cap the number of cases run.")
    parser.add_argument("--timeout", type=float, default=None, help="Soft per-case wall-time budget in seconds.")
    parser.add_argument("--save-json", default=None, help="Path to write structured per-case + summary results.")
    parser.add_argument("--resume", action="store_true",
                         help="With --save-json pointing at an existing file, skip case_ids already recorded in it.")
    args = parser.parse_args()

    if args.provider:
        import os
        os.environ["NOVA_LLM_PROVIDER"] = args.provider
        get_config(reload=True)

    client = get_llm_client()
    provider_is_real = not isinstance(client, MockLLMClient)
    cfg = get_config()

    if not provider_is_real:
        print(
            "=" * 70 + "\n"
            "NOTICE: NOVA_LLM_PROVIDER is 'mock' -- this run exercises the harness's OWN\n"
            "plumbing (JSON output, metric collection, resume logic) only. It is NOT a real-LLM\n"
            "evaluation and every result below is tagged provider_is_real=false. Set\n"
            "NOVA_LLM_PROVIDER (or pass --provider) to a real provider to get an actual reading.\n"
            + "=" * 70,
            file=sys.stderr,
        )
    else:
        ok, reason = client.preflight()
        print(f"Provider: {cfg.llm_provider} | preflight: {'OK' if ok else 'FAILED'} ({reason})", file=sys.stderr)
        if not ok:
            print("Refusing to run a real-LLM benchmark against an endpoint that failed preflight.", file=sys.stderr)
            sys.exit(1)

    cases = HELD_OUT_CASES
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c.case_id in wanted]
    if args.max_cases:
        cases = cases[: args.max_cases]

    already_done = {}
    if args.resume and args.save_json and Path(args.save_json).exists():
        existing = json.loads(Path(args.save_json).read_text(encoding="utf-8"))
        already_done = {r["case_id"]: r for r in existing.get("cases", [])}
        cases = [c for c in cases if c.case_id not in already_done]
        print(f"Resuming: {len(already_done)} case(s) already recorded, {len(cases)} remaining.", file=sys.stderr)

    agent = DoctorAgent(llm_client=client)
    case_records = list(already_done.values())
    for case in cases:
        print(f"Running {case.case_id}...", file=sys.stderr)
        result, wall_seconds, timed_out, state = run_one_case(agent, case, args.timeout)
        record = {
            "case_id": result.case_id, "ground_truth": result.ground_truth,
            "final_diagnosis": result.final_diagnosis, "correct": result.correct,
            "critical": result.critical, "critical_miss": result.critical_miss,
            "turns": result.turns, "ask_count": result.ask_count, "exam_count": result.exam_count,
            "test_count": result.test_count, "unnecessary_tests": result.unnecessary_tests,
            "llm_calls": state.llm_call_count, "llm_failures": state.llm_failure_count,
            "fallback_count": state.llm_fallback_count,
            "avg_llm_latency_seconds": state.llm_avg_latency_seconds,
            "total_case_latency_seconds": round(wall_seconds, 3),
            "input_tokens": state.llm_total_input_tokens if state.llm_token_usage_available else None,
            "output_tokens": state.llm_total_output_tokens if state.llm_token_usage_available else None,
            "timed_out": timed_out,
        }
        case_records.append(record)
        print(f"  -> {record['final_diagnosis']!r} (correct={record['correct']}, "
              f"turns={record['turns']}, llm_calls={record['llm_calls']}, "
              f"fallbacks={record['fallback_count']})", file=sys.stderr)
        if args.save_json:
            Path(args.save_json).write_text(
                json.dumps({"provider": cfg.llm_provider, "provider_is_real": provider_is_real,
                            "model": getattr(client, "model", None), "cases": case_records}, indent=2),
                encoding="utf-8",
            )

    n = len(case_records) or 1
    scored = [r for r in case_records if r["correct"] or r["final_diagnosis"] is not None]
    critical = [r for r in case_records if r["critical"]]
    print(f"\n=== Real-LLM benchmark summary ({len(case_records)} cases, provider_is_real={provider_is_real}) ===")
    print(f"  Accuracy (all-case):     {sum(r['correct'] for r in case_records) / n * 100:.1f}%")
    if critical:
        print(f"  Critical recall:         {sum(r['correct'] for r in critical) / len(critical) * 100:.1f}%")
        print(f"  Critical miss rate:      {sum(r['critical_miss'] for r in critical) / len(critical) * 100:.1f}%")
    print(f"  Avg turns:               {sum(r['turns'] for r in case_records) / n:.1f}")
    print(f"  Avg LLM calls/case:      {sum(r['llm_calls'] for r in case_records) / n:.1f}")
    fallback_total = sum(r['fallback_count'] for r in case_records)
    call_total = sum(r['llm_calls'] for r in case_records)
    print(f"  Fallback rate:           {(fallback_total / call_total * 100) if call_total else 0:.1f}%")
    latencies = [r["avg_llm_latency_seconds"] for r in case_records if r["avg_llm_latency_seconds"] is not None]
    print(f"  Avg LLM latency:         {(sum(latencies) / len(latencies)):.2f}s" if latencies else "  Avg LLM latency:         NOT VERIFIED (no real call latency recorded)")
    token_records = [r for r in case_records if r["input_tokens"] is not None]
    if token_records:
        print(f"  Avg input/output tokens: {sum(r['input_tokens'] for r in token_records) / len(token_records):.0f} / "
              f"{sum(r['output_tokens'] for r in token_records) / len(token_records):.0f}")
    else:
        print("  Avg input/output tokens: NOT VERIFIED (endpoint did not report token usage)")


if __name__ == "__main__":
    main()
