"""Hybrid Candidate Expansion: Canonicalization (spec section 5).

The LLM may introduce a differential diagnosis outside the local knowledge base (spec section 7),
but that would be useless if it could never act on it: the deterministically-generated candidate
pool (missing_info.py) is built only from KNOWN differential diagnoses' `discriminating_*` lists,
so a novel diagnosis's own workup is never in it by construction. Without this module, "the LLM
thinks it's Boerhaave syndrome" could never lead to "so let's get a chest CT" -- the agent would be
stuck re-asking/re-testing only what the local 34-disease catalog already anticipated.

This bridges that gap for ASK/EXAM/TEST (never for DIAGNOSE, which safety_validator.py handles
separately): if the LLM's selected_action key isn't in this turn's candidate pool, its key/content
text is matched against the FULL taxonomy catalog (nova_agent.taxonomy) by keyword overlap -- the
same mechanism semantic_dedup.py already uses for duplicate detection, applied here in the
opposite direction (find a real match, not detect a repeat). A successful match to a real,
not-yet-performed catalog entry is accepted, phrased with the catalog's own canonical text (never
the LLM's raw, unverified string). No match -- including a plausible-sounding but non-existent
test name -- is never executed; safety_validator.py's normal unknown-key rejection applies.
"""

from __future__ import annotations

from typing import Optional

from nova_agent.action_selector import AgentAction
from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG, QUESTION_CATALOG, TEST_CATALOG, normalize_free_text_to_category


def canonicalize_action(action_type: str, key: str, content: str, state: PatientState) -> Optional[AgentAction]:
    """Returns a legal, catalog-backed AgentAction if `key`/`content` can be mapped onto a real,
    not-yet-performed catalog entry; None if no reasonable mapping exists (never invents one)."""
    search_text = f"{key} {content}".strip()

    if action_type == "ASK":
        category = key if key in QUESTION_CATALOG else normalize_free_text_to_category(search_text, QUESTION_CATALOG)
        if category and not state.question_asked(category):
            spec = QUESTION_CATALOG[category]
            return AgentAction(
                action_type="ASK", key=category, content=spec["text_en"],
                rationale=f"Canonicalized from LLM proposal (key={key!r}, content={content!r}) onto "
                          f"known question category {category!r}.",
            )
        return None

    if action_type == "EXAM":
        exam_id = key if key in EXAM_CATALOG else normalize_free_text_to_category(search_text, EXAM_CATALOG)
        if exam_id and not state.exam_done(exam_id):
            spec = EXAM_CATALOG[exam_id]
            return AgentAction(
                action_type="EXAM", key=exam_id, content=spec["name_en"],
                rationale=f"Canonicalized from LLM proposal (key={key!r}, content={content!r}) onto "
                          f"known exam {exam_id!r}.",
            )
        return None

    if action_type == "TEST":
        test_id = key if key in TEST_CATALOG else normalize_free_text_to_category(search_text, TEST_CATALOG)
        if test_id and not state.test_done(test_id):
            spec = TEST_CATALOG[test_id]
            return AgentAction(
                action_type="TEST", key=test_id, content=spec["name_en"],
                rationale=f"Canonicalized from LLM proposal (key={key!r}, content={content!r}) onto "
                          f"known test {test_id!r}.",
            )
        return None

    return None
