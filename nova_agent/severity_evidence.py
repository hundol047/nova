"""Generalizable objective physiologic-derangement evidence: a small, fixed set of vital-sign/
lab-value/exam-finding thresholds that mark a PATIENT (not any one diagnosis) as systemically sick.

This is a SEPARATE axis from diagnostic evidence, deliberately never mixed into it:
  - `systemic_severity_signals()` / `severity_score()` describe how physiologically deranged the
    patient currently looks -- shock, hypoxemia, marked tachycardia/tachypnea, high lactate,
    altered mental status, multi-organ dysfunction. This says nothing about which diagnosis is
    correct; it is used only for triage/safety purposes (stop_policy.py keeping a dangerous
    alternative "actively unresolved" even before its own diagnostic evidence is strong, and
    action_selector.py's existing safety-relevance weighting) -- never added to any diagnosis's
    own diagnostic_score in differential.py. An earlier version of this module DID feed a generic
    severity bonus into every `dangerous: true` diagnosis's score directly, and that produced a
    real, measured regression (a diagnosis with strong vitals-derangement-only "evidence" could
    outscore a diagnosis with genuine disease-specific confirmatory findings, e.g. a case that
    should have stayed a benign/localized diagnosis being swept into sepsis/stroke/PE purely
    because the patient looked sick in a way common to many different dangerous conditions at
    once). Diagnostic plausibility must keep coming ONLY from evidence specific to that one
    disease (its own typical_features/confirmatory_findings/risk_factors) -- severity_score never
    substitutes for that.
  - Numeric labs this codebase interprets for actual DIAGNOSTIC evidence (glucose for
    hypoglycemia/DKA in glucose_evidence.py; lactate for sepsis's own KB-declared "elevated
    lactate" confirmatory_finding in differential.py's `_score_lactate`) stay disease-specific and
    live in their own scoring functions, not here -- this module's job is only the patient-level
    triage signal, read the same numeric way ("lactate 1.1" and "lactate 8.4" share every content
    word but mean opposite things) for the same reason glucose_evidence.py reads glucose
    numerically instead of via word overlap.
"""

from __future__ import annotations

import re
from typing import List, Optional

from nova_agent.matching import feature_denied, feature_present
from nova_agent.glucose_evidence import current_asserted_lab_clauses
from nova_agent.state import PatientState

HYPOTENSION_SBP_THRESHOLD = 90
HYPOXEMIA_SPO2_THRESHOLD = 90
MARKED_TACHYCARDIA_HR_THRESHOLD = 130
MARKED_TACHYPNEA_RR_THRESHOLD = 28
ELEVATED_LACTATE_MMOL_L = 2.0
HIGH_LACTATE_MMOL_L = 4.0
# A lab result reported as a qualitative category ("elevated lactate") rather than a raw number is
# unambiguous on its own terms -- unlike a bare number (which genuinely needs threshold comparison,
# "lactate 1.1" vs "lactate 8.4"), "elevated" already IS the threshold judgment, so it is read as
# just-above-threshold rather than discarded for lacking a digit.
QUALITATIVE_ELEVATED_LACTATE_MMOL_L = ELEVATED_LACTATE_MMOL_L

_LACTATE_PATTERN = re.compile(r"lactate[^0-9]{0,15}?(\d{1,2}(?:\.\d+)?)", re.IGNORECASE)
# Round O: the result text read here is the LACTATE test's own result, so a bare value that explicitly carries the
# mmol/L unit ("4.6 mmol/L") is that lactate even without the analyte name repeated.
_BARE_MMOL_PATTERN = re.compile(r"^\s*(\d{1,2}(?:\.\d+)?)\s*mmol\s*/\s*l\b", re.IGNORECASE)
_QUALITATIVE_ELEVATED_LACTATE_PATTERN = re.compile(
    r"lactate[^.]{0,20}?\belevated\b|\belevated\b[^.]{0,20}?lactate", re.IGNORECASE,
)

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

