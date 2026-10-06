"""Round M: when NOTHING in the 34-disease knowledge base matches a presentation, the broad ontology
retrieval must still run (that is exactly when the true diagnosis is a long-tail concept). It used to
be skipped by candidate_generator's zero-evidence early return. Retrieval-only candidates are recall,
not evidence, so a presentation with no scored support must still be flagged zero-evidence."""

from __future__ import annotations

import os

import pytest

from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


@pytest.fixture(autouse=True)
def _isolated_config():
    saved = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved)
    get_config(reload=True)


def _state(text: str) -> PatientState:
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "150"
    os.environ["NOVA_RERANK_TOP_K"] = "25"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)
    return PatientState(case_id="kb-silent", chief_complaint=text)


def test_long_tail_candidate_is_retrieved_even_though_no_kb_disease_matches():
    differential = DifferentialEngine().update(_state("hot swollen painful joint of the big toe overnight"))
    names = [d.diagnosis for d in differential]
    assert any("Gout" in n for n in names), names


def test_unscored_presentation_is_still_flagged_zero_evidence_not_confidently_ranked():
    differential = DifferentialEngine().update(_state("zzz qqq nothing recognisable here"))
    assert differential and differential[0].fallback_candidate
