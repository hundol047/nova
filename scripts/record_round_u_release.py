"""Bind local v26 evidence to executed source, commit and exact ZIP bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.runtime_identity import tracked_runtime_hashes


def read(name):
    return json.loads((ROOT/name).read_text())


def digest(name):
    return hashlib.sha256((ROOT/name).read_bytes()).hexdigest()


def write(name, data):
    p = ROOT/name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runtime', required=True)
    a = p.parse_args()
    base = 'artifacts/round_u/final/'
    core = tracked_runtime_hashes(ROOT)
    runtime = dict(core, **{n:digest(n) for n in ('submission/run.py','submission/requirements.txt')})
    for name in runtime:
        assert (ROOT/name).read_bytes() == subprocess.check_output(['git','show',a.runtime+':'+name],cwd=ROOT), name
    required_checks = ('pytest_runtime pytest_research pytest_package_completion prelim round_p round_q '
        'round_r round_s acceptance_regression round_t_development confirmation_development probe_development '
        'post_t new_validation confirmation final_confirmation closing regressions round_m assertion_contrasts '
        'provenance specificity routing retrieval_stages retrieval_benchmark adversarial failure_analysis leakage '
        'package_build package_audit zip_validation fresh_package_mock').split()
    if (ROOT/base/'pytest_release.execution.json').exists():
        required_checks.append('pytest_release')
    executions = {}
    for name in required_checks:
        rec = read(base+name+'.execution.json')
        assert rec['exit_code'] == 0 and rec['runtime_unchanged'], name
        assert rec['head'] == a.runtime and rec['runtime_sha256'] == core, name
        assert rec['output_sha256'] == digest(base+name+'.log'), name
        executions[name] = {k:rec[k] for k in ('exit_code','started_utc','finished_utc','runtime_unchanged','output_sha256','conditions')}
    reg = read(base+'regressions.json')
    assert reg['runtime_unchanged_during_execution'] and reg['runtime_sha256'] == core
    m = read(base+'round_m/final_summary.json')
    assert m['runtime_sha256'] == core
    new = read(base+'closing/summary.json')
    assert new['runtime_unchanged'] and new['runtime_sha256'] == core
    assert new['fixture_sha256'] == read('evaluation/frozen_validation_round_u_closing_manifest.json')['sha256']
    files = [base+'pytest_runtime.xml', base+'pytest_research.xml']
    if (ROOT/base/'pytest_release.xml').exists():
        files.append(base+'pytest_release.xml')
    cases = [c for f in files for c in ET.parse(ROOT/f).getroot().iter('testcase')]
    assert len(cases) == len({(c.get('classname'), c.get('name')) for c in cases})
    assert not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
    # The first full suite intentionally preceded copying the already audited ZIP.
    # Complete its one package-not-built skip without rerunning thousands of tests
    # or rewriting the original JUnit. Only a prior SKIP may be replaced by PASS.
    completed_skips = []
    supplement = base+'pytest_package_completion.xml'
    if (ROOT/supplement).exists():
        index = {(c.get('classname'), c.get('name')):i for i,c in enumerate(cases)}
        for c in ET.parse(ROOT/supplement).getroot().iter('testcase'):
            key = c.get('classname'),c.get('name')
            assert key in index and len(c) == 0
            previous = cases[index[key]]
            assert previous.find('skipped') is not None
            completed_skips.append({'test':'.'.join(key),'original_reason':previous.find('skipped').get('message'),
                                    'completion_junit':supplement,'result':'PASS'})
            cases[index[key]] = c
        files.append(supplement)
    skips = [{'test':c.get('classname')+'.'+c.get('name'),'reason':c.find('skipped').get('message')}
             for c in cases if c.find('skipped') is not None]
    tests = dict(passed=len(cases)-len(skips), failed=0, skipped=len(skips), skip_reasons=skips,
                 deselected=0, not_executed=[] if base+'pytest_release.xml' in files else ['3 release-binding checks pending'],
                 scope='Complete unique tests/: runtime, NCIt research, release binding; one initial package skip completed separately.',
                 completed_initial_skips=completed_skips,
                 junit_sha256={f:digest(f) for f in files})
    audit = read(base+'package_audit.json')
    validation = read(base+'zip_validation.json')
    assert audit['source_submission_byte_equivalence'] and validation['all_pass']
    assert audit['secret_scan']['status'] == 'PASS'
    package = 'artifacts/verification/nova-pre-guide-v26.zip'
    assert digest(package) == audit['zip_sha256'] == validation['sha256']
    with zipfile.ZipFile(ROOT/package) as z:
        for name,h in runtime.items():
            assert hashlib.sha256(z.read(name.removeprefix('submission/'))).hexdigest() == h, name
    artifact = 'artifacts/verification/local-release-'+a.runtime[:7]+'-v26.json'
    data = dict(schema='nova-verification-v26', status='NOT READY', verified_runtime_sha=a.runtime,
        runtime_sha256=runtime, generated_utc=datetime.now(timezone.utc).isoformat(),
        runtime_changed_after_freeze=False, tests=tests, source_submission_sync=True,
        execution_summary=executions,
        official_api_status='NOT VERIFIED', real_model_status='NOT VERIFIED', schema_status='PLACEHOLDER',
        official_submission_allowed=False, new_blind_runs=0, fresh_final_blind='NOT YET AUTHORED',
        submission=dict(zip=package, bytes=(ROOT/package).stat().st_size, sha256=digest(package)),
        round_m=m['metrics'], round_m_artifact=base+'round_m/final_summary.json',
        failure_analysis_artifact=base+'round_m/failure_analysis.json',
        preliminary=read(base+'prelim.json')['summaries'], regressions={k:v['summary'] for k,v in reg['suites'].items()},
        new_validation=dict(artifact=base+'closing/summary.json',summary=new['summary'],behavior=new['behavior'],limitation=new['limitation']),
        reasoning_freeze_artifact=base+'reasoning_freeze.json', report='docs/competition/ROUND_U_REPAIR_REPORT_KO.md',
        acceptance='See report: engineering regression, behavioral validation, package integrity and external/clinical validation are separate.',
        publication='Local complete evidence; public source-review parity is separately recorded. No claim of public detailed traces or ZIP.')
    write(artifact,data)
    write(base+'test_summary.json',tests)
    pointer = read('artifacts/verification/CURRENT_RELEASE.json')
    old = pointer['current_verification_artifact']
    pointer.update(current_verification_artifact=artifact,current_verification_schema='nova-verification-v26',
                   verified_runtime_sha=a.runtime, reason='Round U offline relations, evidence and retrieval repair; see final report for limits.')
    if old != artifact:
        pointer['previous_verification_artifacts'] = list(dict.fromkeys([old]+pointer['previous_verification_artifacts']))
    write('artifacts/verification/CURRENT_RELEASE.json',pointer)
    print(json.dumps(dict(artifact=artifact,tests=tests,zip_sha256=digest(package)),indent=2))


if __name__ == '__main__':
    main()
