"""Full Round M development evaluation. No blind import, selection, label edits or tuning."""
import concurrent.futures
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tarfile
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.trace_diagnostic_ranking import trace_case, aggregate, archive_traces
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from nova_agent.diagnosis_normalizer import same_diagnosis

OUT=ROOT/'artifacts/round_m/final'

def worker(case):
    row,turns=trace_case(case)
    row['asks']=sum(t['action']['action_type']=='ASK' for t in turns)
    row['exams']=sum(t['action']['action_type']=='EXAM' for t in turns)
    row['internal_result']=None
    # Reconstruct wire uncertainty from the same recorded state-free final metadata if present;
    # OOD detailed states are measured separately by the existing OOD evaluator.
    row['redundant_tests']=sum(count-1 for count in Counter(t['action']['key'] for t in turns if t['action']['action_type']=='TEST').values())
    final=turns[-1]
    row['unresolved_critical_alternatives']=sum(c['dangerous'] and not c['resolved'] and c['active'] for c in final['candidates'])
    text=case.chief_complaint
    import re
    ko=bool(re.search('[가-힣]',text)); ja=bool(re.search('[ぁ-ヿ一-龯]',text));en=bool(re.search('[A-Za-z]{2,}',text))
    row['language']='Mixed' if (ko or ja) and en else 'KO' if ko else 'JA' if ja else 'EN'
    row['final_retrieval_at150']=any((c['retrieval_rank'] or 100000)<=150 for c in final['candidates'] if same_diagnosis(c['id'],case.ground_truth_diagnosis) or same_diagnosis(c['name'],case.ground_truth_diagnosis))
    row['final_rerank_at25']=any((c['rerank_rank'] or 100000)<=25 for c in final['candidates'] if same_diagnosis(c['id'],case.ground_truth_diagnosis) or same_diagnosis(c['name'],case.ground_truth_diagnosis))
    payload=json.dumps({'summary':row,'turns':turns},ensure_ascii=False,separators=(',',':')).encode()
    target=OUT/(case.case_id+'.json.gz');target.write_bytes(gzip.compress(payload,mtime=0))
    row['trace_file']=target.name;row['trace_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    return row


def main():
    from nova_agent.config import get_config
    from dataclasses import asdict
    cfg=get_config()
    assert cfg.llm_provider=='mock' and cfg.competition_retrieval_enabled
    assert (cfg.retrieval_top_k,cfg.rerank_top_k,cfg.reasoning_top_k)==(150,25,25)
    OUT.mkdir(parents=True,exist_ok=True)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    from scripts.runtime_identity import tracked_runtime_hashes
    runtime=tracked_runtime_hashes(ROOT)
    rows=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for row in pool.map(worker,ROUND_M_CASES):
            rows.append(row); print(row['case_id'],row['correct'],row['primary_failure'],flush=True)
    assert len(rows)==len(ROUND_M_CASES) and {r['case_id'] for r in rows}=={c.case_id for c in ROUND_M_CASES}
    for path,h in runtime.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    archive_hash=archive_traces(OUT,rows)
    s=[r for r in rows if r['scored']];lt=[r for r in s if 'long_tail' in r['category']]
    m=aggregate(rows)
    def rate(rs,key):return sum(bool(r[key]) for r in rs)/len(rs) if rs else None
    def top(rs,k):return sum(r['final_rank'] is not None and r['final_rank']<=k for r in rs)/len(rs) if rs else None
    m.update(cases=len(rows),median_turns=statistics.median(r['turns'] for r in rows),average_ask=statistics.mean(r['asks'] for r in rows),average_exam=statistics.mean(r['exams'] for r in rows),retrieval_at150=rate(s,'final_retrieval_at150'),rerank_at25=rate(s,'final_rerank_at25'),redundant_tests=sum(r['redundant_tests'] for r in rows),average_unresolved_critical_alternatives=statistics.mean(r['unresolved_critical_alternatives'] for r in rows))
    m['long_tail'].update(Top10=top(lt,10),retrieval_at150=rate(lt,'final_retrieval_at150'),rerank_at25=rate(lt,'final_rerank_at25'),interpretation='Round M category-defined symptom-only development probes, no independent medical adjudication')
    m['languages']={lang:{'count':len(rs),'correct':sum(r['correct'] for r in rs),'accuracy':rate(rs,'correct')} for lang in ('EN','KO','JA','Mixed') if (rs:=[r for r in s if r['language']==lang])}
    failures=[{'case_id':r['case_id'],'truth':r['truth'],'prediction':r['final'],'earliest_failure':r['primary_failure'],'final_stage':r['final_stage'],'unrequested_scripted_objective':r['unrequested_scripted_objective'],'trace_file':r['trace_file']} for r in s if not r['correct']]
    result={'runtime_sha':sha,'runtime_sha256':runtime,'effective_config':asdict(cfg),'case_schema_sha256':hashlib.sha256(Path(sys.modules[ROUND_M_CASES[0].__class__.__module__].__file__).read_bytes()).hexdigest(),'round_m_case_file_sha256':hashlib.sha256((ROOT/'evaluation/generalization_dev_cases_round_m.py').read_bytes()).hexdigest(),'data_type':'SYNTHETIC DEVELOPMENT / MOCK LLM','expert_reviewed':False,'independent_clinical_validation':False,'metrics':m,'cases':rows,'trace_archive_sha256':archive_hash,'definitions':{'stage_retention':'Final decision turn, fixed scored denominator; core scoring can bypass ontology retrieval','critical_recall':'Correct final diagnosis / existing critical property; critical-like long-tail tags are not relabeled critical','language':'Mutually exclusive chief-complaint script partition; follow-up text often English. Pure KO/JA samples are tiny. Labels/tags unchanged.','median_rank':'Finite active ranks only; missing_rank_count disclosed','failure_attribution':'Ordered earliest observed terminal-stage loss, then heuristic evidence/action/ranking attribution; not clinician causal adjudication; see trace_diagnostic_ranking.primary_failure','ood':'Five existing unscored controls preserved; forced DIAGNOSE is not evidence of supported diagnosis. Detailed separate OOD report included.'}}
    (OUT.parent/'final_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT.parent/'failure_analysis.json').write_text(json.dumps({'definition':result['definitions']['failure_attribution'],'counts':dict(Counter(f['earliest_failure'] for f in failures)),'failures':failures},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(m,indent=2),flush=True)

if __name__=='__main__':main()
