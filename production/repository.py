"""Case + audit persistence (spec: not process-memory-only; a case must be resumable after a
restart; idempotent writes via event/observation id dedup; no cross-case state leakage under
concurrency).

Two abstract repositories (`CaseRepository`, `AuditRepository`) with one concrete implementation
each here: a thread-safe in-memory store, the right default for local dev/test and for the
in-process competition runtime. A real deployment swaps in a database-backed implementation behind
the same two interfaces (e.g. `SqlCaseRepository`) without any caller (production/api.py) changing --
this module deliberately never imports a DB driver itself, so the production package's own
dependency surface stays whatever the swapped-in implementation needs, not a blanket requirement.

Concurrency safety: every mutating method takes a per-case lock (never a single global lock across
all cases -- that would serialize unrelated cases for no reason) so two requests for the SAME case_id
can never interleave a partial state read/write, while different cases proceed fully in parallel.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from nova_agent.state import PatientState
from production.errors import ConflictError, NotFoundError


@dataclass
class AuditEntry:
    """One immutable audit-log record (spec: case_id, request_id, timestamp, model/provider,
    model_version, prompt_version, kb_version, input_hash, actions, observations, final_output,
    fallbacks, errors, latency)."""

    entry_id: str
    case_id: str
    request_id: str
    timestamp: str
    event: str
    agent_version: str
    schema_version: str
    prompt_version: str
    kb_version: str
    model_version: str
    latency_ms: Optional[float] = None
    input_hash: Optional[str] = None
    detail: dict = field(default_factory=dict)


@dataclass
class CaseRecord:
    case_id: str
    state: PatientState
    created_at: str
    updated_at: str
    # Idempotency: every observation/decide request that mutated this case, keyed by the caller-
    # supplied event id (spec: idempotency via event_id/observation_id dedup).
    applied_event_ids: set = field(default_factory=set)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaseRepository:
    """Abstract base -- see module docstring. A DB-backed implementation subclasses this and keeps
    the same method contract (including the per-case-id locking guarantee)."""

    def create(self, state: PatientState) -> CaseRecord:  # pragma: no cover - interface
        raise NotImplementedError

    def get(self, case_id: str) -> CaseRecord:  # pragma: no cover - interface
        raise NotImplementedError

    def save(self, record: CaseRecord) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def try_apply_event(self, case_id: str, event_id: str) -> bool:  # pragma: no cover - interface
        """Returns True and records the event id if this is the first time it's been seen for this
        case (caller should proceed), False if it's a replay (caller should treat as a no-op)."""
        raise NotImplementedError

    def list_case_ids(self) -> list:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryCaseRepository(CaseRepository):
    def __init__(self) -> None:
        self._records: dict[str, CaseRecord] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def _lock_for(self, case_id: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._locks.get(case_id)
            if lock is None:
                lock = threading.Lock()
                self._locks[case_id] = lock
            return lock

    def create(self, state: PatientState) -> CaseRecord:
        lock = self._lock_for(state.case_id)
        with lock:
            if state.case_id in self._records:
                raise ConflictError(f"Case {state.case_id!r} already exists.")
            now = _utcnow_iso()
            record = CaseRecord(case_id=state.case_id, state=state, created_at=now, updated_at=now)
            self._records[state.case_id] = record
            return record

    def get(self, case_id: str) -> CaseRecord:
        lock = self._lock_for(case_id)
        with lock:
            record = self._records.get(case_id)
            if record is None:
                raise NotFoundError(f"Case {case_id!r} not found.")
            return record

    def save(self, record: CaseRecord) -> None:
        lock = self._lock_for(record.case_id)
        with lock:
            if record.case_id not in self._records:
                raise NotFoundError(f"Case {record.case_id!r} not found.")
            record.updated_at = _utcnow_iso()
            self._records[record.case_id] = record

    def try_apply_event(self, case_id: str, event_id: str) -> bool:
        lock = self._lock_for(case_id)
        with lock:
            record = self._records.get(case_id)
            if record is None:
                raise NotFoundError(f"Case {case_id!r} not found.")
            if event_id in record.applied_event_ids:
                return False
            record.applied_event_ids.add(event_id)
            return True

    def list_case_ids(self) -> list:
        with self._registry_lock:
            return list(self._records.keys())


class AuditRepository:
    def append(self, entry: AuditEntry) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def list_for_case(self, case_id: str) -> list:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryAuditRepository(AuditRepository):
    """Append-only by construction: no method here ever removes or mutates a stored entry (spec:
    immutable audit log)."""

    def __init__(self) -> None:
        self._entries: list = []
        self._lock = threading.Lock()

    def append(self, entry: AuditEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def list_for_case(self, case_id: str) -> list:
        with self._lock:
            return [e for e in self._entries if e.case_id == case_id]

    def all(self) -> list:
        with self._lock:
            return list(self._entries)


_case_repository: Optional[CaseRepository] = None
_audit_repository: Optional[AuditRepository] = None
_repo_lock = threading.Lock()


def get_case_repository() -> CaseRepository:
    global _case_repository
    with _repo_lock:
        if _case_repository is None:
            _case_repository = InMemoryCaseRepository()
        return _case_repository


def get_audit_repository() -> AuditRepository:
    global _audit_repository
    with _repo_lock:
        if _audit_repository is None:
            _audit_repository = InMemoryAuditRepository()
        return _audit_repository


def reset_repositories() -> None:
    """Test-only: forces fresh, empty repositories on the next get_*_repository() call."""
    global _case_repository, _audit_repository
    with _repo_lock:
        _case_repository = None
        _audit_repository = None
