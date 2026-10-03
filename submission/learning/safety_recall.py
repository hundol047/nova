"""Deterministic safety-recall expansion (PHASE 1 PART F).

The must-not-miss backstop: even if embedding retrieval, the specialty router, the ML reranker, and
the LLM all MISS a dangerous diagnosis, deterministic rules add it back to the candidate pool. This
is the concrete implementation of the immutable priority:

    DETERMINISTIC SAFETY  >  ML RANKER  >  LLM

Rules map presentation triggers (symptoms + risk factors + objective signals) to critical concept
ids that must appear in the pool. A critical candidate can NEVER be removed by a low embedding
score / low ML score / LLM omission / specialty-router miss — safety-recall re-adds it and marks it
`safety_mandatory=True` so downstream ranking is forbidden from dropping it.

Dependency-free. Rules are GENERIC clinical must-not-miss associations, NOT tuned to any blind case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _toks(text: str) -> Set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


@dataclass(frozen=True)
class SafetyRule:
    """If ANY trigger group is fully satisfied, the listed critical concepts are mandatory."""

    name: str
    # list of trigger groups; a group is a set of tokens that must ALL be present (AND);
    # groups are OR'd together.
    trigger_groups: Sequence[Sequence[str]]
    critical_concepts: Sequence[str]   # concept ids / canonical-name fragments to ensure present
    rationale: str = ""


# GENERIC must-not-miss rules. concept targets are given as lower-case name fragments so they can be
# matched against catalog concept names (robust to id scheme). NOT tuned to any evaluation case.
SAFETY_RULES: List[SafetyRule] = [
    SafetyRule("acs_chest", [["chest", "pain"], ["chest", "pressure"], ["chest", "tightness"]],
               ["acute coronary syndrome", "aortic dissection", "pulmonary embolism"],
               "Chest pain must always keep ACS / dissection / PE alive."),
    SafetyRule("pe_dyspnea", [["dyspnea", "tachycardia"], ["dyspnea", "hypoxia"], ["pleuritic"],
                             ["calf", "swelling"], ["sudden", "breathless"]],
               ["pulmonary embolism"],
               "Sudden dyspnea / hypoxia / DVT signs must keep PE alive even if retrieval missed it."),
    SafetyRule("dissection", [["tearing"], ["ripping"], ["migrating", "pain"]],
               ["aortic dissection"], "Tearing/ripping/migrating pain -> aortic dissection."),
    SafetyRule("sah_headache", [["worst", "headache"], ["thunderclap"], ["sudden", "headache"]],
               ["subarachnoid hemorrhage", "bacterial meningitis"],
               "Sudden/worst headache -> SAH + meningitis."),
    SafetyRule("stroke", [["weakness", "sudden"], ["aphasia"], ["facial", "droop"], ["slurred"]],
               ["ischemic stroke", "intracerebral hemorrhage", "transient ischemic attack"],
               "Focal neuro deficit -> stroke spectrum."),
    SafetyRule("sepsis", [["fever", "hypotension"], ["fever", "confusion"], ["rigors", "tachycardia"]],
               ["sepsis"], "Fever + hemodynamic/mental change -> sepsis."),
    SafetyRule("meningitis", [["fever", "neck", "stiff"], ["photophobia", "fever"], ["meningismus"]],
               ["bacterial meningitis"], "Fever + meningismus -> meningitis."),
    SafetyRule("surgical_abdomen", [["abdominal", "pain", "rigid"], ["rebound"], ["guarding"],
                                    ["abdominal", "pain", "fever"]],
               ["acute abdomen", "acute appendicitis", "mesenteric ischemia", "perforated"],
               "Peritoneal signs -> surgical abdomen spectrum."),
    SafetyRule("ectopic", [["pregnant", "abdominal", "pain"], ["missed", "period", "pain"],
                          ["vaginal", "bleeding", "pain"]],
               ["ectopic pregnancy"], "Reproductive-age abdominal pain -> ectopic pregnancy."),
    SafetyRule("testicular_torsion", [["testicular", "pain"], ["scrotal", "pain", "sudden"]],
               ["testicular torsion"], "Acute testicular pain -> torsion."),
    SafetyRule("dka", [["polyuria", "vomiting"], ["thirst", "abdominal", "pain"], ["kussmaul"]],
               ["diabetic ketoacidosis"], "Hyperglycemic emergency signs -> DKA."),
    SafetyRule("anaphylaxis", [["hives", "dyspnea"], ["lip", "swelling", "wheeze"], ["throat", "closing"]],
               ["anaphylaxis"], "Urticaria + airway/resp -> anaphylaxis."),
    SafetyRule("tension_ptx", [["chest", "trauma", "dyspnea"], ["absent", "breath", "sounds"]],
               ["tension pneumothorax"], "Trauma + respiratory distress -> tension pneumothorax."),
    SafetyRule("gi_bleed", [["melena"], ["hematemesis"], ["black", "stool"]],
               ["gastrointestinal bleeding"], "Melena/hematemesis -> GI bleed."),
    SafetyRule("co_poisoning", [["headache", "multiple", "household"], ["carbon", "monoxide"],
                               ["exposure", "heater"]],
               ["carbon monoxide poisoning"], "Cluster headache-in-household / heater -> CO poisoning."),
]


@dataclass
class SafetyRecallResult:
    mandatory_concept_fragments: List[str]      # name fragments that must be present in the pool
    fired_rules: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "mandatory_concept_fragments": list(self.mandatory_concept_fragments),
            "fired_rules": list(self.fired_rules),
            "notes": list(self.notes),
        }


def evaluate_safety_rules(text: str, extra_signals: Optional[Sequence[str]] = None) -> SafetyRecallResult:
    """Return the must-not-miss concept name fragments triggered by this presentation."""
    toks = _toks(text)
    for sig in (extra_signals or []):
        toks |= _toks(str(sig))
    mandatory: List[str] = []
    fired: List[str] = []
    for rule in SAFETY_RULES:
        for group in rule.trigger_groups:
            if all(t in toks for t in group):
                fired.append(rule.name)
                for concept in rule.critical_concepts:
                    if concept not in mandatory:
                        mandatory.append(concept)
                break
    notes = []
    if fired:
        notes.append(f"Safety-recall fired {len(fired)} rule(s); {len(mandatory)} must-not-miss "
                     "concept(s) are mandatory in the candidate pool (Safety > ML > LLM).")
    return SafetyRecallResult(mandatory_concept_fragments=mandatory, fired_rules=fired, notes=notes)


def apply_safety_recall(candidate_items: List, catalog, text: str,
                        extra_signals: Optional[Sequence[str]] = None) -> dict:
    """Ensure every safety-mandatory concept is present in `candidate_items`. If a mandatory concept
    is missing, it is ADDED from the catalog and flagged safety_mandatory=True. Existing candidates
    matching a mandatory fragment are also flagged. Returns an audit dict.

    `candidate_items` are mutable objects with `.name`, `.concept_id`, `.score`, and (added)
    `.safety_mandatory`. NEVER removes a candidate. Requires a catalog with search_conditions()."""
    result = evaluate_safety_rules(text, extra_signals)
    present_names = {getattr(it, "name", "").strip().lower() for it in candidate_items}
    added: List[str] = []
    flagged: List[str] = []

    for frag in result.mandatory_concept_fragments:
        frag_l = frag.strip().lower()
        # flag any existing candidate whose name contains the fragment
        matched_existing = False
        for it in candidate_items:
            if frag_l in getattr(it, "name", "").strip().lower():
                setattr(it, "safety_mandatory", True)
                flagged.append(getattr(it, "name", ""))
                matched_existing = True
        if matched_existing:
            continue
        # otherwise pull the best catalog match and add it (safety-mandatory)
        if catalog is not None:
            hits = catalog.search_conditions(frag, limit=1)
            if hits:
                c = hits[0].concept
                if c.canonical_name.strip().lower() not in present_names:
                    # append as a mandatory candidate; use a duck-typed simple object matching
                    # RetrievedItem's attributes so downstream handles it uniformly.
                    from types import SimpleNamespace
                    item = SimpleNamespace(
                        concept_id=c.concept_id, name=c.canonical_name,
                        tier=c.tier.value, category=c.category or "",
                        score=0.0, sources=["safety"], safety_mandatory=True,
                    )
                    candidate_items.append(item)
                    present_names.add(c.canonical_name.strip().lower())
                    added.append(c.canonical_name)
    return {
        "fired_rules": result.fired_rules,
        "mandatory_fragments": result.mandatory_concept_fragments,
        "added_candidates": added,
        "flagged_existing": flagged,
        "notes": result.notes,
    }


def assert_no_critical_dropped(before_items: Sequence, after_items: Sequence) -> None:
    """Invariant guard: any candidate flagged safety_mandatory in `before_items` MUST still be in
    `after_items`. Raises AssertionError if a downstream stage dropped a mandatory candidate."""
    mandatory_before = {getattr(it, "concept_id", getattr(it, "name", ""))
                        for it in before_items if getattr(it, "safety_mandatory", False)}
    after_ids = {getattr(it, "concept_id", getattr(it, "name", "")) for it in after_items}
    dropped = mandatory_before - after_ids
    if dropped:
        raise AssertionError(f"SAFETY VIOLATION: safety-mandatory candidate(s) dropped: {dropped}")
