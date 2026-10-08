"""`python evaluation/dev_benchmark_round_q.py` -- Round Q contrast DEVELOPMENT set under the PRELIMINARY rules
(SAY / EXAM / DIAGNOSE, competition retrieval, mock LLM). Not an evaluation: see evaluation/dev_cases_round_q.py.

Reports separately: scored Top-1 and critical Top-1 (existing same_diagnosis matcher, unchanged); expected-behaviour
checks of the unscored cases; dangerous diagnoses NAMED as primary on unscored (insufficient) information; the
number of undifferentiated completions; interactions. --exam-rejection runs the assumed-unsupported-exam scenario;
--unscripted-unknown runs the separate evaluation-tool variant. LOCAL DEVELOPMENT SIMULATION -- not an official score."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")

from evaluation.dev_cases_round_q import DEV_CASES_ROUND_Q  # noqa: E402
from evaluation.preliminary_driver import Environment, LABEL, run_episode, summarize  # noqa: E402

ASSUMED_UNSUPPORTED = frozenset({"meningeal_signs", "costovertebral_tenderness", "pelvic_exam", "extremity_exam"})


def _dangerous(key: str) -> bool:
    from nova_agent.differential import _entry_for_candidate_id
    entry = _entry_for_candidate_id(key) if key and key != "unknown" else None
    return bool(entry and entry.get("dangerous"))


def _expectations(category: str):
    return [part.split(":", 1)[1] for part in category.split(";") if part.startswith("expect:")]


def _check(expectation: str, key: str) -> bool:
    if expectation == "no_dangerous_named":
        return not _dangerous(key)
    if expectation.startswith("not:"):
        return key != expectation[len("not:"):]
    raise ValueError(expectation)


def run(env: Environment):
    rows = []
    for case in DEV_CASES_ROUND_Q:
        ep = run_episode(case, env=env)
        final = ep.wire[-1]
        md = final.get("metadata") or {}
        key = md.get("key", "")
        row = dict(ep.result)
        row.update(primary_key=key, final_decision=md.get("final_decision"),
                   named_dangerous=_dangerous(key), undifferentiated=key == "unknown",
                   expectations={e: _check(e, key) for e in _expectations(case.category)})
        rows.append(row)
    return rows


def report(rows):
    scored = [r for r in rows if r["scored"]]
    critical = [r for r in scored if r["critical"]]
    unscored = [r for r in rows if not r["scored"]]
    checks = [ok for r in unscored for ok in r["expectations"].values()]
    return {
        "scored_top1": f"{sum(r['top1'] for r in scored)}/{len(scored)}",
        "critical_top1": f"{sum(r['top1'] for r in critical)}/{len(critical)}",
        "scored_undifferentiated": sum(r["undifferentiated"] for r in scored),
        "unscored_expectations_met": f"{sum(checks)}/{len(checks)}",
        "unscored_dangerous_named": sum(r["named_dangerous"] for r in unscored),
        "unscored_undifferentiated": f"{sum(r['undifferentiated'] for r in unscored)}/{len(unscored)}",
        "avg_interactions": round(sum(r["interactions"] for r in rows) / len(rows), 2),
        "max_interactions": max(r["interactions"] for r in rows),
        "rule_violations": sum(r["rule_violations"] for r in rows),
        "soap_unsupported": sum(r["soap_unsupported"] for r in rows),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--exam-rejection", action="store_true")
    p.add_argument("--unscripted-unknown", action="store_true")
    p.add_argument("--output")
    args = p.parse_args()
    env = Environment(unsupported_exams=ASSUMED_UNSUPPORTED if args.exam_rejection else frozenset(),
                      unscripted_unknown=args.unscripted_unknown)
    rows = run(env)
    print(LABEL)
    print("Round Q contrast DEVELOPMENT set" + (" (EXAM-rejection)" if args.exam_rejection else "")
          + (" (unscripted-unknown variant)" if args.unscripted_unknown else ""))
    for r in rows:
        print(f"{r['case_id']:8s} {r['category'][:48]:48s} truth={r['truth']:26s} -> {r['primary_key'][:34]:34s} "
              f"top1={'YES' if r['top1'] else 'NO ':3s} I={r['interactions']:2d} {r['expectations'] or ''}")
    summary = report(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summarize(rows), ensure_ascii=False, indent=1, default=str))
    if args.output:
        Path(args.output).write_text(json.dumps({"label": LABEL, "exam_rejection": args.exam_rejection,
                                                 "unscripted_unknown": args.unscripted_unknown, "summary": summary,
                                                 "cases": rows}, ensure_ascii=False, indent=1, default=str) + "\n")
