#!/usr/bin/env python3
"""Round U follow-up: bind LOCAL v27 evidence to the executed runtime commit and exact ZIP bytes.

Writes, inside --checkout only (a verification worktree; nothing here is meant to be pushed):
  artifacts/verification/nova-pre-guide-v27.zip            copy of the audited ZIP
  artifacts/verification/local-release-<sha7>-v27.json     the record
  artifacts/verification/CURRENT_RELEASE.json              pointer (local)
  artifacts/round_u_followup/final/round_m_*.json          the Round M evidence the record references

Refuses unless every runtime file equals the commit, the submission mirror and the ZIP, and unless the only
failures in the supplied JUnit are the release-binding checks that read this very record (they are re-run after).
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BINDING = {'tests.test_current_pre_guide_release'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', required=True)
    p.add_argument('--runtime', required=True)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--zip', required=True)
    p.add_argument('--junit', required=True)
    a = p.parse_args()
    root, run = Path(a.checkout).resolve(), Path(a.run_dir).resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    assert head == a.runtime, (head, a.runtime)
    names = subprocess.check_output(['git', 'ls-files', 'nova_agent', 'competition'], cwd=root, text=True).split()
    core = {n: sha(root / n) for n in sorted(names) if Path(n).suffix in {'.py', '.json', '.md'}}
    runtime = dict(core, **{n: sha(root / n) for n in ('submission/run.py', 'submission/requirements.txt')})
    with zipfile.ZipFile(a.zip) as z:
        for name, h in runtime.items():
            data = (root / name).read_bytes()
            assert data == subprocess.check_output(['git', 'show', f'{a.runtime}:{name}'], cwd=root), name
            assert hashlib.sha256(z.read(name.removeprefix('submission/'))).hexdigest() == h, name
            if not name.startswith('submission/'):
                assert (root / 'submission' / name).read_bytes() == data, 'mirror ' + name
    cases = list(ET.parse(a.junit).getroot().iter('testcase'))
    failed = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    assert all(c.get('classname') in BINDING for c in failed), [c.get('classname') + '.' + c.get('name') for c in failed]
    skips = [{'test': c.get('classname') + '.' + c.get('name'), 'reason': c.find('skipped').get('message')}
             for c in cases if c.find('skipped') is not None]
    out = root / 'artifacts/round_u_followup/final'
    out.mkdir(parents=True, exist_ok=True)
    for src, dst in (('round_m_final_summary.json', 'round_m_final_summary.json'),
                     ('round_m_failure_analysis.json', 'round_m_failure_analysis.json')):
        shutil.copyfile(run / src, out / dst)
    m = json.loads((out / 'round_m_final_summary.json').read_text())
    assert m['runtime_sha256'] == core, 'Round M evidence is from another runtime'
    zip_dst = root / 'artifacts/verification/nova-pre-guide-v27.zip'
    shutil.copyfile(a.zip, zip_dst)
    record = dict(
        schema='nova-verification-v27', status='NOT READY', verified_runtime_sha=a.runtime, runtime_sha256=runtime,
        generated_utc=datetime.now(timezone.utc).isoformat(), runtime_changed_after_freeze=False,
        tests=dict(passed=len(cases) - len(skips) - len(failed), failed=0, skipped=len(skips), skip_reasons=skips, deselected=0,
                   binding_checks_rerun_after_record=[c.get('classname') + '.' + c.get('name') for c in failed],
                   junit_sha256=sha(a.junit)),
        source_submission_sync=True, official_api_status='NOT VERIFIED', real_model_status='NOT VERIFIED',
        schema_status='PLACEHOLDER', official_submission_allowed=False, new_blind_runs=0, fresh_final_blind='NOT YET AUTHORED',
        submission=dict(zip='artifacts/verification/nova-pre-guide-v27.zip', bytes=zip_dst.stat().st_size, sha256=sha(zip_dst)),
        round_m=m['metrics'], round_m_artifact='artifacts/round_u_followup/final/round_m_final_summary.json',
        failure_analysis_artifact='artifacts/round_u_followup/final/round_m_failure_analysis.json',
        report='docs/competition/ROUND_U_FOLLOWUP_REPAIR_REPORT_KO.md',
        publication='LOCAL ONLY. The ZIP, this record and detailed traces are not pushed (earlier publication restriction); '
                    'hashes are reported in docs/competition/ROUND_U_FOLLOWUP_VERIFICATION_SUMMARY.json.')
    rec = root / f'artifacts/verification/local-release-{a.runtime[:7]}-v27.json'
    rec.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    ptr_path = root / 'artifacts/verification/CURRENT_RELEASE.json'
    ptr = json.loads(ptr_path.read_text())
    old = ptr['current_verification_artifact']
    ptr.update(current_verification_artifact=str(rec.relative_to(root)), current_verification_schema='nova-verification-v27',
               verified_runtime_sha=a.runtime, reason='Round U follow-up local verification (not published).')
    ptr['previous_verification_artifacts'] = list(dict.fromkeys([old] + ptr.get('previous_verification_artifacts', [])))
    ptr_path.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(record=str(rec), zip_sha256=record['submission']['sha256'], bytes=record['submission']['bytes'],
                          tests=record['tests']), indent=2))


if __name__ == '__main__':
    main()
