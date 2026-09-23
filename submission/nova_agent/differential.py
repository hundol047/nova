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

from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.chief_complaint import related_tags, top_candidates
from nova_agent.config import get_config
from nova_agent.glucose_evidence import (
    DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL,
    HYPOGLYCEMIA_THRESHOLD_MG_DL,
    extract_glucose_mg_dl,
)
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id, diseases_for_tag
from nova_agent.matching import feature_denied, feature_present
from nova_agent.severity_evidence import TOTAL_SEVERITY_SIGNAL_CATEGORIES, systemic_severity_signals
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
        max_possible += FEATURE_WEIGHT
        score += _score_phrase(feature, FEATURE_WEIGHT, findings, negatives, supporting, contradictory, missing)

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

    # Generalizable systemic-severity evidence (spec section 6/8/9): objective physiologic
    # derangement (shock, hypoxemia, marked tachycardia/tachypnea, high lactate, AMS, multi-organ
    # dysfunction) is scored at the same objective-evidence tier as a confirmatory lab/imaging
    # finding, for every diagnosis the knowledge base itself already flags `dangerous: true` --
    # never one named disease. Eligibility deliberately uses the KB's own existing dangerous flag
    # rather than the smaller CROSS_CUTTING_DANGEROUS_DIAGNOSES routing list: an earlier version of
    # this restricted eligibility to that shorter list and it produced a real, measured regression
    # (sepsis outscoring the correctly-diagnosed anaphylaxis/tension-pneumothorax cases in held-out)
    # -- shock/hypoxemia/tachycardia are shared physiology across MANY dangerous diagnoses, so
    # awarding the same generic boost to only a curated subset unfairly advantaged that subset over
    # equally-dangerous diagnoses (anaphylaxis, tension pneumothorax, ...) whenever they share the
    # same vitals picture, which is exactly the kind of diagnosis-specific favoritism the spec
    # prohibits. Every `dangerous: true` diagnosis competing on the same footing removes that bias.
    # Gated on real signals actually being present (see severity_evidence.py): a stable patient
    # contributes nothing here, so this can only ever help a genuinely sick-looking presentation
    # compete against a localized diagnosis, never inflate every case toward the dangerous list.
    if entry.get("dangerous") is True:
        max_possible += CONFIRMATORY_WEIGHT * TOTAL_SEVERITY_SIGNAL_CATEGORIES
        for signal in systemic_severity_signals(state):
            supporting.append(signal)
            score += CONFIRMATORY_WEIGHT

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


def _ensure_cross_cutting_dangerous_diagnoses(candidates: list) -> list:
    """Can't-miss diagnoses (spec section 4/6: unknown-routing safety net) must always compete in
    scoring, not only when routing produced no pool at all. A confident tag match narrows the pool
    by presenting symptom -- but symptom-based routing is exactly the mechanism that fails for an
    ATYPICAL presentation of a dangerous diagnosis (e.g. hypoglycemia presenting as palpitations
    and jitteriness routes cleanly to a cardiac-tag pool that has no symptom-level reason to
    include hypoglycemia at all). Riding a small, fixed list of dangerous diagnoses along with
    every routed pool -- not just the empty-pool fallback -- means their own scoring (risk factors,
    labs, exam findings gathered later in the case) still gets a chance to surface them, without
    ever letting them replace or narrow whatever routing already found."""
    present_ids = {entry["id"] for entry in candidates}
    extended = list(candidates)
    for diagnosis_id in CROSS_CUTTING_DANGEROUS_DIAGNOSES:
        if diagnosis_id not in present_ids:
            entry = disease_by_id(diagnosis_id)
            if entry is not None:
                extended.append(entry)
                present_ids.add(diagnosis_id)
    return extended


