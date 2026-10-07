"""Differential Diagnosis Engine (spec section 4).

Ranks candidate diagnoses from the local knowledge base against everything currently known about
the patient. Confidence is reported as a LOW/MEDIUM/HIGH calibration band (how much of a disease's
known evidence profile has actually been confirmed so far) alongside an internal 0..1 ranking
score -- the band is never presented as if it were a calibrated probability.

Re-run every turn (never "first differential only") so newly observed findings immediately
reshuffle the ranking.
"""

from __future__ import annotations

import math
import re

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

from nova_agent.candidate_generator import generate_candidates
from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.config import get_config
from nova_agent.glucose_evidence import (
    DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL,
    HYPOGLYCEMIA_THRESHOLD_MG_DL,
    extract_glucose_mg_dl,
)
from nova_agent.matching import (
    FEATURE_ALIASES,
    content_word_count,
    content_words,
    feature_denied,
    explicitly_denied_in_findings,
    feature_present,
    feature_present_with_aliases,
)
from nova_agent.objective_evidence import (
    CONFIRMATORY_PHRASE_TO_LAB,
    NONSPECIFIC_INFLAMMATORY_LAB_IDS,
    ObjectiveFinding,
    _current_result_texts,
    normalize_objective_evidence,
)
from nova_agent.severity_evidence import (
    ELEVATED_LACTATE_MMOL_L,
    GENERIC_PHYSIOLOGIC_SEVERITY_WORDS,
    extract_lactate_mmol_l,
)
from nova_agent.state import DifferentialSnapshot, PatientState

ConfidenceBand = Literal["LOW", "MEDIUM", "HIGH"]

FEATURE_WEIGHT = 1.0
RISK_FACTOR_WEIGHT = 0.4
CONTRADICTION_PENALTY = 1.2
# Objective exam/imaging/lab findings that confirm a diagnosis (knowledge/diseases/*.json's
# `confirmatory_findings`) are weighted higher than a soft symptom feature -- clinically, "ST
# elevation on ECG" should move the ranking far more than "chest pain worse with exertion" does.
CONFIRMATORY_WEIGHT = 2.5
# Soft ceiling on how much cumulative credit stacked typical_feature matches alone can contribute
# to one diagnosis's score (see _score_disease's typical_features loop) -- exactly one confirmatory
# finding's worth. Generous enough to never change a diagnosis with a genuinely small, focused
# typical_features list (most of this KB, where the uncapped sum rarely approaches this anyway),
# but guaranteeing that no amount of stacked, individually-weak generic symptom-word matches for
# one diagnosis can outscore a single decisive confirmatory/objective finding for a competing,
# more dangerous candidate (spec: converging evidence must not let simple keyword counting
# overpower one decisive finding).
_TYPICAL_FEATURE_CONTRIBUTION_CAP = CONFIRMATORY_WEIGHT
_TYPICAL_FEATURE_KNEE = _TYPICAL_FEATURE_CONTRIBUTION_CAP - 0.5


def _soft_saturate(total: float) -> float:
    """Identity up to the knee; beyond it an exponential approach to _TYPICAL_FEATURE_CONTRIBUTION_CAP
    (strictly increasing, never above the cap)."""
    if total <= _TYPICAL_FEATURE_KNEE:
        return total
    headroom = _TYPICAL_FEATURE_CONTRIBUTION_CAP - _TYPICAL_FEATURE_KNEE
    return _TYPICAL_FEATURE_KNEE + headroom * (1.0 - math.exp(-(total - _TYPICAL_FEATURE_KNEE) / headroom))

_NEGATIVE_FEATURE_PREFIXES = ("no ", "denies ", "without ", "absent ")

# FEATURE_ALIASES / feature_present_with_aliases now live in matching.py, shared with
# candidate_generator.py's risk_match/medication_match/history_match (pool-membership) checks --
# see that module's own docstring for why the two call sites must never diverge. `_present_with_aliases`
# stays as a thin local name for this module's own call sites below, unchanged otherwise.
_present_with_aliases = feature_present_with_aliases


