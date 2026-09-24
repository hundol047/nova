"""Production API request/response schemas (spec: strict Pydantic schemas with explicit error
codes, api_version/request_id/case_id/timestamp, minimal silent coercion; final result must always
carry the clinical safety boundary banner and clinician_review_required=true; explainability without
storing private chain-of-thought).

`model_config = ConfigDict(extra="forbid")` on every request model is deliberate (spec: minimal
silent coercion) -- an unexpected field is a caller bug worth surfacing as a 422, not something to
silently drop.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from production.versions import AGENT_VERSION, PROMPT_VERSION, SCHEMA_VERSION

API_VERSION = "v1"

CLINICAL_SAFETY_BANNER = (
    "Decision Support / Not Autonomous Medical Diagnosis / Clinician Review Required. "
    "This system's output is a structured suggestion for a licensed clinician to evaluate, not a "
    "final diagnosis or treatment directive. It never autonomously executes a prescription or "
    "treatment order."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    timestamp: str = Field(default_factory=_now_iso)
    error_code: str
    message: str
    case_id: Optional[str] = None


class DemographicsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = None
    pregnant: Optional[bool] = None


class CreateCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    chief_complaint: str
    demographics: DemographicsIn = Field(default_factory=DemographicsIn)
    max_turns: Optional[int] = Field(default=None, gt=0, le=200)


class CaseCreatedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    timestamp: str = Field(default_factory=_now_iso)
    case_id: str
    turn_count: int
    max_turns: int
    safety_banner: str = CLINICAL_SAFETY_BANNER


class AddObservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str  # idempotency key -- a retried POST with the same id is a no-op replay
    action_type: Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
    key: str
    result: str = ""


class ObservationAckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    timestamp: str = Field(default_factory=_now_iso)
    case_id: str
    applied: bool  # False when this observation_id was already applied (idempotent replay)
    turn_count: int


class DecideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: Optional[str] = None


class DifferentialItemOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: str
    diagnosis_id: str
    rank: int
    confidence_band: str
    urgency: str
    dangerous_if_missed: bool
    supporting_evidence: list[str] = []
    contradictory_evidence: list[str] = []
    missing_discriminative_evidence: list[str] = []
    candidate_sources: list[str] = []


class NextActionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
    key: str
    content: str
    rationale: str


class VersionsOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_version: str = AGENT_VERSION
    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION
    kb_version: str
    model_version: str


class DecideResponse(BaseModel):
    """Spec: suggested diagnosis, differential, supporting/contradictory evidence, red flags,
    recommended next info, confidence band, limitations, plus clinician_review_required=true.
    Deliberately carries no private chain-of-thought field -- only the structured evidence/action
    fields safety_validator.py and clinical_summary.py already produce for the deterministic layer."""

    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    timestamp: str = Field(default_factory=_now_iso)
    case_id: str
    turn_count: int
    remaining_turns: int
    differential: list[DifferentialItemOut]
    next_action: NextActionOut
    red_flags: list[str]
    confidence_band: Optional[str]
    limitations: list[str]
    clinician_review_required: Literal[True] = True
    safety_banner: str = CLINICAL_SAFETY_BANNER
    versions: VersionsOut


class CaseStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: str = API_VERSION
    request_id: str
    timestamp: str = Field(default_factory=_now_iso)
    case_id: str
    chief_complaint: str
    turn_count: int
    max_turns: int
    final_diagnosis: Optional[str]
    differential: list[DifferentialItemOut]
    clinician_review_required: Literal[True] = True
    safety_banner: str = CLINICAL_SAFETY_BANNER


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    agent_version: str = AGENT_VERSION


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ok: bool
    detail: Optional[str] = None


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ready: bool
    checks: list[ReadinessCheck]
