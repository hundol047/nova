"""Dangerous-diagnosis resolution policy (spec sections 6/7/24).

Single source of truth for "has this dangerous diagnosis been adequately addressed", used by both
stop_policy.py (should we DIAGNOSE now) and safety_validator.py (should a DIAGNOSE be blocked).
Previously duplicated in both files with a critical bug: a diagnosis with no local knowledge-base
entry (i.e. a novel diagnosis the LLM introduced) was treated as automatically "resolved" just
because there was no entry to check workup against -- meaning an LLM-flagged
`dangerous_if_missed=True` diagnosis outside the 34-disease catalog could never actually block a
premature/wrong DIAGNOSE. Fixed here: a diagnosis is resolved only via explicit contradictory
evidence, or (for a KNOWN diagnosis only) by completing its minimum rule-out/confirm workup.

Minimum workup (not "every discriminating exam/test"): requiring the full discriminating_exams +
discriminating_tests list before considering a dangerous alternative addressed drove unnecessary
testing (spec section 7). `minimum_workup` in a disease's knowledge-base entry, when present, is
the small subset of tests that actually rules the diagnosis in or out (e.g. ACS: ECG + troponin,
not also CXR); entries without it fall back to the full discriminating list for backward
compatibility.
"""

from __future__ import annotations

from typing import List

from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.state import PatientState


def is_resolved(diagnosis_id: str, contradictory_evidence: List[str], state: PatientState) -> bool:
    """True if this dangerous diagnosis no longer needs to block a DIAGNOSE / stop decision."""
    from nova_agent.config import get_config
    if get_config().competition_retrieval_enabled:
        return _competition_resolved(diagnosis_id, contradictory_evidence, state)
    if contradictory_evidence:
        # Explicit evidence against it -- resolves a known OR a novel/unknown diagnosis alike.
        return True

    entry = disease_by_id(diagnosis_id)
    if entry is None:
        # Unknown/novel diagnosis (e.g. LLM-introduced, outside the local knowledge base): NEVER
        # auto-resolved just because there is no knowledge-base entry to check a workup against.
        # Unresolved by default until contradictory evidence (above) or a future explicit
        # resolution signal says otherwise.
        return False

    required = entry.get("minimum_workup") or (
        list(entry.get("discriminating_exams", [])) + list(entry.get("discriminating_tests", []))
    )
    if not required:
        return True
    done = set(state.completed_examinations) | set(state.completed_tests)
    return set(required).issubset(done)


def _competition_resolved(diagnosis_id, contradictory_evidence, state):
    """Workup addressed != disease excluded. Soft negatives alone never close a danger.

    No knowledge of simulator labels, case IDs or answer order is available here. A performed
    action with no interpretable result is still unknown. After minimum workup, an evidenced
    diagnosis lacking its confirmatory findings may still need a remaining discriminator.
    """
    import re
    from nova_agent.differential import _score_disease, _strip_negative_prefix
    entry = disease_by_id(diagnosis_id)
    if entry is None:
        if diagnosis_id.startswith("onto::"):
            return _ontology_workup_addressed(diagnosis_id, state)
        return False
    required = entry.get("minimum_workup")
    if required is None:
        required = list(entry.get("discriminating_exams", [])) + list(entry.get("discriminating_tests", []))
    results = {**state.physical_examinations, **state.imaging, **state.laboratory_tests}
    unavailable = re.compile(r"\b(pending|unavailable|unknown|not (?:done|performed|available)|insufficient sample|awaiting)\b", re.I)
    completed = set(state.completed_examinations) | set(state.completed_tests)
    if any(k not in completed or not str(results.get(k, '')).strip() or unavailable.search(results[k]) for k in required):
        return False
    if not required:
        return True
    confirm = set(entry.get("confirmatory_findings", []))
    remaining = set(entry.get("discriminating_tests", [])) - completed
    if confirm and remaining:
        from nova_agent.severity_evidence import GENERIC_PHYSIOLOGIC_SEVERITY_WORDS
        from nova_agent.matching import content_words
        _, _, support, _, _ = _score_disease(entry, state)
        specific = [p for p in support if p in entry.get("typical_features", [])
                    and not _strip_negative_prefix(p)
                    and not content_words(p).issubset(GENERIC_PHYSIOLOGIC_SEVERITY_WORDS)]
        if len(specific) >= 2 and not confirm.intersection(support):
            return False
    return True


def _ontology_workup_addressed(diagnosis_id: str, state: PatientState) -> bool:
    """Tier-2/3 (ontology) candidates have no exam/test workup of their own, so the only
    discriminators that EXIST for them are their generic feature questions (missing_info generates at
    most MAX_TIER2_DISCRIMINATING_FEATURES). Round M: they used to be unresolvable forever, so any
    supported dangerous long-tail candidate blocked the stop until the turn budget forced a diagnosis
    (50+ turn encounters). They are addressed once every discriminator that exists has been asked;
    "addressed" still does not mean excluded -- a decisive lead is separately required to stop."""
    try:
        from nova_agent.missing_info import _resolve_entry
        entry = _resolve_entry(diagnosis_id)
    except Exception:
        return False
    if entry is None:
        return False
    # Match the action generator: a specific positive feature already in this
    # patient's evidence does not need to be elicited again. This only records
    # discriminator coverage; it does not exclude the disease or bypass stop safety.
    from nova_agent.differential import _score_disease
    from nova_agent.ontology.normalizer import normalize
    _, _, support, _, _ = _score_disease(entry, state)
    supported = {normalize(s) for s in support}
    def covered(question):
        if state.question_asked(question):
            return True
        if ":" not in question:
            return False
        feature = normalize(question.split(":", 1)[1])
        return bool(feature and feature in supported)
    return all(covered(q) for q in entry.get("discriminating_questions", []))
