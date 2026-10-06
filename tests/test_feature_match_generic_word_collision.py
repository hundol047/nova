"""Adversarial regression tests for the exact generic-word fuzzy-match collision class Round E's
feature-match specificity gate (matching.py's `_distinguishing_tokens()` +
`feature_present()`'s new gate) closes: a multi-word KB phrase dominated by low-information
relational/temporal words (after, worse, with, during, ...) must never be satisfied by unrelated
text that only shares those relational words, missing the phrase's own real distinguishing concept.

Uses fresh, independently-authored wording -- never phrases copied from Blind v14 or any other
frozen/dev evaluation set (per this round's explicit discipline: prove the ARCHITECTURAL mechanism
generically, not just make the specific Blind v14 misses pass).
"""

from __future__ import annotations

import pytest

from nova_agent.matching import feature_present

# (kb_phrase, unrelated_finding_text) pairs that MUST NOT match -- the finding shares only
# relational/generic words with the phrase, never its real distinguishing concept.
GENERIC_COLLISION_MUST_NOT_MATCH = [
    ("worse after meals", "pain that gets worse when I breathe in deeply"),
    ("chest pain after trauma", "chest pain after a long work shift"),
    ("chest pain after trauma", "chest pain after climbing several flights of stairs"),
    ("worse with exertion", "feels worse with a loud noise nearby"),
    ("no palpitations before the episode", "patient felt dizzy before the episode, denies chest pain"),
    ("worse during pregnancy", "symptoms are worse during the winter months"),
]

# The SAME phrases with real distinguishing evidence present -- must still match (the gate is
# purely additive; it must never create false NEGATIVES for genuine matches).
GENERIC_COLLISION_TRUE_POSITIVES = [
    ("worse after meals", "stomach burns and gets worse after I eat a big meal"),
    ("chest pain after trauma", "sudden chest pain that started right after the car accident, real trauma"),
    ("worse with exertion", "chest tightness that gets worse with exertion, like climbing stairs"),
]


@pytest.mark.parametrize("phrase,unrelated_text", GENERIC_COLLISION_MUST_NOT_MATCH)
def test_generic_relational_word_overlap_alone_never_satisfies_a_specific_feature(phrase, unrelated_text):
    assert feature_present(phrase, [unrelated_text]) is False, (
        f"{unrelated_text!r} must NOT satisfy {phrase!r} -- they share only generic/relational "
        "words, never the phrase's own distinguishing concept"
    )


@pytest.mark.parametrize("phrase,matching_text", GENERIC_COLLISION_TRUE_POSITIVES)
def test_genuine_match_still_works_when_the_distinguishing_concept_is_actually_present(phrase, matching_text):
    assert feature_present(phrase, [matching_text]) is True, (
        f"{matching_text!r} genuinely supports {phrase!r} (its distinguishing concept IS present) "
        "-- the new gate must never create a false negative here"
    )


# A SHORT disease-name/alias (2-4 characters, e.g. the knowledge base's own "PE", "MI", "UTI",
# "DKA", "CVA", "SAH" abbreviations, used by candidate_generator.py's history_match step and
# differential.py's own name/alias matching) is a case the distinguishing-token gate above never
# touches at all: it satisfies feature_present()'s unconditional EXACT/substring tier before that
# gate is ever reached. A naive `feature_lower in finding_lower` substring check there is exactly
# the same generic false-positive risk this round's phrase-level gate closes, just one level up --
# "PE" silently matches inside the completely unrelated word "period", and "MI" inside "family" or
# "time". Discovered independently during this round's own development-case work (a reproductive-
# age-emergency case's "period is about seven weeks late" spuriously activated pulmonary embolism's
# "PE" alias and hijacked the whole candidate pool), not copied from any blind/dev case's exact
# wording -- these are fresh pairs proving the general word-boundary fix.
SHORT_ALIAS_COLLISION_MUST_NOT_MATCH = [
    ("PE", "her period is about seven weeks late"),
    ("PE", "patient reports a strange experience last night"),
    ("MI", "no family history of heart disease"),
    ("MI", "denies taking any medication this morning"),
    ("UTI", "feels a bit beautiful today, otherwise well"),
]

SHORT_ALIAS_COLLISION_TRUE_POSITIVES = [
    ("PE", "known PE diagnosed last year, on anticoagulation"),
    ("MI", "prior MI two years ago, stents placed"),
]


@pytest.mark.parametrize("alias,unrelated_text", SHORT_ALIAS_COLLISION_MUST_NOT_MATCH)
def test_short_alias_never_matches_as_a_substring_inside_an_unrelated_word(alias, unrelated_text):
    assert feature_present(alias, [unrelated_text], scrub_negated_spans=True) is False, (
        f"{unrelated_text!r} must NOT satisfy the short alias {alias!r} -- it only appears as a "
        "substring inside an unrelated word, never as its own token"
    )


@pytest.mark.parametrize("alias,matching_text", SHORT_ALIAS_COLLISION_TRUE_POSITIVES)
def test_short_alias_still_matches_as_its_own_word(alias, matching_text):
    assert feature_present(alias, [matching_text], scrub_negated_spans=True) is True, (
        f"{matching_text!r} genuinely mentions {alias!r} as its own word -- the word-boundary fix "
        "must never create a false negative here"
    )
