"""External JSON case loading and pre-evaluation freezing. Never imported at inference.

A hash proves unchanged bytes, not independent authorship or medical correctness.
Missing scripted results default to unknown, not fabricated normal/negative results.
"""
import argparse
import hashlib
import json
from pathlib import Path
from evaluation.cases import SyntheticCase
from nova_agent.taxonomy import QUESTION_CATALOG, EXAM_CATALOG, TEST_CATALOG


def read_cases(path):
    raw=Path(path).read_bytes()
    bundle=json.loads(raw)
    if not isinstance(bundle,dict) or not isinstance(bundle.get('cases'),list) or not bundle['cases']:
        raise ValueError('Expected nonempty cases list and provenance metadata')
    if not all(isinstance(bundle.get(key), str) and bundle[key].strip()
               for key in ('author', 'provenance')):
        raise ValueError('author and provenance are required; these are declarations, not verified credentials')
    cases=[]
    seen=set()
    for data in bundle['cases']:
        if not isinstance(data, dict):
            raise ValueError('Each case must be a JSON object')
        data=dict(data)
        if set(data)-set(SyntheticCase.model_fields):raise ValueError("Unknown case fields")
        for key in ('case_id', 'chief_complaint', 'ground_truth_diagnosis'):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError('Nonempty string required: '+key)
        for key in ('critical_override', 'scoring_expected'):
            if key in data and type(data[key]) is not bool:
                raise ValueError('Explicit JSON boolean required: '+key)
        for key in ('acceptable_diagnoses', 'coexisting_diagnoses'):
            values = data.get(key, [])
            if not isinstance(values, list) or not all(isinstance(v, str) and v.strip() for v in values):
                raise ValueError('Nonempty diagnosis strings required: '+key)
        from nova_agent.knowledge.retrieval import disease_by_id
        if disease_by_id(data.get("ground_truth_diagnosis", "")) is None and "critical_override" not in data:
            raise ValueError("Out-of-catalog cases require an explicit critical_override")
        for key in ['default_answer','default_exam_result','default_test_result']:
            data.setdefault(key,'Unknown / not provided.')
        case=SyntheticCase.model_validate(data)
        if case.case_id.strip() in seen:raise ValueError('Duplicate case_id')
        seen.add(case.case_id.strip())
        if set(case.relevant_test_ids)-set(TEST_CATALOG):
            raise ValueError('Unknown action key in relevant_test_ids')
        for name,legal in [('answers',QUESTION_CATALOG),('exam_results',EXAM_CATALOG),('test_results',TEST_CATALOG)]:
            if set(getattr(case,name))-set(legal):raise ValueError('Unknown action key in '+name)
        cases.append(case)
    return cases, {'sha256':hashlib.sha256(raw).hexdigest(),'n_cases':len(cases),
        'author_declared':bundle['author'],'provenance_declared':bundle['provenance'],
        'independence_verified':False,'clinician_review_verified':False}


def load_frozen_cases(path,manifest):
    cases,metadata=read_cases(path)
    frozen=json.loads(Path(manifest).read_text())
    if frozen!=metadata:raise ValueError('Case content or provenance differs from frozen manifest')
    return cases,metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases-json',required=True)
    parser.add_argument('--manifest',required=True)
    args=parser.parse_args()
    _,metadata=read_cases(args.cases_json)
    with Path(args.manifest).open('x') as stream:json.dump(metadata,stream,indent=2)
    print('Frozen manifest created; independent authorship is NOT verified by hashing.')

if __name__=='__main__':main()
