"""Diagnosis Normalization (spec section 14).

Follows the same explicit-reference-table, never-guess philosophy as SynexAgent's
backend/app/services/terminology_mapper.py: a diagnosis is only ever mapped to a canonical id
through a table entry (built from knowledge/diseases/*.json's `aliases` plus a small manual table
of extra abbreviations), never inferred at runtime. Anything that doesn't match comes back
unmapped, with the original text preserved, rather than silently coerced into the wrong bucket.

If the competition publishes an official final-diagnosis format (e.g. a fixed code list), that
format must be layered on top of this (or replace it) rather than this module inventing its own
submission codes -- see competition/adapter.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

from nova_agent._synex import normalize_condition
from nova_agent.knowledge.retrieval import all_diseases

# Extra abbreviations/synonyms not already captured by a knowledge/diseases/*.json `aliases` list.
# Kept tiny and explicit -- add here only, never guessed from string similarity at runtime.
EXTRA_ALIASES: Dict[str, List[str]] = {
    "acute_coronary_syndrome": ["nstemi", "stemi", "acute mi"],
    "ischemic_stroke": ["cva", "tia-like presentation"],
}


def _clean(text: str) -> str:
    # Underscore -> space BEFORE stripping punctuation: a raw disease id like
    # "acute_coronary_syndrome" (as evaluation ground-truth values use) must clean down to the
    # same string as its natural-language name "Acute Coronary Syndrome" -- \w already matches
    # underscore, so without this replacement first, the id's underscores would survive stripping
    # and never equal the space-separated alias-table key built from the same disease's name.
    text = text.replace("_", " ")
    return re.sub(r"[^\w\s]", "", text.strip().lower())


@lru_cache(maxsize=1)
def _alias_table() -> Dict[str, str]:
    """alias (cleaned) -> canonical disease id. Longest aliases are matched first by the caller,
    so a specific alias (e.g. 'acute myocardial infarction') is preferred over a shorter one that
    happens to be a substring of it."""
    table: Dict[str, str] = {}
    for disease_id, entry in all_diseases().items():
        table[_clean(entry["name"])] = disease_id
        table[_clean(disease_id.replace("_", " "))] = disease_id
        for alias in entry.get("aliases", []):
            table[_clean(alias)] = disease_id
    for disease_id, aliases in EXTRA_ALIASES.items():
        for alias in aliases:
            table[_clean(alias)] = disease_id
    return table


@dataclass
class NormalizedDiagnosis:
    raw_text: str
    canonical_id: Optional[str]
    canonical_name: Optional[str]
    mapped: bool
    codes: list


def normalize_diagnosis(text: str) -> NormalizedDiagnosis:
    if not text or not text.strip():
        return NormalizedDiagnosis(raw_text=text, canonical_id=None, canonical_name=None, mapped=False, codes=[])
    cleaned = _clean(text)
    table = _alias_table()

    if cleaned in table:
        canonical_id = table[cleaned]
    else:
        # Longest-alias-first containment match: prevents a short generic alias ("mi") from
        # matching before a longer, more specific one already ruled it out.
        canonical_id = None
        for alias in sorted(table.keys(), key=len, reverse=True):
            if alias and (alias in cleaned or cleaned in alias):
                canonical_id = table[alias]
                break

    if canonical_id is None:
        return NormalizedDiagnosis(raw_text=text, canonical_id=None, canonical_name=None, mapped=False, codes=[])

    diseases = all_diseases()
    canonical_name = diseases.get(canonical_id, {}).get("name", canonical_id)
    codes = [c.to_dict() for c in normalize_condition(canonical_name)] if normalize_condition else []
    return NormalizedDiagnosis(raw_text=text, canonical_id=canonical_id, canonical_name=canonical_name,
                                mapped=True, codes=codes)


def same_diagnosis(a: str, b: str) -> bool:
    """True if two free-text diagnosis strings normalize to the same canonical id. Two unmapped
    strings are NEVER considered equal (each is only equal to itself would be a false positive
    for evaluation scoring -- an unmapped guess must not accidentally 'match' an unmapped ground
    truth just because both failed to normalize)."""
    na, nb = normalize_diagnosis(a), normalize_diagnosis(b)
    if na.mapped and nb.mapped:
        return na.canonical_id == nb.canonical_id
    return _clean(a) == _clean(b) and bool(_clean(a))
