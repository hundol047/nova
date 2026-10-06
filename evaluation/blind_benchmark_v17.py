"""One-shot post-freeze synthetic holdout. No implicit reruns or legacy second pass."""
from pathlib import Path
import hashlib,json,os,subprocess,statistics
from datetime import datetime,timezone
from dataclasses import asdict
from nova_agent.config import get_config
from evaluation.benchmark import run_all,compute_summary,print_case_table,print_summary
ROOT=Path(__file__).resolve().parents[1]

def verify():
    m=json.loads((ROOT/'evaluation/blind_v17_manifest.json').read_text())
    assert hashlib.sha256((ROOT/'evaluation/blind_cases_v17.py').read_bytes()).hexdigest()==m['file_sha256'],'Case hash mismatch'
    for p,h in m['runtime_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'Frozen runtime drift: '+p
    cfg=get_config(reload=True)
    assert cfg.llm_provider=='mock','Only declared mock run allowed'
    assert cfg.competition_retrieval_enabled and (cfg.retrieval_top_k,cfg.rerank_top_k,cfg.reasoning_top_k)==(150,25,25),'Undeclared configuration'
    assert asdict(cfg)==m['effective_config'],'Effective configuration drift'
    return m

def main():
    m=verify()
    from evaluation.blind_cases_v17 import BLIND_CASES_V17
    out=ROOT/'artifacts/blind_runs';out.mkdir(parents=True,exist_ok=True)
    stamp=dict(runtime_sha=m['final_reasoning_sha'],authoring_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        started_utc=datetime.now(timezone.utc).isoformat(),configuration='COMPETITION-STRUCTURE / MOCK-LLM',status='STARTED')
    # Atomic exclusive creation occurs BEFORE any diagnostic execution. Failed attempts count too.
    with (out/'blind_v17_attempt.json').open('x') as f:json.dump(stamp,f,indent=2)
    results=run_all(BLIND_CASES_V17)
    report=dict(**stamp,completed_utc=datetime.now(timezone.utc).isoformat(),summary=compute_summary(results),
        case_count=len(results),scored_case_count=sum(r.scoring_expected for r in results),critical_case_count=sum(r.critical for r in results),
        cases=[r.model_dump() for r in results],run_count=1,data_type='POST-FREEZE SYNTHETIC HOLDOUT; NOT INDEPENDENT CLINICAL VALIDATION')
    report['status']='COMPLETED'
    (out/'blind_v17_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print_case_table(results);print_summary('Blind v17: one declared mock run',results)
if __name__=='__main__':main()
