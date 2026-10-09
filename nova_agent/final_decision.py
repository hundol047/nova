"""Round Q: ONE final decision for the preliminary-round DIAGNOSE -- the submitted primary, the SOAP assessment, the
closing explanation and the metadata are all produced from it, so they can no longer disagree.

Completion and support are separate questions:
- ``completion_reason`` says WHY the encounter ends: the stop policy found the leader supported, nothing meaningful
  is left to ask or examine (information exhausted), or the interaction budget ran out. Running out of actions or
  turns permits completion; it never makes a diagnosis supported.
- ``support`` says whether a SPECIFIC named diagnosis may be the primary. A candidate selected by catalog or safety
  order with no evidence, a dangerous diagnosis resting on a single non-specific observation, a dangerous tie decided
  only by insertion order, or a profile whose required current context was never observed is not named. A better
  supported candidate further down the top five may be named instead; otherwise the completion is an explicit
  "undifferentiated presentation" (wire key ``unknown``). No candidate is deleted or marked absent: everything stays
  in the differential and the SOAP plan.

Danger is never a reason to name a diagnosis and never adds score. PROVENANCE: engineering-authored contract; the
four required-context profiles cite their clinical sources inline; not clinician-reviewed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

UNDIFFERENTIATED_ID = "unknown"
UNDIFFERENTIATED_LABEL = {"en": "Undifferentiated presentation", "ko": "미분화 증상 (진단 미확정)"}


@dataclass(frozen=True)
class FinalDecision:
    primary_id: str
    item: Optional[object]                 # the DifferentialItem named as primary, None when undifferentiated
    support: str                           # "SUPPORTED" | "UNDIFFERENTIATED"
    completion_reason: str                 # "supported" | "information_exhausted" | "budget"
    reasons: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def undifferentiated(self) -> bool:
        return self.primary_id == UNDIFFERENTIATED_ID

    def label(self, lang: str = "en") -> str:
        if self.item is None:
            return UNDIFFERENTIATED_LABEL["ko" if lang == "ko" else "en"]
        return self.item.diagnosis

    def as_metadata(self) -> dict:
        return {"primary_id": self.primary_id, "support": self.support,
                "completion_reason": self.completion_reason, "reasons": list(self.reasons),
                "support_scope": "working_diagnosis_not_confirmation"}


def _current_texts(state) -> List[str]:
    return state.all_findings_text(include_context=False, include_family=False)


def _any_phrase(phrases: Tuple[str, ...]) -> Callable:
    def check(state, item) -> bool:
        from nova_agent.matching import feature_present_with_aliases
        current = _current_texts(state)
        return any(feature_present_with_aliases(p, current, scrub_negated_spans=True) for p in phrases)
    return check


def _hypertensive_range(state, item) -> bool:
    return any((v.sbp or 0) >= 180 or (v.dbp or 0) >= 120 for v in state.vital_signs)


# Required CURRENT context before a profile may be named as the primary (never a score change, never an exclusion).
_REQUIRED_CONTEXT: Dict[str, Tuple[str, Callable]] = {
    # Hypertensive emergency = severe BP elevation (>180/120 mm Hg) with acute target-organ damage
    # (Whelton PK et al., 2017 ACC/AHA High Blood Pressure Guideline, Hypertension 2018;71:e13, section 11.2).
    "hypertensive_emergency": ("measured blood pressure >= 180/120", _hypertensive_range),
    # Haemoptysis is, by definition, coughing up blood (NICE CKS "Haemoptysis", definition).
    "hemoptysis": ("blood actually coughed up", _any_phrase((
        "coughing up blood", "coughed up blood", "coughing blood", "blood in sputum", "blood in my sputum",
        "bloody sputum", "blood-stained sputum", "blood streaked sputum", "hemoptysis", "haemoptysis", "spitting blood",
        "객혈", "각혈", "피 섞인 가래", "피가 섞인 가래", "기침할 때 피"))),
    # SIADH is a cause of hypotonic hyponatraemia; symptoms alone cannot establish it -- a low sodium is required
    # (Spasovski G et al., European clinical practice guideline on hyponatraemia, Eur J Endocrinol 2014;170:G1).
    "siadh": ("documented low sodium", _any_phrase(("low sodium", "hyponatremia", "hyponatraemia", "저나트륨"))),
    # Ectopic pregnancy presents with pregnancy-related features: missed period, abdominal/pelvic pain, vaginal
    # bleeding, positive pregnancy test (NICE NG126, Ectopic pregnancy and miscarriage, section 1.2/1.3).
    "ectopic_pregnancy": ("a pregnancy-related feature", _any_phrase((
        "missed period", "late period", "period is late", "positive pregnancy test", "pregnant", "vaginal bleeding",
        "pelvic pain", "lower abdominal pain", "unilateral pelvic pain",
        "생리가 늦", "생리를 안", "생리가 없", "임신", "질 출혈", "하혈", "아랫배", "하복부", "골반 통증"))),
}


def _profile_key(diagnosis_id: str) -> Optional[str]:
    for key in _REQUIRED_CONTEXT:
        if diagnosis_id == key or diagnosis_id.endswith(":" + key) or diagnosis_id.endswith("_" + key) \
                or (key in diagnosis_id and diagnosis_id.startswith("onto::")):
            return key
    return None


def _entry(diagnosis_id: str) -> dict:
    from nova_agent.differential import _entry_for_candidate_id
    return _entry_for_candidate_id(diagnosis_id) or {}


def _specific_support(item, entry: dict) -> List[str]:
    """Supporting items that are objective/confirmatory (not a symptom any condition could share)."""
    from nova_agent.clinical_concepts import is_objective_only_feature
    confirm = {str(c).lower() for c in entry.get("confirmatory_findings", [])}
    # Measured is not synonymous with disease-specific. A pulse threshold is
    # a real observation and safety concern, not the rhythm's cause/subtype.
    return [e for e in item.supporting_evidence if not _nonspecific_measurement(e)
            and (e.lower() in confirm or e.lower().startswith("elevated lactate") or is_objective_only_feature(e))]


def _nonspecific_measurement(phrase: str) -> bool:
    return phrase.lower() in {"pulse rate below 50", "pulse rate of 150 or more", "tachycardia", "bradycardia"}


def _hemodynamic_only(phrase: str) -> bool:
    """Rate/perfusion observations cannot identify an underlying cause alone.

    A broader gate treating *every* abnormal observation as interchangeable was
    rejected: it erased converging fever/mental-state and hypoxic presentations.
    Keep those distinctions; do not claim to have proved an etiology from vitals.
    """
    return _nonspecific_measurement(phrase) or phrase.lower() in {
        "hypotension", "tachypnea", "shock", "low blood pressure"}


def _distinct(evidence: List[str]) -> int:
    """Distinct supporting observations: the same canonical phrase counts once. (Several features stated in one
    sentence -- "crushing chest pain to my left arm with sweating" -- are several observations.)"""
    from nova_agent.ontology.normalizer import normalize
    return len({normalize(e) or e.lower() for e in evidence})


# Symptoms too common across presentations to name a cause on their own. Engineering-authored list.
_GENERIC_SYMPTOMS = frozenset({
    "dizziness", "dizzy", "lightheadedness", "lightheaded", "nausea", "vomiting", "fatigue", "tiredness", "weakness",
    "generalized weakness", "generalised weakness", "malaise", "headache", "confusion", "fever", "cough", "chest pain",
    "abdominal pain", "shortness of breath", "dyspnea", "breathlessness", "palpitations", "feeling unwell", "syncope",
    "altered mental status", "anxiety", "sweating", "diaphoresis", "back pain", "productive cough", "diarrhea",
})


def _base_name(name: str) -> str:
    return re.sub(r"\s*\(.*?\)", "", name or "").strip().lower()


def _generic_symptom(phrase: str) -> bool:
    # Grammatical qualifiers are not new discriminating evidence.
    plain = re.sub(r"^(?:(?:associated|reported|persistent|severe|marked|profound)\s+)+", "", phrase.strip().lower())
    if plain in _GENERIC_SYMPTOMS:
        return True
    # A conjunction stored as ONE catalog feature does not become specific merely
    # because its components were joined. Anatomical/trigger qualifiers and any
    # non-generic component keep their existing discriminating interpretation.
    parts = re.split(r"\s+(?:and|or|with)\s+", plain)
    return len(parts) > 1 and all(p in _GENERIC_SYMPTOMS for p in parts)


def _risk_context(phrase: str) -> bool:
    """Some shallow ontology profiles store risk context under typical_features.
    Preserve ranking inputs, but a past illness/age cannot establish a current illness."""
    return bool(re.search(r"^(?:(?:known |family )?history of |known .+ on |prior |previous |older age$|advanced age$|young age$)",
                          phrase.lower())) or phrase.lower() == "atrial fibrillation or vascular disease"


def support_problems(item, state, differential: list) -> List[str]:
    """Why ``item`` may not be NAMED as the primary (empty list: it may)."""
    from nova_agent.differential import _strip_negative_prefix
    entry = _entry(item.diagnosis_id)
    problems: List[str] = []
    risk_only = {str(x).lower() for x in entry.get("risk_factors", [])}
    risk_only.update(e.lower() for e in item.supporting_evidence if _risk_context(e))
    positive = [e for e in item.supporting_evidence
                if e.lower() not in risk_only and _strip_negative_prefix(e) is None and e != "documented diagnosis"]
    documented = "documented diagnosis" in item.supporting_evidence
    if getattr(item, "fallback_candidate", False) or item.score <= 0 or not (positive or documented):
        return ["no_positive_support"]
    specific = _specific_support(item, entry)
    observations = [e for e in item.supporting_evidence if _strip_negative_prefix(e) is None]
    if positive and all(_hemodynamic_only(e) for e in positive) and not documented:
        problems.append("only_hemodynamic_support")
    if (not specific and not documented and _distinct(observations) <= 1
            and all(e.lower() in risk_only or _generic_symptom(e) or _nonspecific_measurement(e) for e in observations)):
        # ONE observation in total, and it is a symptom shared by most presentations or a lone risk factor
        # ("dizziness" -> ectopic pregnancy). A single SPECIFIC sign (facial droop) is not caught here.
        problems.append("single_nonspecific_support")
    index = next((i for i, d in enumerate(differential) if d.diagnosis_id == item.diagnosis_id), None)
    generic_only = all(e.lower() in risk_only or _generic_symptom(e) or _nonspecific_measurement(e) for e in observations)
    if item.dangerous_if_missed and generic_only and not specific and not documented:
        problems.append("only_nonspecific_support")
    if index is not None and item.dangerous_if_missed and not specific and not documented and generic_only:
        # A tie on generic evidence alone would be decided by insertion order. A neighbour that is the same disease
        # under another catalog name ("Septic Arthritis" / "Septic Arthritis (Joint)") is not a competitor.
        neighbours = [differential[j] for j in (index - 1, index + 1) if 0 <= j < len(differential)]
        if any(abs(n.score - item.score) < 1e-6 and _base_name(n.diagnosis) != _base_name(item.diagnosis)
               for n in neighbours):
            problems.append("tied_on_nonspecific_support")
    profile = _profile_key(item.diagnosis_id)
    if profile is not None:
        description, check = _REQUIRED_CONTEXT[profile]
        if not check(state, item):
            problems.append(f"required_context_missing:{description}")
    # ESC 2022 ventricular-arrhythmia guideline, doi:10.1093/eurheartj/ehac262,
    # section 5.1.3: rhythm subtype requires recorded electrical evidence. A rate alone
    # does not identify ventricular origin. Current clinician documentation is separate.
    if item.diagnosis_id == "onto::tier2:ventricular_tachycardia" and not documented:
        from nova_agent.matching import feature_present_with_aliases
        if not feature_present_with_aliases("ventricular tachycardia", state.objective_findings_text(),
                                            scrub_negated_spans=True, strict=True):
            problems.append("rhythm_subtype_not_observed")
    # NICE CG109 1.1.4.3: uncomplicated faint requires no features suggesting an
    # alternative. Reuse the existing measured-rate thresholds; do not infer an ECG.
    if item.diagnosis_id in {"vasovagal_syncope", "orthostatic_hypotension", "onto::tier2:orthostatic_hypotension"}:
        rate = state.latest_vital_signs()
        if rate and rate.heart_rate is not None and (rate.heart_rate < 50 or rate.heart_rate >= 150):
            problems.append("marked_pulse_rate_requires_explanation")
    return problems


def decide_final(state, differential: list, completion_reason: str = "supported") -> FinalDecision:
    """The leader if it may be named; else the best-ranked top-five candidate with SPECIFIC or at least two distinct
    supporting observations that may be named; else an undifferentiated completion."""
    from nova_agent.config import get_config
    if not differential:
        return FinalDecision(UNDIFFERENTIATED_ID, None, "UNDIFFERENTIATED", completion_reason, ("empty_differential",))
    leader = differential[0]
    if not get_config().final_decision_enabled:
        return FinalDecision(leader.diagnosis_id, leader, "SUPPORTED", completion_reason, ("final_decision_off",))
    leader_problems = support_problems(leader, state, differential)
    if not leader_problems:
        return FinalDecision(leader.diagnosis_id, leader, "SUPPORTED", completion_reason)
    reasons = tuple(f"leader:{p}" for p in leader_problems)
    for alt in differential[1:5]:
        if support_problems(alt, state, differential):
            continue
        entry = _entry(alt.diagnosis_id)
        if ("documented diagnosis" in alt.supporting_evidence or _specific_support(alt, entry)
                or _distinct(alt.supporting_evidence) >= 2):
            return FinalDecision(alt.diagnosis_id, alt, "SUPPORTED", completion_reason,
                                 reasons + (f"named:{alt.diagnosis_id}",))
    return FinalDecision(UNDIFFERENTIATED_ID, None, "UNDIFFERENTIATED", completion_reason, reasons)
