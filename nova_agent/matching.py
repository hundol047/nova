"""Shared keyword/phrase overlap matching used by differential.py and safety.py to check whether a
knowledge-base feature phrase (e.g. "exertional chest pain") is supported by, or contradicted by,
the free-text findings gathered in PatientState. Deliberately simple (word-overlap + substring),
not an NLP/embedding similarity model -- keeps matching behavior stable/testable across runs.

Plain single-word overlap is too permissive for this domain: "left arm pain" and "denies
unilateral leg pain" share only the word "pain", which is generic enough to appear in almost every
finding regardless of relevance, and would otherwise register as a match. So:
  - stopwords and domain-generic words (pain, ache, discomfort, ...) never count toward overlap.
  - a short phrase (<=2 remaining content words) requires ALL of them present, not just some.
  - a longer phrase requires most (>=60%) of them present.
  - words are lightly stemmed (truncated to 6 chars) so "exertional"/"exertion" etc. still match
    without a full NLP stemmer dependency.
"""

from __future__ import annotations

import re
from typing import List, Set

_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "or", "and", "with", "is", "are", "was", "were",
    "at", "by", "for", "my", "it", "this", "that", "i", "have", "has", "no", "not", "also",
}
_GENERIC_MEDICAL_WORDS = {"pain", "ache", "aching", "discomfort", "feeling", "symptom", "symptoms", "sensation"}
_IGNORED = _STOPWORDS | _GENERIC_MEDICAL_WORDS
_OVERLAP_RATIO_THRESHOLD = 0.6


def _stem(word: str) -> str:
    return word[:6] if len(word) > 6 else word


def _content_words(text: str) -> Set[str]:
    words = re.split(r"[^a-z0-9가-힣]+", text.lower())
    return {_stem(w) for w in words if w and w not in _IGNORED}


def feature_present(feature: str, findings_text: List[str]) -> bool:
    feature_content = _content_words(feature)
    feature_lower = feature.lower()
    for finding in findings_text:
        finding_lower = finding.lower()
        if feature_lower in finding_lower or finding_lower in feature_lower:
            return True
        if not feature_content:
            continue
        overlap = feature_content & _content_words(finding)
        if len(feature_content) <= 2:
            if overlap == feature_content:
                return True
        elif len(overlap) / len(feature_content) >= _OVERLAP_RATIO_THRESHOLD:
            return True
    return False


def feature_denied(feature: str, negatives: List[str]) -> bool:
    return feature_present(feature, negatives)
