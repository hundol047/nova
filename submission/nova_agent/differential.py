"""Differential Diagnosis Engine (spec section 4).

Ranks candidate diagnoses from the local knowledge base against everything currently known about
the patient. Confidence is reported as a LOW/MEDIUM/HIGH calibration band (how much of a disease's
known evidence profile has actually been confirmed so far) alongside an internal 0..1 ranking
score -- the band is never presented as if it were a calibrated probability.

Re-run every turn (never "first differential only") so newly observed findings immediately
reshuffle the ranking.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional
import re

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
from nova_agent.objective_evidence import CONFIRMATORY_PHRASE_TO_LAB, ObjectiveFinding, normalize_objective_evidence
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
    # Generic multilingual equivalents for high-value neurologic/infectious signs. These are
    # feature-local aliases: they help only the canonical feature named on the left and never act
    # as a global synonym table across unrelated diagnoses.
    "fever": ["high fever", "高熱", "発熱", "熱がある", "열이 나다", "고열"],
    "neck stiffness": ["stiff neck", "首が硬い", "首が硬く", "首がこわばる", "首が動かしにくい", "項部硬直", "경부강직"],
    "headache": ["激しい頭痛", "頭痛", "頭が痛い", "열과 두통"],
    "slurred speech": ["言葉が出にくい", "言葉が出にく", "言葉がうまく出ない", "word-finding difficulty", "difficulty finding words", "ろれつが回らない"],
    "vaginal bleeding": ["vaginal spotting", "spotting", "light spotting", "膣出血", "膣から出血"],
    "missed period": ["period is late", "late period", "missed period", "生理が遅れている", "月経が遅い"],
    "unilateral pelvic pain": ["one-sided pelvic pain", "sharp pain on one side of the pelvis",
                               "한쪽 골반 통증", "片側の骨盤痛"],
    # AHA: acute aortic pain may be described in chest, back or abdomen.
    "tearing chest pain": ["tearing back pain", "tearing breastbone pain",
                            "tearing abdominal pain"],
    # NIDDK GI bleeding symptoms. These are symptom support, not confirmation.
    "melena": ["black tarry stool", "black and tarry stool",
               "black tarry stools", "black and tarry stools", "黒い便", "黒色便", "黒くてタール状の便",
               "タール便", "タール状便", "便が黒い", "검은 변", "흑변", "黑色便", "黑便"],
    "hematemesis": ["vomiting blood", "vomited blood", "吐血", "血を吐く", "토혈", "피를 토함", "呕血",
                     "呕出鲜红色血液", "吐出鲜血", "呕吐鲜血"],
    "liver disease": ["cirrhosis", "肝硬化", "간경변"],
    "alcohol use": ["长期饮酒", "长期喝酒", "heavy drinking", "chronic alcohol use"],
    "appendiceal inflammation": ["inflamed appendix", "appendiceal wall thickening",
                                  "thickened appendix", "noncompressible appendix"],
    "unilateral pulsating headache": ["throbbing headache", "pounding headache", "one-sided headache",
                                       "one sided headache", "pounding pain", "throbbing pain",
                                       "pulsating pain"],
    "photophobia": ["sensitive to light", "light sensitivity", "light bothers me", "光がまぶしい", "光がつらい"],
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
    "throat tightness": ["throat feels like it is closing", "throat feels like it's closing",
                         "throat closing", "throat swelling", "喉が締め付けられる", "喉が詰まる",
                         "목이 조이는 느낌", "목이 붓는 느낌", "喉咙发紧"],
    "recent allergen exposure": ["after eating", "after taking a new medication", "after a new drug",
                                 "after an antibiotic", "new medication", "new antibiotic",
                                 "食後", "新しい薬の後", "薬を飲んだ後", "새 약을 먹은 후"],
    "sudden onset urticaria": ["hives", "widespread hives", "urticaria", "じんましん", "蕁麻疹",
                               "두드러기", "荨麻疹"],
    "bilateral band-like pressure": ["bilateral pressure", "pressure on both sides", "tight band around my head",
                                     "양쪽 머리를 누르는 느낌", "両側の圧迫感"],
    "lightheadedness on standing up": ["dizzy when standing", "lightheaded when I stand", "어지러울 때 일어남",
                                       "立ち上がるとふらつく"],
    "sudden onset palpitations": ["sudden heart racing", "sudden fluttering", "갑자기 심장이 두근",
                                  "突然の動悸"],
    "periumbilical pain migrating to right lower quadrant": [
        "pain moved from the belly button to the right lower abdomen",
        "pain started around the navel and moved right", "배꼽에서 오른쪽 아랫배로 통증이 이동",
        "へそから右下腹部へ痛みが移る"],
    "epigastric pain radiating to back": ["upper abdominal pain going to the back", "upper belly pain to the back",
                                          "명치 통증이 등으로 뻗음", "上腹部痛が背中に放散"],
    "unilateral absent breath sounds": ["one-sided absent breath sounds", "breath sounds absent on one side",
                                        "片側の呼吸音が聞こえない"],
    "tracheal deviation": ["windpipe shifted", "trachea shifted", "기관이 한쪽으로 밀림", "気管偏位"],
    "sudden onset focal weakness": [
        "sudden arm weakness", "arm weakness", "right arm weakness", "left arm weakness",
        "right arm drift", "left arm drift", "突然腕に力が入らない", "急に腕が動かしにくい",
        "右腕 weakness", "左腕 weakness", "片側 weakness"],
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


def _present_with_aliases(phrase: str, findings: List[str], strict: bool = False) -> bool:
    """feature_present() on `phrase` itself, OR on any of its feature-local aliases (see
    FEATURE_ALIASES above) -- the alias never widens matching for any OTHER knowledge-base phrase."""
    if feature_present(phrase, findings, scrub_negated_spans=True, strict=strict):
        return True
    for alias in FEATURE_ALIASES.get(phrase.lower(), ()):
        # Require every alias content word: 'black stool' alone is not 'black tarry stool'.
        if feature_present(alias, findings, scrub_negated_spans=True, strict=True):
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
    return any(feature_present(phrase, current, scrub_negated_spans=True, strict=True)
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
    abnormal = {"high": ("high", "critical_high"), "low": ("low", "critical_low")}[direction]
    opposite = {"high": ("low", "critical_low"), "low": ("high", "critical_high")}[direction]
    if finding.interpretation in abnormal:
        supporting.append(phrase)
        return weight
    if finding.interpretation in opposite:
        contradictory.append(phrase)
        return -CONTRADICTION_PENALTY
    missing.append(phrase)
    return 0.0


def _score_phrase(phrase: str, weight: float, findings: List[str], negatives: List[str],
                   supporting: List[str], contradictory: List[str], missing: List[str], strict: bool = False) -> float:
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
    if _present_with_aliases(phrase, findings, strict=strict):
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

    # A past/family report is risk context, not a current objective test result.
    objective_text = list(state.physical_examinations.values()) + list(state.imaging.values()) + list(state.laboratory_tests.values())
    seen_lab_evidence = set()
    for finding in entry.get("confirmatory_findings", []):
        lab_key = CONFIRMATORY_PHRASE_TO_LAB.get(finding.lower())
        if lab_key is not None:
            if lab_key in seen_lab_evidence:
                continue
            seen_lab_evidence.add(lab_key)
        max_possible += CONFIRMATORY_WEIGHT
        lab_aware_delta = _score_lab_aware_phrase(finding, CONFIRMATORY_WEIGHT, objective_findings,
                                                   supporting, contradictory, missing)
        if lab_aware_delta is not None:
            score += lab_aware_delta
        else:
            score += _score_phrase(finding, CONFIRMATORY_WEIGHT, objective_text, negatives, supporting, contradictory, missing, strict=True)

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
        )
        candidates = [c.entry for c in candidate_records]
        sources_by_id = {c.id: c.sources for c in candidate_records}

        scored = []
        for entry in candidates:
            score, max_possible, supporting, contradictory, missing = _score_disease(entry, state, objective_findings)
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
