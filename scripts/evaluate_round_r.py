"""Offline replay of frozen Round R fixtures, preserving the existing evaluator/matcher.
--checkout permits the SAME fixtures/driver to run against a pinned earlier runtime.
Runtime cannot access expected checks or truth labels. No blind imports.
"""
import argparse, concurrent.futures, hashlib, json, os, sys, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run_one(job):
    checkout,raw=job
    sys.path.insert(0,checkout)
    os.environ['NOVA_LLM_PROVIDER']='mock';os.environ['NOVA_COMPETITION_RETRIEVAL']='1'
    from nova_agent.config import get_config
    get_config(reload=True)
    from evaluation.cases import SyntheticCase
    from evaluation.preliminary_driver import run_episode, Environment
    from competition.adapter import NovaCompetitionAgent
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.llm_client import MockLLMClient
    from nova_agent.differential import _entry_for_candidate_id
    from unittest.mock import patch
    raw=dict(raw);expect=raw.pop('audit_expect',{});reject=raw.pop('audit_rejected_exams',[])
    case=SyntheticCase(**raw);agent=NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()),preliminary=True)
    trace=[];final_state={};decide=agent.agent.decide
    def traced(state):
        action,scored,diff=decide(state)
        trace.append({'turn':state.turn_count,'action':action.model_dump(),
                      'differential':[d.model_dump() for d in diff]})
        final_state.clear();final_state.update(state.model_dump(mode='json'))
        return action,scored,diff
    with patch.object(agent.agent,'decide',traced):
        ep=run_episode(case,agent=agent,env=Environment(unsupported_exams=frozenset(reject)))
    md=ep.wire[-1].get('metadata',{});key=md.get('key','')
    entry=_entry_for_candidate_id(key) or {}
    row=dict(ep.result,primary_key=key,named_dangerous=bool(entry.get('dangerous')),final_decision=md.get('final_decision'))
    candidate_ever=any(d['diagnosis_id']==case.ground_truth_diagnosis for t in trace for d in t['differential'])
    checks={}
    if expect.get('candidate'): checks['candidate']=candidate_ever
    if expect.get('undifferentiated'):checks['undifferentiated']=key=='unknown'
    if expect.get('no_dangerous_named'): checks['no_dangerous_named']=not row['named_dangerous']
    for bad in expect.get('forbidden',[]):checks['not:'+bad]=key!=bad
    row['behavior_checks']=checks
    row['tests_observed']=bool(final_state.get('laboratory_tests') or final_state.get('imaging'))
    return row,{'case':raw,'wire':ep.wire,'trace':trace,'final_state':final_state,'result':row}

def hashes(checkout):
    root=Path(checkout)
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for d in ('nova_agent','competition')
            for p in sorted((root/d).rglob('*')) if p.is_file() and p.suffix in {'.py','.json','.md'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',default=str(ROOT));p.add_argument('--cases',required=True)
    p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--freeze')
    a=p.parse_args();source=Path(a.cases);digest=hashlib.sha256(source.read_bytes()).hexdigest()
    if a.freeze: assert json.loads(Path(a.freeze).read_text())['sha256']==digest
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True);runtime=hashes(a.checkout)
    rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for row,detail in pool.map(run_one,[(a.checkout,x) for x in json.loads(source.read_text())]):
            rows.append(row)
            (out/(row['case_id']+'.json')).write_text(json.dumps(detail,ensure_ascii=False,indent=1)+'\n')
            print(row['case_id'],row['primary_key'],row['top1'],row['behavior_checks'],flush=True)
    sys.path.insert(0,a.checkout)
    from evaluation.preliminary_driver import summarize
    assert hashes(a.checkout)==runtime,'Runtime changed during replay'
    checks=[v for r in rows for v in r['behavior_checks'].values()]
    result={'head':subprocess.check_output(['git','-C',a.checkout,'rev-parse','HEAD'],text=True).strip(),
            'runtime_sha256':runtime,'fixture_sha256':digest,'summary':summarize(rows),'rows':rows,
            'behavior':{'passed':sum(checks),'total':len(checks)},'runtime_unchanged':True}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n')
    print(result['summary'],result['behavior'],flush=True)
if __name__=='__main__':main()
