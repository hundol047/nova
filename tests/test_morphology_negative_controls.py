"""Negative-control proof that matching.py's morphology normalizer (Round D) never conflates
unrelated words that merely share a short prefix -- the specific failure mode the naive
first-6-characters truncation predecessor was vulnerable to in the OPPOSITE direction (false
negatives on real variant pairs), and that any new stemming rule must not re-introduce in the
FALSE-POSITIVE direction instead.
"""

from __future__ import annotations

import pytest

from nova_agent.matching import feature_present, _stem

UNRELATED_WORD_PAIRS = [
    ("pain", "painting"),  # the spec's own named example of what must stay distinct
    ("need", "needle"),
    ("mass", "massage"),
    ("scar", "scarce"),
    ("rash", "rasher"),
]


@pytest.mark.parametrize("word_a,word_b", UNRELATED_WORD_PAIRS)
def test_unrelated_words_sharing_a_short_prefix_stay_distinct(word_a, word_b):
    assert _stem(word_a) != _stem(word_b), (
        f"{word_a!r} and {word_b!r} are unrelated words that happen to share a prefix -- "
        "they must never stem to the same value"
    )


def test_bleed_variant_matching_never_misfires_off_unrelated_bleak():
    assert feature_present("bleeding", ["patient describes their mood as bleak lately"]) is False


def test_needed_still_matches_need_despite_the_ed_suffix_guard():
    # "need"/"needed" is a real, legitimate -ed variant pair -- the eed-pattern guard (bleed/
    # breed/feed/need/seed/speed) must not accidentally block ordinary -ed stripping for "need"
    # itself when the KB phrase and the patient's wording differ only by that suffix.
    assert feature_present("needed", ["patient says they need help getting up"]) is True
