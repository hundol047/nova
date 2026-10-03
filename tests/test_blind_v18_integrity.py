"""Integrity only: never execute the consumed one-shot benchmark from pytest."""
import hashlib
import json
from pathlib import Path
import pytest
from evaluation.blind_cases_v18 import BLIND_CASES_V18
from evaluation.current_blind import CURRENT_BLIND_VERSION, CURRENT_BLIND_STATUS, reference_only_versions
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG

ROOT = Path(__file__).resolve().parents[1]


def test_v18_case_manifest_runner_and_frozen_runtime_hashes():
    m = json.loads((ROOT/'evaluation/blind_v18_manifest.json').read_text())
    assert CURRENT_BLIND_VERSION == 'v18' and CURRENT_BLIND_STATUS == 'CURRENT'
    assert 'v17' in reference_only_versions()
    for filename,key in [('blind_cases_v18.py','file_sha256'),('blind_benchmark_v18.py','runner_sha256')]:
        assert hashlib.sha256((ROOT/'evaluation'/filename).read_bytes()).hexdigest() == m[key]
    for name,digest in m['runtime_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    assert len(BLIND_CASES_V18) == m['case_count'] == 64
    assert len({c.case_id for c in BLIND_CASES_V18}) == 64
    assert sum(c.scoring_expected for c in BLIND_CASES_V18) == m['scored_case_count'] == 58
    for c in BLIND_CASES_V18:
        assert set(c.test_results) <= set(TEST_CATALOG)
        assert set(c.exam_results) <= set(EXAM_CATALOG)
    assert len(m['declared_runs']) == 1 and m['declared_runs'][0]['count'] == 1
    assert not m['independent_clinical_validation'] and not m['expert_reviewed']


def test_v18_second_attempt_rejected_without_executing_a_case(monkeypatch,tmp_path):
    import evaluation.blind_benchmark_v18 as b
    monkeypatch.setattr(b,'ROOT',tmp_path)
    monkeypatch.setattr(b,'verify',lambda:{'final_reasoning_sha':'test'})
    monkeypatch.setattr(b.subprocess,'check_output',lambda *a,**k:'test')
    monkeypatch.setattr(b,'run_all',lambda *a:pytest.fail('must not execute a case'))
    (tmp_path/'evaluation').mkdir()
    (tmp_path/'evaluation/blind_v18_manifest.json').write_text('{}')
    out=tmp_path/'artifacts/blind_runs';out.mkdir(parents=True)
    marker=out/'blind_v18_attempt.json';marker.write_text('already attempted')
    with pytest.raises(FileExistsError):
        b.main()
    assert marker.read_text() == 'already attempted'
