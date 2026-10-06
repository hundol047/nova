"""Exercises PostgresNovaCaseRepository against a REAL local Postgres server (not a mock) -- proves
the in-memory NovaCaseRepository's disclosed process-restart limitation (see
test_process_restart_is_not_survived_by_the_in_memory_repository in test_nova_concurrency.py) is
actually closed by this backend, and that its optimistic-concurrency write-race detection works.

Requires a Postgres server reachable at NOVA_TEST_POSTGRES_URL (default
postgresql://postgres:postgres@localhost:5432/nova_test). Skips cleanly if that's not available,
rather than failing the whole suite in an environment without Postgres -- same shape as
test_smart_launch_redis.py's own skip-if-unavailable convention for its Redis-backed tests.
"""
import os

import pytest

psycopg = pytest.importorskip('psycopg')

from app.services.nova_repository import (CaseConflict, ConcurrentModificationError, NotFound,
                                           PostgresNovaCaseRepository)
from nova_agent.state import PatientState

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
def repo():
    r = PostgresNovaCaseRepository(POSTGRES_URL)
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute('TRUNCATE nova_case_observations, nova_cases')
    return r


def _new_state(case_id='pg-case-1', cc='chest pain'):
    return PatientState(case_id=case_id, chief_complaint=cc)


def test_create_and_get_round_trips_patient_state(repo):
    state = _new_state()
    created = repo.create(case_id='pg-case-1', patient_id='SYN-001', encounter_id=None, state=state,
                           created_by='tester', agent_version='v1', kb_version='kb1')
    assert created.status == 'open' and created.version == 0

    fetched = repo.get('pg-case-1')
    assert fetched.state.chief_complaint == 'chest pain'
    assert fetched.patient_id == 'SYN-001'
    assert fetched.applied_observation_ids == set()


def test_duplicate_case_id_raises_case_conflict(repo):
    state = _new_state()
    repo.create(case_id='pg-dup', patient_id='SYN-001', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    with pytest.raises(CaseConflict):
        repo.create(case_id='pg-dup', patient_id='SYN-001', encounter_id=None, state=state,
                    created_by='tester', agent_version='v1', kb_version='kb1')


def test_get_missing_case_raises_not_found(repo):
    with pytest.raises(NotFound):
        repo.get('does-not-exist')


def test_save_persists_state_mutations(repo):
    state = _new_state()
    repo.create(case_id='pg-save', patient_id='SYN-002', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    record = repo.get('pg-save')
    record.state.symptoms.append('nausea')
    repo.save(record)

    refetched = repo.get('pg-save')
    assert refetched.state.symptoms == ['nausea']
    assert refetched.version == 1


def test_try_apply_observation_is_atomic_and_idempotent(repo):
    state = _new_state()
    repo.create(case_id='pg-obs', patient_id='SYN-003', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    assert repo.try_apply_observation('pg-obs', 'obs-1') is True
    assert repo.try_apply_observation('pg-obs', 'obs-1') is False  # replay never re-applies
    assert repo.try_apply_observation('pg-obs', 'obs-2') is True


def test_try_apply_observation_concurrent_same_id_applies_exactly_once(repo):
    import threading
    state = _new_state()
    repo.create(case_id='pg-race', patient_id='SYN-004', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    results = []
    lock = threading.Lock()

    def worker():
        applied = repo.try_apply_observation('pg-race', 'race-obs')
        with lock:
            results.append(applied)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1, results


def test_save_detects_concurrent_modification_instead_of_silently_losing_a_write(repo):
    state = _new_state()
    repo.create(case_id='pg-cas', patient_id='SYN-005', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')

    writer_a = repo.get('pg-cas')
    writer_b = repo.get('pg-cas')

    writer_a.state.symptoms.append('from-a')
    repo.save(writer_a)  # succeeds, bumps the stored version past writer_b's stale copy

    writer_b.state.symptoms.append('from-b')
    with pytest.raises(ConcurrentModificationError):
        repo.save(writer_b)  # must be REJECTED, never silently overwrite writer_a's committed write

    final = repo.get('pg-cas')
    assert final.state.symptoms == ['from-a']  # writer_a's write survives; writer_b's did not vanish silently


def test_update_locale_persists_and_is_process_restart_safe(repo):
    state = _new_state()
    repo.create(case_id='pg-locale', patient_id='SYN-006', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    repo.update_locale('pg-locale', 'ja')

    # A fresh repository instance stands in for a new backend process/container -- unlike the
    # in-memory NovaCaseRepository (see test_process_restart_is_not_survived_by_the_in_memory_
    # repository), this one must see data written before it was constructed.
    fresh = PostgresNovaCaseRepository(POSTGRES_URL)
    reloaded = fresh.get('pg-locale')
    assert reloaded.state.locale == 'ja'


def test_close_sets_status_and_survives_a_fresh_repository_instance(repo):
    state = _new_state()
    repo.create(case_id='pg-close', patient_id='SYN-007', encounter_id=None, state=state,
                created_by='tester', agent_version='v1', kb_version='kb1')
    repo.close('pg-close', reason='resolved')

    fresh = PostgresNovaCaseRepository(POSTGRES_URL)
    reloaded = fresh.get('pg-close')
    assert reloaded.status == 'closed'
    assert reloaded.close_reason == 'resolved'
    assert reloaded.closed_at is not None


def test_close_missing_case_raises_not_found(repo):
    with pytest.raises(NotFound):
        repo.close('does-not-exist')


def test_update_locale_missing_case_raises_not_found(repo):
    with pytest.raises(NotFound):
        repo.update_locale('does-not-exist', 'ko')


def test_list_for_patient_returns_only_that_patients_cases(repo):
    s1, s2, s3 = _new_state('pg-list-1'), _new_state('pg-list-2'), _new_state('pg-list-3')
    repo.create(case_id='pg-list-1', patient_id='SYN-008', encounter_id=None, state=s1,
                created_by='tester', agent_version='v1', kb_version='kb1')
    repo.create(case_id='pg-list-2', patient_id='SYN-008', encounter_id=None, state=s2,
                created_by='tester', agent_version='v1', kb_version='kb1')
    repo.create(case_id='pg-list-3', patient_id='SYN-009', encounter_id=None, state=s3,
                created_by='tester', agent_version='v1', kb_version='kb1')

    cases = repo.list_for_patient('SYN-008')
    assert {c.case_id for c in cases} == {'pg-list-1', 'pg-list-2'}


def test_novaservice_with_postgres_backend_survives_a_fresh_service_instance():
    """The exact scenario test_process_restart_is_not_survived_by_the_in_memory_repository
    documents as a limitation for the default backend -- proven CLOSED here for the Postgres one,
    driven through the real NovaService/DoctorAgent path (not just the repository in isolation)."""
    from app.services.emr_adapter import DemoAdapter
    from app.services.nova_service import NovaService

    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute('TRUNCATE nova_case_observations, nova_cases')

    adapter = DemoAdapter()
    service_a = NovaService(repository=PostgresNovaCaseRepository(POSTGRES_URL))
    record = service_a.create_case(adapter=adapter, patient_id='SYN-002',
                                    encounter=None, chief_complaint='dizziness',
                                    created_by='tester')

    # A fresh NovaService with its own fresh PostgresNovaCaseRepository -- standing in for the
    # process having restarted -- must still see the case service_a created.
    service_b = NovaService(repository=PostgresNovaCaseRepository(POSTGRES_URL))
    reloaded = service_b.get_case(record.case_id)
    assert reloaded.state.chief_complaint == 'dizziness'
