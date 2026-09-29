"""Context-aware critical safety activation (Round E, defect B).

`chief_complaint.CROSS_CUTTING_DANGEROUS_DIAGNOSES` is a small, FIXED, UNCONDITIONAL list --
always in the candidate pool regardless of context, by design cheap/safe for genuinely common
life-threats (sepsis, ACS, PE, stroke, dissection, DKA, hypoglycemia, acute_abdomen). Growing that
list to also unconditionally cover every OTHER dangerous diagnosis with any plausible context
(ectopic pregnancy, testicular torsion, ...) would blanket-inflate the candidate pool -- and
therefore the workup -- for every single case regardless of relevance, destroying the point of
dynamic, evidence-driven candidate generation.

This module is the alternative: a small table of CONTEXTUAL activation rules, each pairing one
dangerous diagnosis with a NARROW predicate over demographics / chief-complaint routing concepts /
pregnancy status -- e.g. a reproductive-age patient with abdominal/pelvic symptoms, or unexplained
syncope/bleeding, specifically justifies considering ectopic pregnancy; nothing else does. Every
predicate reasons over the same structured signals every other candidate-generation step already
uses (ClinicalPresentation.symptoms/demographic_context) -- never a single case's exact wording,
never a blanket "always include."

Activating a diagnosis here only means it ENTERS the pool for ordinary scoring/ranking, exactly
like any other CandidateSource -- it is not "kept forever": once real evidence (or the lack of it)
is gathered, differential.py's normal scoring and resolution.py's existing is_resolved() logic can
rank it down or let it leave the active differential exactly as any other candidate would.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from nova_agent.clinical_presentation import ClinicalPresentation

REPRODUCTIVE_AGE_MIN = 12
REPRODUCTIVE_AGE_MAX = 55

# Concepts chief_complaint.py already routes to that plausibly involve the pelvis/abdomen, or that
# represent an otherwise-unexplained acute event (syncope, GI/vaginal-type bleeding) worth
# considering a pregnancy-related emergency cause for in a reproductive-age patient.
_ABDOMINAL_PELVIC_CONCEPTS = {"abdominal_pain", "pelvic_gynecologic"}
_UNEXPLAINED_ACUTE_EVENT_CONCEPTS = {"syncope", "gi_bleeding"}


def _is_reproductive_age_female(demographic_context: Dict[str, object]) -> bool:
    sex = str(demographic_context.get("sex") or "").strip().lower()
    if sex not in ("female", "f"):
        return False
    age = demographic_context.get("age")
    if not isinstance(age, (int, float)):
        return False
    return REPRODUCTIVE_AGE_MIN <= age <= REPRODUCTIVE_AGE_MAX


def _ectopic_pregnancy_context_applies(presentation: ClinicalPresentation) -> bool:
    """A reproductive-age patient (sex + age both known and in range) is NEVER assumed pregnant or
    assumed to have an ectopic pregnancy on demographics alone -- activation additionally requires
    a plausible presenting concept (abdominal/pelvic symptoms, or an otherwise-unexplained syncope/
    bleeding event) already extracted by the SAME routing pipeline every other candidate uses.
    Explicit demographics.pregnant == False (rare, only ever set when the competition observation
    itself supplies it) rules this out entirely -- a real exclusion, not silently ignored."""
    demo = presentation.demographic_context
    if demo.get("pregnant") is False:
        return False
    if not _is_reproductive_age_female(demo):
        return False
    symptom_tags = set(presentation.symptoms)
    return bool(symptom_tags & (_ABDOMINAL_PELVIC_CONCEPTS | _UNEXPLAINED_ACUTE_EVENT_CONCEPTS))


@dataclass(frozen=True)
class ContextualActivation:
    diagnosis_id: str
    predicate: Callable[[ClinicalPresentation], bool]
    reason: str


# Hand-curated, narrow, and small BY DESIGN -- each entry is a real architectural gap this round's
# audit identified (a dangerous diagnosis reachable only through vague/atypical presentations that
# the fixed CROSS_CUTTING_DANGEROUS_DIAGNOSES list does not cover), never a case-specific patch.
CONTEXTUAL_DANGEROUS_ACTIVATIONS: List[ContextualActivation] = [
    ContextualActivation(
        diagnosis_id="ectopic_pregnancy",
        predicate=_ectopic_pregnancy_context_applies,
        reason="reproductive-age patient with abdominal/pelvic symptoms or unexplained syncope/bleeding",
    ),
]


def contextually_activated_diagnosis_ids(presentation: ClinicalPresentation) -> List[str]:
    """Every dangerous diagnosis whose contextual predicate matches this presentation -- used by
    candidate_generator.py to add a small, targeted, ADDITIVE set of candidates on top of (never
    instead of) ordinary symptom/risk/objective-evidence sourcing."""
    return [rule.diagnosis_id for rule in CONTEXTUAL_DANGEROUS_ACTIVATIONS if rule.predicate(presentation)]
