#!/usr/bin/env python3
"""Preliminary-ONLY development benchmark: LOCAL DEVELOPMENT / PRELIMINARY SIMULATION, NOT AN OFFICIAL SCORE.

Every case runs through ``competition.adapter.NovaCompetitionAgent(preliminary=True)`` -- the adapter path
the submission will use -- with SAY / EXAM / DIAGNOSE only (TEST is a recorded rule violation). The model is
the deterministic MOCK (never the fixed competition model); cases are synthetic development vignettes; no
blind / reference-only module may be loaded. Historical results that used TEST actions are NOT comparable.

    python scripts/evaluate_preliminary_benchmark.py --output artifacts/preliminary_benchmark/latest.json
    python scripts/evaluate_preliminary_benchmark.py --suites ko_new --exam-rejection   # recovery scenario
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluation.preliminary_driver import LABEL, Environment, ORGANIZER_ASSUMPTIONS, run_episode, summarize  # noqa: E402

SUITES = {
    "ko_new": ("evaluation.preliminary_dev_cases", "PRELIM_KO_CASES"),
    "dev_round_m": ("evaluation.generalization_dev_cases_round_m", "ROUND_M_CASES"),
    "dev_round_j": ("evaluation.generalization_dev_cases_round_j", "ROUND_J_CASES"),
    "dev_round_i": ("evaluation.generalization_dev_cases_round_i", "ROUND_I_CASES"),
    "tuning": ("evaluation.cases", "CASES"),
}
# ASSUMED unsupported maneuvers for the recovery scenario only. NOT the organizer's list (unpublished).
ASSUMED_UNSUPPORTED = frozenset({"meningeal_signs", "costovertebral_tenderness", "pelvic_exam", "extremity_exam"})


# Deterministic SAFETY / RULE gates (zero tolerance) and conservative accuracy floors set below the values measured
# on this mock-LLM development simulation. They catch regressions; they are not performance claims.
HARD_GATES = {"rule_violations": 0, "malformed_output_rate": 0.0, "soap_unsupported_info_rate": 0.0, "cases_over_cap": 0}
FLOORS = {"soap_information_retention": 1.0, "soap_completeness": 1.0, "explained_before_diagnose_rate": 1.0}
SUITE_FLOORS = {"ko_new": {"top1": 0.85, "critical_recall": 0.75}, "ALL": {"critical_recall": 0.80}}


def check_gates(summaries: dict, hard_only: bool = False) -> list:
    failures = []
    for name, s in summaries.items():
        for key, limit in HARD_GATES.items():
            if s[key] > limit:
                failures.append(f"{name}: {key}={s[key]} > {limit}")
        if hard_only:
            continue
        for key, limit in FLOORS.items():
            if s[key] < limit:
                failures.append(f"{name}: {key}={s[key]} < {limit}")
        for key, limit in SUITE_FLOORS.get(name, {}).items():
            if s[key] is not None and s[key] < limit:
                failures.append(f"{name}: {key}={s[key]:.3f} < floor {limit}")
    return failures


def _load(suite: str):
    if "blind" in suite or "blind" in SUITES.get(suite, ("",))[0]:
        raise SystemExit("refusing to evaluate a blind / reference-only module")
    module, var = SUITES[suite]
    return getattr(importlib.import_module(module), var)


def _one(args):
    suite, index, rejection = args
    case = _load(suite)[index]
    env = Environment(unsupported_exams=ASSUMED_UNSUPPORTED if rejection else frozenset())
    return suite, run_episode(case, env=env).result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--suites", default=",".join(SUITES))
    p.add_argument("--exam-rejection", action="store_true", help="simulate rejection of an ASSUMED unsupported-exam set")
    p.add_argument("--gate", action="store_true", help="exit 1 when a rule/safety gate or accuracy floor is violated")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--output")
    args = p.parse_args()
    names = [s for s in args.suites.split(",") if s]
    jobs = [(s, i, args.exam_rejection) for s in names for i in range(len(_load(s)))]
    by_suite = {s: [] for s in names}
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for suite, row in pool.map(_one, jobs, chunksize=2):
            by_suite[suite].append(row)
    summaries = {s: summarize(rows) for s, rows in by_suite.items()}
    summaries["ALL"] = summarize([r for rows in by_suite.values() for r in rows])
    out = {"label": LABEL, "model": "deterministic MOCK (not the fixed competition model)",
           "organizer_assumptions": {k: {"value": v[0], "status": v[1]} for k, v in ORGANIZER_ASSUMPTIONS.items()},
           "exam_rejection_scenario": bool(args.exam_rejection),
           "assumed_unsupported_exams": sorted(ASSUMED_UNSUPPORTED) if args.exam_rejection else [],
           "summaries": summaries}
    print(LABEL)
    for name, s in summaries.items():
        keys = ("cases", "top1", "top3", "top5", "critical_recall", "avg_interactions", "median_interactions",
                "soap_unsupported_info_rate", "soap_information_retention", "rule_violations", "unresolved_critical_alternative_rate")
        print(f"{name:12s} " + "  ".join(f"{k}={s[k]:.3f}" if isinstance(s.get(k), float) else f"{k}={s.get(k)}" for k in keys))
    failures = check_gates(summaries, hard_only=args.exam_rejection) if args.gate else []
    out["gate_failures"] = failures
    for failure in failures:
        print("GATE FAIL:", failure, file=sys.stderr)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**out, "cases": by_suite}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
