"""Round E: matching.py's `_stem()` no longer falls back to truncating an unmatched word to its
first 6 characters -- that fallback could silently equate two otherwise-UNRELATED words that merely
share a prefix. These negative controls prove unrelated, same-first-characters words stay distinct
(they are returned unchanged, never truncated into equality), independent of any blind evaluation
set -- chosen specifically because each pair WOULD have collided under the old 6-character
truncation but must not collide now.
"""

from __future__ import annotations

import pytest

from nova_agent.matching import _stem, feature_present

# (word_a, word_b) pairs that share a >=6-character prefix (so the OLD truncation fallback would
# have equated them) but are clinically/semantically unrelated words with no real suffix
# relationship -- must stem to DIFFERENT values now that truncation is gone.
UNRELATED_LONG_PREFIX_PAIRS = [
    ("generic", "generalized"),
    ("several", "severely"),
    ("continue", "continent"),
    ("respond", "responsible"),
    ("cardiac", "cardiology"),
    ("abdomen", "abdominal"),
]


@pytest.mark.parametrize("word_a,word_b", UNRELATED_LONG_PREFIX_PAIRS)
def test_unrelated_words_with_shared_long_prefix_stay_distinct(word_a, word_b):
    stem_a, stem_b = _stem(word_a), _stem(word_b)
    assert stem_a != stem_b, (
        f"{word_a!r} and {word_b!r} are unrelated (no real suffix relationship) but share a "
        f"6+ character prefix -- the removed truncation fallback would have wrongly equated them "
        f"as {stem_a!r}"
    )


def test_no_truncation_fallback_conflates_unrelated_clinical_terms_in_practice():
    # "cardiac" (a KB phrase's own adjective) must never spuriously match a finding whose only
    # overlap is the unrelated, longer word "cardiology" (a department/specialty noun, not a
    # clinical finding).
    assert feature_present("cardiac arrest", ["referred to cardiology for a routine follow-up"]) is False


def test_exertional_exertion_irregular_pair_still_normalizes_via_explicit_override():
    # The one genuine irregular derivational pair this module's suffix rules can't connect on
    # their own -- handled by a tightly-scoped explicit override (_IRREGULAR_STEM_OVERRIDES), never
    # by a blanket truncation fallback.
    assert _stem("exertional") == _stem("exertion")
    assert feature_present("exertional chest pain", ["chest pain that gets worse with exertion"]) is True


def test_unmatched_word_with_no_suffix_rule_returns_the_original_unchanged():
    # A word with no matching suffix rule and no explicit override must round-trip unchanged --
    # never truncated to a fixed character count, regardless of length.
    assert _stem("aortic") == "aortic"
    assert _stem("pericardial") == "pericardial"
    assert _stem("tachycardia") == "tachycardia"


# Round E: making feature_present()'s EXACT/substring tier word-boundary-safe (closing the "PE"/
# "period" short-alias false-positive class -- see test_feature_match_generic_word_collision.py)
# also, as a side effect, closed off a case that tier used to cover by ACCIDENT: a plain unbounded
# `"fever" in "...feverish..."` substring match. That is a real, legitimate clinical variant (the
# "-ish" adjectival suffix on a symptom word: feverish, bluish, yellowish), so it now needs its own
# explicit, general suffix rule in _SUFFIX_RULES rather than silently regressing. Discovered via
# this round's own generalization regression suite (evaluation.generalization_cases_v2's
# AbdominalPain03_YoungAdultAppendicitis case), fixed generically (a suffix RULE, not a case-
# specific patch) and verified with fresh pairs here, independent of any blind/dev case wording.
ISH_SUFFIX_PAIRS = [
    ("feverish", "fever"),
]


@pytest.mark.parametrize("derived,base", ISH_SUFFIX_PAIRS)
def test_ish_adjectival_suffix_normalizes_to_its_base_clinical_word(derived, base):
    assert _stem(derived) == _stem(base)


def test_feverish_satisfies_a_bare_fever_typical_feature():
    assert feature_present("fever", ["no appetite, felt a little feverish, nauseous"]) is True


def test_ish_suffix_rule_does_not_introduce_an_unrelated_collision():
    # "selfish"/"finish" share the "-ish" suffix but their stems ("self"/"fin") must not
    # accidentally satisfy an unrelated clinical phrase.
    assert feature_present("self harm", ["patient describes feeling selfish about asking for help"]) is False
