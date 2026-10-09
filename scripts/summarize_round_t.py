"""Same-denominator comparisons. Never aggregate development and unused confirmation."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.summarize_round_r import comparison,rows,stats
def read(n):return json.loads((ROOT/n).read_text())
def main():
 old='artifacts/round_s/final/';new='artifacts/round_t/final/'
 pairs={'preliminary':(old+'prelim.json',new+'prelim.json'),'round_p':(old+'round_p.json',new+'round_p.json'),
        'round_q':(old+'round_q.json',new+'round_q.json'),'round_r':(old+'round_r/summary.json',new+'round_r/summary.json'),
        'round_s':(old+'new_validation/summary.json',new+'round_s/summary.json'),
        'acceptance_development':(old+'acceptance_regression/summary.json',new+'acceptance_regression/summary.json'),
        'round_t_promoted_development':('artifacts/round_t/baseline/new_validation/summary.json',new+'round_t_development/summary.json'),
        'prior_confirmation_development':('artifacts/round_t/baseline/confirmation/summary.json',new+'confirmation_development/summary.json'),
        'final_probe_promoted_development':('artifacts/round_t/baseline/final_probe/summary.json',new+'new_validation/summary.json'),
        'unused_postfreeze_confirmation':('artifacts/round_t/baseline/postfreeze_confirmation/summary.json',new+'postfreeze_confirmation/summary.json')}
 result={name:comparison(*paths) for name,paths in pairs.items()}
 for name,paths in pairs.items():
  b,a=read(paths[0]),read(paths[1]);result[name]['behavior']={'before':b.get('behavior'),'after':a.get('behavior')}
  ar=rows(a)
  if ar and 'named_dangerous' in ar[0]:
   # A proxy only, never equated with clinician-adjudicated overdiagnosis.
   result[name]['dangerous_name_proxy']={label:sum(bool(r.get('named_dangerous')) and (not r['scored'] or not r['top1']) for r in rows(d)) for label,d in [('before',b),('after',a)]}
 before=read(old+'regressions.json')['suites'];after=read(new+'regressions.json')['suites']
 result['test_enabled']={}
 for name,d in after.items():
  b={r['case_id']:r for r in before[name]['cases']}
  result['test_enabled'][name]={'before':before[name]['summary'],'after':d['summary'],
    'new_wrong':[r['case_id'] for r in d['cases'] if b[r['case_id']]['correct'] and not r['correct']],
    'new_critical_miss':[r['case_id'] for r in d['cases'] if r['critical_miss'] and not b[r['case_id']]['critical_miss']]}
 b=read(old+'round_m/final_summary.json');a=read(new+'round_m/final_summary.json');prior={r['case_id']:r for r in b['cases']}
 result['round_m_test_enabled']={'before':b['metrics'],'after':a['metrics'],
    'new_correct':[r['case_id'] for r in a['cases'] if r['scored'] and not prior[r['case_id']]['correct'] and r['correct']],
    'new_wrong':[r['case_id'] for r in a['cases'] if r['scored'] and prior[r['case_id']]['correct'] and not r['correct']]}
 result['retrieval_proxy']={'before':read('artifacts/round_t/development/retrieval_s_baseline.json')['aggregate'],'after':read(new+'retrieval_stages.json')['aggregate']}
 result['limitation']='Synthetic offline mock. Same author saw implementation. Initial T became development after critical failure; all 32+12+8 T cases exposed before final freeze and are development; 12 postfreeze cases first evaluated on final runtime; implementation-aware author, not independently clinical. No independent clinical or real-model claim. Behavioral gates and SOAP string audits are not clinical truth.'
 (ROOT/new/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:dict(before=v['before'].get('correct'),after=v['after'].get('correct'),n=v['after'].get('scored'),new_wrong=v.get('new_wrong')) for k,v in result.items() if isinstance(v,dict) and isinstance(v.get('before'),dict) and 'correct' in v['before']},indent=2))
if __name__=='__main__':main()
