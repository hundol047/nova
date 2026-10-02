"""Dangerous Diagnosis Safety Layer (spec section 5).

Makes sure a time-critical condition is never silently dropped just because it currently ranks
low in the differential. A critical condition is only ever flagged when it is already plausible
for this case -- relevant to the current chief complaint AND/OR already showing at least one
matching keyword/vital-sign trigger -- never as a blanket "test everything dangerous" reflex.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel

from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.differential import DifferentialItem
from nova_agent.knowledge.retrieval import (
    critical_condition_ids,
    demographic_risk_rules,
    disease_by_id,
    medication_risk_rules,
    vital_sign_red_flags,
)
from nova_agent.matching import feature_present
from nova_agent.state import PatientState, RedFlag

_OPS = {">=": lambda v, t: v >= t, "<=": lambda v, t: v <= t, ">": lambda v, t: v > t, "<": lambda v, t: v < t}

# Safety red-flag entries use concise clinical terms, while a patient usually uses a lay
# description.  Keep these aliases scoped to the one red-flag phrase they expand (never a global
# synonym table), and run the same negation-aware matcher used by the rest of the engine.  These
# are generic paraphrases supported by public patient-facing PE symptom guidance (for example,
# "sudden shortness of breath" for "sudden onset dyspnea" and "racing heart" for "tachycardia").
# They are deliberately small: this table is a safety recall bridge, not a diagnostic model.
_SAFETY_FEATURE_ALIASES: dict[str, tuple[str, ...]] = {
    "sudden onset dyspnea": (
        "sudden shortness of breath", "abrupt shortness of breath",
        "sudden difficulty breathing", "sudden trouble breathing",
        "can't breathe came on suddenly", "unable to breathe started suddenly",
        "갑자기 숨이 차", "갑자기 숨이 차고", "갑자기 숨이 참", "갑자기 호흡이 곤란",
    ),
    "tachycardia": (
        "racing heart", "fast heartbeat", "rapid heartbeat",
        "heart beating very fast",
    ),
    "pleuritic": (
        "chest pain worse with breathing", "pain worse when i breathe",
        "pain when breathing in", "pain with deep breaths", "sharp pain with breathing",
        "숨 쉴 때 가슴이 아프", "숨쉴 때 가슴이 아프", "호흡할 때 가슴 통증",
    ),
    "hypoxia": (
        "low oxygen", "low oxygen level", "oxygen saturation is low",
    ),
}


def _safety_feature_present(keyword: str, findings: list[str]) -> bool:
    """Match one red-flag keyword plus only its scoped lay aliases.

    `feature_present(..., scrub_negated_spans=True)` remains the first check and is also used for
    aliases, so a sentence such as "no racing heart" cannot raise a tachycardia/PE flag merely
    because it contains the alias text.
    """
    if feature_present(keyword, findings, scrub_negated_spans=True):
        return True
    return any(feature_present(alias, findings, scrub_negated_spans=True, strict=True)
               for alias in _SAFETY_FEATURE_ALIASES.get(keyword.lower(), ()))


class SafetyFinding(BaseModel):
    diagnosis_id: str
    condition: str
    reason: str
    evidence: List[str]
    source: str  # 'symptom_keyword' | 'vital_sign' | 'demographic_risk' | 'medication_risk'
    urgency: str = "CRITICAL"


class SafetyLayer:
    def assess(self, state: PatientState, differential: List[DifferentialItem]) -> List[SafetyFinding]:
        findings: List[SafetyFinding] = []
        # Safety relevance must see every currently positive presentation concept, not only the
        # single primary router tag.  A mixed complaint such as fever+cough+pleuritic pain can
        # still be PE-relevant even when fever wins the single-tag tie; the presentation builder
        # already excludes negated clauses and folds in later positive observations.
        presentation_tags = set(build_clinical_presentation(state).symptoms)
        # A diagnosis counts as "already in the differential" here only if it has some evidence-
        # based reason to be there (symptom/risk/objective match) -- not merely because it rides
        # along as part of the fixed cross-cutting safety net every candidate pool now always
        # carries (candidate_generator.py). Without this distinction, every one of that small
        # fixed list would always satisfy this OR-condition on every single case, defeating this
        # layer's own stated purpose ("never a blanket test-everything-dangerous reflex") and
        # measurably inflating turn counts by keeping irrelevant diagnoses "actively flagged"
        # purely because they exist somewhere in the pool.
        differential_ids = {d.diagnosis_id for d in differential if d.candidate_sources != ["safety_candidate"]}
        findings_text = state.all_findings_text()

        for diagnosis_id in critical_condition_ids():
            entry = disease_by_id(diagnosis_id)
            if entry is None:
                continue
            relevant = bool(presentation_tags & set(entry.get("chief_complaint_tags", []))) \
                or diagnosis_id in differential_ids
            if not relevant:
                continue
            matched_keywords = [kw for kw in entry.get("red_flag_keywords", [])
                                 if _safety_feature_present(kw, findings_text)]
            if matched_keywords:
                findings.append(SafetyFinding(
                    diagnosis_id=diagnosis_id, condition=entry["name"],
                    reason=f"Symptom findings overlap with red-flag features for {entry['name']}",
                    evidence=matched_keywords, source="symptom_keyword", urgency=entry.get("urgency", "CRITICAL"),
                ))

        for vitals in state.vital_signs:
            values = vitals.model_dump()
            for rule in vital_sign_red_flags():
                value = values.get(rule["field"])
                if value is None:
                    continue
                if _OPS[rule["op"]](value, rule["value"]):
                    for diagnosis_id in rule.get("suggests", []):
                        entry = disease_by_id(diagnosis_id)
                        if entry is None:
                            continue
                        if not (presentation_tags & set(entry.get("chief_complaint_tags", []))) \
                                and diagnosis_id not in differential_ids:
                            continue  # not relevant to this case -- do not raise a flag for it
                        findings.append(SafetyFinding(
                            diagnosis_id=diagnosis_id, condition=entry["name"],
                            reason=rule["reason"], evidence=[f"{rule['field']}={value}"],
                            source="vital_sign", urgency=entry.get("urgency", "CRITICAL"),
                        ))

        # Demographic risk (spec section 15): e.g. a reproductive-age female with abdominal pain
        # gets ectopic pregnancy actively considered even before any pregnancy-specific keyword
        # has come up -- still gated to the matching chief-complaint tag, never a blanket check.
        demographics = state.demographics
        for rule in demographic_risk_rules():
            if not (presentation_tags & set(rule.get("chief_complaint_tags", []))):
                continue
            if rule.get("requires_sex") and (demographics.sex or "").lower() != rule["requires_sex"]:
                continue
            age = demographics.age
            if age is not None:
                if rule.get("age_min") is not None and age < rule["age_min"]:
                    continue
                if rule.get("age_max") is not None and age > rule["age_max"]:
                    continue
            entry = disease_by_id(rule["diagnosis_id"])
            if entry is None:
                continue
            findings.append(SafetyFinding(
                diagnosis_id=rule["diagnosis_id"], condition=entry["name"], reason=rule["reason"],
                evidence=[f"demographic: sex={demographics.sex}, age={demographics.age}"],
                source="demographic_risk", urgency=entry.get("urgency", "CRITICAL"),
            ))

        # Medication risk (spec section 15): a medication the patient reports (e.g. warfarin) that
        # is a known risk factor for a dangerous diagnosis relevant to THIS complaint raises that
        # diagnosis's priority even without its own symptom keywords having matched yet.
        medication_text_blob = " ".join(state.medication_text + [m.name for m in state.medications]).lower()
        if medication_text_blob:
            for rule in medication_risk_rules():
                if not (presentation_tags & set(rule.get("chief_complaint_tags", []))):
                    continue
                matched = [kw for kw in rule["trigger_keywords"] if kw in medication_text_blob]
                if not matched:
                    continue
                entry = disease_by_id(rule["diagnosis_id"])
                if entry is None:
                    continue
                findings.append(SafetyFinding(
                    diagnosis_id=rule["diagnosis_id"], condition=entry["name"], reason=rule["reason"],
                    evidence=[f"medication: {kw}" for kw in matched], source="medication_risk",
                    urgency=entry.get("urgency", "CRITICAL"),
                ))

        # Dedup (same diagnosis flagged by both a keyword and a vital sign) while keeping the
        # richer entry (more evidence).
        by_id: Dict[str, SafetyFinding] = {}
        for f in findings:
            existing = by_id.get(f.diagnosis_id)
            if existing is None or len(f.evidence) > len(existing.evidence):
                by_id[f.diagnosis_id] = f
            elif existing is not None:
                existing.evidence = list(dict.fromkeys(existing.evidence + f.evidence))

        result = sorted(by_id.values(), key=lambda f: f.condition)
        state.red_flags = [RedFlag(condition=f.condition, reason=f.reason, severity=f.urgency) for f in result]
        return result

    def safety_gain(self, diagnosis_id: str, findings: List[SafetyFinding]) -> float:
        """Boost magnitude used by action_selector.py's utility function: 1.0 if this diagnosis is
        currently flagged as a safety concern (still needs to be actively ruled out), else 0.0."""
        return 1.0 if any(f.diagnosis_id == diagnosis_id for f in findings) else 0.0
