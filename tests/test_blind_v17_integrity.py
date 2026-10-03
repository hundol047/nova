"""Integrity only: never execute the one-shot holdout from pytest."""
import hashlib,json,zipfile
from pathlib import Path
from evaluation.blind_cases_v17 import BLIND_CASES_V17
from evaluation.current_blind import CURRENT_BLIND_VERSION,reference_only_versions
from nova_agent.taxonomy import TEST_CATALOG,EXAM_CATALOG
ROOT=Path(__file__).resolve().parents[1]

def test_current_and_historical_sets_are_distinguished():
    assert CURRENT_BLIND_VERSION=='v17'
    assert 'v16' in reference_only_versions()
    assert 'v17' in reference_only_versions()

def test_v17_manifest_hash_and_case_schema():
    m=json.loads((ROOT/'evaluation/blind_v17_manifest.json').read_text())
    assert hashlib.sha256((ROOT/'evaluation/blind_cases_v17.py').read_bytes()).hexdigest()==m['file_sha256']
    assert len(BLIND_CASES_V17)==m['case_count']==60
    assert len({c.case_id for c in BLIND_CASES_V17})==60
    for c in BLIND_CASES_V17:
        assert set(c.test_results)<=set(TEST_CATALOG)
        assert set(c.exam_results)<=set(EXAM_CATALOG)
    assert len(m['declared_runs'])==1
    assert m['declared_runs'][0]['count']==1
    assert not m['independent_clinical_validation'] and not m['expert_reviewed']

def test_historical_frozen_runtime_and_submission_bytes_are_unchanged():
    m=json.loads((ROOT/'evaluation/blind_v17_manifest.json').read_text())
    # Preserved v8 ZIP contains the exact frozen bytes, also available in shallow CI checkouts.
    # Check every historical root AND mirrored runtime hash, without claiming today's runtime
    # is still v17-compatible or weakening the one-shot runner's current-file freeze check.
    with zipfile.ZipFile(ROOT/'artifacts/verification/nova-submission-v8.zip') as z:
        for p,h in m['runtime_sha256'].items():
            archived=p.removeprefix('submission/')
            assert hashlib.sha256(z.read(archived)).hexdigest()==h,p

def test_second_attempt_is_rejected_before_diagnostic_execution(monkeypatch,tmp_path):
    import evaluation.blind_benchmark_v17 as b
    monkeypatch.setattr(b,'ROOT',tmp_path)
    monkeypatch.setattr(b,'verify',lambda:{'final_reasoning_sha':'test'})
    monkeypatch.setattr(b.subprocess,'check_output',lambda *a,**k:'test')
    monkeypatch.setattr(b,'run_all',lambda *a: (_ for _ in ()).throw(AssertionError('Must not run')))
    out=tmp_path/'artifacts/blind_runs';out.mkdir(parents=True)
    marker=out/'blind_v17_attempt.json';marker.write_text('existing attempt')
    import pytest
    with pytest.raises(FileExistsError):b.main()
    assert marker.read_text()=='existing attempt'
