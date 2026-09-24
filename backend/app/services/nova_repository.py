"""N.O.V.A. case persistence: styled after services/repositories.py's existing conventions (a
thin, narrow-interface class wrapping an in-memory store, `NotFound`/`_new_id` helpers, no ORM --
easy to later swap the backing store for Postgres without changing callers, same "reusable
interface, swappable implementation" shape repositories.py itself documents).

A N.O.V.A. case is NOT a Clinical Workspace resource the way an Encounter/Note/Order is (it holds
a whole nova_agent.state.PatientState -- conversation history, differential trajectory, turn
count -- not a flat clinical fact), so it gets its own repository rather than being forced into
EncounterRepository's shape. It is still keyed by patient_id (a case is always FOR a patient in
this backend, created from POST /v1/nova/cases with a patient_id), so it composes naturally with
the existing patient-scoped audit/auth/repository pattern.

Process-memory-only, exactly like every other Clinical Workspace repository in this backend today
(EncounterRepository/ClinicalNoteRepository/... all wrap DemoAdapter.mutate(), which is itself
process memory) -- restart recovery within THIS backend requires the same real database swap the
rest of the Clinical Workspace already needs (see docs/NOVA_DEPLOYMENT.md), not a NOVA-specific
gap.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from nova_agent.state import PatientState


class NotFound(KeyError):
    pass


class CaseConflict(Exception):
    """Raised when a case_id is created twice -- distinct from NotFound so callers can return a
    409, not a 404, on a duplicate create (same shape as MedicationOrderRepository's own
    idempotent-vs-conflicting distinctions elsewhere in this file's sibling module)."""


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
