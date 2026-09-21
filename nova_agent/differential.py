"""Differential Diagnosis Engine (spec section 4).

Ranks candidate diagnoses from the local knowledge base against everything currently known about
the patient. Confidence is reported as a LOW/MEDIUM/HIGH calibration band (how much of a disease's
known evidence profile has actually been confirmed so far) alongside an internal 0..1 ranking
score -- the band is never presented as if it were a calibrated probability.

Re-run every turn (never "first differential only") so newly observed findings immediately
reshuffle the ranking.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel

from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.config import get_config
from nova_agent.knowledge.retrieval import all_diseases, diseases_for_tag
from nova_agent.matching import feature_denied, feature_present
from nova_agent.state import DifferentialSnapshot, PatientState

ConfidenceBand = Literal["LOW", "MEDIUM", "HIGH"]

FEATURE_WEIGHT = 1.0
RISK_FACTOR_WEIGHT = 0.4
CONTRADICTION_PENALTY = 1.2
# Objective exam/imaging/lab findings that confirm a diagnosis (knowledge/diseases/*.json's
# `confirmatory_findings`) are weighted higher than a soft symptom feature -- clinically, "ST
# elevation on ECG" should move the ranking far more than "chest pain worse with exertion" does.
CONFIRMATORY_WEIGHT = 2.5


class DifferentialItem(BaseModel):
    diagnosis: str
    diagnosis_id: str
    rank: int
    score: float
    score_ratio: float
    supporting_evidence: List[str] = []
    contradictory_evidence: List[str] = []
    missing_discriminative_evidence: List[str] = []
    urgency: str
    dangerous_if_missed: bool
    confidence_band: ConfidenceBand


def _score_disease(entry: dict, state: PatientState) -> tuple[float, float, List[str], List[str], List[str]]:
    findings = state.all_findings_text()
    negatives = state.pertinent_negatives

    supporting: List[str] = []
    contradictory: List[str] = []
    missing: List[str] = []
    score = 0.0
    max_possible = 0.0

    for feature in entry.get("typical_features", []):
        max_possible += FEATURE_WEIGHT
        if feature_denied(feature, negatives):
            contradictory.append(feature)
            score -= CONTRADICTION_PENALTY
        elif feature_present(feature, findings):
            supporting.append(feature)
            score += FEATURE_WEIGHT
        else:
            missing.append(feature)

    for risk_factor in entry.get("risk_factors", []):
        max_possible += RISK_FACTOR_WEIGHT
        if feature_present(risk_factor, findings):
            supporting.append(risk_factor)
            score += RISK_FACTOR_WEIGHT

    for finding in entry.get("confirmatory_findings", []):
        max_possible += CONFIRMATORY_WEIGHT
        if feature_present(finding, findings):
            supporting.append(finding)
            score += CONFIRMATORY_WEIGHT

    return score, max(max_possible, 1.0), supporting, contradictory, missing


def _confidence_band(score_ratio: float, turn_count: int, supporting_count: int) -> ConfidenceBand:
    cfg = get_config().stop_policy
    if turn_count < cfg.min_turns_before_diagnose or supporting_count < 1:
        return "LOW"
    if score_ratio >= 0.65 and supporting_count >= cfg.min_evidence_items:
        return "HIGH"
    if score_ratio >= 0.30:
        return "MEDIUM"
    return "LOW"


class DifferentialEngine:
    """Stateless ranker: call `update(state)` every turn; it recomputes from scratch off the
    current PatientState rather than incrementally patching the previous ranking, so a
    contradicted early guess is never "sticky"."""

    def update(self, state: PatientState) -> List[DifferentialItem]:
        tag = classify_chief_complaint(state.chief_complaint)
        candidates = diseases_for_tag(tag)
        if not candidates:
            # Chief complaint didn't match a known tag -- fall back to the whole knowledge base
            # rather than returning an empty differential (spec: agent must always reason toward
            # a diagnosis, never stall for lack of a tag match).
            candidates = list(all_diseases().values())

        scored = []
        for entry in candidates:
            score, max_possible, supporting, contradictory, missing = _score_disease(entry, state)
            score_ratio = max(0.0, score) / max_possible
            band = _confidence_band(score_ratio, state.turn_count, len(supporting))
            scored.append((score, score_ratio, entry, supporting, contradictory, missing, band))

        scored.sort(key=lambda t: t[0], reverse=True)
        top_k = get_config().top_k_differential
        items: List[DifferentialItem] = []
        for rank, (score, score_ratio, entry, supporting, contradictory, missing, band) in enumerate(scored[:top_k], start=1):
            items.append(DifferentialItem(
                diagnosis=entry["name"], diagnosis_id=entry["id"], rank=rank, score=round(score, 3),
                score_ratio=round(score_ratio, 3),
                supporting_evidence=supporting, contradictory_evidence=contradictory,
                missing_discriminative_evidence=missing, urgency=entry.get("urgency", "LOW"),
                dangerous_if_missed=bool(entry.get("dangerous", False)), confidence_band=band,
            ))

        state.current_differential = [
            DifferentialSnapshot(diagnosis=i.diagnosis, rank=i.rank, confidence_band=i.confidence_band,
                                  urgency=i.urgency, dangerous_if_missed=i.dangerous_if_missed)
            for i in items
        ]
        return items