def _ensure_decisive_lab_evidence_diagnoses(candidates: list, state: PatientState) -> list:
    """Chief-complaint routing narrows the candidate pool by presenting symptom, but a decisive
    objective lab result must never be excluded just because the routed pool didn't happen to
    include the diagnosis it confirms -- objective evidence outranks a keyword/routing signal, the
    same priority order the scoring hierarchy already enforces within a pool (confirmatory finding
    > exam/lab > symptom > risk factor). Glucose is the one lab this codebase already interprets
    numerically (glucose_evidence.py, standard ADA thresholds, not fitted to any specific case) --
    when it has actually been drawn and crosses a diagnostic threshold, the diagnosis it confirms
    must be reachable by scoring even if chief-complaint routing pointed elsewhere (e.g. atypical
    hypoglycemia presenting as palpitations/jitteriness routes to a cardiac-tag pool that has no
    reason to include hypoglycemia by symptom text alone -- the lab result is the reason)."""
    glucose = extract_glucose_mg_dl(state.laboratory_tests.get("glucose_point_of_care"))
    if glucose is None:
        return candidates
    present_ids = {entry["id"] for entry in candidates}
    forced_ids = []
    if glucose < HYPOGLYCEMIA_THRESHOLD_MG_DL and "hypoglycemia" not in present_ids:
        forced_ids.append("hypoglycemia")
    if glucose >= DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL and "diabetic_ketoacidosis" not in present_ids:
        forced_ids.append("diabetic_ketoacidosis")
    if not forced_ids:
        return candidates
    extended = list(candidates)
    for diagnosis_id in forced_ids:
        entry = disease_by_id(diagnosis_id)
        if entry is not None:
            extended.append(entry)
    return extended


class DifferentialEngine:
    """Stateless ranker: call `update(state)` every turn; it recomputes from scratch off the
    current PatientState rather than incrementally patching the previous ranking, so a
    contradicted early guess is never "sticky"."""

    def update(self, state: PatientState) -> List[DifferentialItem]:
        tag = classify_chief_complaint(state.chief_complaint)
        candidates = diseases_for_tag(tag)
        if not candidates:
            # No disease is directly tagged for this presentation -- try clinically related tags
            # first (spec section 8/24H) so the candidate pool stays targeted instead of jumping
            # straight to the untargeted whole catalog (e.g. "syncope" pulls the dizziness and
            # chest_pain pools, not all 29+ diseases regardless of relevance).
            seen_ids = set()
            merged = []
            for related in related_tags(tag):
                for entry in diseases_for_tag(related):
                    if entry["id"] not in seen_ids:
                        merged.append(entry)
                        seen_ids.add(entry["id"])
            candidates = merged
        if not candidates:
            # Still nothing via the single best tag -- before falling all the way back to the
            # untargeted whole catalog, try SOFT routing (spec: prefer an imprecise-but-plausible
            # 2-3-category pool over either a single wrong hard routing or a same-weight dump of
            # every diagnosis regardless of relevance). top_candidates() ranks tags by a fuzzy
            # word-overlap score even when no exact keyword/alias matched at all, so genuinely
            # ambiguous lay-language chief complaints usually produce SOME plausible candidates
            # here, not just an empty list.
            seen_ids = set()
            merged = []
            for candidate_tag in top_candidates(state.chief_complaint, k=3):
                for entry in diseases_for_tag(candidate_tag):
                    if entry["id"] not in seen_ids:
                        merged.append(entry)
                        seen_ids.add(entry["id"])
            candidates = merged
        if not candidates:
            # Genuinely no signal at all (soft routing found nothing either) -- fall back to the
            # whole knowledge base rather than returning an empty differential (spec: the agent
            # must always reason toward a diagnosis, never stall for lack of a tag match). The LLM
            # reasoning layer can also introduce a diagnosis outside this pool entirely (spec
            # section 7/24 -- see safety_validator.merge_differential).
            candidates = list(all_diseases().values())

        candidates = _ensure_cross_cutting_dangerous_diagnoses(candidates)
        candidates = _ensure_decisive_lab_evidence_diagnoses(candidates, state)

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
            ))

        state.current_differential = [
            DifferentialSnapshot(diagnosis=i.diagnosis, rank=i.rank, confidence_band=i.confidence_band,
                                  urgency=i.urgency, dangerous_if_missed=i.dangerous_if_missed)
            for i in items
        ]
        return items
