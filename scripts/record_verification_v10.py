"""Record executed evidence, never execute/retry a blind evaluation or modify frozen runtime."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(name):
    return json.loads((ROOT/name).read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(junit, final_tests=False):
    manifest = read('evaluation/blind_v18_manifest.json')
    frozen = manifest['final_reasoning_sha']
    for name, expected in manifest['runtime_sha256'].items():
        data = (ROOT/name).read_bytes()
        assert digest(data) == expected, name
        assert data == subprocess.check_output(['git','show',frozen+':'+name],cwd=ROOT), name
        if name.startswith(('nova_agent/','competition/')):
            assert data == (ROOT/'submission'/name).read_bytes(), name
    result = read('artifacts/blind_runs/blind_v18_results.json')
    attempt = read('artifacts/blind_runs/blind_v18_attempt.json')
    assert result['status'] == 'COMPLETED' and result['run_count'] == 1
    assert result['runtime_sha'] == attempt['runtime_sha'] == frozen
    assert result['authoring_sha'] == attempt['authoring_sha']
    assert result['manifest_sha256'] == attempt['manifest_sha256'] == digest((ROOT/'evaluation/blind_v18_manifest.json').read_bytes())
    assert digest((ROOT/'evaluation/blind_cases_v18.py').read_bytes()) == manifest['file_sha256']
    assert digest((ROOT/'evaluation/blind_benchmark_v18.py').read_bytes()) == manifest['runner_sha256']

    archive = 'artifacts/verification/nova-submission-v10.zip'
    # Preserve archive bytes across metadata-only updates after final pytest.
    if not (ROOT/archive).exists():
        shutil.copyfile(ROOT/'submission/submission.zip',ROOT/archive)
    with zipfile.ZipFile(ROOT/archive) as z:
        archive_names = z.namelist()
        package_manifest = json.loads(z.read('MANIFEST.json'))
        assert {'run.py','requirements.txt','MANIFEST.json'} <= set(archive_names)
        assert set(archive_names) == set(package_manifest['files']) | {'MANIFEST.json'}
        for name, expected in package_manifest['files'].items():
            assert name in {'run.py','requirements.txt'} or name.startswith(('nova_agent/','competition/'))
            assert digest(z.read(name)) == expected and z.read(name) == (ROOT/'submission'/name).read_bytes()
    size = (ROOT/archive).stat().st_size
    assert size < 50_000_000

    cases = list(ElementTree.parse(junit).getroot().iter('testcase'))
    failed = sum(c.find('failure') is not None or c.find('error') is not None for c in cases)
    skipped = sum(c.find('skipped') is not None for c in cases)
    assert not failed and len(cases) > 800
    test_names = {c.get('name') for c in cases}
    assert {'test_isolated_submission_runtime_modes[mock]', 'test_isolated_submission_runtime_modes[unreachable]',
        'test_isolated_submission_runtime_modes[stub]', 'test_preflight_success_does_not_credit_new_case',
        'test_schema_blocks_official_readiness_even_with_valid_stub'} <= test_names
    tests = dict(passed=len(cases)-skipped,failed=failed,skipped=skipped,finalized=final_tests,
        source='Parsed executed pytest JUnit XML',junit_sha256=digest(Path(junit).read_bytes()),
        skip_reasons=[c.find('skipped').get('message') for c in cases if c.find('skipped') is not None])
    regression = read('artifacts/round_i/regression/competition_metrics.json')
    deltas = read('artifacts/round_i/regression/deltas.json')
    assert all(d['accuracy_delta'] >= 0 and d['critical_delta'] >= 0 for d in deltas.values())
    assert all(c['returncode'] == 0 for c in read('artifacts/round_i/regression/checks.json'))
    round_g = read('artifacts/round_i/round_g_summary.json')
    assert round_g == read('artifacts/round_g/after_summary.json')
    retrieval_text = (ROOT/'artifacts/round_i/regression/retrieval.txt').read_text()
    retrieval = {}
    for name, section in re.findall(r'-- (chief_complaint_\w+) \(n=44\) --(.*?)(?=\n--|\nBaseline)',retrieval_text,re.S):
        retrieval[name] = {f'Recall@{k}':float(v)/100 for k,v in re.findall(r'Recall@(20|50): baseline [\d.]+% -> new ([\d.]+)%',section)}
    assert len(retrieval) == 2
    preflight = read('artifacts/round_i/real_model_preflight.json')
    assert preflight['status'] == 'NOT_CONFIGURED' and not preflight['official_submission_ready']
    prefix = ROOT/'artifacts/round_i'
    (prefix/'pytest_summary.json').write_text(json.dumps(tests,indent=2)+'\n')
    data = dict(schema='nova-verification-v10',status='LOCAL_VERIFICATION_COMPLETED_EXTERNAL_BLOCKED',
        generated_utc=datetime.now(timezone.utc).isoformat(),verified_runtime_sha=frozen,
        runtime_changed_after_freeze=False,runtime_sha256=manifest['runtime_sha256'],
        current_blind_version='v18',current_blind_status='CURRENT',new_blind_runs=1,
        blind_v18=dict(provider='COMPETITION-STRUCTURE / MOCK-LLM',authoring_sha=result['authoring_sha'],
            file_sha256=manifest['file_sha256'],manifest_sha256=result['manifest_sha256'],run_count=1,
            cases=result['case_count'],scored_cases=result['scored_case_count'],critical_cases=result['critical_case_count'],
            summary=result['summary'],result_sha256=digest((ROOT/'artifacts/blind_runs/blind_v18_results.json').read_bytes())),
        v17_cases_changed=False,v17_rerun=False,tests=tests,
        ood=read('artifacts/round_i/after.json')['ood']['metrics'],
        ood_regression=read('artifacts/round_i/ood_regression.json')['metrics'],
        ranking=read('artifacts/round_i/after.json')['ranking'],
        ranking_before=read('artifacts/round_i/baseline.json')['ranking'],
        data_type='SYNTHETIC DEVELOPMENT AND POST-FREEZE SYNTHETIC HOLDOUT / MOCK-LLM',
        independent_clinical_validation=False,expert_reviewed=False,
        real_gpt_oss=preflight,official_api_status='NOT VERIFIED',schema_status='PLACEHOLDER',
        legal_action_names='CONFIRMED_OFFICIAL; JSON encoding PLACEHOLDER',
        real_call_gate='PASS in local HTTP stub and isolated case tests; not live model verification',
        runtime_modes=dict(mock='PASS',unreachable_fails_closed='PASS',local_protocol_stub='PASS; NOT real model verification',real_model='NOT VERIFIED',official_api='NOT VERIFIED'),
        submission=dict(zip=archive,bytes=size,sha256=digest((ROOT/archive).read_bytes()),file_count=len(archive_names),
            under_50mb=True,source_sync=True,secret_scan='PASS / build scanner',standalone='PASS / isolated mock, unreachable and local stub',
            dependencies=['pydantic>=2.6,<3'],default_provider='competition'),
        regression_competition=regression,regression_deltas=deltas,round_g=round_g,
        retrieval= retrieval,retrieval_regression=False,critical_recall_regression=False,
        limitations=['No configured official endpoint/token; real model comparison was not run.',
            'Server model/revision identity is not independent attestation of weights.',
            'Official executable schema/auth/endpoint/abstention legality remain externally blocked.',
            'Same-author synthetic v18 is not independently adjudicated clinical evaluation.',
            'Artificial default negatives and lexical label matching can bias simulator metrics.',
            'Round I positional dizziness and long-tail retrieval failures remain; Round G systemic-infection miss remains.',
            'Forced final labels under the provisional protocol must not be read as confident clinical diagnoses.',
            'No model training or calibrated probability/99.99% accuracy claim.'])
    rel=f'artifacts/verification/local-release-{frozen[:7]}-v10.json'
    (ROOT/rel).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    pointer=read('artifacts/verification/CURRENT_RELEASE.json')
    previous=pointer['previous_verification_artifacts']
    v9='artifacts/verification/local-release-14e6644-v9.json'
    if v9 not in previous: previous.insert(0,v9)
    pointer.update(current_verification_artifact=rel,current_verification_schema=data['schema'],verified_runtime_sha=frozen,
        current_blind_version='v18',current_blind_manifest='evaluation/blind_v18_manifest.json',current_blind_status='CURRENT',
        status=data['status'],updated_utc=data['generated_utc'],reason='Frozen Round I runtime and one v18 mock run; external gates remain blocked.')
    (ROOT/'artifacts/verification/CURRENT_RELEASE.json').write_text(json.dumps(pointer,indent=2)+'\n')
    print(json.dumps(dict(artifact=rel,tests=tests,zip_bytes=size,archive_files=len(archive_names)),indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--junit',required=True);p.add_argument('--final-tests',action='store_true')
    a=p.parse_args();record(a.junit,a.final_tests)
