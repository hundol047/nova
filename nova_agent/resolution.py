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
