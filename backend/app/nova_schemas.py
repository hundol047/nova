"""Request/response schemas for POST/GET /v1/nova/* (main.py). Kept in their own module rather
than added to schemas.py -- schemas.py is entirely Clinical-Workspace/SynexAgent-resource-shaped
(Patient/Encounter/MedicationOrder/...); N.O.V.A.'s case/differential/decision shapes are a
different resource family with their own versioning story (agent_version/kb_version/model_version,
never present on any existing schema here).

Every response that reflects a clinical recommendation carries `clinician_review_required: True`
(a fixed Literal, not a toggle) and `safety_banner` -- see nova_service.CLINICAL_SAFETY_BANNER.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import Field, field_validator

from .schemas import StrictModel
from .services.nova_service import CLINICAL_SAFETY_BANNER

# C0/C1 control characters other than ordinary whitespace (\t \n \r) a real clinical free-text
# answer could legitimately contain. Same pattern this project's earlier production/validation.py
# used for the standalone production/ package's API boundary.
_DISALLOWED_CONTROL_CHARS = re.compile(
    "[" + "".join(chr(c) for c in range(0x00, 0x20) if chr(c) not in "\t\n\r") + chr(0x7F) + "]"
)


def _reject_control_characters(value: Optional[str]) -> Optional[str]:
    if value and _DISALLOWED_CONTROL_CHARS.search(value):
        raise ValueError("must not contain control characters")
    return value


class NovaCaseCreateRequest(StrictModel):
    patient_id: str = Field(min_length=1, max_length=80)
    encounter_id: Optional[str] = Field(default=None, max_length=80)
    chief_complaint: Optional[str] = Field(default=None, max_length=4000)
    max_turns: Optional[int] = Field(default=None, gt=0, le=200)
    # UI/output locale (spec: never affects internal reasoning -- see PatientState.locale's own
    # docstring). Defaults to "en" so every existing caller that omits it keeps working unchanged.
    locale: Literal["en", "ko", "ja", "zh"] = "en"

    _validate_chief_complaint = field_validator("chief_complaint")(_reject_control_characters)


class NovaCaseCreatedResponse(StrictModel):
    case_id: str
    request_id: str
    patient_id: str
    encounter_id: Optional[str]
    turn_count: int
    max_turns: int
    status: str
    safety_banner: str = CLINICAL_SAFETY_BANNER


class NovaObservationRequest(StrictModel):
    observation_id: str = Field(min_length=1, max_length=128)
    action_type: Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
    key: str = Field(min_length=1, max_length=128)
    result: str = Field(default="", max_length=4000)

    _validate_result = field_validator("result")(_reject_control_characters)


class NovaObservationResponse(StrictModel):
    case_id: str
    request_id: str
    applied: bool
    turn_count: int


class NovaDifferentialItemOut(StrictModel):
    diagnosis: str
    # Locale-rendered display name for the SAME diagnosis_id (spec: internal canonical IDs never
    # vary per locale; only this field does). Falls back to the English `diagnosis` name whenever
    # the case's locale is "en" or this diagnosis_id has no translation row yet -- never fabricated.
    display_diagnosis: str = ""
    diagnosis_id: str
    rank: int
    confidence_band: str
    urgency: str
    dangerous_if_missed: bool
    supporting_evidence: list = Field(default_factory=list)
    contradictory_evidence: list = Field(default_factory=list)
    missing_discriminative_evidence: list = Field(default_factory=list)
    candidate_sources: list = Field(default_factory=list)


class NovaRecommendedActionOut(StrictModel):
    action_type: Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
    key: str
    content: str
    # For ASK/EXAM/TEST this already equals `content` (DoctorAgent(lang=...) renders those in the
    # case's own locale at generation time). For DIAGNOSE, `content`/`key` stay the English
    # canonical diagnosis name/id -- required internally for evaluation/audit diagnosis matching,
    # see nova_agent.i18n's own module docstring -- and this field carries the SEPARATE,
    # locale-rendered display name for that same diagnosis_id.
    display_content: str = ""
    rationale: str


class NovaVersionsOut(StrictModel):
    agent_version: str
    schema_version: str
    prompt_version: str
    kb_version: str
    model_version: str


class NovaDecideResponse(StrictModel):
    case_id: str
    request_id: str
    turn_count: int
    remaining_turns: int
    differential: list[NovaDifferentialItemOut]
    recommended_next_action: NovaRecommendedActionOut
    red_flags: list[str]
    confidence_band: Optional[str]
    limitations: list[str]
    clinician_review_required: Literal[True] = True
    safety_banner: str = CLINICAL_SAFETY_BANNER
    llm_degraded: bool = False
    versions: NovaVersionsOut


class NovaConversationTurnOut(StrictModel):
    """One recorded ASK/EXAM/TEST/DIAGNOSE turn, mirrored from PatientState.conversation_history so
    the frontend case timeline can be restored from the server (durable), not only from client
    session state. Display text only -- no canonical reasoning state is exposed here."""
    turn: int
    action_type: str
    content: str
    result: str = ""
    timestamp: str = ""


class NovaCaseStateResponse(StrictModel):
    case_id: str
    request_id: str
    patient_id: str
    encounter_id: Optional[str]
    chief_complaint: str
    status: str
    turn_count: int
    max_turns: int
    final_diagnosis: Optional[str]
    differential: list[NovaDifferentialItemOut]
    # Durable per-turn history (ASK/EXAM/TEST/DIAGNOSE) for timeline restore across refresh/re-open.
    conversation_history: list[NovaConversationTurnOut] = Field(default_factory=list)
    clinician_review_required: Literal[True] = True
    safety_banner: str = CLINICAL_SAFETY_BANNER


class NovaCloseRequest(StrictModel):
    disposition: Literal["accept", "modify", "reject"]
    reason: str = Field(default="", max_length=1000)


class NovaLocaleUpdateRequest(StrictModel):
    locale: Literal["en", "ko", "ja", "zh"]


class NovaLocaleUpdateResponse(StrictModel):
    case_id: str
    request_id: str
    locale: str


class NovaCloseResponse(StrictModel):
    case_id: str
    request_id: str
    status: str
    disposition: str
