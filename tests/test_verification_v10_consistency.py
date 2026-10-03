import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def current():
    # Frozen historical release; the current runtime is verified separately by v11.
    d = json.loads((ROOT/'artifacts/verification/local-release-d6e2b84-v10.json').read_text())
    assert d['schema'] == 'nova-verification-v10'
    return d


def test_historical_v10_archive_and_frozen_hashes_agree():
    d=current(); package=ROOT/d['submission']['zip']
    assert package.stat().st_size == d['submission']['bytes'] < 50_000_000
    assert hashlib.sha256(package.read_bytes()).hexdigest() == d['submission']['sha256']
    with zipfile.ZipFile(package) as z:
        assert len(z.namelist()) == d['submission']['file_count']
        assert {'run.py','requirements.txt','MANIFEST.json'} <= set(z.namelist())
        m=json.loads(z.read('MANIFEST.json'))
        assert set(z.namelist()) == set(m['files']) | {'MANIFEST.json'}
        for name,h in m['files'].items():
            assert name in {'run.py','requirements.txt'} or name.startswith(('nova_agent/','competition/'))
            assert hashlib.sha256(z.read(name)).hexdigest() == h
        for name,h in d['runtime_sha256'].items():
            assert hashlib.sha256(z.read(name.removeprefix('submission/'))).hexdigest() == h


def test_historical_v10_blind_attempt_manifest_and_result_agree():
    d=current(); m=json.loads((ROOT/'evaluation/blind_v18_manifest.json').read_text())
    r=json.loads((ROOT/'artifacts/blind_runs/blind_v18_results.json').read_text())
    a=json.loads((ROOT/'artifacts/blind_runs/blind_v18_attempt.json').read_text())
    assert d['verified_runtime_sha'] == m['final_reasoning_sha'] == r['runtime_sha'] == a['runtime_sha']
    assert d['blind_v18']['manifest_sha256'] == r['manifest_sha256'] == a['manifest_sha256']
    assert hashlib.sha256((ROOT/'evaluation/blind_v18_manifest.json').read_bytes()).hexdigest() == a['manifest_sha256']
    assert d['blind_v18']['result_sha256'] == hashlib.sha256((ROOT/'artifacts/blind_runs/blind_v18_results.json').read_bytes()).hexdigest()
    assert d['blind_v18']['summary'] == r['summary']
    assert d['blind_v18']['run_count'] == r['run_count'] == 1
    assert not d['v17_cases_changed'] and not d['v17_rerun'] and not d['runtime_changed_after_freeze']


def test_v10_never_promotes_mock_or_stub_to_official_model_verification():
    d=current()
    assert not d['independent_clinical_validation'] and not d['expert_reviewed']
    assert d['official_api_status'] == 'NOT VERIFIED' and d['schema_status'] == 'PLACEHOLDER'
    assert d['real_gpt_oss']['status'] == 'NOT_CONFIGURED'
    assert not d['real_gpt_oss']['official_submission_ready']
    assert d['runtime_modes']['real_model'] == d['runtime_modes']['official_api'] == 'NOT VERIFIED'
    assert 'NOT real model' in d['runtime_modes']['local_protocol_stub']
    assert d['tests']['failed'] == 0 and d['tests']['passed'] > 800
