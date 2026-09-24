"""Production FastAPI service layer (spec: POST /v1/cases, POST /v1/cases/{id}/observations,
POST /v1/cases/{id}/decide, GET /v1/cases/{id}, GET /health, GET /ready).

Concurrency safety note: a fresh `DoctorAgent` (and therefore a fresh LLM client instance) is
constructed PER decide() call rather than shared across requests. `nova_agent.llm_client.
BaseLLMClient` tracks the outcome of its most recent call on plain instance attributes
(`_last_call_was_real`, `_last_call_succeeded`, ...) that `orchestrator.decide()` reads immediately
after calling it -- correct for the SEQUENTIAL evaluation harnesses this codebase was built for, but
a real race if two concurrent HTTP requests shared one client instance (request A's read could pick
up request B's in-flight write). Constructing per-request avoids the race without touching
orchestrator.py's own tested internals. `DoctorAgent` construction itself is cheap (a handful of
stateless helper objects); see nova_agent/llm_client.py's get_llm_client().

This module never imports `production.*` from `nova_agent/`, `competition/`, or `submission/`, and
is never copied by scripts/build_nova_submission.py -- see production/__init__.py.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse

from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import Demographics, PatientState
from production import auth
from production.config import ProductionConfigError, get_production_config
from production.errors import NovaProductionError
from production.logging_config import log_event
from production.metrics import get_metrics
from production.repository import (
    AuditEntry,
    get_audit_repository,
    get_case_repository,
)
from production.schemas import (
    AddObservationRequest,
    CaseCreatedResponse,
    CaseStateResponse,
    CreateCaseRequest,
    DecideRequest,
    DecideResponse,
    DifferentialItemOut,
    HealthResponse,
    NextActionOut,
    ObservationAckResponse,
    ReadinessCheck,
    ReadinessResponse,
    VersionsOut,
)
from production.validation import (
    MAX_FREE_TEXT_LENGTH,
    validate_action_type,
    validate_free_text,
    validate_identifier,
)
from production.versions import kb_fingerprint, model_version

COMPONENT = "production.api"


def create_app() -> FastAPI:
    app = FastAPI(title="N.O.V.A. Doctor Agent - Decision Support API", version="1")

    # --- auth dependency --------------------------------------------------------------------

    def get_principal(x_api_key: Optional[str] = Header(default=None)) -> auth.Principal:
        # Let NovaProductionError propagate as-is -- the exception_handler below converts it into
        # the same structured ApiError body every other endpoint failure uses, so a caller never
        # has to handle two different error shapes depending on whether auth or validation failed.
        return auth.authenticate(x_api_key)

    def new_request_id() -> str:
        return uuid.uuid4().hex

    def _audit(case_id: str, request_id: str, event: str, *, latency_ms: float | None = None,
               detail: Optional[dict] = None) -> None:
        get_audit_repository().append(AuditEntry(
            entry_id=uuid.uuid4().hex, case_id=case_id, request_id=request_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            event=event, agent_version="0.1.0", schema_version="1", prompt_version="1",
            kb_version=kb_fingerprint(), model_version=model_version(),
            latency_ms=latency_ms, detail=detail or {},
        ))

    # --- error handling: every NovaProductionError becomes a structured ApiError body --------

    @app.exception_handler(NovaProductionError)
    async def _handle_production_error(request: Request, exc: NovaProductionError) -> JSONResponse:
        get_metrics().increment("errors_total")
        log_event(COMPONENT, "request_error", severity="WARNING", error_type=exc.error_code, path=str(request.url.path))
        return JSONResponse(
            status_code=exc.http_status,
            content={"api_version": "v1", "request_id": uuid.uuid4().hex, "error_code": exc.error_code, "message": str(exc)},
        )

    # --- health / readiness / metrics ---------------------------------------------------------

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/ready", response_model=ReadinessResponse)
    def ready() -> ReadinessResponse:
        checks = []
        try:
            fp = kb_fingerprint()
            checks.append(ReadinessCheck(name="knowledge_base", ok=bool(fp), detail=fp))
        except Exception as exc:  # noqa: BLE001 - readiness must report, never crash on a failed dependency
            checks.append(ReadinessCheck(name="knowledge_base", ok=False, detail=str(exc)))
        try:
            get_case_repository().list_case_ids()
            checks.append(ReadinessCheck(name="case_repository", ok=True))
        except Exception as exc:  # noqa: BLE001
            checks.append(ReadinessCheck(name="case_repository", ok=False, detail=str(exc)))
        try:
            cfg = get_production_config()
            cfg.validate()
            checks.append(ReadinessCheck(name="config", ok=True))
        except ProductionConfigError as exc:
            checks.append(ReadinessCheck(name="config", ok=False, detail=str(exc)))
        return ReadinessResponse(ready=all(c.ok for c in checks), checks=checks)

    @app.get("/metrics")
    def metrics(principal: auth.Principal = Depends(get_principal)) -> dict:
        auth.authorize(principal, "read_metrics")
        return get_metrics().snapshot()

    # --- case lifecycle ------------------------------------------------------------------------

    @app.post("/v1/cases", response_model=CaseCreatedResponse, status_code=201)
    def create_case(body: CreateCaseRequest, principal: auth.Principal = Depends(get_principal)) -> CaseCreatedResponse:
        auth.authorize(principal, "create_case")
        request_id = new_request_id()
        start = time.monotonic()
        validate_identifier(body.case_id, field_name="case_id")
        validate_free_text(body.chief_complaint, field_name="chief_complaint", max_length=MAX_FREE_TEXT_LENGTH)

        agent = DoctorAgent()
        state = agent.new_case(
            case_id=body.case_id, chief_complaint=body.chief_complaint,
            demographics=body.demographics.model_dump(), max_turns=body.max_turns,
        )
        get_case_repository().create(state)
        get_metrics().increment("requests_total")
        _audit(body.case_id, request_id, "case_created", latency_ms=round((time.monotonic() - start) * 1000, 2))
        log_event(COMPONENT, "case_created", request_id=request_id, case_id=body.case_id)
        return CaseCreatedResponse(request_id=request_id, case_id=state.case_id,
                                    turn_count=state.turn_count, max_turns=state.max_turns)

    @app.post("/v1/cases/{case_id}/observations", response_model=ObservationAckResponse)
    def add_observation(case_id: str, body: AddObservationRequest,
                         principal: auth.Principal = Depends(get_principal)) -> ObservationAckResponse:
        auth.authorize(principal, "add_observation")
        request_id = new_request_id()
        start = time.monotonic()
        validate_identifier(case_id, field_name="case_id")
        validate_identifier(body.observation_id, field_name="observation_id")
        validate_identifier(body.key, field_name="key")
        validate_action_type(body.action_type)
        validate_free_text(body.result, field_name="result")

        repo = get_case_repository()
        record = repo.get(case_id)
        applied = repo.try_apply_event(case_id, body.observation_id)
        if applied:
            agent = DoctorAgent()
            from nova_agent.action_selector import AgentAction  # local import: avoids a module-level
            # cycle between production.api and nova_agent.action_selector at import time.
            action = AgentAction(action_type=body.action_type, key=body.key, content=body.key, rationale="")
            agent.observe(record.state, action, body.result)
            repo.save(record)
            get_metrics().increment("observations_total")
        _audit(case_id, request_id, "observation_added" if applied else "observation_replayed",
               latency_ms=round((time.monotonic() - start) * 1000, 2),
               detail={"observation_id": body.observation_id, "applied": applied})
        log_event(COMPONENT, "observation_added", request_id=request_id, case_id=case_id, applied=applied)
        return ObservationAckResponse(request_id=request_id, case_id=case_id, applied=applied,
                                       turn_count=record.state.turn_count)

    @app.post("/v1/cases/{case_id}/decide", response_model=DecideResponse)
    def decide(case_id: str, body: DecideRequest, principal: auth.Principal = Depends(get_principal)) -> DecideResponse:
        auth.authorize(principal, "decide")
        request_id = body.request_id or new_request_id()
        start = time.monotonic()
        validate_identifier(case_id, field_name="case_id")

        repo = get_case_repository()
        record = repo.get(case_id)
        # A fresh agent per call -- see module docstring on concurrency safety.
        agent = DoctorAgent()
        action, llm_output, differential = agent.decide(record.state)
        repo.save(record)

        get_metrics().increment("requests_total")
        get_metrics().increment("decide_calls_total")
        latency_ms = round((time.monotonic() - start) * 1000, 2)
        get_metrics().observe_latency("decide_latency_ms", latency_ms)
        if record.state.llm_call_count > 0:
            get_metrics().increment("llm_calls_total", record.state.llm_call_count)
            get_metrics().increment("llm_success_total", record.state.llm_success_count)
            get_metrics().increment("llm_fallback_total", record.state.llm_fallback_count)
        _audit(case_id, request_id, "decide", latency_ms=latency_ms,
               detail={"action_type": action.action_type, "action_key": action.key})
        log_event(COMPONENT, "decide", request_id=request_id, case_id=case_id, latency_ms=latency_ms,
                  action_type=action.action_type)

        top = differential[0] if differential else None
        limitations = [
            "This output has not undergone institutional clinical validation or regulatory review.",
            "Suggestions are based on a limited structured evidence model, not the full clinical picture.",
        ]
        if top and top.missing_discriminative_evidence:
            limitations.append(
                "Missing discriminative evidence for the leading diagnosis: "
                + "; ".join(top.missing_discriminative_evidence[:5])
            )
        red_flags = [f"{d.diagnosis}: dangerous if missed" for d in differential if d.dangerous_if_missed]

        return DecideResponse(
            request_id=request_id, case_id=case_id, turn_count=record.state.turn_count,
            remaining_turns=record.state.remaining_turns,
            differential=[
                DifferentialItemOut(
                    diagnosis=d.diagnosis, diagnosis_id=d.diagnosis_id, rank=d.rank,
                    confidence_band=d.confidence_band, urgency=d.urgency,
                    dangerous_if_missed=d.dangerous_if_missed,
                    supporting_evidence=d.supporting_evidence, contradictory_evidence=d.contradictory_evidence,
                    missing_discriminative_evidence=d.missing_discriminative_evidence,
                    candidate_sources=d.candidate_sources,
                ) for d in differential
            ],
            next_action=NextActionOut(action_type=action.action_type, key=action.key,
                                       content=action.content, rationale=action.rationale),
            red_flags=red_flags,
            confidence_band=top.confidence_band if top else None,
            limitations=limitations,
            versions=VersionsOut(kb_version=kb_fingerprint(), model_version=model_version()),
        )

    @app.get("/v1/cases/{case_id}", response_model=CaseStateResponse)
    def get_case(case_id: str, principal: auth.Principal = Depends(get_principal)) -> CaseStateResponse:
        auth.authorize(principal, "read_case")
        request_id = new_request_id()
        validate_identifier(case_id, field_name="case_id")
        record = get_case_repository().get(case_id)
        state = record.state
        log_event(COMPONENT, "case_read", request_id=request_id, case_id=case_id)
        return CaseStateResponse(
            request_id=request_id, case_id=state.case_id, chief_complaint=state.chief_complaint,
            turn_count=state.turn_count, max_turns=state.max_turns, final_diagnosis=state.final_diagnosis,
            differential=[
                # DifferentialSnapshot (the lightweight mirror stored on PatientState) never kept
                # a separate diagnosis_id field -- the diagnosis label itself is the only
                # identifier available here, unlike the full DifferentialItem the /decide
                # endpoint returns straight from orchestrator.decide().
                DifferentialItemOut(
                    diagnosis=d.diagnosis, diagnosis_id=d.diagnosis, rank=d.rank,
                    confidence_band=d.confidence_band, urgency=d.urgency,
                    dangerous_if_missed=d.dangerous_if_missed,
                ) for d in state.current_differential
            ],
        )

    return app


app = create_app()
