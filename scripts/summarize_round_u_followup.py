#!/usr/bin/env python3
"""Round U follow-up: same-label, same-denominator comparison of two run directories produced by
scripts/run_round_u_followup_suite.py (baseline vs final). Reads results only; changes no score policy.

    python scripts/summarize_round_u_followup.py --before <baseline_out> --after <final_out> --output comparison.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.summarize_round_r import rows, stats  # noqa: E402

CASE_SUITES = ['prelim', 'prelim_exam_rejection', 'prelim_unscripted_unknown', 'round_p', 'round_q',
               'round_r/summary', 'acceptance_regression/summary', 'round_s/summary', 'round_t_development/summary',
               't_confirmation/summary', 't_probe/summary', 't_postfreeze/summary', 'u20/summary', 'u12/summary',
               'u10/summary', 'closing_u8/summary', 'followup_new/summary', 'followup_closing/summary']


def load(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else None


def case_compare(b, a):
    old = {r['case_id']: r for r in rows(b)}
    new = rows(a)
    changed = [dict(case_id=r['case_id'], scored=r['scored'], critical=r['critical'],
                    before=old[r['case_id']].get('primary') or old[r['case_id']].get('primary_key'),
                    after=r.get('primary') or r.get('primary_key'),
                    before_correct=old[r['case_id']]['top1'], after_correct=r['top1'])
               for r in new if r['top1'] != old[r['case_id']]['top1']
               or (r.get('primary') or r.get('primary_key')) != (old[r['case_id']].get('primary') or old[r['case_id']].get('primary_key'))]
    out = dict(before=stats(rows(b)), after=stats(new), changed=changed,
               new_correct=[c['case_id'] for c in changed if c['scored'] and not c['before_correct'] and c['after_correct']],
               new_wrong=[c['case_id'] for c in changed if c['scored'] and c['before_correct'] and not c['after_correct']],
               new_critical_misses=[c['case_id'] for c in changed if c['scored'] and c['critical']
                                    and c['before_correct'] and not c['after_correct']],
               still_wrong=[r['case_id'] for r in new if r['scored'] and not r['top1']])
    if 'behavior' in b and 'behavior' in a:
        out['behavior'] = dict(before=b['behavior'], after=a['behavior'])
        failed = lambda d: sorted(f"{r['case_id']}:{k}" for r in rows(d) for k, v in r.get('behavior_checks', {}).items() if not v)
        out['behavior_failures'] = dict(before=failed(b), after=failed(a))
    if all(isinstance(r.get('named_dangerous'), bool) for r in rows(a)):
        out['unscored_dangerous_named'] = {k: sum(bool(r.get('named_dangerous')) for r in rows(d) if not r['scored'])
                                           for k, d in (('before', b), ('after', a))}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--before', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    B, A = Path(a.before), Path(a.after)
    result = {'before_head': (load(B / 'executions.json') or {}).get('head'),
              'after_head': (load(A / 'executions.json') or {}).get('head')}
    for name in CASE_SUITES:
        b, f = load(B / f'{name}.json'), load(A / f'{name}.json')
        if b and f:
            result[name.split('/')[0]] = case_compare(b, f)
    b, f = load(B / 'regressions.json'), load(A / 'regressions.json')
    if b and f:
        result['test_enabled'] = {}
        for name, new in f['suites'].items():
            old = {r['case_id']: r for r in b['suites'][name]['cases']}
            result['test_enabled'][name] = dict(before=b['suites'][name]['summary'], after=new['summary'],
                new_wrong=[r['case_id'] for r in new['cases'] if old[r['case_id']]['correct'] and not r['correct']],
                new_correct=[r['case_id'] for r in new['cases'] if not old[r['case_id']]['correct'] and r['correct']],
                new_critical_miss=[r['case_id'] for r in new['cases'] if r['critical_miss'] and not old[r['case_id']]['critical_miss']])
    b, f = load(B / 'round_m_final_summary.json'), load(A / 'round_m_final_summary.json')
    if b and f:
        old = {r['case_id']: r for r in b['cases']}
        lt = lambda d, k: sum(r['final_rank'] is not None and r['final_rank'] <= k for r in d['cases']
                              if r['scored'] and 'long_tail' in r['category'])
        result['round_m_test_enabled'] = dict(
            before={k: b['metrics'].get(k) for k in ('top1', 'critical_recall', 'retrieval_at150', 'rerank_at25', 'active_truth_retention')},
            after={k: f['metrics'].get(k) for k in ('top1', 'critical_recall', 'retrieval_at150', 'rerank_at25', 'active_truth_retention')},
            correct=dict(before=sum(r['correct'] for r in b['cases'] if r['scored']), after=sum(r['correct'] for r in f['cases'] if r['scored']),
                         scored=sum(r['scored'] for r in f['cases'])),
            critical=dict(before=sum(r['correct'] for r in b['cases'] if r['scored'] and r['critical']),
                          after=sum(r['correct'] for r in f['cases'] if r['scored'] and r['critical']),
                          n=sum(r['scored'] and r['critical'] for r in f['cases'])),
            final_top150=dict(before=sum(bool(r['final_retrieval_at150']) for r in b['cases'] if r['scored']),
                              after=sum(bool(r['final_retrieval_at150']) for r in f['cases'] if r['scored'])),
            final_top25=dict(before=sum(bool(r['final_rerank_at25']) for r in b['cases'] if r['scored']),
                             after=sum(bool(r['final_rerank_at25']) for r in f['cases'] if r['scored'])),
            active=dict(before=sum(r['final_rank'] is not None for r in b['cases'] if r['scored']),
                        after=sum(r['final_rank'] is not None for r in f['cases'] if r['scored'])),
            long_tail={k: dict(before=lt(b, n), after=lt(f, n)) for k, n in (('Top1', 1), ('Top5', 5), ('Top10', 10))},
            long_tail_n=sum(r['scored'] and 'long_tail' in r['category'] for r in f['cases']),
            avg_turns=dict(before=b['metrics'].get('average_turns'), after=f['metrics'].get('average_turns')),
            new_correct=[r['case_id'] for r in f['cases'] if r['scored'] and not old[r['case_id']]['correct'] and r['correct']],
            new_wrong=[r['case_id'] for r in f['cases'] if r['scored'] and old[r['case_id']]['correct'] and not r['correct']],
            new_critical_misses=[r['case_id'] for r in f['cases'] if r['scored'] and r['critical'] and old[r['case_id']]['correct'] and not r['correct']])
    b, f = load(B / 'retrieval_stages.json'), load(A / 'retrieval_stages.json')
    if b and f:
        result['retrieval_proxy'] = dict(before=b['aggregate'], after=f['aggregate'])
    for name in ('assertion_contrasts',):
        for side, d in (('before', B), ('after', A)):
            log = (d / f'{name}.log')
            if log.exists():
                m = re.search(r'"passed":\s*(\d+),\s*"total":\s*(\d+)', log.read_text())
                result.setdefault(name, {})[side] = f"{m.group(1)}/{m.group(2)}" if m else None
    result['limitation'] = ('Offline mock-LLM, synthetic development evidence. Not independent clinical validation, not real-model '
                            'or official-API evidence. Development sets were used to change source (see report).')
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    for k, v in result.items():
        if isinstance(v, dict) and 'before' in v and isinstance(v['before'], dict) and 'correct' in v['before']:
            print(f"{k:28s} {v['before']['correct']}->{v['after']['correct']}/{v['after']['scored']} "
                  f"crit {v['before']['critical_correct']}->{v['after']['critical_correct']}/{v['after']['critical_cases']} "
                  f"turns {v['before']['avg_interactions']:.2f}->{v['after']['avg_interactions']:.2f} "
                  f"new_wrong={v['new_wrong']} new_correct={v['new_correct']}")


if __name__ == '__main__':
    main()
