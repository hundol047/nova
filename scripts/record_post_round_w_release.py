#!/usr/bin/env python3
"""Post-Round-W: bind the v30 verification evidence to the executed runtime commit and the audited archive.

Unlike the Round R-W recorders, the record and pointer are written into --repo to be COMMITTED, while the ZIP stays
local (earlier publication restriction). The archive is pinned member by member (`submission.member_sha256`), so CI can
check every member against the committed submission mirror without the archive itself (see
tests/test_current_pre_guide_release.py).

Refuses unless every runtime file equals the commit, the submission mirror and the ZIP, and unless the only failures
in each supplied JUnit are the release-binding checks that read this very record (they are re-run after).

    python scripts/record_post_round_w_release.py --checkout <verification worktree> --repo . --runtime <sha> \
        --run-dir <suite output> --zip <checkout>/submission/submission.zip --junit a.xml --junit b.xml ...
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


def junit_summary(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    failed = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
    assert all(c.get('classname') in BINDING for c in failed), \
        [c.get('classname') + '.' + c.get('name') for c in failed]
    skips = [{'test': c.get('classname') + '.' + c.get('name'), 'reason': c.find('skipped').get('message')}
             for c in cases if c.find('skipped') is not None]
    return dict(passed=len(cases) - len(skips) - len(failed), failed=0, skipped=len(skips), skip_reasons=skips,
                binding_checks_rerun_after_record=[c.get('classname') + '.' + c.get('name') for c in failed],
                junit_sha256=sha(path))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--checkout', required=True)
    p.add_argument('--repo', required=True)
    p.add_argument('--runtime', required=True)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--zip', required=True)
    p.add_argument('--junit', action='append', required=True, help='label=path (e.g. py3.11=/tmp/junit.xml)')
    p.add_argument('--version', default='v30', help='schema suffix (v30 post-Round-W, v31 Round X, ...)')
    p.add_argument('--evidence-dir', default='artifacts/post_round_w/final')
    p.add_argument('--report', default='docs/preliminary/POST_ROUND_W_REPORT.md')
    p.add_argument('--reason', default='Post-Round-W verification (record committed; archive local).')
    p.add_argument('--extra', help='JSON file merged into the record (e.g. official SDK integration statuses)')
    a = p.parse_args()
    root, repo, run = Path(a.checkout).resolve(), Path(a.repo).resolve(), Path(a.run_dir).resolve()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    assert head == a.runtime, (head, a.runtime)
    names = subprocess.check_output(['git', 'ls-files', 'nova_agent', 'competition'], cwd=root, text=True).split()
    core = {n: sha(root / n) for n in sorted(names) if Path(n).suffix in {'.py', '.json', '.md'}}
    runtime = dict(core, **{n: sha(root / n) for n in ('submission/run.py', 'submission/requirements.txt')})
    with zipfile.ZipFile(a.zip) as z:
        members = {i.filename: hashlib.sha256(z.read(i.filename)).hexdigest() for i in z.infolist()}
        for name, h in runtime.items():
            data = (root / name).read_bytes()
            assert data == subprocess.check_output(['git', 'show', f'{a.runtime}:{name}'], cwd=root), name
            assert members[name.removeprefix('submission/')] == h, name
            if not name.startswith('submission/'):
                assert (root / 'submission' / name).read_bytes() == data, 'mirror ' + name
            assert (repo / name).read_bytes() == data, 'repo differs from the verified runtime: ' + name
    for name, h in members.items():
        if name != 'MANIFEST.json':
            assert sha(root / 'submission' / name) == h, 'archive member differs from the mirror: ' + name
    tests = {label: junit_summary(path) for label, path in (j.split('=', 1) for j in a.junit)}
    out = repo / a.evidence_dir
    out.mkdir(parents=True, exist_ok=True)
    for name in ('round_m_final_summary.json', 'round_m_failure_analysis.json'):
        shutil.copyfile(run / name, out / name)
    m = json.loads((out / 'round_m_final_summary.json').read_text())
    assert m['runtime_sha256'] == core, 'Round M evidence is from another runtime'
    zip_path = Path(a.zip)
    primary = tests[sorted(tests)[0]]
    record = dict(
        schema=f'nova-verification-{a.version}', status='NOT READY', verified_runtime_sha=a.runtime, runtime_sha256=runtime,
        generated_utc=datetime.now(timezone.utc).isoformat(), runtime_changed_after_freeze=False,
        tests=dict(primary, deselected=0, by_interpreter=tests),
        source_submission_sync=True, official_api_status='NOT VERIFIED', real_model_status='NOT VERIFIED',
        official_model='openai/gpt-oss-20b@4d7ae4984b7db7de8f8457170b3f1a419ee76d52 (NOT VERIFIED; transport BLOCKED; fail-closed)',
        schema_status='PLACEHOLDER', official_submission_allowed=False, new_blind_runs=0, fresh_final_blind='NOT YET AUTHORED',
        submission=dict(zip='LOCAL ONLY (not in the repository)', publication='LOCAL_ONLY', bytes=zip_path.stat().st_size,
                        sha256=sha(zip_path), member_sha256=members, status='PRE-GUIDE CANDIDATE / NOT OFFICIALLY READY'),
        round_m=m['metrics'], round_m_artifact=f'{a.evidence_dir}/round_m_final_summary.json',
        failure_analysis_artifact=f'{a.evidence_dir}/round_m_failure_analysis.json',
        report=a.report,
        publication='The record and member hashes are committed; the ZIP and detailed traces stay local (earlier '
                    'publication restriction). CI verifies every archive member against the committed mirror.')
    if a.extra:
        record.update(json.loads(Path(a.extra).read_text()))
    rec = repo / f'artifacts/verification/local-release-{a.runtime[:7]}-{a.version}.json'
    rec.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    ptr_path = repo / 'artifacts/verification/CURRENT_RELEASE.json'
    ptr = json.loads(ptr_path.read_text())
    old = ptr['current_verification_artifact']
    ptr.update(current_verification_artifact=str(rec.relative_to(repo)), current_verification_schema=f'nova-verification-{a.version}',
               verified_runtime_sha=a.runtime, reason=a.reason)
    ptr['previous_verification_artifacts'] = list(dict.fromkeys([old] + ptr.get('previous_verification_artifacts', [])))
    ptr_path.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(record=str(rec), zip_sha256=record['submission']['sha256'], bytes=record['submission']['bytes'],
                          tests={k: (v['passed'], v['failed'], v['skipped']) for k, v in tests.items()}), indent=2))


if __name__ == '__main__':
    main()
