"""Structured LLM output schema (spec section 12).

The model is never asked for free-form prose or private chain-of-thought -- only this JSON shape,
validated through Pydantic. `summary` is a short, evaluable evidence summary, not a reasoning
transcript.

`key` on CandidateActionOutput/SelectedActionOutput is the authoritative field for ASK/EXAM/TEST
selection (the exact catalog id offered in the prompt's candidate list) -- `content` is free text
for readability/phrasing only and is never used to decide WHICH action was chosen (matching on
free text was the old, fragile design; see orchestrator.py's SafetyValidator). `diagnosis_id` on
DifferentialItemOutput is None for a diagnosis the LLM introduces that isn't in the local knowledge
base -- open-world differential reasoning is allowed; the local knowledge base is a prior/aid, not
a closed-world classifier (spec section 7).
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ActionTypeLiteral = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
ConfidenceLiteral = Literal["LOW", "MEDIUM", "HIGH"]


class DifferentialItemOutput(BaseModel):
    diagnosis: str
    diagnosis_id: Optional[str] = None
    rank: int
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    dangerous_if_missed: bool = False
    confidence: ConfidenceLiteral = "LOW"


class CandidateActionOutput(BaseModel):
    type: ActionTypeLiteral
    key: str = ""
    content: str
    utility: Optional[float] = None


class SelectedActionOutput(BaseModel):
    type: ActionTypeLiteral
    key: str = ""
    content: str


class AgentTurnOutput(BaseModel):
    summary: str
    differential: List[DifferentialItemOutput] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    candidate_actions: List[CandidateActionOutput] = Field(default_factory=list)
    selected_action: SelectedActionOutput
    ready_to_diagnose: bool = False
