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
from nova_agent.contextual_safety import contextually_activated_diagnosis_ids
from nova_agent.glucose_evidence import (
    DKA_HYPERGLYCEMIA_THRESHOLD_MG_DL,
    HYPOGLYCEMIA_THRESHOLD_MG_DL,
    extract_glucose_mg_dl,
)
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id, diseases_for_tag
from nova_agent.matching import feature_present, feature_present_with_aliases
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
                           "imaging_match", "objective_finding", "safety_candidate",
                           "ontology_broadening", "ontology_retrieval", "zero_evidence_fallback",
                           "contextual_safety"]

# Tier-2 structured concepts carry real curated typical_features but no KB-depth discriminating
# questions of their own; this bounds how many of those features become generic ASK candidates
# (see _concept_to_kb_entry) so a single broad concept can never flood the differential engine's
# missing-information analysis with dozens of near-duplicate generic questions.
MAX_TIER2_DISCRIMINATING_FEATURES = 4

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


def _concept_to_kb_entry(concept) -> dict:
    """Adapt an ontology ClinicalConcept into the minimal KB-shaped dict downstream scoring expects.
    Core catalog hits preserve the complete authoritative KB profile. Tier-2/3 adapters remain
    deliberately shallow: those concepts carry no discriminating exams/tests or confirmatory findings, so
    those keys stay EMPTY — the concept enters the pool as a low-evidence, named possibility, never
    as if it had deep curated evidence. `id` is namespaced so it can never collide with a real
    34-KB diagnosis id.

    TIER-AWARE discriminating_questions (missing_info.py's action-generation gap fix): a Tier-2
    STRUCTURED concept's own curated `typical_features` become a BOUNDED set of generic
    "associated_symptoms:<feature>" discriminators -- the exact same generic fallback phrasing
    taxonomy.disease_specific_question() already produces for any KB discriminator it doesn't have a
    templated question for, so this fabricates no new clinical content, only reuses real curated
    ontology data through an existing generic template. A Tier-3 ontology-only concept carries no
    curated clinical claims (see nova_agent/open_world.py's design constraints), so it correctly
    gets NO discriminating_questions here -- it can still appear in the differential/LLM context via
    retrieval, but never generates a deterministic action of its own."""
    if getattr(concept, "kb_id", None):
        deep = disease_by_id(concept.kb_id)
        if deep is not None:
            return deep
    is_tier2_structured = concept.tier.value == "TIER2_STRUCTURED"
    discriminating_questions = (
        [f"associated_symptoms:{feature}"
         for feature in list(concept.typical_features)[:MAX_TIER2_DISCRIMINATING_FEATURES]]
        if is_tier2_structured else []
    )
    return {
        "id": f"onto::{concept.concept_id}",
        "name": concept.canonical_name,
        "aliases": list(concept.aliases),
        "category": concept.category or "ontology",
        "dangerous": bool(concept.dangerous) if concept.dangerous is not None else False,
        "urgency": concept.urgency or "ROUTINE",
        "chief_complaint_tags": list(concept.chief_complaint_tags),
        "typical_features": list(concept.typical_features),
        "risk_factors": [],
        "discriminating_questions": discriminating_questions,
        "discriminating_exams": [],
        "discriminating_tests": [],
        "confirmatory_findings": list(getattr(concept, "confirmatory_findings", ()) or ()),
        "red_flag_keywords": [],
        "minimum_workup": [],
        "evidence_level": "ontology_tier2_structured" if is_tier2_structured else "ontology_tier3",
    }


