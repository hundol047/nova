"""Compare unchanged scorers and denominators; keep engineering behavior separate."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_round_r import comparison, read


def main():
    old = 'artifacts/round_r/final/'
    new = 'artifacts/round_s/final/'
    pairs = {
        'preliminary': (old+'prelim.json', new+'prelim.json'),
        'round_p': (old+'round_p.json', new+'round_p.json'),
        'round_q': (old+'round_q.json', new+'round_q.json'),
        'acceptance_development': (old+'acceptance_regression/summary.json', new+'acceptance_regression/summary.json'),
        'round_r_development': (old+'new_validation/summary.json', new+'round_r/summary.json'),
        'new_validation': ('artifacts/round_s/baseline/new_validation/summary.json', new+'new_validation/summary.json'),
    }
    result = {name: comparison(*paths) for name, paths in pairs.items()}
    before = read(old+'regressions.json')['suites']
    after = read(new+'regressions.json')['suites']
    result['test_enabled'] = {}
    for name, value in after.items():
        b = {r['case_id']: r for r in before[name]['cases']}
        result['test_enabled'][name] = {
            'before': before[name]['summary'], 'after': value['summary'],
            'new_correct': [r['case_id'] for r in value['cases'] if not b[r['case_id']]['correct'] and r['correct']],
            'new_wrong': [r['case_id'] for r in value['cases'] if b[r['case_id']]['correct'] and not r['correct']],
            'new_critical_miss': [r['case_id'] for r in value['cases'] if r['critical_miss'] and not b[r['case_id']]['critical_miss']],
        }
    b = read(old+'round_m_verified/final_summary.json')
    a = read(new+'round_m/final_summary.json')
    old_rows = {r['case_id']: r for r in b['cases']}
    result['round_m_test_enabled'] = {
        'before': b['metrics'], 'after': a['metrics'],
        'new_correct': [r['case_id'] for r in a['cases'] if r['scored'] and not old_rows[r['case_id']]['correct'] and r['correct']],
        'new_wrong': [r['case_id'] for r in a['cases'] if r['scored'] and old_rows[r['case_id']]['correct'] and not r['correct']],
    }
    result['behavior'] = {
        name: {'before': read(paths[0]).get('behavior'), 'after': read(paths[1]).get('behavior')}
        for name, paths in pairs.items() if name in ('round_r_development', 'new_validation', 'acceptance_development')
    }
    result['limitations'] = [
        'Mock, synthetic cases. No independent clinical validation or real-model accuracy claim.',
        'Old R/P/Q/acceptance and M are development data. Only Round S was unused before this implementation.',
        'Author saw implementation and prior failures. New Round S is not independent clinical validation.',
        'Legacy SOAP provenance checks are string-oriented, not a clinical audit; semantic findings are in the report.',
    ]
    (ROOT/new/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    for name, value in result.items():
        if isinstance(value, dict) and 'new_wrong' in value:
            print(name, 'new correct', value.get('new_correct'), 'new wrong', value['new_wrong'])


if __name__ == '__main__':
    main()
