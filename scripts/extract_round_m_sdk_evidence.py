"""Bind the 128 Round M cases already executed in the full SDK regression.

This is a lossless subset of captured encounters, not a new evaluation or a
replay. It replaces redundant legacy TEST-enabled candidate-stage tracing for
this interaction-only release. Its SDK metrics are not comparable to the old
Round M trace metrics; the reference labels and scored denominator stay fixed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from scripts.evaluate_clinical_quality import summary


def extract(source, output, runtime):
    source=Path(source);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    captured=json.loads(source.read_text())
    expected={c.case_id:c for c in ROUND_M_CASES}
    rows=[dict(r,case_id=r['base_id'],correct=r['top1'],truth=expected[r['base_id']].ground_truth_diagnosis)
          for r in captured['cases'] if r['base_id'] in expected and r['mode']=='complete']
    assert len(rows)==len(expected)==128
    assert {r['case_id'] for r in rows}==set(expected)
    assert sum(r['scored'] for r in rows)==123
    assert captured['runtime_unchanged_during_execution']
    result={'schema':'round-m-official-sdk-captured-subset-v37',
            'runtime_sha':runtime,'runtime_sha256':captured['runtime_sha256'],
            'label':'LOCAL SDK REGRESSION / SCRIPTED PATIENT AND DOCTOR / NOT OFFICIAL SCORE',
            'source_artifact_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_artifact':str(source),'execution_path':'OfficialEncounter; SAY/EXAM/DIAGNOSE only',
            'legacy_round_m_trace_comparable':False,'candidate_stage_traces':'NOT MEASURED',
            'metrics':summary(rows),'cases':rows}
    failures={'definition':'Final SDK diagnosis differs from the unchanged development label; no causal stage attribution.',
              'failures':[{'case_id':r['case_id'],'truth':r['truth'],'prediction':r['primary']}
                          for r in rows if r['scored'] and not r['correct']]}
    for name,data in [('round_m_final_summary.json',result),('round_m_failure_analysis.json',failures)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    return result['metrics']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--runtime',required=True);a=p.parse_args()
    print(json.dumps(extract(a.source,a.output,a.runtime),ensure_ascii=False))