def _broaden_with_ontology(pool: dict, presentation: ClinicalPresentation, max_add: int) -> None:
    """OPT-IN open-world broadening. Adds up to `max_add` Tier-2 structured concepts that lexically
    match the presentation's chief-complaint text/symptoms but are NOT already represented in the
    closed-KB pool. Additive only: never removes or reweights an existing candidate. Imports the
    ontology lazily so this cost is paid only when the deployer enables broadening. Any failure to
    load the catalog degrades silently to the unchanged closed-KB pool (never breaks a case)."""
    if max_add <= 0:
        return
    try:
        from nova_agent.ontology.registry import get_default_catalog
        from nova_agent.ontology.models import Tier
    except Exception:
        return  # ontology unavailable -> unchanged behavior

    # Build the query from the concepts we already extracted (symptoms + chief complaint text).
    query_terms = list(presentation.symptoms)
    chief = getattr(presentation, "chief_complaint_text", None) or getattr(presentation, "raw_text", None)
    if chief:
        query_terms.append(str(chief))
    if not query_terms:
        return

    try:
        catalog = get_default_catalog()
    except Exception:
        return

    added = 0
    seen_names = {c.entry.get("name", "").strip().lower() for c in pool.values()}
    for term in query_terms:
        if added >= max_add:
            break
        for match in catalog.search_conditions(term, limit=max_add, fuzzy=True):
            if added >= max_add:
                break
            concept = match.concept
            # Only Tier-2 structured concepts broaden the pool here: Tier-1 deep concepts are the
            # 34 KB entries already handled above, and Tier-3 ontology-only concepts carry no
            # clinical structure to score. Skip anything already present (by namespaced id or name).
            if concept.tier != Tier.TIER2_STRUCTURED:
                continue
            onto_id = f"onto::{concept.concept_id}"
            if onto_id in pool or concept.canonical_name.strip().lower() in seen_names:
                continue
            _add(pool, _concept_to_kb_entry(concept), "ontology_broadening")
            seen_names.add(concept.canonical_name.strip().lower())
            added += 1


def _broaden_with_open_world(pool: dict, presentation: ClinicalPresentation,
                             imaging_text: Optional[List[str]], chief_complaint_text: Optional[str],
                             retrieval_top_k: int, rerank_top_k: int,
                             objective_findings: Optional[Dict[str, ObjectiveFinding]] = None) -> None:
    """Competition-mode broad retrieval (NOVA_COMPETITION_RETRIEVAL), now a real 3-stage funnel
    instead of a single small `limit`: nova_agent.retrieval_pipeline.retrieve_and_rerank() first
    retrieves up to `retrieval_top_k` (recommended 100-200) candidates -- HIGH RECALL, so a true
    long-tail diagnosis has room to survive -- fuses EVERY signal already extracted this turn (chief
    complaint text, symptom concepts, risk/PMH/social history, medication context, imaging findings)
    through the existing, already-tested OpenWorldRetriever.retrieve_multi_signal(), rebuilt fresh
    every call from whatever `presentation`/`imaging_text`/`chief_complaint_text` the caller
    currently has (never limited to the original presenting sentence, since differential.py already
    rebuilds `presentation` from the FULL current PatientState every turn). It then deterministically
    reranks that pool down to `rerank_top_k` (recommended 20-30) before ANY of it reaches this
    function's caller -- expensive downstream reasoning (differential scoring, LLM context) only
    ever sees the narrowed, reranked survivors, never the full retrieval pool.

    Allows BOTH Tier-2 structured AND Tier-3 ontology-only concepts through: a Tier-3 concept still
    enters the pool as a named, zero-deep-evidence possibility (via `_concept_to_kb_entry`, which
    correctly gives it no discriminating_questions), exactly like the existing fixed safety-net
    entries -- and the reranker's dangerous-concept reinjection (see retrieval_pipeline.py) means a
    `dangerous: true` ontology concept cannot be silently reranked away even at this stage, on top
    of (not instead of) the pool-level `trimmable_only_sources` protection below.

    Source-tagged 'ontology_retrieval' -- distinct from the legacy 'ontology_broadening' tag -- so
    provenance stays honest about which mechanism actually found the candidate. Additive only:
    never removes or reweights an existing candidate. Any failure to import/load the catalog,
    retriever, or reranker degrades silently to the unchanged pool -- the deterministic KB pool
    remains the safe fallback, a broad-retrieval outage never crashes or blocks a case."""
    if retrieval_top_k <= 0 or rerank_top_k <= 0:
        return
    try:
        from nova_agent.open_world import OpenWorldRetriever
        from nova_agent.ontology.registry import get_default_catalog
        from nova_agent.retrieval_pipeline import retrieve_and_rerank
    except Exception:
        return

    try:
        retriever = OpenWorldRetriever(get_default_catalog())
    except Exception:
        return

    # Decisive abnormal objective findings become their OWN weighted retrieval signal (real,
    # already-computed ObjectiveFinding.evidence_label text -- never fabricated here), so e.g. a
    # positive troponin or severe hypoglycemia carries more retrieval weight than a generic word
    # like "pain"/"fatigue" (see retrieval_pipeline.SIGNAL_WEIGHTS) -- generic through signal TYPE,
    # never a disease-specific rule. Only genuinely abnormal findings are included; "normal"/
    # "unknown" interpretations carry no retrieval signal.
    objective_finding_phrases = [
        finding.evidence_label for finding in (objective_findings or {}).values()
        if finding.interpretation not in ("normal", "unknown")
    ]
    try:
        reranked = retrieve_and_rerank(
            retriever,
            chief_complaint=str(chief_complaint_text or ""),
            symptoms=list(presentation.symptoms),
            history=list(presentation.risk_factors),
            medications=list(presentation.medication_context),
            objective_finding_phrases=objective_finding_phrases,
            imaging_concepts=list(imaging_text or []),
            retrieval_top_k=retrieval_top_k,
            rerank_top_k=rerank_top_k,
        )
    except Exception:
        return

    seen_names = {c.entry.get("name", "").strip().lower() for c in pool.values()}
    for candidate in reranked:
        concept = candidate.concept
        onto_id = f"onto::{concept.concept_id}"
        if onto_id in pool or concept.canonical_name.strip().lower() in seen_names:
            continue
        _add(pool, _concept_to_kb_entry(concept), "ontology_retrieval")
        seen_names.add(concept.canonical_name.strip().lower())


