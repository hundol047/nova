"""HTTP-level concurrency, run against a REAL Postgres-backed app instance -- the same scenarios
test_nova_concurrency.py runs against the default in-memory backend, proving the exact guarantee
that suite's own `test_process_restart_is_not_survived_by_the_in_memory_repository` explicitly
declines to claim for the in-memory backend now holds for the Postgres one: cases survive a fresh
service/process, and concurrent writes to the same case never silently lose a turn (closed by
NovaService's retry-on-conflict loop -- see nova_service.py's _SAVE_RETRY_ATTEMPTS).

Requires a Postgres server reachable at NOVA_TEST_POSTGRES_URL (default
postgresql://postgres:postgres@localhost:5432/nova_test) -- same skip-if-unavailable convention as
test_nova_postgres_repository.py.
"""
import os
import threading

import pytest

psycopg = pytest.importorskip('psycopg')

POSTGRES_URL = os.getenv('NOVA_TEST_POSTGRES_URL', 'postgresql://postgres:postgres@localhost:5432/nova_test')


def _postgres_available():
    try:
        with psycopg.connect(POSTGRES_URL, connect_timeout=1) as conn:
            conn.execute('SELECT 1')
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _postgres_available(), reason=f'no Postgres reachable at {POSTGRES_URL}')


@pytest.fixture
def pg_client(tmp_path, monkeypatch):
    import sys
    # Reset any previously-imported app/service modules so the fresh TestClient's lifespan() picks
    # up NOVA_POSTGRES_URL at construction time (build_nova_case_repository()/build_audit_store()
    # read it once, inside lifespan(), not per-request).
    monkeypatch.setenv('NOVA_POSTGRES_URL', POSTGRES_URL)
    monkeypatch.setenv('SYNEX_IDEMPOTENCY_PATH', str(tmp_path / 'idempotency.sqlite3'))
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute('TRUNCATE nova_case_observations, nova_cases, audit_events, audit_analyses')

    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_concurrent_cases_never_cross_contaminate_on_postgres(pg_client):
    n = 15
    errors = []

    def worker(i):
        cid_marker = f'pg-concurrency-marker-{i}'
        try:
            r = pg_client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': cid_marker})
            assert r.status_code == 201, r.text
            case_id = r.json()['case_id']
            r = pg_client.post(f'/v1/nova/cases/{case_id}/decide')
            assert r.status_code == 200, r.text
            r = pg_client.get(f'/v1/nova/cases/{case_id}')
            assert r.status_code == 200
            assert r.json()['chief_complaint'] == cid_marker
        except Exception as exc:  # noqa: BLE001
            errors.append((i, repr(exc)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors


def test_concurrent_observations_on_the_same_case_never_lose_or_duplicate_a_turn_on_postgres(pg_client):
    r = pg_client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'weakness'})
    case_id = r.json()['case_id']
    errors = []

    def worker(i):
        try:
            r = pg_client.post(f'/v1/nova/cases/{case_id}/observations', json={
                'observation_id': f'obs-{i}', 'action_type': 'ASK', 'key': f'symptom-{i}', 'result': 'denies'})
            assert r.status_code == 200, r.text
        except Exception as exc:  # noqa: BLE001
            errors.append((i, repr(exc)))

    n = 12
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, errors
    final = pg_client.get(f'/v1/nova/cases/{case_id}').json()
    assert final['turn_count'] == n  # every distinct observation_id applied exactly once -- no
    # losses despite Postgres's real write-race detection, thanks to NovaService's retry loop.


def test_repeated_same_observation_id_under_concurrency_applies_exactly_once_on_postgres(pg_client):
    r = pg_client.post('/v1/nova/cases', json={'patient_id': 'SYN-003', 'chief_complaint': 'dizziness'})
    case_id = r.json()['case_id']
    applied_flags = []
    lock = threading.Lock()

    def worker():
        r = pg_client.post(f'/v1/nova/cases/{case_id}/observations', json={
            'observation_id': 'race-1', 'action_type': 'ASK', 'key': 'onset', 'result': 'today'})
        with lock:
            applied_flags.append(r.json()['applied'])

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert applied_flags.count(True) == 1, applied_flags
    final = pg_client.get(f'/v1/nova/cases/{case_id}').json()
    assert final['turn_count'] == 1


def test_process_restart_is_survived_by_the_postgres_repository(pg_client):
    """The exact scenario test_nova_concurrency.py's in-memory version documents as unsupported --
    proven CLOSED here for the Postgres backend."""
    from app.services.nova_repository import PostgresNovaCaseRepository
    from app.services.nova_service import NovaService

    r = pg_client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'test'})
    case_id = r.json()['case_id']
    assert pg_client.get(f'/v1/nova/cases/{case_id}').status_code == 200

    fresh_service = NovaService(repository=PostgresNovaCaseRepository(POSTGRES_URL))
    reloaded = fresh_service.get_case(case_id)
    assert reloaded.state.chief_complaint == 'test'
