"""Migration-runner drill against a REAL Postgres server (R5.3 / Migration Drill).

Covers:
  - empty DB -> apply_migrations brings the schema up, records every version, and is idempotent
    (a second run applies nothing);
  - an existing pre-migration schema (the old CREATE TABLE IF NOT EXISTS baseline, no
    schema_migrations table, no state_schema_version column) -> apply_migrations adopts the
    baseline (0001) and adds the new column (0002) WITHOUT losing existing data;
  - state_schema_version round-trips through PostgresNovaCaseRepository.

Skips cleanly locally without Postgres; NOVA_CI_REQUIRE_POSTGRES=1 (set by the postgres-integration
CI job) turns that skip into a failure via conftest.py, so the build goes red if this never ran.
"""
import os

import pytest

psycopg = pytest.importorskip("psycopg")

from app.services.nova_migrations import (CURRENT_STATE_SCHEMA_VERSION, MIGRATIONS,
                                           apply_migrations, schema_history)
from app.services.nova_repository import PostgresNovaCaseRepository
from nova_agent.state import PatientState

POSTGRES_URL = os.getenv("NOVA_TEST_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/nova_test")


def _postgres_available():
    try:
        with psycopg.connect(POSTGRES_URL, connect_timeout=1) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _postgres_available(), reason=f"no Postgres reachable at {POSTGRES_URL}")


def _drop_all():
    with psycopg.connect(POSTGRES_URL) as conn:
        conn.execute("DROP TABLE IF EXISTS nova_case_observations CASCADE")
        conn.execute("DROP TABLE IF EXISTS nova_cases CASCADE")
        conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")


def test_apply_migrations_on_empty_db_is_complete_and_idempotent():
    _drop_all()
    with psycopg.connect(POSTGRES_URL) as conn:
        applied = apply_migrations(conn)
        assert applied == [v for v, _, _ in MIGRATIONS]  # all versions applied, in order
        # Second run applies nothing.
        assert apply_migrations(conn) == []
        history = schema_history(conn)
        assert [h["version"] for h in history] == [v for v, _, _ in MIGRATIONS]
        # state_schema_version column exists now.
        cols = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='nova_cases'"
        ).fetchall()
        assert "state_schema_version" in {c[0] for c in cols}


def test_migration_preserves_existing_pre_migration_data():
    """An existing DB created by the OLD CREATE TABLE IF NOT EXISTS baseline (no schema_migrations,
    no state_schema_version) must upgrade without losing rows."""
    _drop_all()
    with psycopg.connect(POSTGRES_URL) as conn:
        # Recreate ONLY the old baseline (migration 0001's tables) + one row, WITHOUT the migrations
        # table or the 0002 column, simulating a pre-migration production database.
        for sql in MIGRATIONS[0][2]:
            conn.execute(sql)
        conn.execute(
            """INSERT INTO nova_cases (case_id, patient_id, encounter_id, state, status, created_by,
               created_at, updated_at, agent_version, kb_version, version)
               VALUES ('LEGACY-1','P1',NULL,'{}','open','tester','t','t','a','k',0)"""
        )
        # Now run migrations: 0001 is a no-op (tables exist), 0002 adds the column.
        applied = apply_migrations(conn)
        assert 2 in applied
        row = conn.execute(
            "SELECT case_id, state_schema_version FROM nova_cases WHERE case_id='LEGACY-1'"
        ).fetchone()
        assert row[0] == "LEGACY-1"          # data preserved
        assert row[1] == 1                   # column added with the default


def test_state_schema_version_round_trips_through_repository():
    _drop_all()
    repo = PostgresNovaCaseRepository(POSTGRES_URL)  # _init_schema runs migrations
    state = PatientState(case_id="MIG-CASE", chief_complaint="chest pain")
    repo.create(case_id="MIG-CASE", patient_id="P2", encounter_id=None, state=state,
                created_by="tester", agent_version="a", kb_version="k")
    loaded = repo.get("MIG-CASE")
    assert loaded.state_schema_version == CURRENT_STATE_SCHEMA_VERSION
