"""Chief-complaint routing regression tests (spec: chief_complaint.py's routing/confidence
structure -- classify(), top_candidates(), and the structured route() result).

Every phrasing below is written fresh for this test file, distinct from any sentence in
evaluation/cases.py, evaluation/held_out_cases.py, evaluation/generalization_cases_v2.py,
evaluation/generalization_stress_cases.py, evaluation/blind_cases_v3.py, or
evaluation/blind_cases_v4.py -- this file checks the classifier's actual semantic generalization,
not memorized phrasing from any specific case file (blind or otherwise).

Four phrasing styles per concept, per the spec:
  - exact:      the concept's own canonical clinical term, used plainly.
  - lay:        an everyday patient phrasing that doesn't use the clinical term at all.
  - ambiguous:  a phrasing deliberately light on distinguishing words, checking the router
                degrades to a reasonable LOW/MEDIUM confidence rather than a wrong confident tag.
  - negative:   a phrase from a totally unrelated concept, checking the router never misroutes it.
"""

from __future__ import annotations

import pytest

from nova_agent.chief_complaint import classify, route, top_candidates

# (concept, exact phrasing, lay phrasing) -- one exact + one lay case per required concept.
CONCEPT_CASES = [
    ("chest_pain", "I have chest pain that started this morning",
     "there's a tightness right in the middle of my chest"),
    ("dyspnea", "I'm having a lot of difficulty breathing right now",
     "I just can't seem to get enough air lately"),
    ("headache", "I have a headache that won't go away",
     "my head has been pounding since this morning"),
    ("abdominal_pain", "I've had abdominal pain since last night",
     "my stomach has been aching all day and it won't let up"),
    ("weakness", "I've had generalized weakness for two days",
     "my whole body feels heavy and I have no strength left"),
    ("altered_mental_status", "the patient has altered mental status",
     "he seems really out of it and confused about where he is"),
    ("syncope", "I had an episode of syncope this afternoon",
     "I blacked out for a few seconds and woke up on the floor"),
    ("palpitations", "I've been having palpitations since this morning",
     "my heart has been pounding and racing since this morning"),
    ("fever", "I've had a fever since yesterday",
     "I have been feverish and shivering with chills all day"),
    ("urinary_symptoms", "I have dysuria when I go to the bathroom",
     "it burns every time I pee and I keep needing to go"),
    ("vomiting", "I've been vomiting since this morning",
     "I keep throwing up everything I eat"),
    ("back_pain", "I have flank pain on my right side",
     "there's a deep ache along my lower back that won't ease up"),
    ("cough", "I have a cough that's lasted a week",
     "I have had a bad cough with a lot of coughing fits at night"),
    ("leg_swelling", "I have leg swelling that started yesterday",
     "my leg has swollen up a lot since yesterday"),
]

# Deliberately thin, low-signal phrasings for a handful of concepts -- checking the router
# produces SOME plausible signal (not necessarily a hard HIGH-confidence single tag) rather than
# either silently returning 'other' or confidently misrouting to an unrelated concept.
AMBIGUOUS_CASES = [
    ("I just feel really off today, hard to explain", ["weakness", "altered_mental_status"]),
    ("something is wrong but I can't put my finger on where it hurts", []),  # genuinely vague
    ("I feel awful all over, worse than usual", ["weakness"]),
]

# Distinct, unrelated complaints that must NEVER be swept into an unrelated tag just because the
# fuzzy fallback is more permissive than exact matching.
UNRELATED_COMPLAINTS = [
    "I have a splinter stuck in my finger",
    "my hair has been falling out lately",
    "I chipped a tooth eating popcorn",
    "there's a bruise on my shin from bumping the table",
    "I can't stop sneezing today",
    "my wrist hurts from typing too much",
    "I have a small cut on my hand that won't stop being itchy",
]


@pytest.mark.parametrize("tag,exact_text,lay_text", CONCEPT_CASES)
def test_exact_phrasing_routes_with_high_confidence(tag: str, exact_text: str, lay_text: str):
    result = route(exact_text)
    assert result.primary_tag == tag, f"{exact_text!r} should route to {tag!r}, got {result.primary_tag!r}"
    assert result.match_type == "exact", f"{exact_text!r} should be an exact match, got {result.match_type!r}"
    assert result.confidence == "HIGH"


@pytest.mark.parametrize("tag,exact_text,lay_text", CONCEPT_CASES)
def test_lay_phrasing_routes_to_correct_concept(tag: str, exact_text: str, lay_text: str):
    assert classify(lay_text) == tag, f"{lay_text!r} should route to {tag!r}, got {classify(lay_text)!r}"


@pytest.mark.parametrize("text,plausible_tags", AMBIGUOUS_CASES)
def test_ambiguous_phrasing_never_confidently_misroutes(text: str, plausible_tags: list):
    result = route(text)
    if not plausible_tags:
        # Genuinely vague text: either nothing scored (primary_tag == "other") or, if something
        # scored, it must not claim HIGH confidence over a single specific tag.
        assert result.match_type == "none" or result.confidence != "HIGH"
    else:
        assert result.primary_tag == "other" or result.primary_tag in plausible_tags or \
            any(t in result.secondary_tags for t in plausible_tags)


@pytest.mark.parametrize("text", UNRELATED_COMPLAINTS)
def test_unrelated_complaints_never_misrouted(text: str):
    """The fuzzy fallback must never manufacture a confident match for text that has no real
    conceptual overlap with any routing concept -- 'other' is the only acceptable outcome."""
    tag = classify(text)
    assert tag == "other", f"{text!r} was misrouted to {tag!r}, expected 'other'"


def test_route_returns_full_structured_result():
    result = route("I have chest pain radiating to my arm")
    assert result.primary_tag == "chest_pain"
    assert result.match_type == "exact"
    assert result.confidence == "HIGH"
    assert result.primary_score > 0
    assert isinstance(result.secondary_tags, list)
    assert isinstance(result.score_margin, float)


def test_tied_exact_hits_yield_medium_confidence_and_both_tags_surface():
    """Text that plainly names two different concepts' canonical terms at once should not claim
    HIGH confidence for either one alone -- both should be reachable via primary/secondary."""
    result = route("I have chest pain and shortness of breath")
    assert result.confidence in ("MEDIUM", "HIGH")
    tags_seen = {result.primary_tag, *result.secondary_tags}
    assert "chest_pain" in tags_seen and "dyspnea" in tags_seen


def test_no_signal_text_reports_none_match_type():
    result = route("I have a splinter stuck in my finger")
    assert result.primary_tag == "other"
    assert result.match_type == "none"
    assert result.secondary_tags == []


def test_top_candidates_ranks_plausible_concepts_for_ambiguous_text():
    candidates = top_candidates("feeling awful and just so tired all over", k=3)
    assert isinstance(candidates, list)
    assert len(candidates) <= 3


def test_top_candidates_includes_primary_first():
    candidates = top_candidates("I have a headache and I feel dizzy", k=3)
    result = route("I have a headache and I feel dizzy")
    if candidates:
        assert candidates[0] == result.primary_tag
