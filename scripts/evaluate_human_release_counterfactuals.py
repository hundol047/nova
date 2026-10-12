"""New local safety variants; no public sample answer maps and no private imports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def run():
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.disposition import disposition_for
    from nova_agent.final_decision import decide_final
    path=ROOT/'evaluation/human_release_counterfactuals.json';suite=json.loads(path.read_text());rows=[]
    for case in suite['cases']:
        agent=DoctorAgent();state=agent.new_case(case['id'],case['opening'],{'age':29,'sex':'female'})
        state.record_ask('past_medical_history','History?',case['history']);state.record_exam('vital_signs',case['exam'])
        _,_,ddx=agent.decide(state);final=decide_final(state,ddx);plan=disposition_for(state,final,ddx)
        first=ddx[0].diagnosis_id if ddx else None
        checks={}
        if 'urgent' in case:checks['urgency']=plan.urgent==case['urgent']
        if 'top_family' in case:checks['diagnosis_family']=case['top_family'] in (first or '')
        rows.append({'id':case['id'],'top1':first,'urgent':plan.urgent,'reasons':list(plan.reasons),'checks':checks,'passed':all(checks.values())})
    return {'label':suite['label'],'fixture_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':rows,
            'passed':sum(r['passed'] for r in rows),'failed':sum(not r['passed'] for r in rows),'clinical_adjudication':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--gate',action='store_true');a=p.parse_args()
    result=run();Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if a.gate and result['failed']:raise SystemExit(1)

if __name__=='__main__':main()
