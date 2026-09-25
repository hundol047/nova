"""N.O.V.A. case persistence: styled after services/repositories.py's existing conventions (a
thin, narrow-interface class wrapping a store, `NotFound`/`_new_id` helpers, no ORM -- same
"reusable interface, swappable implementation" shape repositories.py itself documents).

A N.O.V.A. case is NOT a Clinical Workspace resource the way an Encounter/Note/Order is (it holds
a whole nova_agent.state.PatientState -- conversation history, differential trajectory, turn
count -- not a flat clinical fact), so it gets its own repository rather than being forced into
EncounterRepository's shape. It is still keyed by patient_id (a case is always FOR a patient in
this backend, created from POST /v1/nova/cases with a patient_id), so it composes naturally with
the existing patient-scoped audit/auth/repository pattern.

Two backends implement the identical interface below (create/get/save/try_apply_observation/
update_locale/close/list_for_patient), the same dual-backend shape services/idempotency.py already
established for this codebase (SQLite/in-process by default, a real server opted into via an env
var): `NovaCaseRepository` is process-memory-only (fine for dev/test -- see
test_process_restart_is_not_survived_by_the_in_memory_repository in test_nova_concurrency.py,
which documents this honestly rather than claiming otherwise), and `PostgresNovaCaseRepository` is
a genuinely durable, restart-surviving backend for production (set NOVA_POSTGRES_URL -- see
build_nova_case_repository() at the bottom of this file, and production_guard.py's startup check
that a production deployment cannot silently fall back to the in-memory one).

Concurrency note: `try_apply_observation` is fully safe under concurrent Postgres writers (an
INSERT into a PRIMARY KEY(case_id, observation_id) table -- the same atomicity primitive
idempotency.py uses). The state read-modify-write cycle (get() -> mutate in Python -> save()) is
NOT atomic across that gap for the Postgres backend by design (the repository interface hands the
caller a plain Python object between calls, not an open transaction) -- PostgresNovaCaseRepository
instead uses optimistic concurrency (a `version` column) so a genuine conflict is *detected and
raised* (ConcurrentModificationError) rather than silently lost, and a caller-side retry loop is
tracked as a follow-up (see docs/NOVA_DEPLOYMENT.md), not something this module pretends is solved.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from nova_agent.state import PatientState

from app.services.nova_migrations import CURRENT_STATE_SCHEMA_VERSION


class NotFound(KeyError):
    pass


class CaseConflict(Exception):
    """Raised when a case_id is created twice -- distinct from NotFound so callers can return a
    409, not a 404, on a duplicate create (same shape as MedicationOrderRepository's own
    idempotent-vs-conflicting distinctions elsewhere in this file's sibling module)."""


class ConcurrentModificationError(Exception):
    """Postgres backend only: save() lost a race against another writer of the same case between
    this caller's get() and save() (the version read no longer matches what's stored). Raised
    rather than silently overwriting the other writer's turn -- see this module's docstring."""


class RepositoryError(Exception):
    """An unexpected failure from the backing store itself (connection loss, etc.) -- never raised
    by the in-memory NovaCaseRepository, but PostgresNovaCaseRepository can raise this so every
    call site doesn't need its own psycopg-specific translation logic (see nova_service.py's
    StorageError, which wraps this)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_case_id() -> str:
    return f"NOVA-{uuid.uuid4().hex[:12]}"


@dataclass
class NovaCaseRecord:
    case_id: str
    patient_id: str
    encounter_id: Optional[str]
    state: PatientState
    status: str  # 'open' | 'closed'
    created_by: str
    created_at: str
    updated_at: str
    agent_version: str
    kb_version: str
    # observation_id -> True, for idempotent POST .../observations (spec: a retried observation_id
    # must never increment turn_count twice). Mirrors services/idempotency.py's begin()/complete()
    # shape at the DOMAIN level (has this observation been applied to this case's PatientState at
    # all) -- separate from and in addition to the HTTP-level Idempotency-Key header idempotency
    # main.py's IdempotencyStore already provides for the raw request/response.
    applied_observation_ids: set = field(default_factory=set)
    closed_at: Optional[str] = None
    close_reason: str = ""
    # Optimistic-concurrency token, meaningful only for PostgresNovaCaseRepository (see this
    # module's docstring) -- the in-memory repository carries it for interface parity but never
    # acts on it (a plain dict write is trivially atomic under the GIL for a single attribute set).
    version: int = 0
    # Forward-compatibility marker for the persisted case shape (R5.2). Written on create, read
    # back on load; lets future code detect/upgrade an older persisted PatientState layout. Default
    # is the current version so the in-memory backend and existing callers work unchanged.
    state_schema_version: int = 1


class NovaCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[str, NovaCaseRecord] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def _lock_for(self, case_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._locks.get(case_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[case_id] = lock
            return lock

    def create(self, *, case_id: str, patient_id: str, encounter_id: Optional[str], state: PatientState,
               created_by: str, agent_version: str, kb_version: str) -> NovaCaseRecord:
        lock = self._lock_for(case_id)
        with lock:
            if case_id in self._cases:
                raise CaseConflict(case_id)
            now = _now()
            record = NovaCaseRecord(case_id=case_id, patient_id=patient_id, encounter_id=encounter_id,
                                     state=state, status="open", created_by=created_by, created_at=now,
                                     updated_at=now, agent_version=agent_version, kb_version=kb_version)
            self._cases[case_id] = record
            return record

    def get(self, case_id: str) -> NovaCaseRecord:
        lock = self._lock_for(case_id)
        with lock:
            record = self._cases.get(case_id)
            if record is None:
                raise NotFound(case_id)
            return record

    def save(self, record: NovaCaseRecord) -> None:
        lock = self._lock_for(record.case_id)
        with lock:
            if record.case_id not in self._cases:
                raise NotFound(record.case_id)
            record.updated_at = _now()
            record.version += 1
            self._cases[record.case_id] = record

    def try_apply_observation(self, case_id: str, observation_id: str) -> bool:
        """Domain-level idempotency gate: True (and records it) the first time this observation_id
        is seen for this case, False on a replay -- see NovaCaseRecord.applied_observation_ids."""
        lock = self._lock_for(case_id)
        with lock:
            record = self._cases.get(case_id)
            if record is None:
                raise NotFound(case_id)
            if observation_id in record.applied_observation_ids:
                return False
            record.applied_observation_ids.add(observation_id)
            return True

    def update_locale(self, case_id: str, locale: str) -> NovaCaseRecord:
        """Mid-case language switch (spec: never starts a new case, only changes the UI/explanation
        language -- the case's own reasoning state, PatientState.locale aside, is untouched)."""
        lock = self._lock_for(case_id)
        with lock:
            record = self._cases.get(case_id)
            if record is None:
                raise NotFound(case_id)
            record.state.locale = locale
            record.updated_at = _now()
            return record

    def close(self, case_id: str, *, reason: str = "") -> NovaCaseRecord:
        lock = self._lock_for(case_id)
        with lock:
            record = self._cases.get(case_id)
            if record is None:
                raise NotFound(case_id)
            record.status = "closed"
            record.closed_at = _now()
            record.close_reason = reason
            record.updated_at = record.closed_at
            return record

    def list_for_patient(self, patient_id: str) -> list[NovaCaseRecord]:
        with self._registry_lock:
            return [r for r in self._cases.values() if r.patient_id == patient_id]


class PostgresNovaCaseRepository:
    """Durable, restart-surviving backend -- see this module's docstring for the concurrency model
    (try_apply_observation is fully atomic; the get()->mutate->save() cycle uses optimistic
    concurrency via `version` and raises ConcurrentModificationError on a genuine race instead of
    silently losing a turn). update_locale()/close() are single-method read-modify-writes and use
    `SELECT ... FOR UPDATE` internally, so those two are fully race-safe even under Postgres.

    Lazy-imports psycopg (see services/auth.py/idempotency.py/smart_launch.py's own lazy `import
    redis` for the same reason: a process that never configures NOVA_POSTGRES_URL should never pay
    an import-time cost or failure for a driver it doesn't use)."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        import psycopg
        return psycopg.connect(self.dsn)

    def _init_schema(self) -> None:
        # Schema is now managed by the ordered migration runner (services/nova_migrations.py) --
        # migration 0001 reproduces the original CREATE TABLE IF NOT EXISTS baseline (so an
        # existing pre-migration database adopts it transparently) and 0002 adds
        # state_schema_version. This is idempotent and safe to run at every startup.
        from app.services.nova_migrations import apply_migrations
        with self._connect() as conn:
            apply_migrations(conn)

    # Column list shared by every SELECT below, so the row-unpacking in _record_from_row stays in
    # lockstep with the query. state_schema_version is last so it maps to the trailing tuple slot.
    _SELECT_COLUMNS = ("case_id, patient_id, encounter_id, state, status, created_by, created_at, "
                       "updated_at, agent_version, kb_version, closed_at, close_reason, version, "
                       "state_schema_version")

    @staticmethod
    def _record_from_row(row: tuple, observation_ids: set) -> NovaCaseRecord:
        (case_id, patient_id, encounter_id, state_json, status, created_by, created_at, updated_at,
         agent_version, kb_version, closed_at, close_reason, version, state_schema_version) = row
        return NovaCaseRecord(
            case_id=case_id, patient_id=patient_id, encounter_id=encounter_id,
            state=PatientState.model_validate_json(state_json), status=status, created_by=created_by,
            created_at=created_at, updated_at=updated_at, agent_version=agent_version,
            kb_version=kb_version, applied_observation_ids=observation_ids, closed_at=closed_at,
            close_reason=close_reason, version=version, state_schema_version=state_schema_version,
        )

    def _observation_ids(self, conn, case_id: str) -> set:
        rows = conn.execute(
            "SELECT observation_id FROM nova_case_observations WHERE case_id = %s", (case_id,)
        ).fetchall()
        return {r[0] for r in rows}

    def create(self, *, case_id: str, patient_id: str, encounter_id: Optional[str], state: PatientState,
               created_by: str, agent_version: str, kb_version: str) -> NovaCaseRecord:
        now = _now()
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO nova_cases (case_id, patient_id, encounter_id, state, status,
                        created_by, created_at, updated_at, agent_version, kb_version, version,
                        state_schema_version)
                    VALUES (%s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, 0, %s)
                    """,
                    (case_id, patient_id, encounter_id, state.model_dump_json(), created_by, now, now,
                     agent_version, kb_version, CURRENT_STATE_SCHEMA_VERSION),
                )
        except Exception as exc:
            import psycopg
            if isinstance(exc, psycopg.errors.UniqueViolation):
                raise CaseConflict(case_id) from exc
            raise RepositoryError(str(exc)) from exc
        return NovaCaseRecord(case_id=case_id, patient_id=patient_id, encounter_id=encounter_id,
                               state=state, status="open", created_by=created_by, created_at=now,
                               updated_at=now, agent_version=agent_version, kb_version=kb_version,
                               state_schema_version=CURRENT_STATE_SCHEMA_VERSION)

    def get(self, case_id: str) -> NovaCaseRecord:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    f"SELECT {self._SELECT_COLUMNS} FROM nova_cases WHERE case_id = %s",
                    (case_id,),
                ).fetchone()
                if row is None:
                    raise NotFound(case_id)
                observation_ids = self._observation_ids(conn, case_id)
        except NotFound:
            raise
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
        return self._record_from_row(row, observation_ids)

    def save(self, record: NovaCaseRecord) -> None:
        now = _now()
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    UPDATE nova_cases SET state = %s, status = %s, updated_at = %s,
                        closed_at = %s, close_reason = %s, version = version + 1
                    WHERE case_id = %s AND version = %s
                    RETURNING version
                    """,
                    (record.state.model_dump_json(), record.status, now, record.closed_at,
                     record.close_reason, record.case_id, record.version),
                ).fetchone()
                if row is None:
                    exists = conn.execute(
                        "SELECT 1 FROM nova_cases WHERE case_id = %s", (record.case_id,)
                    ).fetchone()
                    if exists is None:
                        raise NotFound(record.case_id)
                    raise ConcurrentModificationError(
                        f"Case {record.case_id!r} was modified by another writer since it was read "
                        f"(expected version {record.version})."
                    )
        except (NotFound, ConcurrentModificationError):
            raise
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
        record.updated_at = now
        record.version += 1

    def try_apply_observation(self, case_id: str, observation_id: str) -> bool:
        try:
            with self._connect() as conn:
                exists = conn.execute(
                    "SELECT 1 FROM nova_cases WHERE case_id = %s", (case_id,)
                ).fetchone()
                if exists is None:
                    raise NotFound(case_id)
                try:
                    with conn.transaction():
                        conn.execute(
                            "INSERT INTO nova_case_observations (case_id, observation_id) VALUES (%s, %s)",
                            (case_id, observation_id),
                        )
                except Exception as exc:
                    import psycopg
                    if isinstance(exc, psycopg.errors.UniqueViolation):
                        return False
                    raise
                return True
        except NotFound:
            raise
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc

    def update_locale(self, case_id: str, locale: str) -> NovaCaseRecord:
        now = _now()
        try:
            with self._connect() as conn:
                with conn.transaction():
                    row = conn.execute(
                        f"SELECT {self._SELECT_COLUMNS} FROM nova_cases WHERE case_id = %s FOR UPDATE",
                        (case_id,),
                    ).fetchone()
                    if row is None:
                        raise NotFound(case_id)
                    observation_ids = self._observation_ids(conn, case_id)
                    record = self._record_from_row(row, observation_ids)
                    record.state.locale = locale
                    conn.execute(
                        "UPDATE nova_cases SET state = %s, updated_at = %s, version = version + 1 WHERE case_id = %s",
                        (record.state.model_dump_json(), now, case_id),
                    )
        except NotFound:
            raise
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
        record.updated_at = now
        record.version += 1
        return record

    def close(self, case_id: str, *, reason: str = "") -> NovaCaseRecord:
        now = _now()
        try:
            with self._connect() as conn:
                with conn.transaction():
                    row = conn.execute(
                        f"SELECT {self._SELECT_COLUMNS} FROM nova_cases WHERE case_id = %s FOR UPDATE",
                        (case_id,),
                    ).fetchone()
                    if row is None:
                        raise NotFound(case_id)
                    observation_ids = self._observation_ids(conn, case_id)
                    record = self._record_from_row(row, observation_ids)
                    conn.execute(
                        """UPDATE nova_cases SET status = 'closed', closed_at = %s,
                           close_reason = %s, updated_at = %s, version = version + 1
                           WHERE case_id = %s""",
                        (now, reason, now, case_id),
                    )
        except NotFound:
            raise
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc
        record.status = "closed"
        record.closed_at = now
        record.close_reason = reason
        record.updated_at = now
        record.version += 1
        return record

    def list_for_patient(self, patient_id: str) -> list[NovaCaseRecord]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"SELECT {self._SELECT_COLUMNS} FROM nova_cases WHERE patient_id = %s",
                    (patient_id,),
                ).fetchall()
                return [self._record_from_row(row, self._observation_ids(conn, row[0])) for row in rows]
        except Exception as exc:
            raise RepositoryError(str(exc)) from exc


def build_nova_case_repository():
    """Backend selector: NOVA_POSTGRES_URL set -> PostgresNovaCaseRepository (durable, the required
    backend for any real deployment -- see production_guard.py's startup check); unset -> the
    in-memory NovaCaseRepository (dev/test default, matching every existing test's expectations)."""
    dsn = os.getenv("NOVA_POSTGRES_URL")
    if dsn:
        return PostgresNovaCaseRepository(dsn)
    return NovaCaseRepository()
