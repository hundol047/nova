#!/usr/bin/env python3
"""Summarize development traces; delay is the policy's observable non-forced stop point.
Not a clinically adjudicated safe-diagnosis time. Nulls are never replaced with zero.
"""
import argparse,json,statistics
from pathlib import Path

def summarize(data):
    cs=data['cases']; critical=[c for c in cs if c['critical']]
    rows=[r for c in cs for r in c['trajectory']];eligible=sum(c['eligible_critical_candidate_turns'] for c in cs)
    kept=sum(c['retained_critical_candidate_turns'] for c in cs)
    delays=[c['diagnostic_delay_turns'] for c in cs if c['diagnostic_delay_turns'] is not None]
    actions={a:sum(r['action']['action_type']==a for r in rows)/len(cs) for a in ['ASK','EXAM','TEST']}
    return dict(data_type=data['data_type'],cases=len(cs),correct=sum(c['correct'] for c in cs),accuracy=sum(c['correct'] for c in cs)/len(cs),
        critical_cases=len(critical),critical_recall=sum(c['correct'] for c in critical)/len(critical) if critical else None,
        critical_miss=sum(not c['correct'] for c in critical)/len(critical) if critical else None,
        avg_turns=statistics.mean(c['turns'] for c in cs),median_turns=statistics.median(c['turns'] for c in cs),avg_actions=actions,
        diagnostic_delay_turns=statistics.mean(delays) if delays else None,delay_measured_cases=len(delays),
        delay_definition='Actual diagnosis turn minus first non-forced StopPolicy acceptance; not expert clinical safety.',
        malformed_rate=sum(r['malformed'] for r in rows)/len(rows),
        duplicate_rate=sum(r['duplicate'] for r in rows)/len(rows),
        unnecessary_test_proxy=sum(r['action']['action_type']=='TEST' and r['best_information_gain']==0 for r in rows),
        unnecessary_test_proxy_definition='Selected TEST when no candidate action had positive estimated information gain; not clinical adjudication.',
        eligible_critical_candidate_turns=eligible,critical_candidate_survival_rate=kept/eligible if eligible else None,
        critical_candidate_dropout_rate=(eligible-kept)/eligible if eligible else None,
        candidate_dropouts=sum(len(c['candidate_dropouts']) for c in cs),candidate_reentries=sum(len(c['candidate_reentries']) for c in cs),
        cases_detail=[{k:v for k,v in c.items() if k!='trajectory'} for c in cs])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('--output',required=True);a=p.parse_args()
    result=summarize(json.loads(Path(a.trace).read_text()));Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases_detail'},ensure_ascii=False))
