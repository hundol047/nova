"""The 7 new chief-complaint routing domains added by Round D's systematic Tier-1 taxonomy audit
(upper_respiratory, diarrhea, numbness, vision_changes, neck_stiffness, hemoptysis, seizure): each
must (a) actually route a plain presenting-complaint sentence to its own tag, and (b) actually
reach candidate generation -- i.e. at least one real Tier-1 disease's own `chief_complaint_tags`
lists it, so the tag isn't merely a label that routes to nothing in the candidate pool
(diseases_for_tag() returning empty would mean the routing "success" is cosmetic only).
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import route
from nova_agent.knowledge.retrieval import diseases_for_tag

NEW_DOMAIN_CASES = [
    ("my nose is completely stuffed up and my throat is scratchy", "upper_respiratory"),
    ("I've had watery diarrhea since last night", "diarrhea"),
    ("my left hand has been numb since this morning", "numbness"),
    ("my vision went blurry all of a sudden", "vision_changes"),
    ("my neck is so stiff I can't turn my head", "neck_stiffness"),
    ("I coughed up blood this morning", "hemoptysis"),
    ("she had a seizure that lasted about a minute", "seizure"),
]


@pytest.mark.parametrize("text,expected_tag", NEW_DOMAIN_CASES)
def test_new_domain_routes_to_its_own_tag(text, expected_tag):
    result = route(text)
    assert result.primary_tag == expected_tag
    assert result.match_type != "none"


@pytest.mark.parametrize("text,expected_tag", NEW_DOMAIN_CASES)
def test_new_domain_tag_reaches_at_least_one_real_disease(text, expected_tag):
    diseases = diseases_for_tag(expected_tag)
    assert diseases, (
        f"{expected_tag!r} routes successfully but no Tier-1 disease's own chief_complaint_tags "
        "lists it -- the routing tag never reaches candidate generation at all"
    )
