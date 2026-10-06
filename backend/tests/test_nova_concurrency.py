"""Concurrency safety for /v1/nova/* (spec: no cross-case state leakage / race condition under
concurrent cases, concurrent observations, concurrent decide calls; process-restart recovery is
explicitly NOT claimed here -- see the last test's docstring for why).
"""

import threading

import pytest


def test_concurrent_cases_never_cross_contaminate(client):
    n = 20
    errors = []

    def worker(i):
        cid_marker = f'concurrency-marker-{i}'
        try:
            r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': cid_marker})
            assert r.status_code == 201, r.text
            case_id = r.json()['case_id']
            r = client.post(f'/v1/nova/cases/{case_id}/decide')
            assert r.status_code == 200, r.text
            r = client.get(f'/v1/nova/cases/{case_id}')
            assert r.status_code == 200
            assert r.json()['chief_complaint'] == cid_marker
        except Exception as exc:  # noqa: BLE001 - collected, not raised inside a worker thread
            errors.append((i, repr(exc)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors


def test_concurrent_observations_on_the_same_case_never_lose_or_duplicate_a_turn(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'weakness'})
    case_id = r.json()['case_id']
    errors = []

    def worker(i):
        try:
            r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
                'observation_id': f'obs-{i}', 'action_type': 'ASK', 'key': f'symptom-{i}', 'result': 'denies'})
            assert r.status_code == 200, r.text
        except Exception as exc:  # noqa: BLE001
            errors.append((i, repr(exc)))

    n = 15
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    final = client.get(f'/v1/nova/cases/{case_id}').json()
    assert final['turn_count'] == n  # every distinct observation_id applied exactly once


def test_repeated_same_observation_id_under_concurrency_applies_exactly_once(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-003', 'chief_complaint': 'dizziness'})
    case_id = r.json()['case_id']
    applied_flags = []
    lock = threading.Lock()

    def worker():
        r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
            'observation_id': 'race-1', 'action_type': 'ASK', 'key': 'onset', 'result': 'today'})
        with lock:
            applied_flags.append(r.json()['applied'])

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert applied_flags.count(True) == 1, applied_flags
    final = client.get(f'/v1/nova/cases/{case_id}').json()
    assert final['turn_count'] == 1


def test_process_restart_is_not_survived_by_the_in_memory_repository(client):
    """Documents the CURRENT, disclosed limitation rather than a success case: NovaCaseRepository
    is process-memory-only (same as every other Clinical Workspace repository in this backend
    today -- see nova_repository.py's own module docstring). A fresh NovaService (standing in for
    'the process restarted') has an empty repository and cannot see a case created before it. This
    is the reason docs/NOVA_DEPLOYMENT.md lists a database-backed NovaCaseRepository as a genuine
    remaining blocker, not something this test pretends is solved."""
    from app.services.nova_service import CaseNotFoundError, NovaService

    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'test'})
    case_id = r.json()['case_id']
    assert client.get(f'/v1/nova/cases/{case_id}').status_code == 200

    fresh_service = NovaService()
    with pytest.raises(CaseNotFoundError):
        fresh_service.get_case(case_id)
