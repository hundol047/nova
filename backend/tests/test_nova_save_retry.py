"""NovaService.add_observation()/decide() retry-on-conflict loop (task following up on
PostgresNovaCaseRepository's optimistic-concurrency `version` column -- see
docs/NOVA_DEPLOYMENT.md's Persistence section and nova_repository.py's module docstring).

Uses a real in-memory NovaCaseRepository wrapped to inject ConcurrentModificationError on demand --
a deterministic unit test of NovaService's retry logic itself, independent of whether a real
Postgres server is reachable (see test_nova_postgres_repository.py for the live-Postgres version of
this same guarantee)."""
import pytest

from app.services.emr_adapter import DemoAdapter
from app.services.nova_repository import ConcurrentModificationError, NovaCaseRecord, NovaCaseRepository
from app.services.nova_service import NovaService, StorageError
from nova_agent.state import PatientState


class FlakyRepository:
    """Wraps a real NovaCaseRepository; save() raises ConcurrentModificationError the first
    `fail_times` times it's called, then delegates normally.

    get() returns an INDEPENDENT deep copy each call (never the same live object) -- matching
    PostgresNovaCaseRepository's actual behavior (every get() deserializes a fresh PatientState
    from the stored JSON row) rather than NovaCaseRepository's own in-memory shortcut of handing
    back the same shared object every time. This matters here specifically: a retry's get() must
    return the state as last actually COMMITTED, unaffected by a previous, failed attempt's
    in-place mutations -- true for both real backends that can raise ConcurrentModificationError,
    so the test has to model it too, or it would spuriously double-apply a mutation that a real
    deployment never would."""

    def __init__(self, inner: NovaCaseRepository, fail_times: int) -> None:
        self._inner = inner
        self._fail_times = fail_times
        self.save_calls = 0

    def get(self, case_id):
        record = self._inner.get(case_id)
        return NovaCaseRecord(
            case_id=record.case_id, patient_id=record.patient_id, encounter_id=record.encounter_id,
            state=PatientState.model_validate_json(record.state.model_dump_json()),
            status=record.status, created_by=record.created_by, created_at=record.created_at,
            updated_at=record.updated_at, agent_version=record.agent_version,
            kb_version=record.kb_version, applied_observation_ids=set(record.applied_observation_ids),
            closed_at=record.closed_at, close_reason=record.close_reason, version=record.version,
        )

    def save(self, record):
        self.save_calls += 1
        if self.save_calls <= self._fail_times:
            raise ConcurrentModificationError("simulated concurrent write")
        return self._inner.save(record)

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest.fixture
def adapter():
    return DemoAdapter()


def test_add_observation_retries_and_succeeds_after_one_conflict(adapter):
    repo = FlakyRepository(NovaCaseRepository(), fail_times=1)
    service = NovaService(repository=repo)
    record = service.create_case(adapter=adapter, patient_id='SYN-002', encounter=None,
                                  chief_complaint='chest pain', created_by='tester')

    result, applied = service.add_observation(record.case_id, observation_id='obs-1',
                                                action_type='ASK', key='onset', result='today')
    assert applied is True
    assert repo.save_calls == 2  # first attempt failed, retry succeeded
    reloaded = service.get_case(record.case_id)
    assert reloaded.state.turn_count == 1  # applied exactly once, not zero and not twice


def test_add_observation_gives_up_after_exhausting_retries(adapter):
    from app.services.nova_service import _SAVE_RETRY_ATTEMPTS

    repo = FlakyRepository(NovaCaseRepository(), fail_times=99)  # always fails
    service = NovaService(repository=repo)
    record = service.create_case(adapter=adapter, patient_id='SYN-002', encounter=None,
                                  chief_complaint='chest pain', created_by='tester')
    with pytest.raises(StorageError):
        service.add_observation(record.case_id, observation_id='obs-1', action_type='ASK',
                                 key='onset', result='today')
    assert repo.save_calls == _SAVE_RETRY_ATTEMPTS  # bounded, never an infinite retry loop


def test_decide_retries_and_succeeds_after_one_conflict(adapter):
    repo = FlakyRepository(NovaCaseRepository(), fail_times=1)
    service = NovaService(repository=repo)
    record = service.create_case(adapter=adapter, patient_id='SYN-002', encounter=None,
                                  chief_complaint='chest pain', created_by='tester', max_turns=1)

    result = service.decide(record.case_id)
    assert result.action is not None
    assert repo.save_calls == 2  # first attempt failed, retry succeeded


def test_add_observation_retry_re_reads_fresh_state_not_a_stale_copy(adapter):
    """The retry must operate on the CURRENT persisted state (re-fetched), not blindly replay the
    stale object from before the failed save -- otherwise a concurrent writer's change in between
    would be silently discarded by the retry itself."""
    inner = NovaCaseRepository()
    repo = FlakyRepository(inner, fail_times=1)
    service = NovaService(repository=repo)
    record = service.create_case(adapter=adapter, patient_id='SYN-002', encounter=None,
                                  chief_complaint='chest pain', created_by='tester')

    # Simulate a concurrent writer committing a change directly to the inner store while our
    # add_observation() call is "mid-retry" -- bump turn_count so we can tell whether the retry's
    # re-fetch actually happened.
    concurrent_record = inner.get(record.case_id)
    concurrent_record.state.turn_count = 5
    inner.save(concurrent_record)

    result, applied = service.add_observation(record.case_id, observation_id='obs-1',
                                                action_type='ASK', key='onset', result='today')
    assert applied is True
    # The retry re-read turn_count=5 before applying its own +1, proving it didn't overwrite the
    # concurrent writer's change with a stale pre-conflict copy.
    assert result.state.turn_count == 6
