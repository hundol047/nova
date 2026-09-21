"""Missing Information Analyzer (spec section 6).

Given the current top differential, finds which not-yet-gathered piece of information (question /
exam / test) would do the most to separate the leading candidates from each other -- not "get more
info" in the abstract. Each candidate is scored on the axes spec section 6 lists; action_selector.py
turns those axis scores into the final utility ranking (section 7) using the configured weights.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel

from nova_agent.differential import DifferentialItem
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.safety import SafetyFinding, SafetyLayer
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG, disease_specific_question

CandidateActionType = Literal["ASK", "EXAM", "TEST"]

_ANSWERED_CATEGORY_FIELD = {
    "onset": "symptom_onset", "duration": "duration", "severity": "severity",
}


class CandidateInfo(BaseModel):
    action_type: CandidateActionType
    key: str
    content_en: str
    content_ko: str
    disease_ids_discriminated: List[str]
    diagnostic_discrimination: float
    safety_relevance: float
    information_gain: float
    redundancy: float
    turn_cost: int


def _already_answered(state: PatientState, category: str) -> bool:
    field = _ANSWERED_CATEGORY_FIELD.get(category)
    if field and getattr(state, field, None):
        return True
    if category == "past_medical_history" and state.past_medical_history:
        return True
    if category == "family_history" and state.family_history:
        return True
    if category == "social_history" and state.social_history:
        return True
    if category == "medication" and state.medications:
        return True
    if category == "allergy" and state.allergies:
        return True
    return False


class MissingInformationAnalyzer:
    def analyze(self, state: PatientState, differential: List[DifferentialItem],
                safety_findings: List[SafetyFinding]) -> List[CandidateInfo]:
        top_k = differential
        top_k_count = len(top_k) or 1
        safety = SafetyLayer()

        ask_candidates: dict[str, CandidateInfo] = {}
        exam_candidates: dict[str, CandidateInfo] = {}
        test_candidates: dict[str, CandidateInfo] = {}

        for item in top_k:
            entry = disease_by_id(item.diagnosis_id)
            if entry is None:
                continue
            rank_weight = 1.0 / item.rank

            for discriminator in entry.get("discriminating_questions", []):
                category = discriminator.split(":", 1)[0]
                key = f"ask:{discriminator}"
                if state.question_asked(discriminator) or _already_answered(state, category):
                    continue
                spec = disease_specific_question(item.diagnosis_id, discriminator)
                cand = ask_candidates.setdefault(key, CandidateInfo(
                    action_type="ASK", key=discriminator, content_en=spec["text_en"], content_ko=spec["text_ko"],
                    disease_ids_discriminated=[], diagnostic_discrimination=0.0, safety_relevance=0.0,
                    information_gain=0.0, redundancy=0.0, turn_cost=spec["turn_cost"],
                ))
                cand.disease_ids_discriminated.append(item.diagnosis_id)
                cand.information_gain += rank_weight
                cand.safety_relevance = max(cand.safety_relevance, safety.safety_gain(item.diagnosis_id, safety_findings))

            for exam_id in entry.get("discriminating_exams", []):
                if state.exam_done(exam_id):
                    continue
                spec = EXAM_CATALOG.get(exam_id)
                if spec is None:
                    continue
                cand = exam_candidates.setdefault(exam_id, CandidateInfo(
                    action_type="EXAM", key=exam_id, content_en=spec["name_en"], content_ko=spec["name_ko"],
                    disease_ids_discriminated=[], diagnostic_discrimination=0.0, safety_relevance=0.0,
                    information_gain=0.0, redundancy=0.0, turn_cost=spec["turn_cost"],
                ))
                cand.disease_ids_discriminated.append(item.diagnosis_id)
                cand.information_gain += rank_weight
                cand.safety_relevance = max(cand.safety_relevance, safety.safety_gain(item.diagnosis_id, safety_findings))

            for test_id in entry.get("discriminating_tests", []):
                if state.test_done(test_id):
                    continue
                spec = TEST_CATALOG.get(test_id)
                if spec is None:
                    continue
                cand = test_candidates.setdefault(test_id, CandidateInfo(
                    action_type="TEST", key=test_id, content_en=spec["name_en"], content_ko=spec["name_ko"],
                    disease_ids_discriminated=[], diagnostic_discrimination=0.0, safety_relevance=0.0,
                    information_gain=0.0, redundancy=0.0, turn_cost=spec["turn_cost"],
                ))
                cand.disease_ids_discriminated.append(item.diagnosis_id)
                cand.information_gain += rank_weight
                cand.safety_relevance = max(cand.safety_relevance, safety.safety_gain(item.diagnosis_id, safety_findings))

        all_candidates = list(ask_candidates.values()) + list(exam_candidates.values()) + list(test_candidates.values())
        for cand in all_candidates:
            n = len(set(cand.disease_ids_discriminated))
            # Peaks when the item splits the top-K roughly in half (maximally discriminative);
            # low when it's either irrelevant (n=0, filtered out already) or shared by every
            # candidate (doesn't separate anything, though it may still confirm/exclude the group).
            cand.diagnostic_discrimination = round((n * (top_k_count - n + 1)) / (top_k_count ** 2), 3) \
                if top_k_count else 0.0
            cand.redundancy = 0.0  # already-performed items were excluded above, never generated here

        return all_candidates
