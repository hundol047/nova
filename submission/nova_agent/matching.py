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
from nova_agent.assertion_status import is_uncertain

_STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "or", "and", "with", "is", "are", "was", "were",
    "at", "by", "for", "my", "it", "this", "that", "i", "have", "has", "no", "not", "also",
}
_GENERIC_MEDICAL_WORDS = {"pain", "ache", "aching", "discomfort", "feeling", "symptom", "symptoms", "sensation"}
_IGNORED = _STOPWORDS | _GENERIC_MEDICAL_WORDS
_OVERLAP_RATIO_THRESHOLD = 0.6

# EXAM/TEST result strings routinely embed a negation in the SAME string as a positive finding
# (e.g. "clear breath sounds, no focal consolidation") -- unlike ASK answers, this text is never
# clause-split into PatientState.pertinent_negatives at all (see state.py's _absorb_answer vs.
# record_exam/record_test), so a PLAIN feature phrase like "focal consolidation" that happens to
# appear verbatim right after a "no"/"denies"/"without" in a finding must not be treated as that
# finding affirmatively supporting it -- it's the opposite. Handled by scrubbing each negated span
# (the trigger word plus its immediate local clause) out of a finding BEFORE either the substring
# or word-overlap match is attempted, so neither path can see words that were only ever mentioned
# to be denied. Only removes the local clause, not the rest of a longer finding string, so an
# unrelated earlier/later clause in the same finding is unaffected.


def _stem(word: str) -> str:
    return word[:6] if len(word) > 6 else word


def _content_words(text: str) -> Set[str]:
    words = re.split(r"[^a-z0-9가-힣]+", text.lower())
    return {_stem(w) for w in words if w and w not in _IGNORED}


def content_word_count(text: str) -> int:
    """Public wrapper around `_content_words()` -- differential.py uses this to weight a matched
    knowledge-base phrase by its own specificity (see `_specificity_multiplier()` there)."""
    return len(_content_words(text))


def _strip_negated_spans(text: str) -> str:
    # Negation ends at a clause boundary, not an arbitrary four-word window.
    # Keep affirmative clauses after "but"/"however" rather than erasing the entire report.
    # Sentence periods are boundaries too; decimal points are not.
    clauses = re.split(r"[;,\n]|(?<=[a-z])\.(?=\s|$)|\b(?:but|however)\b", text, flags=re.I)
    positive = []
    for clause in clauses:
        if is_uncertain(clause):
            continue
        # Reports often place the negation after the finding. Scrubbing only
        # from "not" onward would leave the denied finding looking positive.
        if re.search(r"(?:\b(?:is|are|was|were)\s+|:\s*)(?:absent|negative|not (?:present|seen|detected))\b"
                     r"|\b(?:absent|not present|not seen|not detected)\s*[.!]?\s*$", clause, re.I):
            continue
        positive.append(re.sub(r"\b(?:no|not|denies|denied|without|absent|negative for)\b.*$", " ", clause, flags=re.I))
    return " ; ".join(positive)


def feature_present(feature: str, findings_text: List[str], scrub_negated_spans: bool = False, strict: bool = False) -> bool:
    """`scrub_negated_spans=True` is for checking against a general finding bag (e.g.
    state.all_findings_text()) that can contain an EXAM/TEST result embedding an unrelated
    negation in the same string. Leave it False (the default) when checking against
    PatientState.pertinent_negatives -- those entries ARE the negative statement itself (e.g.
    "denies chest pain"), so scrubbing them would erase the very text being matched against."""
    feature_content = _content_words(feature)
    feature_lower = feature.lower()
    for finding in findings_text:
        finding_lower = _strip_negated_spans(finding.lower()) if scrub_negated_spans else finding.lower()
        # A prodrome is an explicitly preceding symptom. Preserve that temporal
        # qualifier instead of requiring patients to use the word "prodrome".
        if feature_lower.startswith("prodrome of "):
            symptom = _content_words(feature_lower[len("prodrome of "):])
            for clause in re.split(r"[;,\n]", finding_lower):
                before = re.search(r"\b(?:before|preceding|prior to)\b", clause)
                if before and not re.search(r"\bafter\b", clause[:before.start()]):
                    preceding_words = _content_words(clause[:before.start()])
                    if symptom and symptom <= preceding_words:
                        return True
        # Only the feature-contained-in-finding direction is a safe substring shortcut (a longer
        # finding sentence happens to contain the whole feature phrase verbatim, e.g. feature
        # "diaphoresis" in finding "diaphoresis, nausea, ..."). The reverse direction (finding
        # contained in feature) is NOT safe: a short, generic finding like the bare chief
        # complaint text "headache" is trivially a substring of almost any longer feature phrase
        # that happens to contain that word (e.g. "worst headache of life"), which would falsely
        # match every such feature regardless of relevance -- so it is deliberately not checked.
        if re.search(r"(?<!\w)" + re.escape(feature_lower) + r"(?!\w)", finding_lower):
            return True
        if not feature_content:
            continue
        overlap = feature_content & _content_words(finding_lower)
        if strict or len(feature_content) <= 2:
            if overlap == feature_content:
                return True
        elif len(overlap) / len(feature_content) >= _OVERLAP_RATIO_THRESHOLD:
            return True
    return False


def feature_denied(feature: str, negatives: List[str]) -> bool:
    return feature_present(feature, negatives)
