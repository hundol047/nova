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
from typing import Dict, List, Optional

from nova_agent.chief_complaint import _scores

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
]

_SEVERITY_PATTERNS = [
    (re.compile(r"\b(worst|excruciating|unbearable|severe|intense|extreme)\b", re.IGNORECASE), "severe"),
    (re.compile(r"\b(mild|slight|a little|minor)\b", re.IGNORECASE), "mild"),
    (re.compile(r"\b(moderate)\b", re.IGNORECASE), "moderate"),
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
