#!/usr/bin/env python3
"""Round W diagnostic: which EXAM requests the preliminary benchmark counts as "unnecessary", and for which
candidate the agent requested each one. The metric (evaluation.preliminary_driver._unnecessary_exams) is NOT
changed; this only re-runs the same episodes and attributes each counted exam.

    python scripts/audit_unnecessary_exams.py --output artifacts/round_w/unnecessary_exam_audit.json
"""
import argparse
import collections
import concurrent.futures
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('NOVA_LLM_PROVIDER', 'mock')
os.environ.setdefault('NOVA_COMPETITION_RETRIEVAL', '1')


def _one(args):
    suite, index = args
    from scripts.evaluate_preliminary_benchmark import _load
    from evaluation import preliminary_driver as pd
    from nova_agent.knowledge.retrieval import disease_by_id
    from nova_agent import missing_info as mi
    case = _load(suite)[index]
    requested_for, seen = {}, {}
    orig_analyze, orig_metric = mi.MissingInformationAnalyzer.analyze, pd._unnecessary_exams

    def analyze(self, *a, **kw):
        out = orig_analyze(self, *a, **kw)
        for c in out:
            if c.action_type == 'EXAM':
                requested_for[c.key] = list(c.disease_ids_discriminated or [])[:4]
        return out

    def metric(case_, ep_, differential):
        seen['top5'] = [d.diagnosis_id for d in (differential or [])[:5]]
        return orig_metric(case_, ep_, differential)
    mi.MissingInformationAnalyzer.analyze, pd._unnecessary_exams = analyze, metric
    try:
        ep = pd.run_episode(case, env=pd.Environment())
    finally:
        mi.MissingInformationAnalyzer.analyze, pd._unnecessary_exams = orig_analyze, orig_metric
    useful = {"vital_signs", "general_appearance"}
    for did in [case.ground_truth_diagnosis] + seen.get('top5', []):
        entry = disease_by_id(did)
        if entry:
            useful.update(entry.get("discriminating_exams", []))
    asked = [w["metadata"].get("key") for w in ep.wire if w["action_type"] == "EXAM"]
    return dict(case_id=case.case_id, counted=ep.result['unnecessary_exams'], top5=seen.get('top5', []),
                unnecessary=[dict(exam=k, requested_for=requested_for.get(k, [])) for k in asked if k not in useful])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--workers', type=int, default=4)
    a = p.parse_args()
    from scripts.evaluate_preliminary_benchmark import SUITES, _load
    jobs = [(s, i) for s in SUITES for i in range(len(_load(s)))]
    with concurrent.futures.ProcessPoolExecutor(a.workers) as ex:
        rows = list(ex.map(_one, jobs))
    by_requester = collections.Counter()
    for r in rows:
        for u in r['unnecessary']:
            for did in u['requested_for'] or ['<not from analyzer>']:
                by_requester[f"{u['exam']} <- {did}"] += 1
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(dict(rows=rows, total_counted=sum(r['counted'] for r in rows),
                                              top_requesters=by_requester.most_common(60)), indent=1) + '\n')
    print('counted unnecessary', sum(r['counted'] for r in rows))
    print(json.dumps(by_requester.most_common(25)))


if __name__ == '__main__':
    main()
