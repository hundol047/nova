"""Concurrency-safety and idempotency tests for production/repository.py (spec: no state
collision / cross-case leakage / race condition; idempotent writes via event/observation id dedup;
immutable audit log)."""

from __future__ import annotations

import threading

import pytest

from nova_agent.state import PatientState
from production.repository import (
    AuditEntry,
    InMemoryAuditRepository,
    InMemoryCaseRepository,
)


def _make_state(case_id: str) -> PatientState:
    return PatientState(case_id=case_id, chief_complaint="test complaint")


def test_create_then_get_round_trips():
    repo = InMemoryCaseRepository()
    repo.create(_make_state("c1"))
    record = repo.get("c1")
    assert record.case_id == "c1"
    assert record.state.chief_complaint == "test complaint"


def test_duplicate_create_raises_conflict():
    from production.errors import ConflictError
    repo = InMemoryCaseRepository()
    repo.create(_make_state("c1"))
    with pytest.raises(ConflictError):
        repo.create(_make_state("c1"))


def test_get_unknown_case_raises_not_found():
    from production.errors import NotFoundError
    repo = InMemoryCaseRepository()
    with pytest.raises(NotFoundError):
        repo.get("nope")


def test_try_apply_event_is_idempotent():
    repo = InMemoryCaseRepository()
    repo.create(_make_state("c1"))
    assert repo.try_apply_event("c1", "evt-1") is True
    assert repo.try_apply_event("c1", "evt-1") is False
    assert repo.try_apply_event("c1", "evt-2") is True


def test_concurrent_writes_to_the_same_case_never_lose_an_increment():
    """100 threads each increment the same case's turn_count by 1 via save(); the per-case lock
    must serialize these so the final count is exactly 100, not less (a lost update under a race)."""
    repo = InMemoryCaseRepository()
    repo.create(_make_state("race-case"))
    errors = []

    def bump():
        try:
            record = repo.get("race-case")
            record.state.turn_count += 1
            repo.save(record)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=bump) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert repo.get("race-case").state.turn_count == 100


def test_concurrent_different_cases_never_leak_state_across_each_other():
    """50 distinct cases, each mutated concurrently -- verifies no case's state bleeds into
    another's (a shared/global object would show cross-contaminated chief_complaint values)."""
    repo = InMemoryCaseRepository()
    case_ids = [f"case-{i}" for i in range(50)]
    for cid in case_ids:
        repo.create(PatientState(case_id=cid, chief_complaint=f"complaint-for-{cid}"))

    def mutate(cid: str) -> None:
        record = repo.get(cid)
        record.state.turn_count += 1
        repo.save(record)

    threads = [threading.Thread(target=mutate, args=(cid,)) for cid in case_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for cid in case_ids:
        record = repo.get(cid)
        assert record.state.chief_complaint == f"complaint-for-{cid}"
        assert record.state.turn_count == 1


def test_audit_repository_is_append_only_and_scoped_per_case():
    repo = InMemoryAuditRepository()
    repo.append(AuditEntry(entry_id="e1", case_id="c1", request_id="r1", timestamp="t", event="created",
                            agent_version="0.1.0", schema_version="1", prompt_version="1",
                            kb_version="kb1", model_version="mock"))
    repo.append(AuditEntry(entry_id="e2", case_id="c2", request_id="r2", timestamp="t", event="created",
                            agent_version="0.1.0", schema_version="1", prompt_version="1",
                            kb_version="kb1", model_version="mock"))
    assert len(repo.list_for_case("c1")) == 1
    assert len(repo.list_for_case("c2")) == 1
    assert len(repo.all()) == 2
