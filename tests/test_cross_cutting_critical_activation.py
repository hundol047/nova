"""Context-aware critical safety activation (Round E, defect B): nova_agent/contextual_safety.py's
narrow, contextually-gated activation rules, tested as a GENERAL architectural mechanism -- never
asserting on a single hardcoded case. See tests/test_reproductive_emergency_safety.py for the
ectopic-pregnancy-specific implementation of this architecture (activation conditions, resolution/
exit behavior). Fresh vignette wording, none copied from Blind v14 or any other frozen/dev set.
"""

from __future__ import annotations

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import extract_presentation
from nova_agent.contextual_safety import CONTEXTUAL_DANGEROUS_ACTIVATIONS, contextually_activated_diagnosis_ids


def test_contextual_activations_table_is_small_and_narrow_by_design():
    # The whole point of this mechanism vs. growing CROSS_CUTTING_DANGEROUS_DIAGNOSES globally:
    # stays a small, hand-curated, narrowly-gated table -- never ballooning toward "every dangerous
    # diagnosis, always active."
    assert 1 <= len(CONTEXTUAL_DANGEROUS_ACTIVATIONS) <= 10


def test_contextual_activation_reaches_candidate_generation_end_to_end():
    presentation = extract_presentation(
        "crampy lower abdominal pain, thought it was just a stomach bug",
        demographics={"age": 26, "sex": "female"},
    )
    candidates = generate_candidates(presentation)
    candidate_ids = {c.entry["id"] for c in candidates}
    assert "ectopic_pregnancy" in candidate_ids


def test_contextual_safety_is_never_a_blanket_activation_for_every_dangerous_diagnosis():
    # The mechanism must stay narrow: an unrelated presentation (a simple cough) must not pull in
    # every contextually-activatable diagnosis regardless of relevance.
    presentation = extract_presentation(
        "a dry cough for the last two days, no fever",
        demographics={"age": 26, "sex": "female"},
    )
    assert contextually_activated_diagnosis_ids(presentation) == []
