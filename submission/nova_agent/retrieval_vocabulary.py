"""Round U follow-up: bounded retrieval vocabulary for what the patient actually said.

The chief complaint is usually lay wording ("short of breath", "I passed out", "가슴 통증") while the catalog is
written in clinical phrases ("dyspnea", "syncope", "chest pain"). This module maps observed text to EXISTING
knowledge-base phrases only, through two existing, already-reviewed vocabularies:

  * the feature-local lay aliases (matching.FEATURE_ALIASES, which merges lay_language.py) -- an alias is
    accepted only when it is literally/strictly present, not negated and attributed to the patient; and
  * the existing Korean/Japanese concept table (multilingual_concepts.english_evidence_for).

No free text is generated, no diagnosis label is produced or looked up, no truth/case information is used, and
nothing is weighted by danger. The result is capped and deterministic; it only adds terms to the existing
"symptom" retrieval signal (Weighted RRF and the Top150 / diagnostic Top25 sizes are unchanged).
"""
from __future__ import annotations

import functools
from typing import Dict, List, Tuple

MAX_TERMS = 8


@functools.lru_cache(maxsize=1)
def _alias_index() -> Dict[str, Tuple[Tuple[str, str, frozenset], ...]]:
    from nova_agent.matching import FEATURE_ALIASES, _content_words
    index: Dict[str, list] = {}
    for phrase, aliases in FEATURE_ALIASES.items():
        # Negative-form KB phrases ("no fever") are reassurances, not retrieval terms.
        if phrase.startswith(("no ", "not ", "without ")):
            continue
        for alias in aliases:
            words = frozenset(_content_words(alias.lower()))
            if not words or not alias.isascii():
                continue
            key = min(words)
            index.setdefault(key, []).append((phrase, alias, words))
    return {k: tuple(v) for k, v in index.items()}


@functools.lru_cache(maxsize=4096)
def observed_vocabulary_terms(text: str) -> Tuple[str, ...]:
    """Existing KB phrases whose lay alias / localized wording is actually present (not negated) in ``text``."""
    if not text or len(text.strip()) < 3:
        return ()
    from nova_agent.matching import _content_words, _strict_alias_present
    from nova_agent.multilingual_concepts import english_evidence_for
    from nova_agent.evidence_scope import patient_evidence_text
    # Only the patient's own, current statements (a relative's or past illness is not this complaint).
    text = patient_evidence_text(text, allow_historical=False)
    if not text or not text.strip():
        return ()
    found: List[str] = [t for t in english_evidence_for(text)]
    words = _content_words(text.lower())
    hits = []
    for word in words:
        for phrase, alias, alias_words in _alias_index().get(word, ()):
            if alias_words <= words and phrase not in found and phrase not in hits \
                    and _strict_alias_present(alias, [text], scrub_negated_spans=True):
                hits.append(phrase)
    # More specific (longer) phrases first; deterministic ties.
    hits.sort(key=lambda p: (-len(p.split()), p))
    for phrase in hits:
        if phrase not in found:
            found.append(phrase)
    return tuple(found[:MAX_TERMS])
