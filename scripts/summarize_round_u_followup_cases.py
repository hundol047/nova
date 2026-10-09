#!/usr/bin/env python3
"""Compact per-case mechanism record (baseline vs final) from two scripts/trace_round_u_followup_cases.py outputs.
Truth is used only after each decision to locate the labelled candidate. Development records, not validation."""
import json
import sys


def summ(r):
    first = next((t for t in r['turns'] if t['retrieval_ran']), r['turns'][0])
    last = r['turns'][-1]
    acts = [(t['action']['type'], t['action']['key']) for t in r['turns'] if t['action']['type'] != 'DIAGNOSE']
    return dict(final=r['primary_key'], correct=bool(r['result'].get('top1')), interactions=r['result'].get('interactions'),
                final_decision=r['final_decision'],
                truth_in_initial_retrieval=first['truth_top150'] is not None, chief_turn_top150_rank=first['truth_top150'],
                chief_turn_rerank25_rank=first['truth_rerank_top25'], chief_turn_active_rank=first['truth_active_rank'],
                ever_top150=any(t['truth_top150'] for t in r['turns']),
                ever_rerank25=any((t['truth_rerank_top25'] or 99) <= 25 for t in r['turns']),
                final_top150_rank=last['truth_top150'], final_rerank25_rank=last['truth_rerank_top25'],
                final_active_rank=last['truth_active_rank'], truth_support_final=last['truth_support'],
                truth_naming_problems_final=last['truth_problems'],
                top3_final=[dict(id=x['id'], score=x['score'], dangerous_safety_tracking=x['dangerous'], support=x['support'],
                                 against=x['against'], missing=x.get('missing', []), naming_problems=x['problems'])
                            for x in last['top'][:3]],
                candidate_actions_last_open_turn=next((t['candidate_actions'][:8] for t in reversed(r['turns'])
                                                       if t['action']['type'] != 'DIAGNOSE'), []),
                selected_actions=acts, soap_assessment=r['soap']['A'], soap_plan=r['soap']['P'])


def main(before, after, out):
    B = {r['case_id']: r for r in json.load(open(before))}
    F = {r['case_id']: r for r in json.load(open(after))}
    cases = {c: dict(truth=F[c]['truth'], chief_complaint=F[c]['chief_complaint'], scripted_answers=F[c]['scripted_answers'],
                     scripted_exams=F[c]['scripted_exams'], baseline=summ(B[c]), final=summ(F[c])) for c in F}
    json.dump(dict(scope='Development mechanism records, baseline vs final, preliminary rules, mock LLM.', cases=cases),
              open(out, 'w'), ensure_ascii=False, indent=1)
    for c, v in cases.items():
        print(c, v['baseline']['final'], '->', v['final']['final'], 'correct' if v['final']['correct'] else 'WRONG')


if __name__ == '__main__':
    main(*sys.argv[1:4])
