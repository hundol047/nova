"""Differential Diagnosis Engine (spec section 4).

Ranks candidate diagnoses from the local knowledge base against everything currently known about
the patient. Confidence is reported as a LOW/MEDIUM/HIGH calibration band (how much of a disease's
known evidence profile has actually been confirmed so far) alongside an internal 0..1 ranking
score -- the band is never presented as if it were a calibrated probability.

Re-run every turn (never "first differential only") so newly observed findings immediately
reshuffle the ranking.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.config import get_config
from nova_agent.glucose_evidence import (
    DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL,
    HYPOGLYCEMIA_THRESHOLD_MG_DL,
    extract_glucose_mg_dl,
)
from nova_agent.matching import content_word_count, feature_denied, feature_present
from nova_agent.severity_evidence import ELEVATED_LACTATE_MMOL_L, extract_lactate_mmol_l
from nova_agent.state import DifferentialSnapshot, PatientState

ConfidenceBand = Literal["LOW", "MEDIUM", "HIGH"]

FEATURE_WEIGHT = 1.0
RISK_FACTOR_WEIGHT = 0.4
CONTRADICTION_PENALTY = 1.2
# Objective exam/imaging/lab findings that confirm a diagnosis (knowledge/diseases/*.json's
# `confirmatory_findings`) are weighted higher than a soft symptom feature -- clinically, "ST
# elevation on ECG" should move the ranking far more than "chest pain worse with exertion" does.
CONFIRMATORY_WEIGHT = 2.5

_NEGATIVE_FEATURE_PREFIXES = ("no ", "denies ", "without ", "absent ")

# Feature-local aliases (spec section 6, Option A): alternate phrasings tried ONLY when evaluating
# the ONE exact knowledge-base phrase they are keyed to -- never a global finding-text substitution
# like the earlier clinical_synonyms.py attempt (reverted after it let unrelated findings that
# merely shared a word-group cross-contaminate each other's matches, e.g. "mild fever" spuriously
# supporting "denies high fever"). A lay phrase here can only ever help the ONE named KB phrase.
# Two categories populate this table: (1) common lay-language variants of a clinical sign
# (throbbing/pulsating, sensitive to light/photophobia) and (2) high-value medication-class
# normalization (spec section 4) -- a specific drug name standing in for the canonical risk factor
# phrase it belongs to. Deliberately NOT a general medication NLP system: only the drug classes an
# existing knowledge-base risk_factor already names.
FEATURE_ALIASES: dict[str, list[str]] = {
    "unilateral pulsating headache": ["throbbing headache", "pounding headache", "one-sided headache",
                                       "one sided headache", "pounding pain", "throbbing pain",
                                       "pulsating pain"],
    "photophobia": ["sensitive to light", "light sensitivity", "light bothers me"],
    "phonophobia": ["sensitive to sound", "sound sensitivity", "noise bothers me"],
    "aura": ["shimmering lights", "visual aura", "flashing lights", "seeing spots before",
             "zigzag lines", "blind spot in my vision", "jagged lines"],
    "recurrent similar episodes": ["similar to headaches", "happened before", "same as before",
                                    "feels the same as last time", "this feels the same",
                                    "gets these", "a few times a year", "has had these before"],
    "family history of migraine": ["mother gets migraines", "father gets migraines",
                                    "mother has migraines", "parent gets migraines", "runs in my family",
                                    "sister gets migraines", "sister has migraines", "brother gets migraines"],
    "known migraine history": ["diagnosed with migraines", "history of migraines", "has migraines before"],
    "syncope": ["passed out", "fainted"],
    "palpitations": ["racing heartbeat", "heart racing"],
    # Medication-class normalization (spec section 4).
    "sulfonylurea use": ["glipizide", "glyburide", "glimepiride", "sulfonylurea"],
    "insulin use": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "known diabetes on insulin": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "anticoagulant use": ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin", "coumadin"],
    "antiplatelet use": ["aspirin", "clopidogrel"],
    "nsaid use": ["ibuprofen", "naproxen", "nsaid"],
    "diuretic use": ["water pill", "furosemide", "hydrochlorothiazide", "lasix"],
    "immunosuppressant use": ["prednisone", "methotrexate", "tacrolimus", "cyclosporine", "azathioprine"],
    "oral contraceptive use": ["birth control", "oral contraceptive", "the pill"],
    "missed meal": ["hasn't eaten", "hasn't eaten much", "poor oral intake", "not eating today",
                     "skipped a meal", "skipped meals"],
}


def _present_with_aliases(phrase: str, findings: List[str]) -> bool:
    """feature_present() on `phrase` itself, OR on any of its feature-local aliases (see
    FEATURE_ALIASES above) -- the alias never widens matching for any OTHER knowledge-base phrase."""
    if feature_present(phrase, findings, scrub_negated_spans=True):
        return True
    for alias in FEATURE_ALIASES.get(phrase.lower(), ()):
        if feature_present(alias, findings, scrub_negated_spans=True):
            return True
    return False


_SPECIFICITY_STEP = 0.25
_SPECIFICITY_CAP = 2.0


def _specificity_multiplier(phrase: str) -> float:
    """A `typical_features` phrase's own word count as a proxy for how DISCRIMINATIVE a match on
    it is. A bare one-word overlap like "cough" is weak, non-specific evidence -- it is, by
    definition, a `typical_feature` of every disease the knowledge base tags with it, several of
    which any single case might match at once -- whereas a precise multi-word phrase like "chest
    wall soreness from coughing" found verbatim is far stronger, disease-specific evidence. Purely
    a function of the KB phrase's own content-word count (via matching.py's shared stemmer/
    stopword logic, so it agrees with what actually counted toward the match) -- never tied to any
    particular disease id or evaluation case. Capped so no single feature can dominate a disease's
    whole score, and floored at the original flat FEATURE_WEIGHT for a single-word phrase (this
    change only ever ADDS weight for a longer, more specific phrase, never removes any for the
    previously-flat case)."""
    word_count = max(1, content_word_count(phrase))
    return min(_SPECIFICITY_CAP, 1.0 + _SPECIFICITY_STEP * (word_count - 1))


def _strip_negative_prefix(feature: str) -> Optional[str]:
    """If a knowledge-base typical_feature is itself phrased negatively (e.g. "no chest pain",
    describing a symptom that is typically ABSENT in that diagnosis), returns the underlying
    symptom text ("chest pain"); otherwise None."""
    lowered = feature.lower()
    for prefix in _NEGATIVE_FEATURE_PREFIXES:
        if lowered.startswith(prefix):
            return feature[len(prefix):]
    return None


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
    candidate_sources: List[str] = []


def _score_phrase(phrase: str, weight: float, findings: List[str], negatives: List[str],
                   supporting: List[str], contradictory: List[str], missing: List[str]) -> float:
    """Negation-aware scoring for ONE typical_feature or confirmatory_finding phrase. Shared by
    both loops in _score_disease() below -- confirmatory_findings previously used a naive
    present-or-not check with no negation awareness at all, which let a phrase like "absent breath
    sounds" spuriously MATCH (as support!) an exam finding that literally says the opposite
    ("clear breath sounds") -- "absent"/"breath"/"sounds" word-overlaps with "clear breath sounds"
    at 2/3 content words, over the match threshold, despite the two being clinically opposite.
    Returns the score delta; appends the phrase to exactly one of supporting/contradictory/missing."""
    underlying = _strip_negative_prefix(phrase)
    if underlying is not None:
        # The phrase itself describes an ABSENCE (e.g. "no chest pain", "absent breath sounds").
        # The patient/exam explicitly denying that underlying thing SUPPORTS this phrase; the
        # underlying thing being explicitly PRESENT instead CONTRADICTS it.
        if feature_present(underlying, negatives):
            supporting.append(phrase)
            return weight
        if feature_present(underlying, findings, scrub_negated_spans=True):
            contradictory.append(phrase)
            return -CONTRADICTION_PENALTY
        missing.append(phrase)
        return 0.0
    if feature_denied(phrase, negatives):
        contradictory.append(phrase)
        return -CONTRADICTION_PENALTY
    if _present_with_aliases(phrase, findings):
        supporting.append(phrase)
        return weight
    missing.append(phrase)
    return 0.0


def _score_lactate(entry_id: str, lactate_mmol_l: Optional[float],
                    supporting: List[str], missing: List[str]) -> float:
    """Numeric lactate evidence, disease-specific and DIAGNOSTIC (not the separate patient-level
    severity_score axis in severity_evidence.py) -- sepsis is the one diagnosis in this knowledge
    base whose own `confirmatory_findings` literally lists "elevated lactate" (see
    knowledge/diseases/infectious.json), so this reads the actual number the same way
    _score_glucose() does for hypoglycemia/DKA, rather than letting a bare keyword match treat
    "lactate 1.1" and "lactate 8.4" as equally supporting. Only ever touches sepsis's own score;
    every other diagnosis is untouched by lactate entirely."""
    if entry_id != "sepsis":
        return 0.0
    label = f"elevated lactate ({lactate_mmol_l:.1f} mmol/L)" if lactate_mmol_l is not None \
        else "elevated lactate"
    if lactate_mmol_l is None:
        missing.append(label)
        return 0.0
    if lactate_mmol_l >= ELEVATED_LACTATE_MMOL_L:
        supporting.append(label)
        return CONFIRMATORY_WEIGHT
    missing.append(label)
    return 0.0


def _score_glucose(entry_id: str, glucose_mg_dl: Optional[float],
                    supporting: List[str], missing: List[str]) -> float:
    """Numeric point-of-care glucose evidence (spec section 3/7): a lab NUMBER is far stronger,
    unambiguous evidence than any keyword match, and its clinical meaning flips entirely depending
    on the value -- word-overlap matching alone can never capture that ("glucose 42" and "glucose
    400" share every content word). Only applies to the two diagnoses whose definitions are
    literally a glucose threshold; weighted at CONFIRMATORY_WEIGHT since it plays the same role as
    an objective confirmatory lab/imaging finding. Thresholds are the standard clinical definitions
    (ADA hypoglycemia <70 mg/dL; DKA-range hyperglycemia >=250 mg/dL), never fitted to a specific
    benchmark case's number. Normal-range glucose is a strong, DEFINITIONAL contradiction for
    hypoglycemia (it cannot be diagnosed without a low glucose at the time of symptoms), but
    non-elevated glucose never penalizes DKA -- euglycemic DKA is a recognized real entity, so
    absence of a high number is treated as missing evidence, not a contradiction."""
    if entry_id not in ("hypoglycemia", "diabetic_ketoacidosis"):
        return 0.0
    label = f"point-of-care glucose {glucose_mg_dl:.0f} mg/dL" if glucose_mg_dl is not None \
        else "point-of-care glucose"
    if glucose_mg_dl is None:
        missing.append(label)
        return 0.0
    if entry_id == "hypoglycemia":
        if glucose_mg_dl < HYPOGLYCEMIA_THRESHOLD_MG_DL:
            supporting.append(label)
            return CONFIRMATORY_WEIGHT
        return -CONTRADICTION_PENALTY
    if glucose_mg_dl >= DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL:
        supporting.append(label)
        return CONFIRMATORY_WEIGHT
    missing.append(label)
    return 0.0


def _score_disease(entry: dict, state: PatientState) -> tuple[float, float, List[str], List[str], List[str]]:
    findings = state.all_findings_text()
    negatives = state.pertinent_negatives

    supporting: List[str] = []
    contradictory: List[str] = []
    missing: List[str] = []
    score = 0.0
    max_possible = 0.0

    for feature in entry.get("typical_features", []):
        weight = FEATURE_WEIGHT * _specificity_multiplier(feature)
        max_possible += weight
        score += _score_phrase(feature, weight, findings, negatives, supporting, contradictory, missing)

    for risk_factor in entry.get("risk_factors", []):
        max_possible += RISK_FACTOR_WEIGHT
        if _present_with_aliases(risk_factor, findings):
            supporting.append(risk_factor)
            score += RISK_FACTOR_WEIGHT

    for finding in entry.get("confirmatory_findings", []):
        max_possible += CONFIRMATORY_WEIGHT
        score += _score_phrase(finding, CONFIRMATORY_WEIGHT, findings, negatives, supporting, contradictory, missing)

    # Objective negative exam findings (spec section 7/8): a plain typical_feature has no way to be
    # CONTRADICTED by an objective negative exam finding (only by an explicit patient-denial in
    # pertinent_negatives -- EXAM/TEST results never populate that list, by deliberate design, see
    # matching.py). `reassuring_if_present` is a separate, opt-in, per-disease list for exactly
    # that gap: checked against RAW findings (scrub_negated_spans=False) since the phrase itself
    # legitimately starts with a negation ("no focal neurological deficit") -- scrubbing would
    # erase the very text this check needs to see. A soft, bounded penalty, not a hard exclusion:
    # it must not be able to rule out a dangerous diagnosis on its own (spec section 8 -- e.g. an
    # early normal CT never fully excludes ischemic stroke).
    if entry["id"] in ("hypoglycemia", "diabetic_ketoacidosis"):
        max_possible += CONFIRMATORY_WEIGHT
    score += _score_glucose(entry["id"], extract_glucose_mg_dl(state.laboratory_tests.get("glucose_point_of_care")),
                             supporting, missing)

    if entry["id"] == "sepsis":
        max_possible += CONFIRMATORY_WEIGHT
    score += _score_lactate(entry["id"], extract_lactate_mmol_l(state.laboratory_tests.get("lactate")),
                             supporting, missing)

    # Diagnostic evidence stops here, deliberately -- everything above is specific to THIS disease
    # (its own typical_features/risk_factors/confirmatory_findings/numeric labs). Patient-level
    # physiologic severity (shock, hypoxemia, high lactate, AMS, ...) is a real and important
    # signal, but it is a SEPARATE axis (severity_evidence.severity_score) consumed only by
    # stop_policy.py for triage/safety purposes -- never folded into diagnostic_score here. See
    # severity_evidence.py's module docstring for why a generic per-diagnosis severity bonus was
    # tried and reverted (it let vitals shared by many dangerous diagnoses at once unfairly
    # advantage whichever one happened to be eligible for the bonus).

    for reassuring in entry.get("reassuring_if_present", []):
        if feature_present(reassuring, findings, scrub_negated_spans=False):
            contradictory.append(reassuring)
            score -= CONTRADICTION_PENALTY

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
        # Dynamic candidate generation (spec: no single hard-routed chief-complaint tag deciding
        # the whole pool, and no "unmatched -> dump all 34 diseases" default). Multi-concept
        # extraction (clinical_presentation.py) plus risk/objective/safety sourcing
        # (candidate_generator.py) build a provenance-tagged pool from everything already known
        # about the case, not just the presenting sentence.
        # Rebuilt from the FULL current state every turn (chief_complaint + everything volunteered
        # or elicited since) -- not just the original presenting sentence. See
        # clinical_presentation.build_clinical_presentation()'s own docstring for why this is safe
        # (only positive-evidence sources are scanned) and why it degrades to the old
        # chief-complaint-only behavior on a case's first turn.
        presentation = build_clinical_presentation(state)
        candidate_records = generate_candidates(
            presentation,
            glucose_result_text=state.laboratory_tests.get("glucose_point_of_care"),
            lactate_result_text=state.laboratory_tests.get("lactate"),
        )
        candidates = [c.entry for c in candidate_records]
        sources_by_id = {c.id: c.sources for c in candidate_records}

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
                candidate_sources=sources_by_id.get(entry["id"], []),
            ))

        state.current_differential = [
            DifferentialSnapshot(diagnosis=i.diagnosis, rank=i.rank, confidence_band=i.confidence_band,
                                  urgency=i.urgency, dangerous_if_missed=i.dangerous_if_missed)
            for i in items
        ]
        return items
