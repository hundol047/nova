"""Structured LLM output schema (spec section 12).

The model is never asked for free-form prose or private chain-of-thought -- only this JSON shape,
validated through Pydantic. `summary` is a short, evaluable evidence summary, not a reasoning
transcript.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ActionTypeLiteral = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]
ConfidenceLiteral = Literal["LOW", "MEDIUM", "HIGH"]


class DifferentialItemOutput(BaseModel):
    diagnosis: str
    rank: int
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    dangerous_if_missed: bool = False
    confidence: ConfidenceLiteral = "LOW"


class CandidateActionOutput(BaseModel):
    type: ActionTypeLiteral
    content: str
    utility: Optional[float] = None


class SelectedActionOutput(BaseModel):
    type: ActionTypeLiteral
    content: str


class AgentTurnOutput(BaseModel):
    summary: str
    differential: List[DifferentialItemOutput] = Field(default_factory=list)
    red_flags: List[str] = Field(default_factory=list)
    candidate_actions: List[CandidateActionOutput] = Field(default_factory=list)
    selected_action: SelectedActionOutput
    ready_to_diagnose: bool = False