_SPECIFICITY_STEP = 0.25
_SPECIFICITY_CAP = 2.0
# Round E (defect C): a typical_feature phrase that reduces to NOTHING but generic physiologic-
# severity markers (hypotension, tachycardia, tachypnea, fever, ...) is real but weak, non-
# decisive corroborating signal -- never full disease-identifying weight. Deliberately > 0 (spec:
# generic severity may still keep a dangerous alternative active / raise urgency, it must simply
# never by itself let one dangerous diagnosis outrank another that has genuinely disease-specific
# support) and deliberately << 1.0 so a disease relying ONLY on stacked generic-severity matches
# can never outscore a competitor with real disease-specific findings.
_GENERIC_SEVERITY_MULTIPLIER = 0.3


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
    previously-flat case).

    EXCEPT: a phrase whose content words are ENTIRELY generic physiologic-severity markers (e.g.
    sepsis's own bare "hypotension"/"tachycardia"/"tachypnea" typical_features) gets the separate,
    much smaller `_GENERIC_SEVERITY_MULTIPLIER` instead -- these words mark a PATIENT as sick, not
    WHICH disease is present (severity_evidence.py's own module docstring already establishes this
    for severity_score() itself; this closes the same gap for plain typical_features word-overlap
    matching, which could otherwise let several diseases' shared generic vital-sign wording alone
    decide the ranking -- see tests/test_severity_not_diagnostic_identity.py)."""
    content = content_words(phrase)
    if content and content.issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS):
        return _GENERIC_SEVERITY_MULTIPLIER
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
    # True only when this diagnosis (and, in practice, every other diagnosis in the same
    # differential -- see DifferentialEngine.update()) is present SOLELY via
    # candidate_generator.py's "zero_evidence_fallback" source: literally nothing (no symptom
    # concept, risk factor, medication, history match, imaging, or objective lab) matched anything
    # at all this turn. Always carries score==0.0/score_ratio==0.0/supporting_evidence==[] (there
    # is no evidence to report -- "evidence_score=0, diagnostic_support=none" per spec) and
    # confidence_band=="LOW". stop_policy.py and action_selector.py both check this flag to refuse
    # a confident DIAGNOSE on an unmatched presentation and prefer clarifying ASK/EXAM over TEST --
    # never let stable-sort/dict-insertion order (ultimately disease KB file load order) silently
    # pick an arbitrary "winning" diagnosis out of an undifferentiated tie.
    fallback_candidate: bool = False
    evidence_status: Dict[str, str] = {}



_ESCALATION_MIN_SUPPORT = 3
# Only SYSTEMIC organ-dysfunction findings escalate: a local exam sign that is a red flag for its own organ
# (rebound/guarding in appendicitis) still describes the same local disease, not a different systemic one.
_ORGAN_DYSFUNCTION_FLAGS = frozenset({"hypotension", "shock", "hypoxia", "hypoxemia", "confusion",
                                      "altered mental status"})


def _apply_red_flag_escalation(kept: list, state: PatientState) -> list:
    """Round O: a localized diagnosis's own knowledge-base ``red_flag_keywords`` name the findings that mean it
    has escalated (pyelonephritis/pneumonia: "hypotension", "confusion"). When such a finding is present AND is
    actively supporting a DANGEROUS diagnosis that lists it as a typical feature (sepsis) -- and it is a systemic
    organ-dysfunction finding (hypotension, hypoxia, confusion), not a local sign -- the dangerous systemic
    diagnosis is moved directly above the localized one: the local source then explains WHERE, not WHAT is
    threatening the patient. Purely a re-ordering among already-scored candidates; requires converging support
    (>= 3 matched items) and no contradiction for the dangerous diagnosis, and only fires on findings both
    entries name, so a stable local infection (no red flag present) is never displaced."""
    if len(kept) < 2:
        return kept
    order = list(kept)
    changed = True
    guard = 0
    while changed and guard < len(order):
        changed = False
        guard += 1
        for i, upper in enumerate(order):
            up_entry = upper[2]
            if up_entry.get("dangerous"):
                continue
            flags = {f.lower() for f in up_entry.get("red_flag_keywords", [])}
            if not flags:
                continue
            for j in range(i + 1, len(order)):
                lower = order[j]
                low_entry, low_support, low_contra = lower[2], lower[3], lower[4]
                if not low_entry.get("dangerous") or low_contra or len(low_support) < _ESCALATION_MIN_SUPPORT:
                    continue
                typical = {f.lower() for f in low_entry.get("typical_features", [])}
                shared = {p.lower() for p in low_support} & flags & typical & _ORGAN_DYSFUNCTION_FLAGS
                if shared:
                    order.insert(i, order.pop(j))
                    changed = True
                    break
            if changed:
                break
    return order


def has_positive_diagnostic_support(item: DifferentialItem) -> bool:
    """Risk factors and absent symptoms can adjust a differential, not establish it alone."""
    from nova_agent.knowledge.retrieval import disease_by_id
    entry = disease_by_id(item.diagnosis_id) or {}
    risk_only = {str(x).lower() for x in entry.get("risk_factors", [])}
    return any(e.lower() not in risk_only and _strip_negative_prefix(e) is None
               for e in item.supporting_evidence)


def has_required_diagnostic_context(item: DifferentialItem, state: PatientState) -> bool:
    """A final label may require localizing context beyond generic systemic symptoms.

    This is an abstention guard, not an exclusion rule or a diagnostic criterion.
    Candidates remain available for workup. Read actual current observations, not
    the LLM's claimed supporting evidence or past/family history.
    """
    from nova_agent.knowledge.retrieval import disease_by_id
    entry = disease_by_id(item.diagnosis_id) or {}
    required = entry.get("required_diagnostic_context_any", [])
    if not required:
        return True
    current = [state.chief_complaint, *state.symptoms, *state.associated_symptoms,
               *state.pertinent_positives, *state.physical_examinations.values(),
               *state.imaging.values(), *state.laboratory_tests.values()]
    current = [clause for text in current for clause in re.split(r"[;,\n]", text)
               if not re.search(r"\b(?:previously|historical|baseline|history of|last (?:year|month|week)|"
                                r"prior result|old result|reference range)\b", clause, re.I)]
    from nova_agent.state import _with_canonical_concepts
    current = _with_canonical_concepts(current)  # "nuchal rigidity" is current neck stiffness (negation/history-aware)
    return any(_present_with_aliases(phrase, current, strict=True)
               for phrase in required)


def _score_lab_aware_phrase(phrase: str, weight: float, objective_findings: Dict[str, ObjectiveFinding],
                             supporting: List[str], contradictory: List[str],
                             missing: List[str]) -> Optional[float]:
    """If `phrase` is one of the confirmatory-finding phrases objective_evidence.py knows maps to
    a specific lab (see CONFIRMATORY_PHRASE_TO_LAB), scores it from that lab's actual numeric/
    qualitative INTERPRETATION rather than plain word-overlap against the finding text -- so a raw
    "potassium 6.9 mEq/L" result correctly supports "hyperkalemia" even though the finding text
    never contains the word "hyperkalemia"/"elevated" itself (the same class of gap
    glucose_evidence.py/severity_evidence.py's lactate handling already closed for those two
    labs). Returns None (never 0.0) when `phrase` has no lab mapping at all, so the caller falls
    back to the plain word-overlap `_score_phrase()` path unchanged for every other phrase."""
    mapping = CONFIRMATORY_PHRASE_TO_LAB.get(phrase.lower())
    if mapping is None:
        return None
    lab_id, direction = mapping
    finding = objective_findings.get(lab_id)
    if finding is None or finding.interpretation == "unknown":
        missing.append(phrase)
        return 0.0
    if lab_id in NONSPECIFIC_INFLAMMATORY_LAB_IDS:
        weight = min(weight, FEATURE_WEIGHT)
    abnormal = {"high": ("high", "critical_high"), "low": ("low", "critical_low")}[direction]
    opposite = {"high": ("low", "critical_low"), "low": ("high", "critical_high")}[direction]
    if finding.interpretation in abnormal:
        supporting.append(phrase)
        return weight
    if finding.interpretation in opposite:
        contradictory.append(phrase)
        return -CONTRADICTION_PENALTY
    if finding.interpretation == "normal" and lab_id in RULE_OUT_WHEN_NORMAL and _evidence_v2_enabled():
        # A performed, readable NEGATIVE result for a test whose positivity is a prerequisite of the diagnosis
        # (no pregnancy -> no ectopic pregnancy) is evidence against it -- not merely "missing". Ordering a test
        # never counts; only a recorded result does. Deliberately NOT applied to troponin/D-dimer etc., where a
        # single normal value does not exclude the disease.
        contradictory.append(phrase)
        return -CONTRADICTION_PENALTY
    missing.append(phrase)
    return 0.0


# Labs whose NORMAL result excludes the diagnosis that requires them to be positive.
RULE_OUT_WHEN_NORMAL = frozenset({"lab.beta_hcg"})


def _evidence_v2_enabled() -> bool:
    from nova_agent.config import get_config
    return get_config().evidence_v2_enabled


# A confirmatory phrase such as "atrial fibrillation on ecg" names the test the result came from. The objective
# pool only ever holds EXAM/TEST/imaging results, and an ECG report reads "atrial fibrillation with fast rate"
# without repeating "ecg", so modality words must not be required for the strict match.
_MODALITY_WORDS = frozenset({"ecg", "ekg", "ct", "mri", "cxr", "imaging", "xray", "ultrasound", "echo", "echocardiogram", "radiograph", "scan"})
_INFERENCE_FEATURE = re.compile(r"^(?:suspected|presumed|possible)\b", re.IGNORECASE)


def _score_phrase(phrase: str, weight: float, findings: List[str], negatives: List[str],
                   supporting: List[str], contradictory: List[str], missing: List[str], *, objective: bool = False,
                   strict: bool = False) -> float:
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
        if feature_present(underlying, negatives) or explicitly_denied_in_findings(underlying, findings):
            supporting.append(phrase)
            return weight
        if feature_present(underlying, findings, scrub_negated_spans=True):
            contradictory.append(phrase)
            return -CONTRADICTION_PENALTY
        missing.append(phrase)
        return 0.0
    if _INFERENCE_FEATURE.match(phrase) and not objective:
        # "suspected infection source" is a clinician's inference over MANY possible sources, not a
        # symptom. Denying one source symptom ("denies cough, denies burning with urination") does not
        # refute it -- an occult source is exactly how sepsis in an immunocompromised patient presents --
        # so it can be supported or missing, never contradicted by individual symptom denials.
        if _present_with_aliases(phrase, findings):
            supporting.append(phrase)
            return weight
        missing.append(phrase)
        return 0.0
    if feature_denied(phrase, negatives) or explicitly_denied_in_findings(phrase, findings):
        contradictory.append(phrase)
        return -(CONFIRMATORY_WEIGHT if objective else CONTRADICTION_PENALTY)
    if _present_with_aliases(phrase, findings, strict=strict, ignore_words=_MODALITY_WORDS if objective else frozenset()):
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


def _score_disease(entry: dict, state: PatientState,
                    objective_findings: Optional[Dict[str, ObjectiveFinding]] = None) -> tuple[float, float, List[str], List[str], List[str]]:
    if objective_findings is None:
        objective_findings = normalize_objective_evidence(state)
    findings = state.all_findings_text()
    confirmatory_evidence_pool = state.objective_findings_text()
    negatives = state.pertinent_negatives

    supporting: List[str] = []
    contradictory: List[str] = []
    missing: List[str] = []
    score = 0.0
    max_possible = 0.0

    # Diminishing returns on stacked generic typical_feature matches (spec: converging evidence
    # must be handled without letting simple keyword counting -- many independently-matched but
    # individually low-value symptom words -- mathematically outweigh a single decisive
    # confirmatory/objective finding for a DIFFERENT, more dangerous candidate). Only the total
    # POSITIVE contribution from this one evidence class is capped, at a small multiple of a single
    # confirmatory finding's own weight; a genuine contradiction still applies its full penalty
    # uncapped (this must never soften real evidence AGAINST a diagnosis), and every matched/missing
    # phrase is still recorded in full for supporting_evidence/missing_discriminative_evidence --
    # only the numeric ranking contribution saturates, clinician-facing evidence text does not.
    typical_feature_score = 0.0
    typical_penalty = 0.0
    for feature in entry.get("typical_features", []):
        weight = FEATURE_WEIGHT * _specificity_multiplier(feature)
        max_possible += weight
        delta = _score_phrase(feature, weight, findings, negatives, supporting, contradictory, missing)
        typical_feature_score += max(delta, 0.0)
        typical_penalty += min(delta, 0.0)
    # Soft saturation instead of a flat cap (Round M): with a hard min(), a candidate matching six
    # typical features and one matching two both sat at exactly the cap and TIED, so rank order fell
    # back to pool insertion order. Evidence up to the knee counts in full; beyond it the
    # contribution rises strictly monotonically but asymptotes to the cap, so more converging
    # evidence still orders above less while stacked weak clues can never reach (let alone exceed)
    # one confirmatory finding's worth.
    score += _soft_saturate(typical_feature_score) + typical_penalty

    for risk_factor in entry.get("risk_factors", []):
        max_possible += RISK_FACTOR_WEIGHT
        if _present_with_aliases(risk_factor, findings):
            supporting.append(risk_factor)
            score += RISK_FACTOR_WEIGHT

    # A past/family report is risk context, not a current objective test result; an explicitly
    # historical or hypothetical report is not a current observation either.
    objective_text = _current_result_texts(list(confirmatory_evidence_pool))
    counted_labs = set()
    for finding in entry.get("confirmatory_findings", []):
        # Several knowledge-base phrasings can name the SAME lab reading ("elevated troponin" /
        # "troponin elevated", "positive nitrites" / "positive leukocyte esterase" / "pyuria"); one
        # result is one piece of evidence and is credited once (Round M: ACS scored 5.0 from a single
        # troponin by matching both phrasings).
        lab_key = CONFIRMATORY_PHRASE_TO_LAB.get(finding.lower())
        if lab_key is not None:
            if lab_key in counted_labs:
                continue
            counted_labs.add(lab_key)
        max_possible += CONFIRMATORY_WEIGHT
        lab_aware_delta = _score_lab_aware_phrase(finding, CONFIRMATORY_WEIGHT, objective_findings,
                                                   supporting, contradictory, missing)
        if lab_aware_delta is not None:
            score += lab_aware_delta
        else:
            # Scored against confirmatory_evidence_pool (EXAM/TEST/imaging results only), never the
            # full `findings` bag -- a confirmatory_findings phrase represents a specific objective
            # test/exam result (see PatientState.objective_findings_text()'s docstring for the real
            # false-positive this closes: a merely-reported PAST diagnosis must never satisfy a
            # confirmatory finding that requires an actual current test/exam to have been performed).
            score += _score_phrase(finding, CONFIRMATORY_WEIGHT, objective_text, negatives,
                                    supporting, contradictory, missing, objective=True, strict=True)

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
        negative_target = _strip_negative_prefix(reassuring)
        # A multi-word objective reassurance ("normal neurologic exam") must match as a complete assertion
        # in what an EXAM/TEST actually produced -- never in a family/past-history statement ("Parent had a
        # normal neurologic exam"), and never by partial word overlap ("new focal deficit" is not the
        # opposite of "no focal neurological deficit").
        matched = (explicitly_denied_in_findings(negative_target, findings) if negative_target
                   else feature_present(reassuring, state.objective_findings_text(), scrub_negated_spans=True, strict=True))
        if matched:
            contradictory.append(reassuring)
            score -= CONTRADICTION_PENALTY

    return score, max(max_possible, 1.0), supporting, contradictory, missing


def _evidence_status(entry, state, supporting, contradictory, missing):
    """Observed states, not a diagnostic probability or an inferred negative test result."""
    objective = state.objective_findings_text()
    asked = any(state.question_asked(q) for q in entry.get("discriminating_questions", []))
    tests_done = bool(set(entry.get("discriminating_tests", [])) & set(state.completed_tests)
                      or set(entry.get("discriminating_exams", [])) & set(state.completed_examinations))
    states = {p: "PRESENT" for p in supporting}
    for p in contradictory:
        states[p] = "OBJECTIVELY_CONTRADICTED" if explicitly_denied_in_findings(p, objective) else "ABSENT"
    for p in missing:
        observed = tests_done if p in entry.get("confirmatory_findings", []) else asked
        states[p] = "UNKNOWN" if observed else "NOT_ASKED"
    return states


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
        objective_findings = normalize_objective_evidence(state)
        _cfg = get_config()
        candidate_records = generate_candidates(
            presentation,
            glucose_result_text=state.laboratory_tests.get("glucose_point_of_care"),
            lactate_result_text=state.laboratory_tests.get("lactate"),
            objective_findings=objective_findings,
            imaging_text=list(state.imaging.values()),
            ontology_broadening=_cfg.ontology_broadening_enabled,
            ontology_broadening_max=_cfg.ontology_broadening_max,
            competition_retrieval=_cfg.competition_retrieval_enabled,
            retrieval_top_k=_cfg.retrieval_top_k,
            rerank_top_k=_cfg.rerank_top_k,
            chief_complaint_text=state.chief_complaint,
            pool_target_size=_cfg.reasoning_top_k if _cfg.competition_retrieval_enabled else None,
        )
        candidates = [c.entry for c in candidate_records]
        sources_by_id = {c.id: c.sources for c in candidate_records}

        # UNKNOWN_PRESENTATION / zero-evidence detection (spec: the file-order fallback-ranking
        # bug's real fix). candidate_generator.py's whole-catalog fallback (fired only when
        # literally nothing -- no symptom concept, risk factor, medication, history, imaging, or
        # objective lab -- matched anything) tags EVERY candidate it adds with the single source
        # "zero_evidence_fallback" and returns immediately, before any other source could ever mix
        # in (see that module's own `if not pool:` branch) -- so "every candidate's sources is
        # exactly that one tag" is both necessary and sufficient to detect this state here.
        # (Retrieval-only ontology candidates may ride along; they are recall, not evidence, and any
        # that earns real scored support clears this flag below via `not any(t[3] ...)`.)
        is_zero_evidence_presentation = (
            bool(candidate_records)
            and any("zero_evidence_fallback" in c.sources for c in candidate_records)
            and all(set(c.sources) <= {"zero_evidence_fallback", "ontology_retrieval"} for c in candidate_records)
        )

        scored = []
        for entry in candidates:
            score, max_possible, supporting, contradictory, missing = _score_disease(entry, state, objective_findings)
            score_ratio = max(0.0, score) / max_possible
            band = _confidence_band(score_ratio, state.turn_count, len(supporting))
            scored.append((score, score_ratio, entry, supporting, contradictory, missing, band))

        # Pool provenance describes retrieval, not whether later scoring found evidence.
        is_zero_evidence_presentation = is_zero_evidence_presentation and not any(t[3] for t in scored)

        scored.sort(key=lambda t: t[0], reverse=True)
        # The final active-clinical-differential size: the legacy fixed 5 for any mock/legacy
        # caller (byte-identical, unchanged), or the configured reasoning_top_k (~25) once
        # competition retrieval is enabled -- see NovaConfig.effective_differential_top_k()'s
        # docstring. This is what actually reaches build_clinical_summary()'s LLM-facing text.
        top_k = get_config().effective_differential_top_k()
        kept = scored[:top_k]

        # Retention is separate from score: reinject only evidenced, unresolved dangers.
        # The fixed safety pool remains available upstream, but bare dangerous labels do not
        # receive permanent active-differential slots or a diagnostic likelihood bonus.
        by_id = {t[2]["id"]: t for t in scored}
        kept_ids = {t[2]["id"] for t in kept}
        from nova_agent.resolution import is_resolved
        must_not_miss_missing = [
            by_id[did] for did in CROSS_CUTTING_DANGEROUS_DIAGNOSES
            if did in by_id and did not in kept_ids and by_id[did][3] and not by_id[did][4]
            and not is_resolved(did, by_id[did][4], state)
        ] if _cfg.competition_retrieval_enabled else []
        if must_not_miss_missing:
            # Swap-eligible entries are restricted to ones with NO genuine supporting evidence of
            # their own (mirrors candidate_generator.py's own protected-vs-trimmable split) -- a
            # diagnosis with real matched evidence (e.g. cystitis on an otherwise bland,
            # zero-evidence presentation) must NEVER be sacrificed for this, regardless of how it
            # compares by raw score to the zero-evidence entries around it; that is exactly the
            # "permanently immortal dangerous diagnosis" failure this whole mechanism must avoid
            # (caught by tests/test_severity_evidence.py's negative controls). When no safe swap
            # target exists, this only ever APPENDS (bounded: at most the fixed list's own size),
            # never evicts real evidence.
            non_dangerous_kept = sorted(
                (t for t in kept if not t[2].get("dangerous") and not t[3]), key=lambda t: t[0]
            )
            for missing in must_not_miss_missing:
                if non_dangerous_kept:
                    weakest = non_dangerous_kept.pop(0)
                    kept.remove(weakest)
                kept.append(missing)
            kept.sort(key=lambda t: t[0], reverse=True)

        # Stage B -- the ANALOGOUS protection to
        # retrieval_pipeline.lightweight_rerank's Stage 3, one layer up: candidate_generator.py's
        # own pool-size trim already guarantees a `dangerous: true` candidate is never dropped just
        # to hit ITS size budget, but that pool can still legitimately be larger than `top_k` (many
        # protected, evidenced candidates at once, plus a bounded safety-net reinjection of its
        # own), so this score-based ranking step needs the SAME guarantee at ITS OWN size boundary
        # -- a dangerous diagnosis with REAL matched evidence of its own must never be silently
        # outranked out of the LLM-visible differential purely because more non-dangerous candidates
        # out-scored it on generic keyword volume (spec: converging moderate evidence must not let
        # a decisive/dangerous possibility disappear). Requires at least one genuine
        # supporting_evidence entry -- this is NOT the same fixed, zero-evidence safety net
        # candidate_generator.py's own pool-level protection guarantees mere POOL membership for;
        # without this check a bare safety-net placeholder with no evidence at all would evict a
        # well-evidenced benign diagnosis from the top rank on every bland/normal presentation,
        # exactly the "permanently immortal dangerous diagnosis" failure mode this must NOT cause
        # (caught by tests/test_severity_evidence.py's negative controls). Also excludes anything
        # with real CONTRADICTORY evidence against it -- a genuinely different, resolution.py-style
        # state ("actively evidenced against"), not merely "scored lower than the cutoff" -- so a
        # dangerous diagnosis still loses this protection the moment real evidence rules it out, and
        # stop_policy.py/safety_validator.py's own is_resolved()-based gates (never this ranking)
        # remain the actual authority on whether DIAGNOSE may proceed.
        kept_ids = {t[2]["id"] for t in kept}
        dangerous_missing = [
            t for t in scored[top_k:]
            if t[2].get("dangerous") and t[3] and not t[4] and t[2]["id"] not in kept_ids
            and not is_resolved(t[2]["id"], t[4], state)
        ] if _cfg.competition_retrieval_enabled else []
        if dangerous_missing:
            # Same swap-eligibility restriction as Stage A: only a ZERO-real-evidence non-dangerous
            # kept entry may be evicted, never one with genuine supporting evidence of its own, no
            # matter how much weaker than the incoming dangerous candidate it scores. This makes
            # Stage B a pure "make room among zero-evidence filler" + "grow when none exists"
            # mechanism rather than a rank-inversion one -- the deliberately more powerful,
            # score-affecting fix for "many weak matches outscoring one decisive finding" is
            # `_TYPICAL_FEATURE_CONTRIBUTION_CAP` above, not this reinjection step.
            non_dangerous_kept = sorted(
                (t for t in kept if not t[2].get("dangerous") and not t[3]), key=lambda t: t[0]
            )
            for missing in dangerous_missing:
                if non_dangerous_kept:
                    weakest = non_dangerous_kept.pop(0)
                    kept.remove(weakest)
                kept.append(missing)
            kept.sort(key=lambda t: t[0], reverse=True)

        if _cfg.escalation_priority_enabled:
            kept = _apply_red_flag_escalation(kept, state)

        items: List[DifferentialItem] = []
        for rank, (score, score_ratio, entry, supporting, contradictory, missing, band) in enumerate(kept, start=1):
            items.append(DifferentialItem(
                diagnosis=entry["name"], diagnosis_id=entry["id"], rank=rank, score=round(score, 3),
                score_ratio=round(score_ratio, 3),
                supporting_evidence=supporting, contradictory_evidence=contradictory,
                missing_discriminative_evidence=missing, urgency=entry.get("urgency", "LOW"),
                dangerous_if_missed=bool(entry.get("dangerous", False)), confidence_band=band,
                candidate_sources=sources_by_id.get(entry["id"], []),
                fallback_candidate=is_zero_evidence_presentation,
                evidence_status=_evidence_status(entry, state, supporting, contradictory, missing),
            ))

        state.current_differential = [
            DifferentialSnapshot(diagnosis=i.diagnosis, rank=i.rank, confidence_band=i.confidence_band,
                                  urgency=i.urgency, dangerous_if_missed=i.dangerous_if_missed)
            for i in items
        ]
        return items