MAX_EVIDENCED_ONTOLOGY_PROTECTED = 8
# One bare single-word match (0.5) is not evidence enough to protect a concept from trimming.
MIN_EVIDENCED_ONTOLOGY_WEIGHT = 1.0


def _ontology_evidence_weight(entry: dict, evidence_text) -> float:
    """Bounded count of an ontology entry's own features matched by the patient's evidence. A
    multi-word feature counts 1.0, a bare single-word one 0.5, a confirmatory finding 2.0; the total
    is capped so ten weak matches cannot outrank one specific multi-feature match."""
    total = 0.0
    for feature in entry.get("typical_features", []):
        if feature_present_with_aliases(feature, evidence_text):
            total += 1.0 if len(feature.split()) >= 2 else 0.5
    for finding in entry.get("confirmatory_findings", []):
        if feature_present_with_aliases(finding, evidence_text):
            total += 2.0
    return min(total, 4.0)


def _evidenced_ontology_candidates(candidates, presentation, already_protected):
    protected_ids = {c.id for c in already_protected}
    ontology_only = {"ontology_broadening", "ontology_retrieval"}
    scored = []
    for order, c in enumerate(candidates):
        if c.id in protected_ids or not set(c.sources).issubset(ontology_only):
            continue
        weight = _ontology_evidence_weight(c.entry, presentation.evidence_text)
        if weight >= MIN_EVIDENCED_ONTOLOGY_WEIGHT:
            scored.append((-weight, order, c))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [c for _, _, c in scored[:MAX_EVIDENCED_ONTOLOGY_PROTECTED]]


