"""Semantic Duplicate Detection (spec section 12).

Three-layer fallback for recognizing that two differently-worded actions mean the same thing:

1. canonical action id -- PatientState.is_duplicate() / question_asked() / exam_done() /
   test_done() (exact catalog key match). This is the normal path: every ASK/EXAM/TEST candidate
   this codebase generates already comes from the fixed taxonomy catalog (nova_agent/taxonomy.py),
   so two candidates for "the same question" always share one key by construction.
2. normalized question category -- `key.split(":", 1)[0]`, already what
   missing_info._already_answered() checks for onset/duration/severity/PMH/family/social/
   medication/allergy.
3. semantic keyword-similarity fallback (this module) -- for free text that did NOT originate
   from the catalog (e.g. a competition-environment-authored question, or an LLM's own phrasing
   of a selected_action's `content` when `key` is missing/blank), map it onto the closest catalog
   entry by keyword overlap (taxonomy.normalize_free_text_to_category) and check whether that
   catalog id was already covered.
"""

from __future__ import annotations

from typing import Optional

from nova_agent.state import PatientState
from nova_agent.taxonomy import EXAM_CATALOG, QUESTION_CATALOG, TEST_CATALOG, normalize_free_text_to_category


def semantic_category_for_text(action_type: str, content: str) -> Optional[str]:
    if action_type == "ASK":
        return normalize_free_text_to_category(content, QUESTION_CATALOG)
    if action_type == "EXAM":
        return normalize_free_text_to_category(content, EXAM_CATALOG)
    if action_type == "TEST":
        return normalize_free_text_to_category(content, TEST_CATALOG)
    return None


def is_semantic_duplicate(action_type: str, content: str, state: PatientState) -> bool:
    """Layer 3 only -- callers should already have checked the exact-key layer first."""
    category = semantic_category_for_text(action_type, content)
    if category is None:
        return False
    if action_type == "ASK":
        return state.question_asked(category)
    if action_type == "EXAM":
        return state.exam_done(category)
    if action_type == "TEST":
        return state.test_done(category)
    return False
