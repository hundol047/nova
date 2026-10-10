#!/usr/bin/env python3
"""Post-Round-W generalisation audit over every development case (preliminary suites + frozen fixtures + the
post-W counterfactual set): one replay per case under the preliminary rules (mock LLM, competition retrieval,
no TEST), capturing the final differential. The truth label is read only AFTER the episode to locate it.

Produces, in one JSON: per-case rows; same-condition consistency (grouped by ground truth); age strata; critical
false negatives with a first-guess stage classification; dangerous-candidate over-activation on benign cases;
ranking-margin split (near vs deep); interaction buckets; confidence-calibration view.

    python scripts/post_round_w_analysis.py --output artifacts/post_round_w/analysis.json
"""
import argparse
import collections
import concurrent.futures
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NOVA_LLM_PROVIDER', 'mock')
os.environ.setdefault('NOVA_COMPETITION_RETRIEVAL', '1')

NEAR_MISS_RATIO = 0.85  # truth score >= 85% of the predicted leader's score


def _jobs(extra_json):
    from scripts.evaluate_preliminary_benchmark import SUITES, _load
    jobs = [("prelim:" + s, s, i, None) for s in SUITES for i in range(len(_load(s)))]
    paths = sorted(p for p in (ROOT / "evaluation").glob("frozen_validation_round_*.json") if not p.name.endswith("_manifest.json"))
    paths += [Path(p) for p in extra_json]
    for path in paths:
        rows = json.loads(path.read_text())
        if not isinstance(rows, list) or not rows or "case_id" not in rows[0]:
            continue  # notes / usage records, not case lists
        jobs += [("fixture:" + path.stem, str(path), i, None) for i in range(len(rows))]
    return jobs


def _case(source, index):
    if source.endswith(".json"):
        from evaluation.cases import SyntheticCase
        raw = json.loads(Path(source).read_text())[index]
        reject = raw.get("audit_rejected_exams", [])
        raw = {k: v for k, v in raw.items() if k not in ("audit_expect", "round_s_expect", "audit_rejected_exams")}
        return SyntheticCase(**raw), reject
    from scripts.evaluate_preliminary_benchmark import _load
    return _load(source)[index], []


def _one(job):
    group, source, index, _ = job
    from evaluation import preliminary_driver as pd
    from nova_agent.diagnosis_normalizer import same_diagnosis
    from nova_agent.final_decision import support_problems
    from nova_agent.resolution import is_resolved
    case, reject = _case(source, index)
    seen = {}
    orig = pd._unresolved_critical

    def capture(differential, state):
        seen['diff'], seen['state'] = differential, state
        return orig(differential, state)
    pd._unresolved_critical = capture
    try:
        ep = pd.run_episode(case, env=pd.Environment(unsupported_exams=frozenset(reject)))
    finally:
        pd._unresolved_critical = orig
    diff, state = seen.get('diff') or [], seen.get('state')
    truth = case.ground_truth_diagnosis
    truth_idx = next((i for i, d in enumerate(diff) if same_diagnosis(d.diagnosis_id, truth) or same_diagnosis(d.diagnosis, truth)), None)
    md = ep.wire[-1].get("metadata") or {}
    fd = md.get("final_decision") or {}
    dangerous_active = [d for d in diff[:5] if d.dangerous_if_missed and d.score > 0
                        and any(not p.startswith("no ") for p in d.supporting_evidence)]
    unresolved = [d.diagnosis_id for d in dangerous_active
                  if state is not None and not is_resolved(d.diagnosis_id, list(d.contradictory_evidence), state)]
    leader = diff[0] if diff else None
    r = ep.result
    return dict(
        group=group, case_id=case.case_id, truth=truth, scored=case.scoring_expected, critical=bool(case.critical),
        age=(case.demographics or {}).get("age"), sex=(case.demographics or {}).get("sex"), language=r.get("language"),
        primary=r.get("primary"), primary_key=md.get("key"), top1=bool(r.get("top1")), top3=bool(r.get("top3")),
        top5=bool(r.get("top5")), truth_rank=(truth_idx + 1) if truth_idx is not None else None,
        leader_id=leader.diagnosis_id if leader else None, leader_score=round(leader.score, 3) if leader else None,
        second_score=round(diff[1].score, 3) if len(diff) > 1 else None,
        truth_score=round(diff[truth_idx].score, 3) if truth_idx is not None else None,
        truth_support=list(diff[truth_idx].supporting_evidence) if truth_idx is not None else None,
        truth_against=list(diff[truth_idx].contradictory_evidence) if truth_idx is not None else None,
        truth_problems=support_problems(diff[truth_idx], state, diff) if (truth_idx is not None and state is not None) else None,
        leader_support=list(leader.supporting_evidence) if leader else None,
        leader_confidence=getattr(leader, "confidence_band", None) if leader else None,
        decision_support=fd.get("support"), completion_reason=fd.get("completion_reason"),
        interactions=r.get("interactions"), says=r.get("says"), exams=r.get("exams"),
        unnecessary_exams=r.get("unnecessary_exams"), premature=r.get("premature"),
        dangerous_active=[d.diagnosis_id for d in dangerous_active], dangerous_unresolved=unresolved,
        urgent=bool((md.get("disposition") or {}).get("urgent")),
        soap_unsupported=r.get("soap_unsupported"), soap_retention=r.get("soap_retention"))


