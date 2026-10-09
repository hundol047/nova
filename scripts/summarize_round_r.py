"""Case-level comparison only; does not alter scoring or simulator replies."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def rows(d):
 r=d.get('rows',d.get('cases',[]))
 return [x for v in r.values() for x in v] if isinstance(r,dict) else r

def stats(rs):
 scored=[r for r in rs if r['scored']];critical=[r for r in scored if r['critical']]
 return {'cases':len(rs),'scored':len(scored),'correct':sum(r['top1'] for r in scored),
         'critical_cases':len(critical),'critical_correct':sum(r['top1'] for r in critical),
         'avg_interactions':sum(r['interactions'] for r in rs)/len(rs),'max_interactions':max(r['interactions'] for r in rs),
         'rule_violations':sum(r['rule_violations'] for r in rs),
         'duplicate_actions':sum(r['duplicate_actions'] for r in rs),
         'semantic_duplicate_questions':sum(r['semantic_duplicate_questions'] for r in rs),
         'unresolved_critical_cases':sum(bool(r['unresolved_critical_at_diagnosis']) for r in rs),
         'unnecessary_exams':sum(r['unnecessary_exams'] for r in rs),
         'malformed':sum(r['malformed'] for r in rs),
         'soap_unsupported_lines':sum(r['soap_unsupported'] for r in rs)}

def comparison(before,after):
 b=rows(read(before));a=rows(read(after));old={r['case_id']:r for r in b};assert set(old)=={r['case_id'] for r in a}
 changed=[]
 for r in a:
  o=old[r['case_id']]
  if r['top1']!=o['top1'] or r['primary']!=o['primary']:
   changed.append({'case_id':r['case_id'],'scored':r['scored'],'critical':r['critical'],
    'before':o['primary'],'after':r['primary'],'before_correct':o['top1'],'after_correct':r['top1']})
 return {'before':stats(b),'after':stats(a),'changed':changed,
  'new_correct':[r['case_id'] for r in changed if r['scored'] and not r['before_correct'] and r['after_correct']],
  'new_wrong':[r['case_id'] for r in changed if r['scored'] and r['before_correct'] and not r['after_correct']],
  'new_critical_misses':[r['case_id'] for r in changed if r['scored'] and r['critical'] and r['before_correct'] and not r['after_correct']]}

def main():
 pairs={'preliminary':('artifacts/round_q/final/prelim.json','artifacts/round_r/final/prelim.json'),
        'round_p':('artifacts/round_q/final/validation_round_p.json','artifacts/round_r/final/round_p.json'),
        'round_q':('artifacts/round_q/final/dev_round_q.json','artifacts/round_r/final/round_q.json'),
        'acceptance_development':('artifacts/round_r/baseline/acceptance_fresh.json','artifacts/round_r/final/acceptance_regression/summary.json'),
        'new_validation':('artifacts/round_r/baseline/new_validation/summary.json','artifacts/round_r/final/new_validation/summary.json')}
 result={k:comparison(*v) for k,v in pairs.items()}
 before=read('artifacts/round_q/final/test_enabled_regressions.json')['suites'];after=read('artifacts/round_r/final/regressions.json')['suites']
 result['test_enabled']={}
 for name,v in after.items():
  b={r['case_id']:r for r in before[name]['cases']}
  result['test_enabled'][name]={'before':before[name]['summary'],'after':v['summary'],
   'new_wrong':[r['case_id'] for r in v['cases'] if b[r['case_id']]['correct'] and not r['correct']],
   'new_critical_miss':[r['case_id'] for r in v['cases'] if r['critical_miss'] and not b[r['case_id']]['critical_miss']]}
 result['note']='All unchanged official evaluator labels/denominators. Behavioral pass does not establish clinical safety: NewR_18 remains unsafe on semantic review.'
 (ROOT/'artifacts/round_r/final/comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 for k,v in result.items():
  if isinstance(v,dict) and 'new_wrong' in v:print(k,v['before']['correct'],v['after']['correct'],v['after']['scored'],'new wrong',v['new_wrong'])
if __name__=='__main__':main()
