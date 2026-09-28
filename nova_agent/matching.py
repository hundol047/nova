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
_NEGATED_SPAN_PATTERN = re.compile(
    r"\b(?:no|not|denies|denied|without|absent|negative for)\s+(?:[a-z]+\s*){1,4}", re.IGNORECASE,
)


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
    return _NEGATED_SPAN_PATTERN.sub(" ", text)


def feature_present(feature: str, findings_text: List[str], scrub_negated_spans: bool = False) -> bool:
    """`scrub_negated_spans=True` is for checking against a general finding bag (e.g.
    state.all_findings_text()) that can contain an EXAM/TEST result embedding an unrelated
    negation in the same string. Leave it False (the default) when checking against
    PatientState.pertinent_negatives -- those entries ARE the negative statement itself (e.g.
    "denies chest pain"), so scrubbing them would erase the very text being matched against."""
    feature_content = _content_words(feature)
    feature_lower = feature.lower()
    for finding in findings_text:
        finding_lower = _strip_negated_spans(finding.lower()) if scrub_negated_spans else finding.lower()
        # Only the feature-contained-in-finding direction is a safe substring shortcut (a longer
        # finding sentence happens to contain the whole feature phrase verbatim, e.g. feature
        # "diaphoresis" in finding "diaphoresis, nausea, ..."). The reverse direction (finding
        # contained in feature) is NOT safe: a short, generic finding like the bare chief
        # complaint text "headache" is trivially a substring of almost any longer feature phrase
        # that happens to contain that word (e.g. "worst headache of life"), which would falsely
        # match every such feature regardless of relevance -- so it is deliberately not checked.
        if feature_lower in finding_lower:
            return True
        if not feature_content:
            continue
        overlap = feature_content & _content_words(finding_lower)
        if len(feature_content) <= 2:
            if overlap == feature_content:
                return True
        elif len(overlap) / len(feature_content) >= _OVERLAP_RATIO_THRESHOLD:
            return True
    return False


def feature_denied(feature: str, negatives: List[str]) -> bool:
    return feature_present(feature, negatives)


# Feature-local aliases (spec section 6, Option A): alternate phrasings tried ONLY when evaluating
# the ONE exact knowledge-base phrase they are keyed to -- never a global finding-text substitution
# like the earlier clinical_synonyms.py attempt (reverted after it let unrelated findings that
# merely shared a word-group cross-contaminate each other's matches, e.g. "mild fever" spuriously
# supporting "denies high fever"). A lay phrase here can only ever help the ONE named KB phrase.
# Shared here (not duplicated in differential.py and candidate_generator.py separately) so an
# aliased risk_factor/typical_feature/history phrase behaves identically whether it is being
# scored (differential.py's own _score_disease) or being used to decide candidate POOL MEMBERSHIP
# in the first place (candidate_generator.py's risk_match/medication_match/history_match) -- these
# two call sites diverging was a real bug (a diagnosis reachable ONLY through an aliased
# risk/medication phrase, e.g. "aspirin" for the KB's own "antiplatelet use", could score correctly
# once present, but never actually ENTER the pool via that alias in the first place). Two
# categories populate this table: (1) common lay-language variants of a clinical sign
# (throbbing/pulsating, sensitive to light/photophobia) and (2) high-value medication-class/
# condition-name normalization (spec section 4) -- a specific drug name or plain-English condition
# name standing in for the canonical risk factor phrase it belongs to. Deliberately NOT a general
# medication/condition NLP system: only classes/conditions an existing knowledge-base
# risk_factor/typical_feature already names.
FEATURE_ALIASES: dict[str, list[str]] = {
    "unilateral pulsating headache": ["throbbing headache", "pounding headache", "one-sided headache",
                                       "one sided headache", "pounding pain", "throbbing pain",
                                       "pulsating pain"],
    "photophobia": ["sensitive to light", "light sensitivity", "light bothers me"],
    "phonophobia": ["sensitive to sound", "sound sensitivity", "noise bothers me"],
    "aura": ["shimmering lights", "visual aura", "flashing lights", "seeing spots before",
             "zigzag lines", "blind spot in my vision", "jagged lines"],
    "recurrent similar episodes": ["similar to headaches", "happened before", "same as before",
                                    "feels the same as last time", "this feels the same",
                                    "gets these", "a few times a year", "has had these before"],
    "family history of migraine": ["mother gets migraines", "father gets migraines",
                                    "mother has migraines", "parent gets migraines", "runs in my family",
                                    "sister gets migraines", "sister has migraines", "brother gets migraines"],
    "known migraine history": ["diagnosed with migraines", "history of migraines", "has migraines before"],
    "syncope": ["passed out", "fainted"],
    "palpitations": ["racing heartbeat", "heart racing"],
    # Medication-class normalization (spec section 4).
    "sulfonylurea use": ["glipizide", "glyburide", "glimepiride", "sulfonylurea"],
    "insulin use": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "known diabetes on insulin": ["insulin", "lantus", "humalog", "novolog", "glargine"],
    "anticoagulant use": ["warfarin", "apixaban", "rivaroxaban", "dabigatran", "heparin", "coumadin"],
    "antiplatelet use": ["aspirin", "clopidogrel"],
    "nsaid use": ["ibuprofen", "naproxen", "nsaid"],
    "diuretic use": ["water pill", "furosemide", "hydrochlorothiazide", "lasix"],
    "immunosuppressant use": ["prednisone", "methotrexate", "tacrolimus", "cyclosporine", "azathioprine"],
    "oral contraceptive use": ["birth control", "oral contraceptive", "the pill"],
    "missed meal": ["hasn't eaten", "hasn't eaten much", "poor oral intake", "not eating today",
                     "skipped a meal", "skipped meals"],
    # Common lay/plain-English terms for a risk_factor a KB entry names by its clinical term
    # (spec section 4's medication-class normalization, generalized to a few very common
    # condition-name risk factors) -- scoped to the ONE named risk_factor phrase each, same
    # discipline as every alias above, never a general finding-text substitution.
    "hyperlipidemia": ["high cholesterol", "elevated cholesterol", "high blood cholesterol", "high lipids"],
    "hypertension": ["high blood pressure", "elevated blood pressure"],
    "poorly controlled hypertension": ["poorly controlled high blood pressure", "uncontrolled blood pressure",
                                        "uncontrolled hypertension", "high blood pressure that's not controlled"],
    "atrial fibrillation": ["afib", "a-fib", "irregular heart rhythm", "irregular heartbeat history"],
    "immobilization": ["long flight", "long car ride", "bed rest", "recent long travel", "sitting for hours"],
    "long travel": ["long flight", "long car ride", "recent long trip"],
    "liver disease": ["cirrhosis", "hepatitis", "liver problems"],
    "peptic ulcer disease": ["stomach ulcer", "ulcer history", "history of ulcers"],
}


def feature_present_with_aliases(phrase: str, findings: List[str], scrub_negated_spans: bool = True) -> bool:
    """feature_present() on `phrase` itself, OR on any of its feature-local aliases (see
    FEATURE_ALIASES above) -- the alias never widens matching for any OTHER knowledge-base phrase.
    The single shared entry point for alias-aware matching; both differential.py's scoring and
    candidate_generator.py's pool-membership checks call this rather than plain feature_present()
    directly, so a diagnosis reachable only through an aliased phrase behaves identically at both
    stages."""
    if feature_present(phrase, findings, scrub_negated_spans=scrub_negated_spans):
        return True
    for alias in FEATURE_ALIASES.get(phrase.lower(), ()):
        if feature_present(alias, findings, scrub_negated_spans=scrub_negated_spans):
            return True
    return False