def _age_band(age):
    if age is None:
        return "unknown"
    return ("infant(<1)" if age < 1 else "child(1-11)" if age < 12 else "adolescent(12-17)" if age < 18 else
            "young adult(18-39)" if age < 40 else "middle-aged(40-64)" if age < 65 else "elderly(65+)")


def _rate(rows, key):
    return round(sum(bool(r[key]) for r in rows) / len(rows), 3) if rows else None


def analyse(rows):
    scored = [r for r in rows if r["scored"]]
    # same-condition consistency
    by_truth = collections.defaultdict(list)
    for r in scored:
        by_truth[r["truth"].lower()].append(r)
    conditions = []
    for truth, rs in by_truth.items():
        if len(rs) < 2:
            continue
        ranks = [r["truth_rank"] or 99 for r in rs]
        conditions.append(dict(truth=truth, presentations=len(rs), top1=_rate(rs, "top1"),
                               min_presentation_top1=min(int(r["top1"]) for r in rs),
                               mean_truth_rank=round(statistics.mean(ranks), 2), worst_truth_rank=max(ranks),
                               avg_interactions=round(statistics.mean(r["interactions"] for r in rs), 2),
                               critical_miss_rate=_rate([r for r in rs if r["critical"]], "top1") and
                               round(1 - _rate([r for r in rs if r["critical"]], "top1"), 3),
                               failing=[r["case_id"] for r in rs if not r["top1"]]))
    inconsistent = sorted((c for c in conditions if 0 < (c["top1"] or 0) < 1), key=lambda c: c["top1"])
    # age strata
    strata = collections.defaultdict(list)
    for r in scored:
        strata[_age_band(r["age"])].append(r)
    age = {band: dict(cases=len(rs), top1=_rate(rs, "top1"), critical_cases=sum(r["critical"] for r in rs),
                      critical_recall=_rate([r for r in rs if r["critical"]], "top1"),
                      avg_interactions=round(statistics.mean(r["interactions"] for r in rs), 2))
           for band, rs in sorted(strata.items())}
    # critical false negatives
    crit_fn = []
    for r in rows:
        if not (r["critical"] and r["scored"] and not r["top1"]):
            continue
        if r["truth_rank"] is None:
            cls = "A/B: candidate not in final differential (never generated or trimmed)"
        elif r["truth_problems"]:
            cls = "naming blocked by support problems: " + ", ".join(r["truth_problems"])
        elif r["truth_against"]:
            cls = "G: contradiction weighed against truth (" + ", ".join(r["truth_against"][:3]) + ")"
        elif r["truth_rank"] > 1:
            cls = "J: ranked below another candidate (rank %s)" % r["truth_rank"]
        else:
            cls = "other"
        crit_fn.append(dict(case_id=r["case_id"], group=r["group"], truth=r["truth"], predicted=r["primary_key"],
                            truth_rank=r["truth_rank"], truth_score=r["truth_score"], leader_score=r["leader_score"],
                            truth_support=r["truth_support"], truth_against=r["truth_against"], classification=cls,
                            interactions=r["interactions"], completion=r["completion_reason"]))
    # dangerous over-activation on benign scored cases
    benign = [r for r in scored if not r["critical"]]
    fp = dict(benign_cases=len(benign),
              mean_dangerous_active=round(statistics.mean(len(r["dangerous_active"]) for r in benign), 3) if benign else None,
              mean_dangerous_unresolved=round(statistics.mean(len(r["dangerous_unresolved"]) for r in benign), 3) if benign else None,
              urgent_plan_rate=_rate(benign, "urgent"),
              interactions_benign_with_unresolved=round(statistics.mean([r["interactions"] for r in benign if r["dangerous_unresolved"]] or [0]), 2),
              interactions_benign_without=round(statistics.mean([r["interactions"] for r in benign if not r["dangerous_unresolved"]] or [0]), 2),
              most_activated=collections.Counter(d for r in benign for d in r["dangerous_active"]).most_common(10))
    # ranking margins
    wrong_in_top5 = [r for r in scored if not r["top1"] and r["truth_rank"] and r["truth_rank"] <= 5 and r["leader_score"]]
    margins = [dict(case_id=r["case_id"], truth=r["truth"], predicted=r["leader_id"], truth_rank=r["truth_rank"],
                    ratio=round((r["truth_score"] or 0) / r["leader_score"], 3),
                    kind="NEAR-MISS" if (r["truth_score"] or 0) >= NEAR_MISS_RATIO * r["leader_score"] else "DEEP")
               for r in wrong_in_top5]
    # interaction buckets
    def bucket(n):
        return "<=10" if n <= 10 else "11-15" if n <= 15 else "16-20" if n <= 20 else "21-30" if n <= 30 else ">30"
    buckets = collections.defaultdict(list)
    for r in scored:
        buckets[bucket(r["interactions"])].append(r)
    stop = {b: dict(cases=len(rs), top1=_rate(rs, "top1")) for b, rs in buckets.items()}
    # confidence calibration
    by_band = collections.defaultdict(list)
    for r in scored:
        by_band[(r["decision_support"] or "?", r["leader_confidence"] or "?")].append(r)
    calibration = {f"{s}/{c}": dict(cases=len(rs), top1=_rate(rs, "top1")) for (s, c), rs in sorted(by_band.items())}
    close = [r for r in scored if r["leader_score"] and r["second_score"] is not None and r["second_score"] >= 0.9 * r["leader_score"]]
    return dict(
        totals=dict(cases=len(rows), scored=len(scored), top1=_rate(scored, "top1"),
                    critical_recall=_rate([r for r in scored if r["critical"]], "top1"),
                    critical_misses=len(crit_fn)),
        same_condition=dict(conditions_with_multiple_presentations=len(conditions),
                            consistent=sum(1 for c in conditions if c["top1"] in (0.0, 1.0) and c["top1"] == 1.0),
                            inconsistent=inconsistent, all_wrong=[c for c in conditions if c["top1"] == 0.0],
                            worst=min(conditions, key=lambda c: (c["top1"], -c["presentations"])) if conditions else None),
        age_strata=age, critical_false_negatives=crit_fn, dangerous_overactivation=fp,
        ranking_margins=dict(near_miss=sum(m["kind"] == "NEAR-MISS" for m in margins),
                             deep=sum(m["kind"] == "DEEP" for m in margins),
                             not_in_top5=sum(1 for r in scored if not r["top1"] and not (r["truth_rank"] and r["truth_rank"] <= 5)),
                             cases=margins),
        interaction_buckets=stop,
        confidence=dict(by_decision_and_band=calibration,
                        close_top2_cases=len(close), close_top2_top1=_rate(close, "top1"),
                        close_top2_named_supported=sum(1 for r in close if r["decision_support"] == "SUPPORTED")),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--extra-json", action="append", default=[])
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    jobs = _jobs(a.extra_json)
    with concurrent.futures.ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_one, jobs))
    result = dict(label="LOCAL DEVELOPMENT / PRELIMINARY SIMULATION -- mock LLM, synthetic cases, NOT AN OFFICIAL SCORE",
                  **analyse(rows), rows=rows)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str) + "\n")
    print(json.dumps({k: result[k] for k in ("totals",)}, indent=1))
    print("critical FN:", [(c["case_id"], c["classification"][:40]) for c in result["critical_false_negatives"]])
    print("inconsistent conditions:", [(c["truth"], c["top1"], c["failing"]) for c in result["same_condition"]["inconsistent"]])


if __name__ == "__main__":
    main()
