"""Round E, defect D, end-to-end: mixed-language presentations (Korean+English, Japanese+English)
must reach the SAME candidate-generation pipeline an English-only presentation does -- proving the
bounded multilingual concept layer (nova_agent/multilingual_concepts.py) actually closes the gap
Blind v14 exposed (Korean-mixed passed, Japanese-mixed did not), generalized to fresh diagnoses/
wording distinct from Blind v14's own mixed-language cases (which used ACS/appendicitis).
"""

from __future__ import annotations

import pytest

from nova_agent.candidate_generator import generate_candidates
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.state import PatientState

MIXED_LANGUAGE_CASES = [
    # (chief_complaint, demographics, expected_disease_id)
    ("숨이 차고 다리가 부어요, been like this since yesterday",
     {"age": 68, "sex": "male"}, "pulmonary_embolism"),
    ("下腹部に鈍い痛みがあります, comes and goes since this morning",
     {"age": 25, "sex": "female"}, "gastroenteritis"),
    ("정신을 잃었어요, felt dizzy right before it happened",
     {"age": 45, "sex": "male"}, "vasovagal_syncope"),
    ("頭が痛いです、throbbing on one side, seen this before with migraines",
     {"age": 33, "sex": "female"}, "migraine"),
]

# English-only controls for the SAME underlying concepts, to prove the multilingual layer is
# purely ADDITIVE (an English-only presentation must route exactly as it always has).
ENGLISH_CONTROL_CASES = [
    ("short of breath and my legs are swollen, been like this since yesterday",
     {"age": 68, "sex": "male"}, "pulmonary_embolism"),
    ("dull lower belly pain that comes and goes since this morning",
     {"age": 25, "sex": "female"}, "gastroenteritis"),
    ("passed out for a moment, felt dizzy right before it happened",
     {"age": 45, "sex": "male"}, "vasovagal_syncope"),
    ("throbbing headache on one side, seen this before with my migraines",
     {"age": 33, "sex": "female"}, "migraine"),
]


@pytest.mark.parametrize("chief_complaint,demographics,expected_disease_id", MIXED_LANGUAGE_CASES)
def test_mixed_language_presentation_reaches_the_expected_candidate(chief_complaint, demographics, expected_disease_id):
    state = PatientState(case_id="mixed-lang-test", chief_complaint=chief_complaint, demographics=demographics)
    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation, chief_complaint_text=chief_complaint)
    candidate_ids = {c.entry["id"] for c in candidates}
    assert expected_disease_id in candidate_ids, (
        f"{chief_complaint!r} did not reach {expected_disease_id!r} -- got {sorted(candidate_ids)}"
    )


@pytest.mark.parametrize("chief_complaint,demographics,expected_disease_id", ENGLISH_CONTROL_CASES)
def test_english_only_control_still_reaches_the_expected_candidate(chief_complaint, demographics, expected_disease_id):
    state = PatientState(case_id="en-control-test", chief_complaint=chief_complaint, demographics=demographics)
    presentation = build_clinical_presentation(state)
    candidates = generate_candidates(presentation, chief_complaint_text=chief_complaint)
    candidate_ids = {c.entry["id"] for c in candidates}
    assert expected_disease_id in candidate_ids
