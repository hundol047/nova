"""N.O.V.A. production service: the ONLY code in this backend allowed to construct or call
nova_agent.orchestrator.DoctorAgent. A FastAPI endpoint (main.py) never touches nova_agent
internals directly -- it calls NovaService methods and gets back plain dicts/dataclasses, the
same separation-of-concerns main.py already keeps between its endpoints and services/rule_engine.py
/services/risk_inference.py.

Deliberately reuses `competition/`'s core reasoning engine only (nova_agent.orchestrator.
DoctorAgent) -- never `competition/adapter.py`, which implements the competition PROTOCOL
(stdin/stdout JSON-lines, competition-mode DIAGNOSE hard-fail rules) that has nothing to do with a
production HTTP API and must stay untouched by it (spec: competition submission and production
runtime stay separated).

Clinical safety boundary (never relaxed by any code path here): this service produces a structured
RECOMMENDATION only. It never calls MedicationOrderRepository/LabOrderRepository or any other
write path that would place, modify, or cancel a real clinical order -- see the DecideResult's
`clinician_review_required` field, always True, and main.py's nova endpoints, none of which write
to app.state.medication_order_repo/lab_order_repo.

Concurrency safety: a fresh `DoctorAgent` (and therefore a fresh LLM client instance) is
constructed per decide()/add_observation() call rather than shared across requests -- see
production/api.py's identical fix earlier in this project for the underlying reason
(BaseLLMClient tracks its most recent call's outcome on plain instance attributes that
orchestrator.decide() reads immediately after calling it; sharing one instance across concurrent
requests would race).
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# nova_agent/ lives at the repo root, a sibling of backend/ -- not on sys.path by default when
# this app is launched with `--app-dir backend` (dev) or from /app/backend (container). Bootstrap
# it here, the one place every nova_agent import in this backend transitively goes through, so
# every entry point (uvicorn, pytest, a manual script) gets it consistently without each needing
# its own PYTHONPATH setup. Idempotent and side-effect-free if already present.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from nova_agent.action_selector import AgentAction
from nova_agent.config import get_config
from nova_agent.differential import DifferentialItem
from nova_agent.llm_client import BaseLLMClient, MockLLMClient, get_llm_client
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState

from ..schemas import ClinicalEncounter, Patient
from .nova_fhir_mapper import apply_patient_context, demographics_for
from .nova_observability import get_nova_metrics, log_event
from .nova_repository import (CaseConflict, ConcurrentModificationError, NotFound, NovaCaseRecord,
                               RepositoryError, build_nova_case_repository, new_case_id)

AGENT_VERSION = "1.0.0"
SCHEMA_VERSION = "1"
PROMPT_VERSION = "1"

CLINICAL_SAFETY_BANNER = (
    "Decision Support / Not Autonomous Medical Diagnosis / Clinician Review Required. "
    "This is a structured suggestion for a licensed clinician to evaluate, not a final diagnosis "
    "or treatment directive. N.O.V.A. never places, modifies, or cancels a medication or lab "
    "order, and never auto-confirms a clinical order."
)


class NovaServiceError(Exception):
    error_code = "internal_error"
    http_status = 500


class PatientNotFoundError(NovaServiceError):
    error_code = "patient_not_found"
    http_status = 404


class CaseNotFoundError(NovaServiceError):
    error_code = "case_not_found"
    http_status = 404


class CaseConflictError(NovaServiceError):
    error_code = "case_conflict"
    http_status = 409


class CaseClosedError(NovaServiceError):
    error_code = "case_conflict"
    http_status = 409


class ValidationError(NovaServiceError):
    error_code = "validation_error"
    http_status = 422


class EMRUnavailableError(NovaServiceError):
    """The active EMR adapter (DemoAdapter or a real FHIRAdapter) raised while resolving a
    patient/encounter -- distinct from PatientNotFoundError (a real, reachable answer of 'no such
    patient') so a caller/operator can tell 'the hospital FHIR server is down' apart from 'this
    patient id doesn't exist'."""
    error_code = "EMR_unavailable"
    http_status = 503


class StorageError(NovaServiceError):
    """An unexpected failure from the case repository itself -- never raised by the in-memory
    NovaCaseRepository (a plain dict write cannot fail), but PostgresNovaCaseRepository raises
    RepositoryError (connection loss, etc.) or ConcurrentModificationError (a genuine write race on
    the same case -- see nova_repository.py's module docstring) and both are translated to this one
    error here, so no call site below needs its own psycopg-specific translation logic. 503, not
    500: this is a transient infrastructure condition a retry can resolve, not a code defect."""
    error_code = "storage_error"
    http_status = 503


_KB_FINGERPRINT_CACHE: dict = {}


def kb_fingerprint() -> str:
    knowledge_dir = Path(get_config().knowledge_dir)
    cache_key = str(knowledge_dir)
    cached = _KB_FINGERPRINT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    if knowledge_dir.is_dir():
        for path in sorted(knowledge_dir.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(knowledge_dir)).encode("utf-8"))
                digest.update(path.read_bytes())
    fingerprint = digest.hexdigest()[:16]
    _KB_FINGERPRINT_CACHE[cache_key] = fingerprint
    return fingerprint


def model_version() -> str:
    cfg = get_config()
    return cfg.llm_model if cfg.llm_provider != "mock" else "mock"


class _LLMCircuitBreaker:
    """Closed/open/half-open breaker over WHETHER to attempt a real LLM call this turn -- not a
    wrapper around BaseLLMClient itself (orchestrator.decide() calls the client internally and
    never raises; there is no exception here to intercept). Instead, decide() below inspects
    PatientState's own llm_call_count/llm_success_count/llm_failure_count deltas before/after each
    call and reports the outcome via record_outcome(); when open, decide() constructs the
    DoctorAgent with a forced MockLLMClient for that one turn (the same graceful-degradation shape
    nova_agent's own case-budget mechanism already uses in nova_agent/orchestrator.py) instead of
    attempting a real network call that is very likely to fail and add latency for nothing."""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at: Optional[float] = None

    def should_skip_real_llm(self) -> bool:
        with self._lock:
            if self._state == "open" and self._opened_at is not None:
                if time.monotonic() - self._opened_at >= self.cooldown_seconds:
                    self._state = "half_open"
            return self._state == "open"

    def record_outcome(self, *, attempted: bool, succeeded: bool) -> None:
        if not attempted:
            return
        with self._lock:
            if succeeded:
                self._consecutive_failures = 0
                self._state = "closed"
                self._opened_at = None
            else:
                self._consecutive_failures += 1
                if self._state == "half_open" or self._consecutive_failures >= self.failure_threshold:
                    self._state = "open"
                    self._opened_at = time.monotonic()

    def snapshot(self) -> dict:
        with self._lock:
            return {"state": self._state, "consecutive_failures": self._consecutive_failures}


@dataclass
class DecideResult:
    record: NovaCaseRecord
    action: AgentAction
    differential: list
    llm_circuit_open: bool = False
    versions: dict = field(default_factory=dict)


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class NovaService:
    def __init__(self, repository=None) -> None:
        # build_nova_case_repository() selects PostgresNovaCaseRepository when NOVA_POSTGRES_URL is
        # set, else the in-memory NovaCaseRepository (dev/test default) -- see nova_repository.py's
        # module docstring. `repository` lets tests inject a specific backend directly.
        self.repository = repository if repository is not None else build_nova_case_repository()
        self.circuit_breaker = _LLMCircuitBreaker(
            failure_threshold=_int_env("NOVA_CB_FAILURE_THRESHOLD", 5),
            cooldown_seconds=_float_env("NOVA_CB_COOLDOWN_SECONDS", 30.0),
        )

    def _new_llm_client(self, *, force_mock: bool) -> BaseLLMClient:
        if force_mock:
            return MockLLMClient()
        return get_llm_client()

    def create_case(self, *, adapter, patient_id: str, encounter: Optional[ClinicalEncounter],
                     chief_complaint: Optional[str], created_by: str, max_turns: Optional[int] = None,
                     locale: str = "en") -> NovaCaseRecord:
        try:
            patient: Optional[Patient] = adapter.get(patient_id)
        except NotImplementedError:
            raise
        except Exception as exc:  # noqa: BLE001 - a real FHIRAdapter's network/auth failure surfaces here
            raise EMRUnavailableError(f"EMR adapter failed to resolve patient {patient_id!r}: {exc}") from exc
        if patient is None:
            raise PatientNotFoundError(patient_id)
        cc = (chief_complaint or "").strip() or (encounter.chief_complaint if encounter else "")
        if not cc:
            raise ValidationError(
                "chief_complaint is required (pass it directly, or reference an encounter that already has one)."
            )
        agent = DoctorAgent(llm_client=self._new_llm_client(force_mock=self.circuit_breaker.should_skip_real_llm()),
                             lang=locale)
        case_id = new_case_id()
        state: PatientState = agent.new_case(case_id=case_id, chief_complaint=cc,
                                              demographics=demographics_for(patient), max_turns=max_turns)
        state.locale = locale
        unmapped_clinical_codes = apply_patient_context(state, patient, encounter)
        if unmapped_clinical_codes:
            # Never silently discarded (spec): counted for ops visibility and logged with enough
            # detail (raw code/display) for a dev to add the missing clinical_code_mapper.py row --
            # the case itself still proceeds normally (the raw-name key still lets plain
            # word-overlap matching see the lab's value; only the canonical-id fast path is missing).
            get_nova_metrics().increment("nova_unmapped_clinical_codes_total", len(unmapped_clinical_codes))
            log_event("nova_fhir_mapper", "unmapped_clinical_codes", case_id=case_id,
                       detail={"codes": unmapped_clinical_codes})
        try:
            return self.repository.create(case_id=case_id, patient_id=patient_id,
                                           encounter_id=encounter.id if encounter else None,
                                           state=state, created_by=created_by,
                                           agent_version=AGENT_VERSION, kb_version=kb_fingerprint())
        except CaseConflict as exc:
            raise CaseConflictError(str(exc)) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc

    def add_observation(self, case_id: str, *, observation_id: str, action_type: str, key: str,
                         result: str) -> tuple[NovaCaseRecord, bool]:
        try:
            record = self.repository.get(case_id)
        except NotFound as exc:
            raise CaseNotFoundError(case_id) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc
        if record.status == "closed":
            raise CaseClosedError(f"Case {case_id!r} is closed; no further observations can be recorded.")
        try:
            applied = self.repository.try_apply_observation(case_id, observation_id)
            if applied:
                agent = DoctorAgent()
                action = AgentAction(action_type=action_type, key=key, content=key, rationale="")
                agent.observe(record.state, action, result)
                self.repository.save(record)
        except (RepositoryError, ConcurrentModificationError) as exc:
            # A genuine write race on this case between our get() above and save() here -- surfaced
            # as a transient 503 (a caller retry re-reads the now-current state) rather than
            # silently discarding this observation. See nova_repository.py's module docstring;
            # closing this gap with an automatic server-side retry is tracked separately.
            raise StorageError(str(exc)) from exc
        return record, applied

    def decide(self, case_id: str) -> DecideResult:
        try:
            record = self.repository.get(case_id)
        except NotFound as exc:
            raise CaseNotFoundError(case_id) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc
        if record.status == "closed":
            raise CaseClosedError(f"Case {case_id!r} is closed; no further decisions can be made.")

        skip_real_llm = self.circuit_breaker.should_skip_real_llm()
        agent = DoctorAgent(llm_client=self._new_llm_client(force_mock=skip_real_llm), lang=record.state.locale)

        calls_before, success_before = record.state.llm_call_count, record.state.llm_success_count
        action, _llm_output, differential = agent.decide(record.state)
        calls_after, success_after = record.state.llm_call_count, record.state.llm_success_count
        attempted_real_call = calls_after > calls_before
        self.circuit_breaker.record_outcome(attempted=attempted_real_call,
                                             succeeded=success_after > success_before)

        try:
            self.repository.save(record)
        except (RepositoryError, ConcurrentModificationError) as exc:
            raise StorageError(str(exc)) from exc
        versions = {"agent_version": AGENT_VERSION, "schema_version": SCHEMA_VERSION,
                    "prompt_version": PROMPT_VERSION, "kb_version": kb_fingerprint(),
                    "model_version": model_version()}
        return DecideResult(record=record, action=action, differential=differential,
                             llm_circuit_open=skip_real_llm, versions=versions)

    def get_case(self, case_id: str) -> NovaCaseRecord:
        try:
            return self.repository.get(case_id)
        except NotFound as exc:
            raise CaseNotFoundError(case_id) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc

    def update_locale(self, case_id: str, locale: str) -> NovaCaseRecord:
        try:
            return self.repository.update_locale(case_id, locale)
        except NotFound as exc:
            raise CaseNotFoundError(case_id) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc

    def close_case(self, case_id: str, *, reason: str = "") -> NovaCaseRecord:
        try:
            return self.repository.close(case_id, reason=reason)
        except NotFound as exc:
            raise CaseNotFoundError(case_id) from exc
        except RepositoryError as exc:
            raise StorageError(str(exc)) from exc
