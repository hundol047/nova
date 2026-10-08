"""Round P (NOVA_DOCUMENTED_DX): a diagnosis the patient reports as DOCUMENTED by a clinician.

"My referral letter mentions Meniere disease", "the GP says it's atrial fibrillation", "I was diagnosed with gout"
are genuine clinical information (a known diagnosis from a prior assessment), not a guess. When such a statement
names a condition in the static catalog EXACTLY (canonical name or listed synonym, whole words), that condition is
brought into the candidate pool and receives one feature's worth of support labelled "documented diagnosis".

Guards: the documentation framing must be present in the same clause; a clause carrying uncertainty or denial
("worried it might be", "ruled out", "not", "no") never counts; history-only framing is not required, because a
documented diagnosis is usually the reason for the visit. The patient's own speculation never counts.
PROVENANCE: engineering-authored wording rules; not clinician-reviewed.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List, Tuple

_FRAMING = re.compile(
    r"\b(?:referral|referred|clinic letter|letter|discharge (?:summary|letter)|records?|my notes|the notes|"
    r"(?:my|the) (?:doctor|gp|specialist|consultant|cardiologist|neurologist|hospital))\b[^.;]{0,40}?"
    r"\b(?:mentions?|mentioned|says?|said|states?|stated|lists?|listed|wrote|noted|told me|diagnosed)\b|"
    r"\bdiagnosed with\b|\bdiagnosis of\b|진단(?:을)? ?받|진단서", re.IGNORECASE)
_UNCERTAIN = re.compile(r"\b(?:worried|afraid|might|maybe|could be|wonder\w*|possible|possibly|suspect\w*|rule out|"
                        r"ruled out|not|no|never|unlikely|whether)\b", re.IGNORECASE)
_CLAUSE = re.compile(r"[.;\n]")
_HISTORY_ONLY = re.compile(r"\b(?:as a (?:child|kid|teenager)|years ago|in the past|used to|grew out of|resolved)\b", re.IGNORECASE)
_MIN_NAME_LEN = 5


@lru_cache(maxsize=1)
def _name_index() -> Tuple[Tuple[str, str], ...]:
    """(lower-case name, candidate id) for every KB disease name/alias and every catalog concept name/synonym."""
    names: Dict[str, str] = {}
    from nova_agent.knowledge.retrieval import all_diseases
    for entry in all_diseases().values():
        for name in [entry.get("name", "")] + list(entry.get("aliases", [])):
            for variant in {name, re.sub(r"\s*\(.*?\)", "", name)}:
                if len(variant.strip()) >= _MIN_NAME_LEN:
                    names.setdefault(variant.strip().lower(), entry["id"])
    try:
        from nova_agent.ontology.registry import get_default_catalog
        for concept in get_default_catalog().all_concepts():
            for name in [concept.canonical_name] + list(getattr(concept, "aliases", []) or []):
                if name and len(name.strip()) >= _MIN_NAME_LEN:
                    names.setdefault(name.strip().lower(), f"onto::{concept.concept_id}")
    except Exception:
        pass
    # longest first, so "acute pericarditis" wins over "pericarditis"
    return tuple(sorted(names.items(), key=lambda kv: -len(kv[0])))


def documented_diagnosis_ids(texts: List[str]) -> List[str]:
    """Candidate ids named as a clinician-documented diagnosis in `texts` (order of first mention)."""
    from nova_agent.config import get_config
    if not get_config().documented_dx_enabled:
        return []
    found: List[str] = []
    for text in texts:
        for clause in _CLAUSE.split(text or ""):
            if not _FRAMING.search(clause) or _UNCERTAIN.search(clause) or _HISTORY_ONLY.search(clause):
                continue
            low = clause.lower()
            taken: List[Tuple[int, int]] = []
            for name, cid in _name_index():
                start = low.find(name)
                while start != -1:
                    end = start + len(name)
                    boundary = (start == 0 or not low[start - 1].isalnum()) and (end == len(low) or not low[end].isalnum())
                    if boundary and not any(a < end and start < b for a, b in taken):
                        taken.append((start, end))
                        if cid not in found:
                            found.append(cid)
                        break
                    start = low.find(name, start + 1)
    return found
