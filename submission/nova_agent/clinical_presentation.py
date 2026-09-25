"""Multi-concept clinical presentation extraction (spec: don't rely on a single chief-complaint
routing tag for a raw presentation that plausibly names several distinct clinical concepts at
once).

`chief_complaint.py`'s `route()` remains the single-best-tag primary/secondary/confidence
mechanism `differential.py` uses to size a candidate pool (kept as a compatibility layer, not
deleted). `extract_presentation()` here is a genuinely different, additive capability: it pulls
out EVERY concept the presenting text plausibly names at once (e.g. "sudden onset, can't find my
words, and my right arm won't work" -> `aphasia` AND `focal_weakness` simultaneously, not just
whichever one happens to score highest), plus lightweight temporality/severity/risk extraction --
feeding `candidate_generator.py`'s dynamic pool construction rather than a single hard-routed tag.

Deliberately reuses `chief_complaint.py`'s existing concept-scoped matching (`_scores()`, the same
exact/alias/fuzzy hierarchy, the same `CONCEPT_PHRASES` tables) instead of a second, separate
matching mechanism -- one scoped vocabulary per concept, never a global synonym table.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

from nova_agent.chief_complaint import _scores

if TYPE_CHECKING:
    from nova_agent.state import PatientState

# A concept is included in ClinicalPresentation.symptoms once it clears this score -- lower than
# chief_complaint.py's own single-best-tag threshold implicitly requires, since multi-concept
# extraction deliberately wants to surface a real but secondary concept ("and some nausea too")
# alongside the dominant one, not just the single top match.
_MULTI_CONCEPT_INCLUSION_THRESHOLD = 0.55

_ONSET_PATTERNS = [
    (re.compile(r"\bsudden(ly)?\b", re.IGNORECASE), "sudden"),
    (re.compile(r"\bacute(ly)?\b", re.IGNORECASE), "acute"),
    (re.compile(r"\bgradual(ly)?\b", re.IGNORECASE), "gradual"),
    (re.compile(r"\bslowly\b", re.IGNORECASE), "gradual"),
    (re.compile(r"\bover (the )?(past |last )?(few )?(hours|days|weeks|months)\b", re.IGNORECASE), "gradual"),
    (re.compile(r"\bwoke up (with|and)\b", re.IGNORECASE), "unknown (present on waking)"),
    (re.compile(r"\bfor (the )?(past |last )?\d+\s*(minute|hour|day|week|month)s?\b", re.IGNORECASE), "stated duration"),
    (re.compile(r"\bsince (yesterday|this morning|last night|today)\b", re.IGNORECASE), "stated duration"),
    # Korean
    (re.compile(r"갑자기"), "sudden"),
    (re.compile(r"서서히"), "gradual"),
    (re.compile(r"오늘|어제부터|며칠 전부터|한 시간 전부터"), "stated duration"),
    # Japanese
    (re.compile(r"突然"), "sudden"),
    (re.compile(r"徐々に"), "gradual"),
    (re.compile(r"今日|昨日から|数日前から"), "stated duration"),
    # Chinese (simplified)
    (re.compile(r"突然"), "sudden"),
    (re.compile(r"逐渐"), "gradual"),
    (re.compile(r"今天|从昨天开始|几天前开始"), "stated duration"),
]

_SEVERITY_PATTERNS = [
    (re.compile(r"\b(worst|excruciating|unbearable|severe|intense|extreme)\b", re.IGNORECASE), "severe"),
    (re.compile(r"\b(mild|slight|a little|minor)\b", re.IGNORECASE), "mild"),
    (re.compile(r"\b(moderate)\b", re.IGNORECASE), "moderate"),
    # Korean
    (re.compile(r"극심한|견딜 수 없는|심한"), "severe"),
    (re.compile(r"약한"), "mild"),
    # Japanese
    (re.compile(r"激しい|ひどい|耐えられない"), "severe"),
    (re.compile(r"軽い"), "mild"),
    # Chinese (simplified)
    (re.compile(r"严重|剧烈|无法忍受"), "severe"),
    (re.compile(r"轻微"), "mild"),
]

_BODY_REGION_BY_CONCEPT = {
    "chest_pain": "chest", "abdominal_pain": "abdomen", "headache": "head",
    "back_pain": "back/flank", "leg_swelling": "leg", "urinary_symptoms": "pelvis/urinary tract",
    "pelvic_gynecologic": "pelvis", "focal_weakness": "extremity", "aphasia": "head/neuro",
    "gi_bleeding": "gastrointestinal tract", "trauma": "site of injury",
}


@dataclass
class ClinicalPresentation:
    symptoms: List[str] = field(default_factory=list)            # every concept tag that scored
    onset: Optional[str] = None
    duration_hint: Optional[str] = None
    body_regions: List[str] = field(default_factory=list)
    severity_features: List[str] = field(default_factory=list)
    associated_features: List[str] = field(default_factory=list)  # secondary concepts, ranked
    risk_factors: List[str] = field(default_factory=list)
    medication_context: List[str] = field(default_factory=list)
    demographic_context: Dict[str, object] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)    # per-concept score


def extract_presentation(raw_text: str, *, past_medical_history: Optional[List[str]] = None,
                          medications: Optional[List[str]] = None,
                          demographics: Optional[Dict[str, object]] = None) -> ClinicalPresentation:
    """Pulls every plausible clinical concept out of `raw_text` at once, plus lightweight
    temporality/severity extraction -- deliberately conservative regex-based extraction (no
    guessed values), consistent with the rest of this codebase's determinism requirements."""
    scored = _scores(raw_text)
    symptoms = [tag for tag, score, _mt in scored if score >= _MULTI_CONCEPT_INCLUSION_THRESHOLD]
    confidence = {tag: round(score, 3) for tag, score, _mt in scored}

    onset = None
    for pattern, label in _ONSET_PATTERNS:
        if pattern.search(raw_text or ""):
            onset = label
            break

    duration_hint = None
    duration_match = re.search(
        r"\b(\d+\s*(?:minute|hour|day|week|month)s?)\b", raw_text or "", re.IGNORECASE)
    if duration_match:
        duration_hint = duration_match.group(1)

    severity_features = []
    for pattern, label in _SEVERITY_PATTERNS:
        if pattern.search(raw_text or "") and label not in severity_features:
            severity_features.append(label)

    body_regions = []
    for tag in symptoms:
        region = _BODY_REGION_BY_CONCEPT.get(tag)
        if region and region not in body_regions:
            body_regions.append(region)

    return ClinicalPresentation(
        symptoms=symptoms,
        onset=onset,
        duration_hint=duration_hint,
        body_regions=body_regions,
        severity_features=severity_features,
        associated_features=symptoms[1:],
        risk_factors=list(past_medical_history or []),
        medication_context=list(medications or []),
        demographic_context=dict(demographics or {}),
        confidence=confidence,
    )


