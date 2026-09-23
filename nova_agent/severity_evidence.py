"""Generalizable objective physiologic-derangement evidence (spec section 6/8/9): a small, fixed
set of vital-sign/lab-value/exam-finding thresholds that mark a patient as systemically SICK,
independent of which localized symptom or source the chief complaint pointed to.

Deliberately NOT disease-specific -- there is no "pyelonephritis -> sepsis" rule anywhere here.
Every signal below is a standard clinical severity marker (the same vitals/labs a qSOFA/shock-index
assessment would use), and differential.py applies the resulting evidence generically to every
diagnosis in chief_complaint.CROSS_CUTTING_DANGEROUS_DIAGNOSES, never to one named disease. A
diagnosis only benefits when the objective evidence for the PATIENT is actually present in the
case -- this module never manufactures a diagnosis-specific boost, and awards nothing at all when
vitals/labs are normal or unmeasured (spec section 9: no over-triggering on a stable patient).

Vitals and lactate are read as NUMBERS from structured/parsed state, not matched as keywords --
"lactate 1.1" and "lactate 8.4" share every content word but mean opposite things, exactly the
reason glucose_evidence.py reads glucose numerically instead of via word overlap.
"""

from __future__ import annotations

import re
from typing import List, Optional

from nova_agent.matching import feature_denied, feature_present
from nova_agent.state import PatientState

HYPOTENSION_SBP_THRESHOLD = 90
HYPOXEMIA_SPO2_THRESHOLD = 90
MARKED_TACHYCARDIA_HR_THRESHOLD = 130
MARKED_TACHYPNEA_RR_THRESHOLD = 28
ELEVATED_LACTATE_MMOL_L = 2.0
HIGH_LACTATE_MMOL_L = 4.0

_LACTATE_PATTERN = re.compile(r"lactate[^0-9]{0,15}?(\d{1,2}(?:\.\d+)?)", re.IGNORECASE)

# Generic phrasings, not tied to any one disease's wording -- the same kind of small, fixed,
# clinically-standard list glucose_evidence.py's threshold constants already are.
_ALTERED_MENTAL_STATUS_PHRASES = [
    "altered mental status", "confusion", "confused", "disoriented", "lethargic",
    "obtunded", "unresponsive",
]

_MULTI_ORGAN_DYSFUNCTION_PHRASES = [
    "acute kidney injury", "elevated creatinine", "rising creatinine", "coagulopathy",
    "thrombocytopenia", "elevated bilirubin", "liver dysfunction", "oliguria",
]


def extract_lactate_mmol_l(lactate_result_text: Optional[str]) -> Optional[float]:
    """Parses PatientState.laboratory_tests.get("lactate") into a mmol/L value. None if no lactate
    test has been performed or the result can't be interpreted -- callers must treat None as "no
    evidence either way", never as a value of 0 (mirrors glucose_evidence.extract_glucose_mg_dl)."""
    if not lactate_result_text:
        return None
    match = _LACTATE_PATTERN.search(lactate_result_text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def systemic_severity_signals(state: PatientState) -> List[str]:
    """Every objective physiologic-derangement signal actually confirmed so far, as short
    human-readable evidence labels. Independent detectors -- a case can match several at once,
    which is the point: multiple simultaneous derangements is what should let a systemic syndrome
    outscore a single localized confirmatory finding, without hand-coding that comparison for any
    specific pair of diagnoses."""
    signals: List[str] = []
    vitals = state.latest_vital_signs()
    if vitals is not None:
        if vitals.sbp is not None and vitals.sbp < HYPOTENSION_SBP_THRESHOLD:
            signals.append(f"hypotension/shock (SBP {vitals.sbp})")
        if vitals.spo2 is not None and vitals.spo2 < HYPOXEMIA_SPO2_THRESHOLD:
            signals.append(f"hypoxemia (SpO2 {vitals.spo2}%)")
        if vitals.heart_rate is not None and vitals.heart_rate > MARKED_TACHYCARDIA_HR_THRESHOLD:
            signals.append(f"marked tachycardia (HR {vitals.heart_rate})")
        if vitals.respiratory_rate is not None and vitals.respiratory_rate > MARKED_TACHYPNEA_RR_THRESHOLD:
            signals.append(f"marked tachypnea (RR {vitals.respiratory_rate})")

    lactate = extract_lactate_mmol_l(state.laboratory_tests.get("lactate"))
    if lactate is not None and lactate >= HIGH_LACTATE_MMOL_L:
        signals.append(f"high lactate ({lactate:.1f} mmol/L)")

    findings = state.all_findings_text()
    negatives = state.pertinent_negatives
    for phrase in _ALTERED_MENTAL_STATUS_PHRASES:
        if feature_denied(phrase, negatives):
            continue
        if feature_present(phrase, findings, scrub_negated_spans=True):
            signals.append("altered mental status")
            break

    for phrase in _MULTI_ORGAN_DYSFUNCTION_PHRASES:
        if feature_denied(phrase, negatives):
            continue
        if feature_present(phrase, findings, scrub_negated_spans=True):
            signals.append("multi-organ dysfunction (" + phrase + ")")
            break

    return signals


# Total number of independent signal categories `systemic_severity_signals` can ever return --
# used by differential.py to size max_possible consistently (a category can contribute at most
# once regardless of how many of its underlying phrases matched, since both loops above `break`
# after the first hit within their category).
SEVERITY_SIGNAL_CATEGORY_COUNT = 6  # hypotension, hypoxemia, tachycardia, tachypnea, lactate, AMS
# multi-organ dysfunction is a 7th, additive category.
TOTAL_SEVERITY_SIGNAL_CATEGORIES = SEVERITY_SIGNAL_CATEGORY_COUNT + 1
