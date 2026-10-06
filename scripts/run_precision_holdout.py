#!/usr/bin/env python3
"""Replay frozen, fully observed synthetic states against a requested code checkout.

All cases count. This tests evidence use at a forced final turn, not autonomous workup or
real-provider clinical accuracy. Input is identical for baseline and candidate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ARTIFACT_ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,default=ARTIFACT_ROOT)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    fixture=ARTIFACT_ROOT/'evaluation/precision_holdout_v1.json'
    manifest=json.loads((ARTIFACT_ROOT/'evaluation/precision_holdout_v1_manifest.json').read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest()==manifest['file_sha256'], 'Frozen fixture changed'
    sys.path.insert(0,str(args.repo.resolve()))
    os.environ['NOVA_LLM_PROVIDER'] = 'mock'
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.knowledge.retrieval import disease_by_id
    agent=DoctorAgent()
    rows=[]
    for c in json.loads(fixture.read_text())['cases']:
        state=agent.new_case(c['id'],c['complaint'],max_turns=15)
        state.turn_count=14
        state.pertinent_positives=c.get('positives',[])
        state.pertinent_negatives=c.get('negatives',[])
        state.family_history=c.get('family_history',[])
        state.physical_examinations=c.get('exams',{})
        state.laboratory_tests=c.get('tests',{})
        state.imaging=c.get('imaging',{})
        state.completed_examinations=list(state.physical_examinations)
        state.completed_tests=list(state.laboratory_tests)+list(state.imaging)
        action,_,diff=agent.decide(state)
        expected=c['expected']
        title=disease_by_id(expected)['name'] if expected!='unknown' else 'unknown'
        correct=action.action_type=='DIAGNOSE' and action.content.casefold()==title.casefold()
        rows.append({'id':c['id'],'expected':expected,'actual':action.content,'correct':correct,
                     'critical':c['critical'],'returned_key':action.key})
    critical=[r for r in rows if r['critical']]
    unknown=[r for r in rows if r['expected']=='unknown']
    report={'fixture_sha256':manifest['file_sha256'],'scope':'synthetic_complete_state_mock',
            'total':len(rows),'correct':sum(r['correct'] for r in rows),
            'critical_total':len(critical),'critical_correct':sum(r['correct'] for r in critical),
            'unknown_total':len(unknown),'unknown_correct':sum(r['correct'] for r in unknown),
            'rows':rows}
    output=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.write_text(output)
    print(output)

if __name__=='__main__':main()
