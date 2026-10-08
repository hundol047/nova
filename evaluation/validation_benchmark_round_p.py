"""`python evaluation/validation_benchmark_round_p.py` -- Round P frozen validation set under the PRELIMINARY rules
(SAY / EXAM / DIAGNOSE, competition retrieval, mock LLM). Pass --exam-rejection to run the assumed-unsupported-exam
scenario. LOCAL DEVELOPMENT / PRELIMINARY SIMULATION -- not an official score."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NOVA_COMPETITION_RETRIEVAL", "1")

from evaluation.preliminary_driver import Environment, LABEL, run_episode, summarize  # noqa: E402
from evaluation.validation_cases_round_p import VALIDATION_CASES_ROUND_P  # noqa: E402

ASSUMED_UNSUPPORTED = frozenset({"meningeal_signs", "costovertebral_tenderness", "pelvic_exam", "extremity_exam"})

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--exam-rejection", action="store_true")
    p.add_argument("--output")
    args = p.parse_args()
    env = Environment(unsupported_exams=ASSUMED_UNSUPPORTED) if args.exam_rejection else Environment()
    rows = [run_episode(c, env=env).result for c in VALIDATION_CASES_ROUND_P]
    print(LABEL)
    print("Round P frozen validation set" + (" (EXAM-rejection scenario)" if args.exam_rejection else ""))
    for r in rows:
        print(f"{r['case_id']:8s} {r['category']:38s} truth={r['truth']:28s} top1={'YES' if r['top1'] else 'NO ':3s} "
              f"interactions={r['interactions']:2d} critical_miss={'YES' if r['critical_miss'] else 'NO'}")
    print(json.dumps(summarize(rows), ensure_ascii=False, indent=1, default=str))
    if args.output:
        Path(args.output).write_text(json.dumps({"label": LABEL, "exam_rejection": args.exam_rejection, "cases": rows},
                                                ensure_ascii=False, indent=1, default=str) + "\n")