def generate_candidates(presentation: ClinicalPresentation,
                         glucose_result_text: Optional[str] = None,
                         lactate_result_text: Optional[str] = None,
                         objective_findings: Optional[Dict[str, ObjectiveFinding]] = None,
                         imaging_text: Optional[List[str]] = None,
                         ontology_broadening: bool = False,
                         ontology_broadening_max: int = 5,
                         competition_retrieval: bool = False,
                         retrieval_top_k: int = 150,
                         rerank_top_k: int = 25,
                         chief_complaint_text: Optional[str] = None,
                         pool_target_size: Optional[int] = None) -> List[CandidateDiagnosis]:
    """Builds the candidate pool for one turn. `glucose_result_text`/`lactate_result_text`/
    `objective_findings`/`imaging_text` are passed explicitly (not a whole PatientState) to keep
    this module's dependency surface small and directly testable. `objective_findings` is the
    canonical-id-keyed dict objective_evidence.normalize_objective_evidence() returns (callers
    already compute it once per turn for differential.py's own scoring, so it's passed through
    rather than re-derived here) -- None (the default) simply skips the generalized-lab pool step
    below, leaving the glucose/lactate-only behavior unchanged for any caller that doesn't pass it.
    `imaging_text` is `state.imaging.values()` -- also None-safe/optional for the same reason.
    `chief_complaint_text` is `state.chief_complaint` -- used ONLY by the opt-in competition
    retrieval step (`_broaden_with_open_world`) as one fused free-text signal alongside
    `presentation`'s already-extracted symptoms/history; None-safe/optional, same reasoning.

    `retrieval_top_k`/`rerank_top_k` are the two DISTINCT stage sizes of the competition retrieval
    pipeline (nova_agent.retrieval_pipeline): `retrieval_top_k` (recommended 100-200) is how many
    catalog hits Stage 1 pulls for high recall; `rerank_top_k` (recommended 20-30) is how many of
    those survive Stage 2/3 (lightweight deterministic rerank + safety reinjection) before entering
    THIS pool. Only consulted when `competition_retrieval=True`.

    `pool_target_size` overrides the module-level TARGET_POOL_SIZE for the final pool-size-trim
    step below (None keeps the existing default, preserving byte-identical legacy/non-retrieval
    behavior). The real runtime (differential.py) passes the configured `reasoning_top_k` here when
    competition retrieval is enabled, so the ACTIVE CLINICAL DIFFERENTIAL -- the deterministic KB
    pool plus reranked ontology candidates -- has room for more than the legacy 12-candidate budget
    without changing that legacy budget for any caller that doesn't opt in."""
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
                if feature_present_with_aliases(risk_factor, presentation.risk_factors, scrub_negated_spans=True):
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
                if feature_present_with_aliases(risk_factor, presentation.medication_context, scrub_negated_spans=True):
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

    if competition_retrieval:
        # Concept routing is intentionally coarse. Preserve observed wording as a separate
        # path to existing deep profiles; no label-only ontology hit gains clinical evidence.
        for entry in all_diseases().values():
            matches = [p for p in entry.get("typical_features", [])
                       if len(p.split()) >= 3 and not p.lower().startswith(("no ", "without ", "absent "))
                       and feature_present_with_aliases(p, presentation.evidence_text)]
            if matches:
                _add(pool, entry, "symptom_match")

    if not pool:
        # Genuinely nothing matched anything at all via symptom/risk/objective evidence -- the
        # untargeted whole catalog is the last resort, never a narrower substitute (spec: the
        # agent must always reason toward a diagnosis, never stall for lack of a match). This check
        # MUST happen before the safety_candidate step below: that step always populates something
        # (a small fixed 8-entry list), so checking `not pool` afterward would make this whole-
        # catalog fallback permanently unreachable -- a real bug caught by a measured regression
        # (a plain viral URI with no matched concept at all lost viral_uri from the pool entirely
        # and was scored as sepsis, the only entries a fully-unmatched presentation would ever see).
        #
        # Tagged with the DISTINCT "zero_evidence_fallback" source (never "safety_candidate", the
        # small fixed must-not-miss list step 4 below adds) so differential.py can tell "every
        # candidate is here purely because NOTHING matched at all" apart from "a normal, possibly
        # well-evidenced pool that also happens to carry the fixed safety net" -- this is what lets
        # differential.py recognize a genuine zero-evidence/UNKNOWN_PRESENTATION case and refuse to
        # let stable-sort/dict-insertion order (ultimately: disease KB file load order) silently
        # decide an arbitrary "winning" diagnosis (spec: this must become an explicit
        # insufficient-information state, never a confident DIAGNOSE). See
        # tests/test_zero_evidence_file_order_independence.py.
        for entry in all_diseases().values():
            _add(pool, entry, "zero_evidence_fallback")
        if competition_retrieval:
            # Round M: "nothing in the 34-disease KB matched" is exactly when the broad ontology
            # retrieval matters most (the true diagnosis is then a long-tail concept), yet this
            # early return used to skip it entirely. It only ADDS candidates; they are retrieval
            # recall, not evidence, so differential.py still treats an unscored pool as zero-evidence.
            _broaden_with_open_world(pool, presentation, imaging_text, chief_complaint_text,
                                     retrieval_top_k, rerank_top_k, objective_findings)
        return list(pool.values())

    # 4. safety_candidate -- the small, fixed can't-miss list always rides along ON TOP OF a
    #    non-empty symptom/risk/objective pool, so a genuinely atypical dangerous presentation is
    #    never entirely absent from scoring just because no signal happened to name it directly
    #    this turn -- additive only, never a substitute for real evidence-based pool membership.
    for diagnosis_id in CROSS_CUTTING_DANGEROUS_DIAGNOSES:
        entry = disease_by_id(diagnosis_id)
        if entry is not None:
            _add(pool, entry, "safety_candidate")

    # 4b. contextual_safety (Round E, defect B) -- a small, NARROW, contextually-gated activation
    #     for a dangerous diagnosis that does NOT belong in the always-on CROSS_CUTTING_DANGEROUS_
    #     DIAGNOSES list (that would blanket-inflate every case's pool regardless of relevance) but
    #     still needs a path into the pool for an atypical/vague presentation that never generates
    #     its own symptom_match -- e.g. ectopic pregnancy for a reproductive-age patient with
    #     abdominal/pelvic symptoms or unexplained syncope/bleeding. See
    #     nova_agent/contextual_safety.py's own module docstring for the full rationale; activation
    #     is additive only (never displaces anything) and never "keeps forever" -- ordinary scoring
    #     and resolution.py's existing is_resolved() logic can still rank it down or resolve it out.
    for diagnosis_id in contextually_activated_diagnosis_ids(presentation):
        entry = disease_by_id(diagnosis_id)
        if entry is not None:
            _add(pool, entry, "contextual_safety")

    # 5. ontology_broadening (OPT-IN, default off) -- thin open-world supplement of Tier-2 concepts
    #    the closed KB doesn't contain. Runs AFTER the safety net and BEFORE trimming so an
    #    ontology-only entry is treated exactly like a zero-KB-evidence safety entry: trimmable,
    #    never protected over a KB candidate with real evidence. When disabled, the pool is
    #    byte-identical to the pre-vNext behavior.
    if ontology_broadening:
        _broaden_with_ontology(pool, presentation, ontology_broadening_max)

    # 6. ontology_retrieval (OPT-IN via NOVA_COMPETITION_RETRIEVAL, default off) -- the broader,
    #    multi-signal, Tier-2+Tier-3 competition retrieval step. Runs after (never instead of) both
    #    the deterministic KB pool and the legacy ontology_broadening step, so it can only ADD
    #    candidates neither of those already found; byte-identical existing behavior when disabled.
    if competition_retrieval:
        _broaden_with_open_world(pool, presentation, imaging_text, chief_complaint_text,
                                 retrieval_top_k, rerank_top_k, objective_findings)

    target_size = pool_target_size if pool_target_size is not None else TARGET_POOL_SIZE
    candidates = list(pool.values())
    if len(candidates) <= target_size:
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
    # An entry reached ONLY via the fixed safety net and/or opt-in ontology broadening/retrieval (no
    # symptom/risk/objective evidence of its own) is trimmable; anything with real evidence is
    # protected. ontology_broadening/ontology_retrieval entries are zero-KB-evidence supplements, so
    # they never displace an evidenced KB candidate (or a must-not-miss safety_candidate) from the
    # size budget -- a broad retrieval hit can add a genuinely new long-tail possibility, but it can
    # never crowd out an existing Tier-1 candidate or must-not-miss diagnosis.
    trimmable_only_sources = {"safety_candidate", "contextual_safety", "ontology_broadening", "ontology_retrieval"}
    # The fixed cross-cutting must-not-miss list (PR #15) always survives the size budget even when only the
    # safety net retrieved it. Other `dangerous` entries are NOT protected on that flag alone: protecting all
    # of them let weakly supported ones (e.g. hypoglycemia from "sweating") displace the disease-specific
    # leaders in the top-K and shift action utilities (tests/test_discriminator_priority.py).
    protected = [c for c in candidates if c.id in CROSS_CUTTING_DANGEROUS_DIAGNOSES
                 or not set(c.sources).issubset(trimmable_only_sources)]
    # Round M: an ontology candidate whose OWN typical/confirmatory features are matched by the
    # patient's evidence is no longer a zero-evidence supplement. Trimming by insertion order cut
    # evidence-bearing long-tail truths that retrieval ranked 1st-10th (they were appended after the
    # fixed safety net, so they sat past the keep_count boundary and were never even scored). The
    # best-evidenced few are protected (bounded by MAX_EVIDENCED_ONTOLOGY_PROTECTED); the rest keep
    # the previous trimmable behavior.
    evidenced_ontology = _evidenced_ontology_candidates(candidates, presentation, protected)
    evidenced_ontology = evidenced_ontology[:max(0, target_size - len(protected))]  # never past the budget
    protected = protected + evidenced_ontology
    trimmable = [c for c in candidates if c.id not in {p.id for p in protected}]
    keep_count = max(0, target_size - len(protected))
    result = protected + trimmable[:keep_count]

    # Bounded safety reinjection (mirrors retrieval_pipeline.lightweight_rerank's Stage 3): the
    # evidence-based trim above deliberately does NOT blanket-protect every `dangerous: true`
    # candidate (an earlier attempt at that starved well-evidenced non-dangerous diagnoses -- see
    # the comment above), but that means a `dangerous: true` entry reached only via the fixed,
    # SMALL, bounded safety net (CROSS_CUTTING_DANGEROUS_DIAGNOSES, ~8 ids) OR the equally small,
    # narrowly-gated `contextual_safety` activations (nova_agent/contextual_safety.py) can still be
    # cut to ZERO when `protected` alone already fills the whole budget -- exactly the "candidate
    # present then silently dropped" failure this pool exists to prevent. Deliberately restricted to
    # `safety_candidate`/`contextual_safety`-sourced entries only (never ontology_broadening/
    # ontology_retrieval, which
    # can surface an open-ended, potentially large number of dangerous concepts of their own --
    # those already have their OWN, separate protection one stage earlier, in
    # retrieval_pipeline.lightweight_rerank's Stage 3 reinjection, before they ever reach this
    # pool), so growth here stays genuinely bounded to at most the fixed safety net's own size, not
    # unbounded. Swaps a dropped safety-net entry in for the weakest already-kept TRIMMABLE
    # (zero-real-evidence, non-dangerous) entry; only grows the pool past `target_size` in the rare
    # case where safety-net omissions outnumber non-dangerous trimmed entries available to swap
    # out. Never touches `protected` (a diagnosis with real evidence of its own is never sacrificed
    # for this).
    result_ids = {c.id for c in result}
    dangerous_missing = [c for c in trimmable[keep_count:]
                          if ("safety_candidate" in c.sources or "contextual_safety" in c.sources)
                          and c.entry.get("dangerous") and c.id not in result_ids]
    if dangerous_missing:
        swappable = [c for c in trimmable[:keep_count] if not c.entry.get("dangerous")]
        for missing in dangerous_missing:
            if swappable:
                weakest = swappable.pop(0)
                result = [c for c in result if c.id != weakest.id]
            result.append(missing)
            result_ids.add(missing.id)
    return result
