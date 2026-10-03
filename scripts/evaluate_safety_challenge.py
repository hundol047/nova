"""Evaluate source-informed safety snapshots; never use expected labels to construct state."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nova_agent.state import PatientState
from nova_agent.safety import SafetyLayer
from nova_agent.differential import DifferentialEngine


def evaluate(split):
    path = ROOT / 'evaluation/safety_challenge_v1/cases.jsonl'
    manifest = json.loads(path.with_name('manifest.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['sha256']
    rows = [r for r in map(json.loads, path.read_text().splitlines()) if r['split'] == split]
    signatures = [json.dumps({k:r[k] for k in ('chief_complaint','current','history_kind','history')},sort_keys=True) for r in rows]
    assert len(signatures) == len(set(signatures)), 'Exact duplicate inputs'
    matrix = dict(tp=0, fp=0, fn=0, tn=0)
    results = []
    for row in rows:
        state = PatientState(case_id=row['id'],chief_complaint=row['chief_complaint'])
        state.record_ask('associated_symptoms','?',row['current'])
        if row['history_kind']:
            state.record_ask(row['history_kind'],'?',row['history'])
        flags = SafetyLayer().assess(state, DifferentialEngine().update(state))
        predicted = row['target_flag'] in {f.diagnosis_id for f in flags}
        expected = row['expected_target_flag']
        matrix[('tp' if predicted else 'fn') if expected else ('fp' if predicted else 'tn')] += 1
        results.append(dict(id=row['id'],expected=expected,predicted=predicted,
                            flags=[f.diagnosis_id for f in flags]))
    return dict(split=split,cases=len(rows),corpus_sha256=manifest['sha256'],**matrix,
                sensitivity=matrix['tp']/(matrix['tp']+matrix['fn']),
                specificity=matrix['tn']/(matrix['tn']+matrix['fp']),
                scope='SYNTHETIC_TARGET_FLAG_TEST_NOT_DIAGNOSTIC_ACCURACY',results=results)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--split',choices=['development','validation'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=evaluate(args.split)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
