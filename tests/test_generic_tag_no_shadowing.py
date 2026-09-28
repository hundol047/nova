"""Negative controls for chief_complaint.py's SPECIFICITY_PRECEDENCE mechanism (Round D): a generic
umbrella tag must remain the primary, valid routing outcome for a genuinely nonspecific
presentation -- the precedence mechanism only ever REORDERS when a specific alternative has real
signal too, it never deletes the generic tag or makes it permanently unreachable.
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import route

# Each text deliberately names ONLY the generic concept, with no specific alternative's own
# evidence present at all -- must stay generic, never spuriously promoted.
GENERIC_ONLY_CASES = [
    ("just feeling weak and tired the last couple days, nothing else", "weakness"),
    ("been feeling lightheaded and dizzy off and on all week", "dizziness"),
    ("crampy abdominal pain since this morning, no other symptoms", "abdominal_pain"),
    ("I have a bad cough that won't go away", "cough"),
]


@pytest.mark.parametrize("text,expected_generic_tag", GENERIC_ONLY_CASES)
def test_generic_tag_stays_primary_when_no_specific_alternative_has_real_signal(text, expected_generic_tag):
    result = route(text)
    assert result.primary_tag == expected_generic_tag


def test_generic_tag_is_never_removed_from_specificity_precedence_when_specific_evidence_wins():
    # Even when a specific concept IS promoted to primary (here via the sub-threshold promotion
    # path, since the generic tag's own alias match keeps match_type != "exact"), the generic tag
    # it was promoted over must still be visible as a secondary tag -- never deleted from the
    # routing result entirely.
    result = route("feeling weak, but only on my right side, and my face is drooping on that side")
    assert result.primary_tag == "focal_weakness"
    assert "weakness" in result.secondary_tags
