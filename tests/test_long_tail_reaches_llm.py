"""End-to-end: a long-tail Tier-2 ontology candidate must survive the full pipeline --
retrieval -> rerank -> candidate_generator pool -> DifferentialEngine.update()'s FINAL
DifferentialItem list -- which is exactly what nova_agent.clinical_summary.build_clinical_summary()
serializes into the LLM-facing text (its `top_differential` section iterates the full differential
list it's given, uncapped internally). Reaching that final differential list is therefore the
correct, direct proxy for "reaches the LLM context" without needing a live LLM call."""

from __future__ import annotations

import os

import pytest

from nova_agent.clinical_summary import build_clinical_summary
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.state import PatientState


@pytest.fixture(autouse=True)
def _isolated_config():
    saved_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(saved_env)
    get_config(reload=True)


def _competition_state(chief_complaint: str) -> PatientState:
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "150"
    os.environ["NOVA_RERANK_TOP_K"] = "25"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)
    return PatientState(case_id="long-tail-test", chief_complaint=chief_complaint)


def test_an_ontology_sourced_candidate_reaches_the_final_differential_and_the_llm_text():
    state = _competition_state("progressive hearing loss and ringing in the ears with vertigo")
    differential = DifferentialEngine().update(state)

    ontology_items = [d for d in differential if d.diagnosis_id.startswith("onto::")]
    assert ontology_items, "an ontology-sourced (long-tail) candidate must reach the final differential"

    summary = build_clinical_summary(state, differential, safety_findings=[])
    prompt_text = summary.to_text()
    for item in ontology_items:
        assert item.diagnosis in prompt_text, (
            f"{item.diagnosis!r} reached the differential but not the LLM-facing prompt text"
        )
        assert any(item.diagnosis in line and "[ontology/" in line for line in summary.top_differential)


def test_disabled_competition_retrieval_never_introduces_ontology_candidates_into_the_differential():
    os.environ["NOVA_LLM_PROVIDER"] = "mock"
    os.environ.pop("NOVA_COMPETITION_RETRIEVAL", None)
    get_config(reload=True)
    state = PatientState(case_id="legacy-test",
                          chief_complaint="progressive hearing loss and ringing in the ears with vertigo")
    differential = DifferentialEngine().update(state)
    assert not any(d.diagnosis_id.startswith("onto::") for d in differential)
