"""End-to-end integration check (Round D): a chief_complaint.py routing tag must actually reach
candidate_generator.py's pool, not merely produce the right routing LABEL. A tag can route
"successfully" (route().primary_tag matches) while still surfacing NO candidates at all if the
relevant disease's own `chief_complaint_tags` in its knowledge-base JSON was never updated to
include that tag -- diseases_for_tag() would then return nothing for it. This is the specific class
of bug the routing/generalization benchmark (scripts/benchmark_chief_complaint_routing.py) checks
at scale; this file pins down a few of the new Round D tags as ordinary regression tests.
"""

from __future__ import annotations

import pytest

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.state import PatientState

END_TO_END_CASES = [
    ("my neck is so stiff I can't turn my head, and I have a fever", "meningitis"),
    ("my left hand has been numb since this morning", "ischemic_stroke"),
    ("I've had watery diarrhea since last night", "gastroenteritis"),
    ("I coughed up blood this morning", "pulmonary_embolism"),
]


@pytest.mark.parametrize("chief_complaint,expected_disease_id", END_TO_END_CASES)
def test_routed_tag_actually_reaches_the_candidate_pool(chief_complaint, expected_disease_id):
    state = PatientState(case_id="integration-test", chief_complaint=chief_complaint,
                          demographics={"age": 40, "sex": "female"})
    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation, chief_complaint_text=chief_complaint)
    candidate_ids = {c.entry["id"] for c in candidates}
    assert expected_disease_id in candidate_ids, (
        f"{chief_complaint!r} routes but {expected_disease_id!r} never reaches the candidate pool "
        f"-- got {sorted(candidate_ids)}"
    )
