"""clinical_presentation.py's multi-concept extraction (Round D): a presentation naming 2+
concurrent, distinct clinical concepts must recover ALL of them, not just the single best-scoring
tag -- so a diagnosis reachable only through the SECOND-named concept isn't silently invisible to
candidate generation just because it wasn't the top-ranked routing tag.
"""

from __future__ import annotations

import pytest

from nova_agent.clinical_presentation import extract_presentation

MULTI_CONCEPT_CASES = [
    ("bad headache, stiff neck, and a fever since this morning",
     {"headache", "neck_stiffness", "fever"}),
    ("can't stop coughing, spiking a fever, and short of breath",
     {"cough", "fever", "dyspnea"}),
    ("chest pain that comes with palpitations and feeling dizzy",
     {"chest_pain", "palpitations", "dizziness"}),
]


@pytest.mark.parametrize("text,expected_tags", MULTI_CONCEPT_CASES)
def test_all_named_concepts_are_recovered(text, expected_tags):
    presentation = extract_presentation(text)
    recovered = set(presentation.symptoms)
    missing = expected_tags - recovered
    assert not missing, f"missing concept(s) {missing} for text {text!r}; recovered={recovered}"


def test_single_concept_presentation_recovers_exactly_that_one():
    presentation = extract_presentation("burning when I pee and I keep needing to go")
    assert "urinary_symptoms" in presentation.symptoms
