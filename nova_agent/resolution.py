"""Conservative, observation-grounded resolution for the synthetic competition agent.

Normal minimum-workup results are an internal heuristic, not a clinical rule-out
protocol. Missing, positive and indeterminate results never count as exclusions.
LLM-authored contradictions alone cannot discharge an unresolved diagnosis.
"""
from __future__ import annotations
import re
from functools import lru_cache
from typing import List
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.state import PatientState

_UNCERTAIN = re.compile(r"\b(pending|unknown|unavailable|inconclusive|indeterminate|equivocal|borderline|insufficient|not performed|not available|cannot exclude|can't exclude|not ruled out)\b", re.I)
_NORMAL = re.compile(r"\b(normal|negative|unremarkable|within normal limits)\b", re.I)
_ABNORMAL = re.compile(r"\b(abnormal|positive|elevated|decreased|increased|ST elevation|ST depression)\b", re.I)


def required_workup(diagnosis_id: str) -> List[str]:
    entry = disease_by_id(diagnosis_id)
    if not entry:
        return []
    return entry.get("minimum_workup") or (list(entry.get("discriminating_exams", [])) + list(entry.get("discriminating_tests", [])))


def reassuring_result(text: str) -> bool:
    """Only an explicit, unambiguous normal/negative observation is reassuring."""
    if not text or _UNCERTAIN.search(text):
        return False
    # 'not normal' and 'not negative' are not reassuring.
    if re.search(r"\b(?:not|no)\s+(?:normal|negative)\b", text, re.I):
        return False
    return bool(_NORMAL.search(text)) and not _ABNORMAL.search(text)


@lru_cache(maxsize=128)
def _exclusion_pattern(diagnosis_id: str):
    entry = disease_by_id(diagnosis_id)
    names = ([entry["name"], entry["id"].replace("_", " ")] + entry.get("aliases", [])) if entry else [diagnosis_id.removeprefix("novel:").replace("_", " ")]
    names = [re.escape(name) for name in names if len(name) >= 4]
    if not names:
        return None
    name = "(?:" + "|".join(names) + ")"
    return re.compile(rf"\b(?:ruled out|no evidence of)\s+{name}\b|\b{name}\s+(?:is |was |has been )?ruled out\b", re.I)


def is_resolved(diagnosis_id: str, contradictory_evidence: List[str], state: PatientState) -> bool:
    """Resolution is based on recorded objective results, never a model's assertion."""
    results = {**state.physical_examinations, **state.laboratory_tests, **state.imaging}
    entry = disease_by_id(diagnosis_id)
    expanded = bool(entry and entry.get('evidence_rules'))
    if expanded:
        allowed = {rule['source'] for rule in entry['evidence_rules']}
        results = {key: value for key, value in results.items() if key in allowed}
    pattern = _exclusion_pattern(diagnosis_id)
    if pattern:
        for text in results.values():
            if text and not _UNCERTAIN.search(text) and pattern.search(text):
                return True
    if expanded:
        # A generic normal result is not a disease-specific exclusion protocol.
        return False
    required = required_workup(diagnosis_id)
    return bool(required) and all(reassuring_result(results.get(key, "")) for key in required)
