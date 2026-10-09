"""New versioned behavior audit; the existing labels/scorer/simulator are unchanged.

Fixture expectations are stripped before constructing a case or calling the agent.
Same driver runs against a pinned baseline using --checkout. No blind imports.
"""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_round_r import run_one, hashes


def audit_job(job):
    checkout, original = job
    raw = dict(original)
    expected = raw.pop('round_s_expect', {})
    row, detail = run_one((checkout, raw))
    wire = detail['wire'][-1]
    state = detail['final_state']
    checks = dict(row['behavior_checks'])
    # Legacy and new implementations get exactly the same semantic checks.
    # This deliberately does not depend on the new disposition metadata.
    plan = wire.get('soap', {}).get('P', '')
    urgent = ('immediate emergency-department evaluation' in plan or '즉시 응급실' in plan)
    if 'urgent' in expected:
        checks['disposition_urgent'] = urgent is expected['urgent']
    support = [p for t in detail['trace'] for d in t['differential'] for p in d['supporting_evidence']]
    for phrase in expected.get('forbidden_support', []):
        checks['no_support:' + phrase] = phrase not in support
    if expected.get('no_unknown_as_content'):
        fields = [*state.get('family_history', []), *state.get('pertinent_positives', []),
                  *[m['name'] for m in state.get('medications', [])],
                  *[a['substance'] for a in state.get('allergies', [])]]
        unknowns = ('i cannot tell you that', 'i cannot say', 'i do not know', '답변할 수 없어요', '모르겠어요')
        checks['no_unknown_as_content'] = not any(
            any(u in f.lower().rstrip('.!? ') for u in unknowns) for f in fields)
    checks['no_TEST'] = not row['tests_observed'] and not any(w['action_type'] == 'TEST' for w in detail['wire'])
    checks['finite_protocol'] = row['rule_violations'] == 0 and row['interactions'] <= 50
    row['behavior_checks'] = checks
    row['urgent_plan'] = urgent
    detail['result'] = row
    return row, detail


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', default=str(ROOT));p.add_argument('--cases', required=True)
    p.add_argument('--freeze', required=True);p.add_argument('--output', required=True)
    p.add_argument('--workers', type=int, default=2)
    a = p.parse_args();source = Path(a.cases)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = json.loads(Path(a.freeze).read_text());assert manifest['sha256'] == digest
    out = Path(a.output);out.mkdir(parents=True, exist_ok=True)
    runtime = hashes(a.checkout);rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for row, detail in pool.map(audit_job, [(a.checkout, r) for r in json.loads(source.read_text())]):
            rows.append(row)
            (out/(row['case_id']+'.json')).write_text(json.dumps(detail,ensure_ascii=False,indent=1)+'\n')
            print(row['case_id'], row['primary_key'], row['top1'],
                  [k for k,v in row['behavior_checks'].items() if not v], flush=True)
    assert hashes(a.checkout) == runtime, 'Runtime changed during evaluation'
    sys.path.insert(0, a.checkout)
    from evaluation.preliminary_driver import summarize
    checks = [v for r in rows for v in r['behavior_checks'].values()]
    result = {'head': subprocess.check_output(['git','-C',a.checkout,'rev-parse','HEAD'],text=True).strip(),
              'runtime_sha256': runtime, 'fixture_sha256': digest, 'summary': summarize(rows), 'rows': rows,
              'behavior': {'passed': sum(checks), 'total':len(checks)}, 'runtime_unchanged': True,
              'limitation': 'Synthetic engineering validation. Author saw prior failures and implementation. Not independent clinical validation.'}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n')
    print(result['summary'],result['behavior'],flush=True)

if __name__ == '__main__':
    main()
