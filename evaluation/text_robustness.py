"""Formatting robustness of reused synthetic cases; not independent validation.

Changes only letter case and comma punctuation, leaving labels, keys, numerical
measurements and clinical content unchanged. Never imported by the agent runtime.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from evaluation.benchmark import run_all, compute_summary
from nova_agent.config import get_config


def formatting_variant(case):
    def convert(text):
        return text.upper().replace(',', ';')
    transformed = case.model_copy(deep=True)
    transformed.case_id += '_format_variant'
    transformed.chief_complaint = convert(case.chief_complaint)
    for attr in ('answers', 'exam_results', 'test_results'):
        setattr(transformed, attr, {key:convert(value) for key,value in getattr(case,attr).items()})
    for attr in ('default_answer','default_exam_result','default_test_result'):
        setattr(transformed, attr, convert(getattr(case,attr)))
    return transformed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save-json', required=True)
    args = parser.parse_args()
    from evaluation.blind_cases_v3 import BLIND_CASES_V3
    from evaluation.blind_cases_v4 import BLIND_CASES_V4
    from evaluation.blind_cases_v5 import BLIND_CASES_V5
    original = os.environ.get('NOVA_LLM_PROVIDER')
    report = {'provider':'mock','role':'formatting perturbations of development cases; not independent',
              'transform':'uppercase text and comma-to-semicolon; all keys/labels/numbers preserved', 'suites':{}}
    try:
        os.environ['NOVA_LLM_PROVIDER']='mock'
        get_config(reload=True)
        for name,cases in [('v3',BLIND_CASES_V3),('v4',BLIND_CASES_V4),('v5',BLIND_CASES_V5)]:
            results=run_all([formatting_variant(case) for case in cases])
            report['suites'][name]={'summary':compute_summary(results),'cases':[r.model_dump() for r in results]}
            Path(args.save_json).write_text(json.dumps(report,indent=2)+'\n')
            print(name, report['suites'][name]['summary']['all_case_diagnostic_accuracy'],flush=True)
    finally:
        if original is None:os.environ.pop('NOVA_LLM_PROVIDER',None)
        else:os.environ['NOVA_LLM_PROVIDER']=original
        get_config(reload=True)

if __name__=='__main__': main()
