"""Direct unit tests for chief_complaint.py's SPECIFICITY_PRECEDENCE mechanism (Round D): a
specific, clinically-decisive concept must outrank a generic umbrella one whenever real specific
evidence is present in the same text -- for every currently-registered precedence pair.
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import route

PRECEDENCE_CASES = [
    ("my right arm and the right side of my face suddenly went weak", "focal_weakness"),
    ("I felt dizzy and then I actually passed out for a few seconds", "syncope"),
    ("bad stomach pain, and now there's blood in my stool", "gi_bleeding"),
    ("I spit out some blood after coughing this morning", "hemoptysis"),
]


@pytest.mark.parametrize("text,expected_specific_tag", PRECEDENCE_CASES)
def test_specific_concept_outranks_generic_umbrella_when_real_evidence_present(text, expected_specific_tag):
    result = route(text)
    assert result.primary_tag == expected_specific_tag
