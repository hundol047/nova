"""Exercises PostgresAuditStore against a REAL local Postgres server (not a mock) -- proves it
implements the exact record()/save_analysis()/get_analysis()/list() interface AuditStore does, so
main.py's app.state.audit can be either backend interchangeably (see build_audit_store()).

Requires a Postgres server reachable at NOVA_TEST_POSTGRES_URL (default
postgresql://postgres:postgres@localhost:5432/nova_test) -- same server/skip-if-unavailable
convention as test_nova_postgres_repository.py.
"""
import os

import pytest

psycopg = pytest.importorskip('psycopg')

from app.services.audit import AuditStore, PostgresAuditStore, build_audit_store

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
def store():
    s = PostgresAuditStore(POSTGRES_URL)
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute('TRUNCATE audit_events, audit_analyses')
    return s


def test_record_and_list_round_trips_events(store):
    store.record('SYN-001', 'patient_selected', {'note': 'first visit'}, user_id='u1', role='physician')
    store.record('SYN-001', 'analysis_completed', {'risk_probability': 0.42})
    entries = store.list('SYN-001')
    assert len(entries) == 2
    assert entries[0]['event'] == 'analysis_completed'  # most recent first
    assert entries[0]['detail']['risk_probability'] == 0.42
    assert entries[1]['user_id'] == 'u1' and entries[1]['role'] == 'physician'


def test_list_is_scoped_to_patient_id(store):
    store.record('SYN-001', 'patient_selected', {})
    store.record('SYN-002', 'patient_selected', {})
    assert len(store.list('SYN-001')) == 1
    assert len(store.list('SYN-002')) == 1


def test_save_and_get_analysis_round_trips(store):
    payload = {'analysis_id': 'an-1', 'patient_id': 'SYN-001', 'risk': {'risk_probability': 0.9}}
    store.save_analysis(payload)
    assert store.get_analysis('an-1') == payload


def test_get_analysis_missing_returns_none(store):
    assert store.get_analysis('does-not-exist') is None


def test_data_survives_a_fresh_store_instance():
    """Process-restart recovery, the reason this backend exists at all (see this module's
    docstring)."""
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute('TRUNCATE audit_events, audit_analyses')
    store_a = PostgresAuditStore(POSTGRES_URL)
    store_a.record('SYN-003', 'patient_selected', {'note': 'persisted'})

    store_b = PostgresAuditStore(POSTGRES_URL)
    entries = store_b.list('SYN-003')
    assert len(entries) == 1 and entries[0]['detail']['note'] == 'persisted'


def test_build_audit_store_selects_postgres_when_env_var_set(monkeypatch):
    monkeypatch.setenv('NOVA_POSTGRES_URL', POSTGRES_URL)
    assert isinstance(build_audit_store(), PostgresAuditStore)


def test_build_audit_store_defaults_to_sqlite_when_unset(monkeypatch, tmp_path):
    monkeypatch.delenv('NOVA_POSTGRES_URL', raising=False)
    monkeypatch.setenv('SYNEX_AUDIT_PATH', str(tmp_path / 'audit.sqlite3'))
    assert isinstance(build_audit_store(), AuditStore)
