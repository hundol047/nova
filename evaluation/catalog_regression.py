"""Enforcing MOCK regression gate; no clinical/generalization accuracy claim.

Run: python -m evaluation.catalog_regression --save-json evaluation/catalog_results.json
Existing case text/labels remain untouched. Any scored miss, critical miss,
malformed action or duplicate action fails; unscored cases stay visible.
"""
import argparse
import hashlib
import json
from pathlib import Path
from evaluation.benchmark import run_all, compute_summary
from evaluation.cases import CASES
from evaluation.held_out_cases import HELD_OUT_CASES
from evaluation.generalization_cases_v2 import GENERALIZATION_CASES_V2
from evaluation.generalization_stress_cases import GENERALIZATION_STRESS_CASES
from evaluation.blind_cases_v3 import BLIND_CASES_V3
from evaluation.blind_cases_v4 import BLIND_CASES_V4
from evaluation.blind_cases_v5 import BLIND_CASES_V5
from evaluation.validation_v6 import VALIDATION_V6
from evaluation.expanded_cases import EXPANDED_CASES
from nova_agent.knowledge.retrieval import all_diseases
from nova_agent.config import get_config

SETS = {'tuning':CASES, 'held_out':HELD_OUT_CASES, 'generalization_v2':GENERALIZATION_CASES_V2,
        'stress':GENERALIZATION_STRESS_CASES, 'v3':BLIND_CASES_V3,'v4':BLIND_CASES_V4,
        'v5':BLIND_CASES_V5,'v6':VALIDATION_V6,'expanded':EXPANDED_CASES}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def regression_failures(results):
    return [r.case_id for r in results if (r.scoring_expected and not r.correct)
            or r.critical_miss or r.duplicate_actions or r.malformed_turns]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save-json', required=True)
    args=parser.parse_args()
    if get_config().llm_provider != 'mock':
        raise SystemExit('This is a MOCK regression gate; use real_llm_benchmark for live validation.')
    report={'provider':'mock','independent_validation':False,'clinical_accuracy_claim':False,
            'catalog_size':len(all_diseases()),'catalog_sha256':digest(all_diseases()),'sets':{},'passed':False}
    failed=[]
    for name,cases in SETS.items():
        results=run_all(cases)
        failures=regression_failures(results)
        failed.extend(failures)
        fields=('case_id','correct','scoring_expected','final_diagnosis','turns','critical_miss','duplicate_actions','malformed_turns','decision_quality')
        report['sets'][name]={'summary':compute_summary(results),'cases_sha256':digest([c.model_dump() for c in cases]),
            'failures':failures,'cases':[{k:v for k,v in r.model_dump().items() if k in fields} for r in results]}
        Path(args.save_json).write_text(json.dumps(report,indent=2)+'\n')
        print(name, 'scored correct',sum(r.correct for r in results if r.scoring_expected), '/',sum(r.scoring_expected for r in results), 'failures', failures,flush=True)
    report['passed']=not failed
    Path(args.save_json).write_text(json.dumps(report,indent=2)+'\n')
    if failed:raise SystemExit('Catalog regression gate failed: '+', '.join(failed))

if __name__=='__main__':main()
