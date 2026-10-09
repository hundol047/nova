"""Same-label/denominator Round T -> U comparison; no score policy edits."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_round_r import comparison, rows


def read(path):
    return json.loads((ROOT/path).read_text())


def main():
    before = 'artifacts/round_t/final/'
    after = 'artifacts/round_u/final/'
    pairs = {'preliminary': ('prelim.json', 'prelim.json'), 'round_p': ('round_p.json', 'round_p.json'),
             'round_q': ('round_q.json', 'round_q.json'), 'round_r': ('round_r/summary.json', 'round_r/summary.json'),
             'round_s': ('round_s/summary.json', 'round_s/summary.json'),
             'acceptance': ('acceptance_regression/summary.json', 'acceptance_regression/summary.json'),
             'round_t': ('round_t_development/summary.json', 'round_t_development/summary.json'),
             't_confirmation': ('confirmation_development/summary.json', 'confirmation_development/summary.json'),
             't_probe': ('new_validation/summary.json', 'probe_development/summary.json'),
             't_postfreeze_now_development': ('postfreeze_confirmation/summary.json', 'post_t/summary.json')}
    paths = {name:(before+b, after+a) for name,(b,a) in pairs.items()}
    paths['u20_now_development'] = ('artifacts/round_u/baseline/new_validation/summary.json', after+'new_validation/summary.json')
    paths['u12_now_development'] = ('artifacts/round_u/baseline/confirmation/summary.json', after+'confirmation/summary.json')
    paths['u10_now_development'] = ('artifacts/round_u/baseline/final_confirmation/summary.json', after+'final_confirmation/summary.json')
    paths['new_closing_u8'] = ('artifacts/round_u/baseline/closing/summary.json', after+'closing/summary.json')
    result = {}
    for name, (b,a) in paths.items():
        result[name] = comparison(b,a)
        old, new = read(b), read(a)
        result[name]['behavior'] = {'before':old.get('behavior'), 'after':new.get('behavior')}
        if 'named_dangerous' in rows(new)[0]:
            result[name]['unscored_dangerous_names'] = {
                label:sum(bool(r.get('named_dangerous')) for r in rows(d) if not r['scored'])
                for label,d in [('before',old),('after',new)]}
    b, a = read(before+'regressions.json'), read(after+'regressions.json')
    assert a['runtime_unchanged_during_execution'] and set(a['suites']) == set(b['suites'])
    result['test_enabled'] = {}
    for name,new in a['suites'].items():
        old = b['suites'][name]
        previous = {r['case_id']:r for r in old['cases']}
        result['test_enabled'][name] = dict(before=old['summary'], after=new['summary'],
            new_wrong=[r['case_id'] for r in new['cases'] if previous[r['case_id']]['correct'] and not r['correct']],
            new_critical_miss=[r['case_id'] for r in new['cases'] if r['critical_miss'] and not previous[r['case_id']]['critical_miss']])
    b,a = read(before+'round_m/final_summary.json'), read(after+'round_m/final_summary.json')
    previous = {r['case_id']:r for r in b['cases']}
    result['round_m_test_enabled'] = dict(before=b['metrics'], after=a['metrics'],
        new_correct=[r['case_id'] for r in a['cases'] if r['scored'] and not previous[r['case_id']]['correct'] and r['correct']],
        new_wrong=[r['case_id'] for r in a['cases'] if r['scored'] and previous[r['case_id']]['correct'] and not r['correct']],
        new_critical_misses=[r['case_id'] for r in a['cases'] if r['scored'] and r['critical'] and previous[r['case_id']]['correct'] and not r['correct']])
    result['retrieval_proxy'] = {'before':read(before+'retrieval_stages.json')['aggregate'],
                               'after':read(after+'retrieval_stages.json')['aggregate']}
    result['limitation'] = ('Offline mock / synthetic engineering evidence, not independent clinical or real-model validation. '
        'T postfreeze, U20, U12 and U10 are development after result-informed repair. Closing U8 was frozen before execution; usage history is recorded separately. '
        'Unscored uncertainty behavior is separate from scored accuracy. Retrieval proxies are not autonomous diagnostic accuracy.')
    (ROOT/after/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:dict(before=v['before']['correct'],after=v['after']['correct'],n=v['after']['scored'],
                            new_wrong=v['new_wrong'],new_critical_misses=v['new_critical_misses'])
                      for k,v in result.items() if isinstance(v,dict) and 'changed' in v},indent=2))


if __name__ == '__main__':
    main()
