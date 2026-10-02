"""Reproducible accuracy/ablation report. No case data is imported by the agent.

V5 is development data. V4 is development data after follow-up error analysis. V6 is same-author synthetic
validation, not external/clinically adjudicated evidence. All metrics retain these labels.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from evaluation.benchmark import run_all, compute_summary
from nova_agent.config import get_config

FLAGS = {'broad_candidates':'NOVA_BROAD_CANDIDATES', 'evidence_interpretation':'NOVA_EVIDENCE_INTERPRETATION',
         'strategic_questions':'NOVA_STRATEGIC_QUESTIONS', 'final_review':'NOVA_FINAL_REVIEW'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite',choices=['v4','v5','v6'],default='v5')
    parser.add_argument('--ablate',action='store_true')
    parser.add_argument('--save-json',required=True)
    args=parser.parse_args()
    if args.suite=='v4':
        from evaluation.blind_cases_v4 import BLIND_CASES_V4 as cases
        role='development; V4 errors analyzed during follow-up fixes'
    elif args.suite=='v5':
        from evaluation.blind_cases_v5 import BLIND_CASES_V5 as cases
        role='development; analyzed during fixes, not blind'
    else:
        from evaluation.validation_v6 import VALIDATION_V6 as cases
        role='reused same-author synthetic validation; not independent clinical validation'
        directory=Path(__file__).parent
        expected=json.loads((directory/'validation_v6_manifest.json').read_text())['sha256']
        if hashlib.sha256((directory/'validation_v6.py').read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Frozen validation V6 was modified')
        if args.ablate:
            parser.error('Ablations belong on development V5, not frozen validation V6')
    original={key:os.environ.get(key) for key in [*FLAGS.values(),'NOVA_LLM_PROVIDER']}
    reports={}
    try:
        os.environ['NOVA_LLM_PROVIDER']='mock'
        configurations=['full']+list(FLAGS) if args.ablate else ['full']
        for omitted in configurations:
            for name,key in FLAGS.items():os.environ[key]='false' if name==omitted else 'true'
            get_config(reload=True)
            results=run_all(cases)
            label='full' if omitted=='full' else 'without_'+omitted
            reports[label]={'summary':compute_summary(results),'cases':[r.model_dump() for r in results]}
            print(label, reports[label]['summary']['all_case_diagnostic_accuracy'],flush=True)
            Path(args.save_json).write_text(json.dumps({'suite':args.suite,'role':role,'provider':'mock',
                'live_model_verified':False,'experiments':reports},indent=2)+'\n')
    finally:
        for key,value in original.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
        get_config(reload=True)

if __name__=='__main__':main()
