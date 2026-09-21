"""Local, offline medical knowledge store + lightweight retrieval (spec section 15).

Never calls out to the network. Loads knowledge/{diseases,red_flags,diagnostic_tests,guidelines}
once per process and exposes small, targeted lookups so callers only ever pull in the handful of
disease entries relevant to the current chief complaint / top differential -- never the whole
knowledge base into a prompt.

RAG (the guideline/test-note retrieval functions) is feature-flagged via NovaConfig.rag_enabled;
the disease catalog itself (diseases_for_tag / diseases_by_id) is always available since
differential.py and safety.py are deterministic consumers of it, not part of the optional RAG path.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from nova_agent.config import get_config

KNOWLEDGE_ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def _load_diseases() -> Dict[str, dict]:
    diseases: Dict[str, dict] = {}
    for path in sorted((KNOWLEDGE_ROOT / "diseases").glob("*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            diseases[entry["id"]] = entry
    return diseases


@lru_cache(maxsize=1)
def _load_red_flags() -> dict:
    path = KNOWLEDGE_ROOT / "red_flags" / "critical_conditions.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_demographic_and_medication_risk() -> dict:
    path = KNOWLEDGE_ROOT / "red_flags" / "demographic_and_medication_risk.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _load_test_notes() -> Dict[str, str]:
    path = KNOWLEDGE_ROOT / "diagnostic_tests" / "notes.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {e["test_id"]: e["note"] for e in entries}


@lru_cache(maxsize=1)
def _load_guidelines() -> Dict[str, str]:
    path = KNOWLEDGE_ROOT / "guidelines" / "chief_complaint_guidelines.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {e["chief_complaint_tag"]: e["guideline"] for e in entries}


def all_diseases() -> Dict[str, dict]:
    return _load_diseases()


def disease_by_id(disease_id: str) -> Optional[dict]:
    return _load_diseases().get(disease_id)


def diseases_for_tag(chief_complaint_tag: str) -> List[dict]:
    """Every disease whose chief_complaint_tags includes this tag -- the candidate pool
    differential.py ranks from. Not itself RAG (always on): this is the deterministic clinical
    knowledge base, not a prompt-context optimization."""
    return [d for d in _load_diseases().values() if chief_complaint_tag in d.get("chief_complaint_tags", [])]


def critical_condition_ids() -> List[str]:
    return list(_load_red_flags().get("critical_diagnosis_ids", []))


def vital_sign_red_flags() -> List[dict]:
    return list(_load_red_flags().get("vital_sign_red_flags", []))


def demographic_risk_rules() -> List[dict]:
    return list(_load_demographic_and_medication_risk().get("demographic_risk_rules", []))


def medication_risk_rules() -> List[dict]:
    return list(_load_demographic_and_medication_risk().get("medication_risk_rules", []))


def retrieve_guideline(chief_complaint_tag: str) -> Optional[str]:
    """RAG-gated: one short guideline sentence for the current chief complaint, or None if RAG is
    disabled / no guideline is on file. This is the only piece of prose text ever added to a
    prompt from the knowledge base -- kept to a single sentence by design."""
    if not get_config().rag_enabled:
        return None
    return _load_guidelines().get(chief_complaint_tag)


def retrieve_test_notes(test_ids: List[str]) -> List[str]:
    """RAG-gated: short clinical notes for the specific tests currently being considered (top-K
    only, never the whole notes.json)."""
    if not get_config().rag_enabled:
        return []
    notes = _load_test_notes()
    top_k = get_config().rag_top_k
    return [notes[t] for t in test_ids[:top_k] if t in notes]


def retrieve_turn_context(chief_complaint_tag: str, top_diagnosis_ids: List[str],
                           candidate_test_ids: List[str]) -> List[dict]:
    """One call that assembles everything a single turn's LLM reasoning call should see from the
    knowledge base (spec section 13): the chief-complaint guideline sentence, plus notes for only
    the tests actually under consideration this turn -- never the whole knowledge base, and only
    when NOVA_RAG_ENABLED is true. Each entry carries `source` so provenance is traceable
    (spec section 13's "retrieval 결과에는 source metadata를 유지한다")."""
    if not get_config().rag_enabled:
        return []
    snippets: List[dict] = []
    guideline = retrieve_guideline(chief_complaint_tag)
    if guideline:
        snippets.append({"source": f"guideline:{chief_complaint_tag}", "text": guideline})
    for diagnosis_id in top_diagnosis_ids[:3]:
        entry = disease_by_id(diagnosis_id)
        if entry and entry.get("urgency") in {"CRITICAL", "MEDIUM"} and entry.get("dangerous"):
            snippets.append({
                "source": f"disease:{diagnosis_id}",
                "text": f"{entry['name']} is {entry.get('urgency', 'LOW').lower()} urgency; "
                        f"dangerous if missed. Key discriminators: "
                        f"{', '.join(entry.get('typical_features', [])[:3]) or 'none listed'}.",
            })
    for note in retrieve_test_notes(candidate_test_ids):
        snippets.append({"source": "diagnostic_tests", "text": note})
    return snippets[: get_config().rag_top_k]