# Round E (defect C: specific diagnostic evidence losing to generic physiologic severity): the
# vital-sign/physiologic-derangement WORDS this module's own thresholds above describe (hypotension,
# hypoxemia, marked tachycardia/tachypnea, fever) are shared, by definition, across dozens of
# dangerous diagnoses' own `typical_features` lists -- they mark a PATIENT as sick, never identify
# WHICH disease is present. differential.py's own docstring/module comment already establishes this
# principle for `severity_score()` itself (never folded into any one diagnosis's score directly),
# but a bare single-word typical_feature phrase like sepsis's "hypotension" or "tachycardia" could
# still reach the SAME diagnostic-identity role through plain word-overlap matching, each counting
# as full-weight disease-specific evidence via `_specificity_multiplier()`'s single-word floor --
# exactly the "generic severity outscores real disease-specific evidence" failure mode (confirmed:
# sepsis's typical_features 'tachycardia'+'hypotension'+'tachypnea' outscored anaphylaxis's own
# 'wheeze'+'hypotension' for a textbook anaphylaxis presentation, purely by matching MORE generic
# severity words). Exported for differential.py's `_specificity_multiplier()` to apply a reduced
# (never zero -- still real, if weak, corroborating signal) weight to a typical_feature phrase that
# reduces to nothing but one of these generic markers.
GENERIC_PHYSIOLOGIC_SEVERITY_WORDS = {
    "hypotension", "hypotensive", "tachycardia", "tachycardic", "bradycardia", "bradycardic",
    "tachypnea", "tachypneic", "bradypnea", "hypoxia", "hypoxemia", "hypoxemic", "fever", "febrile",
    "hyperthermia", "hypothermia", "shock",
}


def _labs_v2() -> bool:
    from nova_agent.config import get_config
    return get_config().labs_v2_enabled


def extract_lactate_mmol_l(lactate_result_text: Optional[str]) -> Optional[float]:
    """Parses PatientState.laboratory_tests.get("lactate") into a mmol/L value. None if no lactate
    test has been performed or the result can't be interpreted -- callers must treat None as "no
    evidence either way", never as a value of 0 (mirrors glucose_evidence.extract_glucose_mg_dl)."""
    if not lactate_result_text:
        return None
    # Unit safety (spec section 19): thresholds here are mmol/L. A value explicitly in mg/dL
    # (~18x larger) must NOT be read as a bare mmol/L number. A qualitative "elevated" with a
    # mg/dL number still counts via the qualitative path below; only the NUMERIC parse is refused.
    from nova_agent.unit_safety import value_is_in_disallowed_unit
    values = set()
    qualitative_high = False
    for clause in current_asserted_lab_clauses(lactate_result_text):
        unsafe = value_is_in_disallowed_unit(clause, ("mmol/l",), ("mg/dl",))
        matches = [] if unsafe else list(_LACTATE_PATTERN.finditer(clause))
        if not matches and not unsafe and _labs_v2():
            matches = list(_BARE_MMOL_PATTERN.finditer(clause))
        values.update(float(match.group(1)) for match in matches)
        if not matches and _QUALITATIVE_ELEVATED_LACTATE_PATTERN.search(clause):
            qualitative_high = True
        elif unsafe:
            return None
    if len(values) > 1:
        return None
    if values:
        value = next(iter(values))
        if qualitative_high and value < ELEVATED_LACTATE_MMOL_L:
            return None
        return value
    return QUALITATIVE_ELEVATED_LACTATE_MMOL_L if qualitative_high else None


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


# Total number of independent signal categories `systemic_severity_signals` can ever return -- a
# category can contribute at most once regardless of how many of its underlying phrases matched,
# since both loops above `break` after the first hit within their category.
SEVERITY_SIGNAL_CATEGORY_COUNT = 6  # hypotension, hypoxemia, tachycardia, tachypnea, lactate, AMS
# multi-organ dysfunction is a 7th, additive category.
TOTAL_SEVERITY_SIGNAL_CATEGORIES = SEVERITY_SIGNAL_CATEGORY_COUNT + 1


def severity_score(state: PatientState) -> float:
    """A single 0..1 patient-level triage score: what fraction of the fixed physiologic-derangement
    signal categories are currently confirmed. 0.0 for a stable/unmeasured patient, up to 1.0 for a
    patient matching every category at once. Deliberately coarse (a count-based fraction, not a
    calibrated severity index) -- it only needs to answer "how sick does this patient look right
    now", for triage/safety purposes, never for ranking any specific diagnosis's plausibility."""
    return len(systemic_severity_signals(state)) / TOTAL_SEVERITY_SIGNAL_CATEGORIES
