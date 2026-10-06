"""Direct unit tests for matching.py's conservative suffix-stripping morphology normalizer
(Round D, replacing the naive first-6-characters truncation). Covers every explicitly required
target pair, plus the pre-existing irregular-derivation pair (exertional/exertion) that has no
simple suffix relationship and must still fall back to the original truncation behavior.
"""

from __future__ import annotations

import pytest

from nova_agent.matching import feature_present

MORPHOLOGICAL_VARIANT_PAIRS = [
    ("weak", "weakness"),
    ("spin", "spinning"),
    ("bleed", "bleeding"),
    ("vomit", "vomiting"),
    ("dizzy", "dizziness"),
    ("faint", "fainting"),
    ("numb", "numbness"),
]


@pytest.mark.parametrize("base,variant", MORPHOLOGICAL_VARIANT_PAIRS)
def test_kb_base_form_matches_patient_variant_wording(base, variant):
    assert feature_present(base, [f"patient reports {variant} today"]) is True


@pytest.mark.parametrize("base,variant", MORPHOLOGICAL_VARIANT_PAIRS)
def test_kb_variant_form_matches_patient_base_wording(base, variant):
    assert feature_present(variant, [f"patient reports feeling {base}"]) is True


def test_irregular_derivation_pair_still_matches_via_truncation_fallback():
    # "exertional"/"exertion" share no simple suffix relationship any rule here handles -- must
    # still match via the original bounded first-6-characters truncation fallback, preserving
    # pre-existing behavior for pairs like this one.
    assert feature_present("exertional chest pain", ["chest pain that gets worse with exertion"]) is True
