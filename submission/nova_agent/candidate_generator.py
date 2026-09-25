"""Dynamic candidate-diagnosis generation (spec: stop using "unmatched chief complaint -> dump all
34 diseases" as the default path). Builds a targeted, provenance-tagged candidate pool from
EVERYTHING already known about the case -- every concurrently-extracted clinical concept, risk-
factor/medication context, decisive objective lab evidence, and a small fixed safety net -- instead
of a single hard-routed tag.

Every candidate records WHY it's in the pool (`sources`), so a diagnosis introduced purely by
`risk_match` or `objective_finding` is visibly distinguishable from one reached by the presenting
symptom itself; a diagnosis can (and often does) carry multiple sources at once. `differential.py`
still owns actual scoring/ranking (diagnostic_score/severity_score/safety_priority) -- this module
only decides which diagnoses are worth scoring in the first place.

Pool sizing: target ~8-15 meaningful candidates (spec), never trimming a `dangerous: true` diagnosis
or one reached via decisive objective evidence just to hit that size -- only non-dangerous,
symptom/risk-only entries are eligible to be trimmed once the pool is genuinely oversized. The full
34-disease catalog is used only as the LAST-resort fallback, when literally nothing else matched
anything at all (mirrors the old chief_complaint-only fallback's safety property, never narrower).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES, related_tags
from nova_agent.clinical_presentation import ClinicalPresentation
from nova_agent.glucose_evidence import (
    DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL,
    HYPOGLYCEMIA_THRESHOLD_MG_DL,
    extract_glucose_mg_dl,
)
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id, diseases_for_tag
from nova_agent.matching import feature_present
from nova_agent.objective_evidence import CONFIRMATORY_PHRASE_TO_LAB, ObjectiveFinding
from nova_agent.severity_evidence import ELEVATED_LACTATE_MMOL_L, extract_lactate_mmol_l

# Reverse index: lab canonical id -> {(diagnosis_id, direction it asserts), ...}, built once from
# the same CONFIRMATORY_PHRASE_TO_LAB table differential.py's lab-aware scoring already uses, so a
# decisive abnormal lab pulls its diagnosis into the CANDIDATE POOL the same way it already gets
# credited once scored -- generalizes the glucose/lactate-only objective_finding step below to
# every lab objective_evidence.py understands (troponin -> ACS, D-dimer -> PE, potassium/sodium ->
# severe_electrolyte_disorder, WBC -> pyelonephritis/meningitis, hemoglobin -> GI bleeding, ketones
# -> DKA, beta-hCG -> ectopic pregnancy, ...) without hand-listing each pair twice.
def _build_lab_to_diagnoses_index() -> dict:
    index: dict = {}
    for entry in all_diseases().values():
        for phrase in entry.get("confirmatory_findings", []):
            mapping = CONFIRMATORY_PHRASE_TO_LAB.get(phrase.lower())
            if mapping is not None:
                lab_id, direction = mapping
                index.setdefault(lab_id, set()).add((entry["id"], direction))
    return index


_LAB_TO_DIAGNOSES = _build_lab_to_diagnoses_index()

CandidateSource = Literal["symptom_match", "risk_match", "medication_match", "history_match",
                           "imaging_match", "objective_finding", "safety_candidate"]

# ~8-15 meaningful candidates, per spec -- a target, not a hard cap: dangerous/objective-evidence
# entries are always kept regardless of this number.
TARGET_POOL_SIZE = 12


@dataclass
class CandidateDiagnosis:
    entry: dict
    sources: List[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.entry["id"]


def _add(pool: dict, entry: dict, source: CandidateSource) -> None:
    existing = pool.get(entry["id"])
    if existing is None:
        pool[entry["id"]] = CandidateDiagnosis(entry=entry, sources=[source])
    elif source not in existing.sources:
        existing.sources.append(source)


def generate_candidates(presentation: ClinicalPresentation,
                         glucose_result_text: Optional[str] = None,
                         lactate_result_text: Optional[str] = None,
                         objective_findings: Optional[Dict[str, ObjectiveFinding]] = None,
                         imaging_text: Optional[List[str]] = None) -> List[CandidateDiagnosis]:
    """Builds the candidate pool for one turn. `glucose_result_text`/`lactate_result_text`/
    `objective_findings`/`imaging_text` are passed explicitly (not a whole PatientState) to keep
    this module's dependency surface small and directly testable. `objective_findings` is the
    canonical-id-keyed dict objective_evidence.normalize_objective_evidence() returns (callers
    already compute it once per turn for differential.py's own scoring, so it's passed through
    rather than re-derived here) -- None (the default) simply skips the generalized-lab pool step
    below, leaving the glucose/lactate-only behavior unchanged for any caller that doesn't pass it.
    `imaging_text` is `state.imaging.values()` -- also None-safe/optional for the same reason."""
    pool: dict = {}

    # 1. symptom_match -- every concurrently-extracted concept's own disease pool (spec: multiple
    #    concepts at once, e.g. aphasia AND focal_weakness, not a single hard-routed tag). A
    #    concept's clinically-related tags are pulled in ONLY as a fallback when that concept has
    #    no directly-tagged disease of its own at all -- unconditionally pulling in every related
    #    tag's full pool for every matched concept was tried and reverted: it inflated the raw pool
    #    enough that a directly, strongly matched diagnosis (e.g. pyelonephritis, tagged under
    #    all three of urinary_symptoms/fever/back_pain) could lose a size-trimming tie-break
    #    against zero-evidence safety-net entries, which is exactly backwards.
    for tag in presentation.symptoms:
        direct = diseases_for_tag(tag)
        for entry in direct:
            _add(pool, entry, "symptom_match")
        if not direct:
            for related in related_tags(tag):
                for entry in diseases_for_tag(related):
                    _add(pool, entry, "symptom_match")

    # 2. risk_match -- a disease's own risk_factors matching the patient's PMH/social-history text
    #    pulls it in even without a symptom-concept hit (e.g. a smoking history keeps COPD
    #    reachable for an atypical, non-classic presentation).
    if presentation.risk_factors:
        for entry in all_diseases().values():
            if entry["id"] in pool:
                continue
            for risk_factor in entry.get("risk_factors", []):
                if feature_present(risk_factor, presentation.risk_factors, scrub_negated_spans=True):
                    _add(pool, entry, "risk_match")
                    break

    # 2b. medication_match -- the SAME mechanism as risk_match, but scanning the patient's
    #     medication context specifically, and SEPARATELY tagged (spec: a diagnosis introduced
    #     purely by medication context should be visibly distinguishable from one introduced by
    #     other PMH/social risk factors) -- e.g. known insulin/sulfonylurea use keeps
    #     hypoglycemia/DKA reachable purely from the medication list, independent of PMH wording.
    #     No `entry["id"] in pool` skip here (unlike risk_match above): a candidate already in the
    #     pool via symptom_match/risk_match still gains this tag when it also applies, so
    #     converging evidence from multiple independent sources stays visible in candidate_sources
    #     rather than being hidden by whichever source happened to add the entry first.
    if presentation.medication_context:
        for entry in all_diseases().values():
            for risk_factor in entry.get("risk_factors", []):
                if feature_present(risk_factor, presentation.medication_context, scrub_negated_spans=True):
                    _add(pool, entry, "medication_match")
                    break

    # 2c. history_match -- distinct from risk_match: risk_match matches a disease's own generic
    #     `risk_factors` phrases (e.g. "smoking", "recent viral upper respiratory infection")
    #     against PMH text; history_match instead catches the patient's PMH/social history naming
    #     a PAST OCCURRENCE of the diagnosis itself BY NAME (e.g. "history of migraines", "known
    #     atrial fibrillation", "recurrent pyelonephritis") -- a disease is not usually listed as
    #     its own risk factor, so this is real, additional signal a plain risk_factors match would
    #     never catch on its own (past-diagnosis recurrence risk).
    if presentation.risk_factors:
        for entry in all_diseases().values():
            for name in (entry["name"], *entry.get("aliases", [])):
                if feature_present(name, presentation.risk_factors, scrub_negated_spans=True):
                    _add(pool, entry, "history_match")
                    break

    # 2d. imaging_match -- an already-available imaging/study finding (state.imaging, e.g. a CXR or
    #     CT read before this turn) pulls in any diagnosis whose OWN typical_features/
    #     confirmatory_findings it matches, even without a matching symptom concept -- e.g. a CXR
    #     incidentally read as "widened mediastinum" keeps aortic_dissection reachable regardless
    #     of how the chief complaint was routed.
    if imaging_text:
        for entry in all_diseases().values():
            phrases = list(entry.get("typical_features", [])) + list(entry.get("confirmatory_findings", []))
            for phrase in phrases:
                if feature_present(phrase, imaging_text, scrub_negated_spans=True):
                    _add(pool, entry, "imaging_match")
                    break

    # 3. objective_finding -- decisive numeric lab evidence pulls its diagnosis in regardless of
    #    symptom-based routing (same numeric-threshold reasoning glucose_evidence.py/
    #    severity_evidence.py already use for scoring, applied here to pool membership too).
    glucose = extract_glucose_mg_dl(glucose_result_text)
    if glucose is not None:
        if glucose < HYPOGLYCEMIA_THRESHOLD_MG_DL:
            entry = disease_by_id("hypoglycemia")
            if entry is not None:
                _add(pool, entry, "objective_finding")
        if glucose >= DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL:
            entry = disease_by_id("diabetic_ketoacidosis")
            if entry is not None:
                _add(pool, entry, "objective_finding")
    lactate = extract_lactate_mmol_l(lactate_result_text)
    if lactate is not None and lactate >= ELEVATED_LACTATE_MMOL_L:
        entry = disease_by_id("sepsis")
        if entry is not None:
            _add(pool, entry, "objective_finding")

    # 3b. Same objective_finding idea, generalized: any OTHER lab objective_evidence.py normalizes
    # (troponin, D-dimer, potassium, sodium, WBC, hemoglobin, ketones, beta-hCG, ...) pulls in
    # every diagnosis whose own confirmatory_findings reference it, once that lab's actual reading
    # is abnormal in the direction that finding asserts -- via the reverse index built above, so a
    # decisive lab result is never invisible to pool membership just because no symptom concept
    # happened to name the diagnosis it confirms.
    abnormal_by_direction = {"high": ("high", "critical_high"), "low": ("low", "critical_low")}
    for lab_id, finding in (objective_findings or {}).items():
        for diagnosis_id, direction in _LAB_TO_DIAGNOSES.get(lab_id, ()):
            if finding.interpretation in abnormal_by_direction[direction]:
                entry = disease_by_id(diagnosis_id)
                if entry is not None:
                    _add(pool, entry, "objective_finding")

    if not pool:
        # Genuinely nothing matched anything at all via symptom/risk/objective evidence -- the
        # untargeted whole catalog is the last resort, never a narrower substitute (spec: the
        # agent must always reason toward a diagnosis, never stall for lack of a match). This check
        # MUST happen before the safety_candidate step below: that step always populates something
        # (a small fixed 8-entry list), so checking `not pool` afterward would make this whole-
        # catalog fallback permanently unreachable -- a real bug caught by a measured regression
        # (a plain viral URI with no matched concept at all lost viral_uri from the pool entirely
        # and was scored as sepsis, the only entries a fully-unmatched presentation would ever see).
        for entry in all_diseases().values():
            _add(pool, entry, "safety_candidate")
        return list(pool.values())

    # 4. safety_candidate -- the small, fixed can't-miss list always rides along ON TOP OF a
    #    non-empty symptom/risk/objective pool, so a genuinely atypical dangerous presentation is
    #    never entirely absent from scoring just because no signal happened to name it directly
    #    this turn -- additive only, never a substitute for real evidence-based pool membership.
    for diagnosis_id in CROSS_CUTTING_DANGEROUS_DIAGNOSES:
        entry = disease_by_id(diagnosis_id)
        if entry is not None:
            _add(pool, entry, "safety_candidate")

    candidates = list(pool.values())
    if len(candidates) <= TARGET_POOL_SIZE:
        return candidates

    # Trim toward the target size -- but ONLY an entry reached SOLELY via the fixed safety-net
    # list, with no symptom/risk/objective evidence of its own at all, is eligible to be trimmed.
    # A diagnosis with any real evidence (symptom_match/risk_match/objective_finding) is always
    # kept regardless of its `dangerous` flag: trimming was earlier keyed on `dangerous` alone,
    # which let the fixed 8-entry safety-net list (all `dangerous: true`) consume the entire size
    # budget and push out a non-dangerous but STRONGLY, DIRECTLY matched diagnosis (e.g.
    # pyelonephritis, tagged under all three of urinary_symptoms/fever/back_pain) -- exactly
    # backwards from the spec's intent (critical diagnoses must not disappear FROM the pool via
    # this mechanism; it never says a well-evidenced diagnosis should be sacrificed to make room
    # for a zero-evidence entry that's only present as a blanket safety net).
    safety_only = {"safety_candidate"}
    protected = [c for c in candidates if set(c.sources) != safety_only]
    trimmable = [c for c in candidates if c.id not in {p.id for p in protected}]
    keep_count = max(0, TARGET_POOL_SIZE - len(protected))
    return protected + trimmable[:keep_count]
