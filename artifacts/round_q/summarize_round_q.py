"""Summarise Round Q preliminary-rule runs against the ead1595 baseline (reads saved JSON only; runs nothing)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def rows(path):
    data = json.loads((ROOT / path).read_text())
    cases = data["cases"]
    return {r["case_id"]: r for v in (cases.values() if isinstance(cases, dict) else [cases]) for r in v}


def dangerous(name):
    from nova_agent.knowledge.retrieval import all_diseases
    low = (name or "").lower()
    for e in all_diseases().values():
        names = [e["name"].lower()] + [a.lower() for a in e.get("aliases", [])]
        if any(n and (n == low or n in low) for n in names):
            return bool(e.get("dangerous"))
    return False


def summary(path, base_path=None):
    r = rows(path)
    scored = [x for x in r.values() if x["scored"]]
    crit = [x for x in scored if x["critical"]]
    out = {"top1": f"{sum(x['top1'] for x in scored)}/{len(scored)}",
           "critical_top1": f"{sum(x['top1'] for x in crit)}/{len(crit)}",
           "critical_misses": sorted(x["case_id"] for x in crit if not x["top1"]),
           "avg_interactions": round(sum(x["interactions"] for x in r.values()) / len(r), 2),
           "max_interactions": max(x["interactions"] for x in r.values()),
           "unnecessary_exams": sum(x["unnecessary_exams"] for x in r.values()),
           "semantic_duplicate_questions": sum(x["semantic_duplicate_questions"] for x in r.values()),
           "rule_violations": sum(x["rule_violations"] for x in r.values()),
           "soap_unsupported": sum(x["soap_unsupported"] for x in r.values()),
           "undifferentiated_scored": sum(1 for x in scored if "ndifferentiated" in x["primary"] or "미분화" in x["primary"]),
           "undifferentiated_unscored": sum(1 for x in r.values() if not x["scored"] and ("ndifferentiated" in x["primary"] or "미분화" in x["primary"])),
           "dangerous_named_on_nondangerous_truth": sum(1 for x in scored if not x["critical"] and not x["top1"] and dangerous(x["primary"])),
           "dangerous_named_on_unscored": sum(1 for x in r.values() if not x["scored"] and dangerous(x["primary"])),
           "unresolved_dangerous_alternative_cases": sum(1 for x in r.values() if x["unresolved_critical_at_diagnosis"])}
    if base_path:
        b = rows(base_path)
        out["newly_correct"] = sorted(k for k in r if r[k]["scored"] and r[k]["top1"] and not b[k]["top1"])
        out["newly_wrong"] = sorted(k for k in r if r[k]["scored"] and b[k]["top1"] and not r[k]["top1"])
    return out


if __name__ == "__main__":
    B = "artifacts/round_p/final/"   # ead1595 == runtime 3831555 (v21)
    F = "artifacts/round_q/final/"
    report = {
        "baseline_prelim": summary(B + "prelim.json"),
        "final_prelim": summary(F + "prelim.json", B + "prelim.json"),
        "baseline_prelim_exam_rejection": summary(B + "prelim_exam_rejection.json"),
        "final_prelim_exam_rejection": summary(F + "prelim_exam_rejection.json", B + "prelim_exam_rejection.json"),
        "baseline_prelim_unscripted_unknown": summary("artifacts/round_q/baseline/prelim_unscripted_unknown.json"),
        "final_prelim_unscripted_unknown": summary(F + "prelim_unscripted_unknown.json", "artifacts/round_q/baseline/prelim_unscripted_unknown.json"),
        "ablation_no_answer_grounding": summary(F + "ablation_no_answer_grounding.json", B + "prelim.json"),
        "ablation_no_final_decision": summary(F + "ablation_no_final_decision.json", B + "prelim.json"),
        "baseline_validation_round_p": summary(B + "validation_round_p.json"),
        "final_validation_round_p": summary(F + "validation_round_p.json", B + "validation_round_p.json"),
        "baseline_validation_round_p_exam_rejection": summary(B + "validation_round_p_exam_rejection.json"),
        "final_validation_round_p_exam_rejection": summary(F + "validation_round_p_exam_rejection.json", B + "validation_round_p_exam_rejection.json"),
    }
    for tag, path in (("baseline_dev_round_q", "artifacts/round_q/baseline/base_dev.json"),
                      ("baseline_dev_round_q_unscripted_unknown", "artifacts/round_q/baseline/base_dev_unk.json"),
                      ("final_dev_round_q", F + "dev_round_q.json"),
                      ("final_dev_round_q_exam_rejection", F + "dev_round_q_exam_rejection.json"),
                      ("final_dev_round_q_unscripted_unknown", F + "dev_round_q_unscripted_unknown.json")):
        data = json.loads((ROOT / path).read_text())
        report[tag] = dict(data["summary"], misses=sorted(r["case_id"] + "->" + r["primary_key"] for r in data["cases"]
                                                          if r["scored"] and not r["top1"]),
                           unmet_expectations=sorted(r["case_id"] + "->" + r["primary_key"] for r in data["cases"]
                                                     if not all(r["expectations"].values())))
    reg_b = json.loads((ROOT / B / "test_enabled_regressions.json").read_text())["suites"]
    reg_f = json.loads((ROOT / F / "test_enabled_regressions.json").read_text())["suites"]
    report["test_enabled_regressions"] = {
        name: {"baseline": {k: reg_b[name]["summary"][k] for k in ("scored_diagnostic_accuracy", "critical_diagnosis_recall", "average_turns", "n_scored_cases")},
               "final": {k: reg_f[name]["summary"][k] for k in ("scored_diagnostic_accuracy", "critical_diagnosis_recall", "average_turns", "n_scored_cases")},
               "newly_wrong": sorted(c["case_id"] for c in reg_f[name]["cases"]
                                     if not c["correct"] and next(x for x in reg_b[name]["cases"] if x["case_id"] == c["case_id"])["correct"]),
               "newly_correct": sorted(c["case_id"] for c in reg_f[name]["cases"]
                                       if c["correct"] and not next(x for x in reg_b[name]["cases"] if x["case_id"] == c["case_id"])["correct"])}
        for name in reg_f}
    (ROOT / F / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=1))
