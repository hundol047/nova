"""Conservative evidence assessment, separate from action selection and wire protocols.

These are auditable heuristics, NOT calibrated probabilities or independent clinical validation.
Low scores never imply OOD. Unrecognized medical presentations remain insufficient-information
and retain the existing safety workup. Catalog name lookup alone is not patient evidence.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.matching import content_words
from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS

if TYPE_CHECKING:
    from nova_agent.differential import DifferentialItem
    from nova_agent.state import PatientState


class EvidenceAssessment(BaseModel):
    internal_result: Literal["SUPPORTED_DIAGNOSIS", "INSUFFICIENT_INFORMATION", "OUT_OF_DOMAIN"]
    reasons: list[str] = Field(default_factory=list)
    signals: dict = Field(default_factory=dict)
    calibrated: bool = False


_NONMEDICAL_DOMAIN = re.compile(
    r"\b(router|wifi|spreadsheet|python|javascript|printer|invoice|sql|football|recipe)\b"
    r"|공유기|와이파이|엑셀|프린터|파이썬|청구서|축구|조리법|ルーター|プリンター", re.I)
_TASK_INTENT = re.compile(
    r"\b(fix|debug|configure|calculate|write|print|connect|solve|format|install|reset)\b"
    r"|고쳐|설정|계산|작성|연결|설치|고장|수리|修理|設定", re.I)
_PATIENT_SIGNAL = re.compile(
    r"\b(pain|ache|fever|breath|breathing|bleed\w*|weakness|numb\w*|vomit\w*|rash|"
    r"swelling|faint\w*|seizure|cough|dizz\w*|sick|unwell|symptom\w*)\b"
    r"|아프|통증|숨|호흡|출혈|마비|열이|구토|발진|어지|경련|痛|息苦|発熱", re.I)
_NON_EVIDENCE_SOURCES = {"safety_candidate", "contextual_safety", "zero_evidence_fallback",
                         "ontology_broadening", "ontology_retrieval"}

# Request scope is orthogonal to medical evidence. Administrative and medication-information
# tasks are outside this diagnostic workflow, not necessarily outside the medical domain.
_REQUEST = re.compile(r"\b(draft|summarize|translate|reschedule|cancel|send|explain|book|renew)\b|변경|취소|예약|번역|요약|보관|予約|翻訳", re.I)
_NONDIAGNOSTIC_OBJECT = re.compile(r"\b(letter|agenda|menu|appointment|invoice|certificate|leaflet|instructions)\b|예약|서류|영수증|설명서|予約|書類", re.I)
_MEDICATION_INFORMATION = re.compile(r"\b(storage|store|label|leaflet|instructions|expiry|expiration)\b|보관|설명서|유효기간|保存|説明書", re.I)
_MEDICATION_NOUN = re.compile(r"\b(medication|medicine|inhaler|tablet|prescription)\b|이 약|약품|吸入|薬", re.I)
_EXPOSURE_RISK = re.compile(r"\b(overdose|poison\w*|accidentally|too many|double dose)\b|과다|잘못 먹|중독|過量", re.I)


def assess_evidence(state: PatientState, differential: list[DifferentialItem],
                    selected_id: str | None = None) -> EvidenceAssessment:
    """Use deterministic patient matches, not LLM-authored evidence or confidence.

    Source count is provenance, not independent-model agreement; RAG's current API does not
    supply calibrated retrieval confidence, so that signal explicitly remains unavailable.
    """
    concepts = build_clinical_presentation(state).symptoms
    top = differential[0] if differential else None
    selected = next((d for d in differential if d.diagnosis_id == selected_id), None) if selected_id else top
    evidence = set()
    if selected:
        for phrase in selected.supporting_evidence:
            words = frozenset(content_words(phrase))
            if words and not words.issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS):
                evidence.add(words)
    # Repeated/subphrase mentions of a single feature must not manufacture multiple signals.
    evidence = {e for e in evidence if not any(e < other for other in evidence)}
    sources = set(selected.candidate_sources if selected else [])
    margin = (top.score - differential[1].score if top and len(differential) > 1 else None)
    objective = bool(state.physical_examinations or state.laboratory_tests or state.imaging
                     or state.vital_signs or state.vital_sign_findings)
    clinical = bool(concepts or state.symptoms or state.associated_symptoms
                    or state.pertinent_positives or objective or _PATIENT_SIGNAL.search(state.chief_complaint))
    clinical = clinical or bool(_EXPOSURE_RISK.search(state.chief_complaint))
    domain = bool(_NONMEDICAL_DOMAIN.search(state.chief_complaint))
    task = bool(_TASK_INTENT.search(state.chief_complaint))
    request = bool(_REQUEST.search(state.chief_complaint) and _NONDIAGNOSTIC_OBJECT.search(state.chief_complaint))
    medication_info = bool(_MEDICATION_INFORMATION.search(state.chief_complaint) and _MEDICATION_NOUN.search(state.chief_complaint))
    contradictions = len(set(selected.contradictory_evidence)) if selected else 0
    signals = {
        "meaningful_evidence_items": len(evidence), "contradiction_count": contradictions,
        "rank1_rank2_score_gap": margin, "known_presentation_concepts": len(concepts),
        "selected_matches_rank1": bool(selected and top and selected.diagnosis_id == top.diagnosis_id),
        "candidate_sources": sorted(sources), "objective_observations_present": objective,
        "nonmedical_domain": domain, "task_intent": task, "clinical_signal_present": clinical,
        "nondiagnostic_request": request, "medication_information_request": medication_info,
        "retrieval_confidence": None, "independent_candidate_agreement": None,
    }
    if ((domain and task) or request or medication_info) and not clinical:
        return EvidenceAssessment(internal_result="OUT_OF_DOMAIN",
            reasons=["outside_diagnostic_task_without_patient_evidence"], signals=signals)
    reasons = []
    if not selected or selected.fallback_candidate:
        reasons.append("no_evidenced_selected_candidate")
    if len(evidence) < 2:
        reasons.append("too_few_distinct_evidence_items")
    if contradictions:
        reasons.append("contradictory_evidence_requires_review")
    if not sources or sources.issubset(_NON_EVIDENCE_SOURCES):
        reasons.append("retrieval_or_safety_membership_is_not_diagnostic_evidence")
    # Profile bands divide by all possible KB findings and can stay LOW despite an observed
    # confirmatory result. Positive objective *candidate provenance* plus distinct support is
    # a separate evidence route; merely having an exam/test (possibly normal) is not enough.
    if not selected or (selected.confidence_band == "LOW" and "objective_finding" not in sources):
        reasons.append("weak_profile_support")
    if not signals["selected_matches_rank1"] or margin is None or margin <= 0:
        reasons.append("candidate_separation_or_agreement_insufficient")
    return EvidenceAssessment(
        internal_result="INSUFFICIENT_INFORMATION" if reasons else "SUPPORTED_DIAGNOSIS",
        reasons=reasons or ["convergent_deterministic_evidence"], signals=signals)