def build_clinical_presentation(state: "PatientState") -> ClinicalPresentation:
    """Re-derives ClinicalPresentation from the FULL current PatientState every turn, not just the
    original presenting sentence -- so a later ASK/EXAM/TEST answer's own findings (e.g. "and my
    right arm went numb too", volunteered on turn 4) feed candidate generation exactly the way the
    initial chief complaint does, instead of being visible only through the disease-scoring layer's
    own separate keyword matching (differential.py's `_score_disease`).

    Only POSITIVE, already-negation-filtered evidence sources are scanned for concept matches:
    `chief_complaint`, `symptoms`, `associated_symptoms`, and `pertinent_positives`.
    `pertinent_negatives` is deliberately EXCLUDED -- `chief_complaint._scores()` (which this
    function delegates to via `extract_presentation()`) has no negation awareness of its own;
    feeding it already-denied text like "denies chest pain" would spuriously re-add a ruled-out
    concept as if newly reported. `state.raw_history_facts` is ALSO deliberately excluded for the
    same reason: unlike `pertinent_positives`/`associated_symptoms` (which `_absorb_answer()`
    already splits into clause-level segments and filters by negation before storing),
    `raw_history_facts` keeps the answer's FULL original text verbatim -- e.g. a single stored
    entry like "[associated_symptoms] runny nose, sore throat; denies shortness of breath, denies
    chest pain" -- so scanning it would re-inject the same denied "chest pain" text this function
    is trying to keep out. (State.py's own `_absorb_answer()` already does the negation-aware
    segment classification that sorts a free-text answer into `pertinent_positives` vs
    `pertinent_negatives` in the first place -- this function trusts and reuses that classification
    rather than re-deriving it from the raw, unsegmented text.)

    At turn 0 (no observations recorded yet), every source besides `chief_complaint` is empty, so
    this degrades to exactly `extract_presentation(state.chief_complaint, ...)` -- the pre-existing
    behavior for a case's very first decide() call is unchanged."""
    positive_sources = [
        state.chief_complaint,
        *state.symptoms,
        *state.associated_symptoms,
        *state.pertinent_positives,
    ]
    combined_text = " ".join(s for s in positive_sources if s)
    demographics = (state.demographics.model_dump()
                    if hasattr(state.demographics, "model_dump") else dict(state.demographics or {}))
    return extract_presentation(
        combined_text,
        past_medical_history=list(state.past_medical_history) + list(state.social_history),
        medications=list(state.medication_text) + [m.name for m in state.medications],
        demographics=demographics,
    )
