"""Current release integrity, independent of preserved historical v18 runtime assertions."""
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def release():
    p={'current_verification_artifact':'artifacts/verification/local-release-f315fbf-v11.json', 'current_verification_schema':'nova-verification-v11', 'verified_runtime_sha':'f315fbf27bafaaeecb43344428ac61d7fe1a7a05'}
    d=json.loads((ROOT/p['current_verification_artifact']).read_text())
    assert p['current_verification_schema']==d['schema']=='nova-verification-v11'
    assert p['verified_runtime_sha']==d['verified_runtime_sha']
    return d


def test_current_runtime_and_submission_match_frozen_hashes():
    d=release();package=ROOT/d['submission']['zip']
    assert package.stat().st_size==d['submission']['bytes']<50_000_000
    assert hashlib.sha256(package.read_bytes()).hexdigest()==d['submission']['sha256']
    with zipfile.ZipFile(package) as z:
        manifest=json.loads(z.read('MANIFEST.json'))
        assert set(z.namelist())==set(manifest['files'])|{'MANIFEST.json'}
        for name,h in manifest['files'].items():
            assert name in {'run.py','requirements.txt'} or name.startswith(('nova_agent/','competition/'))
            assert hashlib.sha256(z.read(name)).hexdigest()==h
            # Historical ZIP is immutable; current runtime is verified by the current release test.
        for name,h in d['runtime_sha256'].items():
            # Historical runtime hash is checked against its archived ZIP below.
            assert hashlib.sha256(z.read(name.removeprefix('submission/'))).hexdigest()==h,name


def test_complete_development_traces_are_lossless_and_all_misses_are_attributed():
    d=release()
    required={'raw_retrieval_ranks','rrf_score','rerank_rank','active_differential_rank',
        'diagnostic_score','specific_evidence_score','generic_evidence_score','objective_evidence_score',
        'risk_score','medication_score','negative_evidence','contradictions','safety_only_support',
        'provenance','active','resolved'}
    for phase in ('before','after'):
        base=ROOT/'artifacts/round_j'/phase;s=json.loads((base/'summary.json').read_text())
        archive=base/'traces.tar.xz'
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==s['trace_archive_sha256']==d['trace_archive_sha256'][phase]
        expected={r['trace_file']:r for r in s['cases']};seen=set()
        assert len(expected)==54 and sum(r['scored'] for r in expected.values())==52
        with tarfile.open(archive,'r|xz') as tf:
            for member in tf:
                assert member.isfile() and member.name in expected and member.name not in seen
                payload=tf.extractfile(member).read();row=expected[member.name]
                assert hashlib.sha256(payload).hexdigest()==row['trace_sha256']
                trace=json.loads(payload);assert len(trace['turns'])==row['turns']
                assert bool(row['primary_failure'])==bool(row['scored'] and not row['correct'])
                for turn in trace['turns']:
                    assert all(required<=set(c) for c in turn['candidates'])
                seen.add(member.name)
        assert seen==set(expected)


def test_reference_only_and_external_limits_remain_explicit():
    d=release()
    assert d['current_blind_version']=='v18' and d['current_blind_status']=='REFERENCE-ONLY'
    assert not d['v18_rerun'] and not d['v18_cases_changed'] and not d['v19_created']
    assert not d['independent_clinical_validation'] and not d['expert_reviewed']
    assert d['official_api_status']==d['real_model_status']=='NOT VERIFIED'
    assert d['schema_status']=='PLACEHOLDER' and not d['runtime_changed_after_freeze']
    assert (ROOT/'docs/round_j/FINAL_REASONING_SHA.txt').read_text().strip()==d['verified_runtime_sha']
    assert d['verified_runtime_sha'] in (ROOT/d['report']).read_text()
