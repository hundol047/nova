"""Compare all reported metrics and patient outcomes without changing denominators."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/clinical_review_pass"


def load(path):
    return json.loads(path.read_text())


def metric_delta(before, after):
    rows = {}
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if isinstance(a, dict) and isinstance(b, dict):
            rows[key] = metric_delta(a, b)
        else:
            rows[key] = {"before": a, "after": b,
                         "delta": b - a if type(a) in (int, float) and type(b) in (int, float) else None}
    return rows


def changed_cases(before, after, fields):
    left = {r["case_id"]: r for r in before}
    right = {r["case_id"]: r for r in after}
    assert left.keys() == right.keys(), "Case selection changed"
    rows = []
    for key in left:
        a, b = left[key], right[key]
        differences = {f: {"before": a.get(f), "after": b.get(f)} for f in fields if a.get(f) != b.get(f)}
        if differences:
            rows.append({"case_id": key, "changes": differences})
    return rows


def main():
    baseline = load(OUT / "baseline_round_m.json")
    final = load(OUT / "final_summary.json")
    assert baseline["round_m_case_file_sha256"] == final["round_m_case_file_sha256"]
    b = {r["case_id"]: r for r in baseline["cases"]}
    assert all((r["scored"], r["critical"], r["truth"]) ==
               (b[r["case_id"]]["scored"], b[r["case_id"]]["critical"], b[r["case_id"]]["truth"]) for r in final["cases"])
    report = {"mode": "SYNTHETIC DEVELOPMENT / MOCK LLM; no real-model or clinical validation",
              "baseline_source": "Retained, previously executed v14 evidence; not a newly rerun baseline",
              "round_m": metric_delta(baseline["metrics"], final["metrics"]),
              "round_m_case_changes": changed_cases(baseline["cases"], final["cases"],
                  ["final", "correct", "final_rank", "turns", "tests", "asks", "exams", "primary_failure", "final_retrieval_at150", "final_rerank_at25"]),
              "regressions": {}}
    old, new = load(OUT / "baseline_regressions.json"), load(OUT / "regressions.json")
    assert old["suites"].keys() == new["suites"].keys()
    for name, row in new["suites"].items():
        before = old["suites"][name]
        report["regressions"][name] = {
            "metrics": metric_delta(before["summary"], row["summary"]),
            "case_changes": changed_cases(before["cases"], row["cases"],
                ["scoring_expected", "ground_truth", "critical", "correct", "final_diagnosis", "turns", "ask_count", "exam_count", "test_count", "critical_miss"])}
        old_cases = {r["case_id"]: r for r in before["cases"]}
        assert all(all(r[k] == old_cases[r["case_id"]][k] for k in ("scoring_expected", "ground_truth", "critical")) for r in row["cases"])
    report["unchanged_case_selection_labels_and_scoring"] = True
    (OUT / "performance_comparison.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
