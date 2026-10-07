#!/usr/bin/env python3
"""Round N comparison runner (deterministic MOCK model; development measurement, not an official score).

Runs every development suite through evaluation.simulator.run_case (the same path as evaluation.benchmark)
under the CURRENT environment switches and writes per-case rows + per-suite summaries. Run it once per
configuration (e.g. NOVA_CONCEPT_NORMALIZATION=0 for the ablation) and diff with --compare.

    NOVA_LLM_PROVIDER=mock python scripts/compare_round_n.py --output artifacts/algorithm_round/run.json
    NOVA_LLM_PROVIDER=mock python scripts/compare_round_n.py --compare A.json B.json
"""
import argparse
import importlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SUITES = {
    "tuning": ("evaluation.cases", "CASES"),
    "held_out": ("evaluation.held_out_cases", "HELD_OUT_CASES"),
    "generalization_v2": ("evaluation.generalization_cases_v2", "GENERALIZATION_CASES_V2"),
    "stress": ("evaluation.generalization_stress_cases", "GENERALIZATION_STRESS_CASES"),
    "blind_v5_dev": ("evaluation.blind_cases_v5", "BLIND_CASES_V5"),  # failure analysis was read: DEVELOPMENT use
    "round_j_dev": ("evaluation.generalization_dev_cases_round_j", "ROUND_J_CASES"),
    "round_m_dev": ("evaluation.generalization_dev_cases_round_m", "ROUND_M_CASES"),
    "validation_round_n": ("evaluation.validation_cases_round_n", "VALIDATION_CASES_ROUND_N"),  # frozen, held out
}


def _one(args):
    suite, index = args
    from evaluation.simulator import run_case
    from nova_agent.llm_client import MockLLMClient
    from nova_agent.orchestrator import DoctorAgent
    module, var = SUITES[suite]
    case = getattr(importlib.import_module(module), var)[index]
    r = run_case(DoctorAgent(llm_client=MockLLMClient()), case)
    scored = bool(case.scoring_expected or case.ground_truth_diagnosis not in {"unknown", ""})
    return suite, {"case_id": case.case_id, "truth": case.ground_truth_diagnosis, "final": r.final_diagnosis,
                   "correct": r.correct, "critical": r.critical, "critical_miss": r.critical_miss, "scored": scored,
                   "turns": r.turns, "asks": r.ask_count, "exams": r.exam_count, "tests": r.test_count,
                   "duplicates": r.duplicate_actions, "unnecessary_tests": r.unnecessary_tests,
                   "malformed": r.malformed_turns, "failed": r.failed_to_diagnose}


def summarize(rows):
    s = [r for r in rows if r["scored"]]
    crit = [r for r in s if r["critical"]]
    n = len(rows)
    return {"cases": n, "scored": len(s), "accuracy": sum(r["correct"] for r in s) / max(1, len(s)),
            "all_case_accuracy": sum(r["correct"] for r in rows) / max(1, n),
            "critical": len(crit), "critical_correct": sum(r["correct"] for r in crit),
            "critical_misses": sum(r["critical_miss"] for r in rows),
            "avg_turns": sum(r["turns"] for r in rows) / max(1, n),
            "avg_tests": sum(r["tests"] for r in rows) / max(1, n),
            "unnecessary_tests_per_case": sum(r["unnecessary_tests"] for r in rows) / max(1, n),
            "duplicates": sum(r["duplicates"] for r in rows), "malformed": sum(r["malformed"] for r in rows),
            "failed": sum(r["failed"] for r in rows)}


HIDE = set(filter(None, os.environ.get("ROUND_N_HIDE", "validation_round_n").split(",")))


def run(output):
    jobs = [(s, i) for s, (m, v) in SUITES.items() for i in range(len(getattr(importlib.import_module(m), v)))]
    rows = {s: [] for s in SUITES}
    with ProcessPoolExecutor(max_workers=4) as pool:
        for suite, row in pool.map(_one, jobs, chunksize=2):
            rows[suite].append(row)
    switches = {k: v for k, v in os.environ.items() if k.startswith("NOVA_")}
    out = {"label": "DEVELOPMENT MEASUREMENT -- deterministic mock model, synthetic cases; not an official score",
           "switches": switches, "summaries": {s: summarize(r) for s, r in rows.items()}, "cases": rows}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(out, indent=1) + "\n")
    for s, v in out["summaries"].items():
        if s in HIDE:
            continue
        print(f"{s:20s} acc={v['accuracy']:.3f} crit={v['critical_correct']}/{v['critical']} turns={v['avg_turns']:.1f} "
              f"tests={v['avg_tests']:.1f} unnec={v['unnecessary_tests_per_case']:.2f} dup={v['duplicates']} malformed={v['malformed']}")


def compare(a_path, b_path, exclude=()):
    a, b = json.loads(Path(a_path).read_text()), json.loads(Path(b_path).read_text())
    for suite in b["cases"]:
        if suite in exclude:
            continue
        ra = {r["case_id"]: r for r in a["cases"].get(suite, [])}
        better = [r["case_id"] for r in b["cases"][suite] if r["case_id"] in ra and r["correct"] and not ra[r["case_id"]]["correct"]]
        worse = [(r["case_id"], ra[r["case_id"]]["final"], r["final"]) for r in b["cases"][suite]
                 if r["case_id"] in ra and ra[r["case_id"]]["correct"] and not r["correct"]]
        sa, sb = a["summaries"][suite], b["summaries"][suite]
        print(f"{suite:20s} acc {sa['accuracy']:.3f}->{sb['accuracy']:.3f} crit {sa['critical_correct']}->{sb['critical_correct']}/{sb['critical']} "
              f"turns {sa['avg_turns']:.1f}->{sb['avg_turns']:.1f} tests {sa['avg_tests']:.1f}->{sb['avg_tests']:.1f} "
              f"unnec {sa['unnecessary_tests_per_case']:.2f}->{sb['unnecessary_tests_per_case']:.2f}")
        if better:
            print("   better:", better)
        if worse:
            print("   WORSE:", worse)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output")
    p.add_argument("--compare", nargs=2)
    p.add_argument("--exclude", default="", help="comma-separated suites to hide (e.g. the frozen validation set during development)")
    a = p.parse_args()
    if a.compare:
        compare(*a.compare, exclude=set(filter(None, a.exclude.split(","))))
    else:
        run(a.output)
