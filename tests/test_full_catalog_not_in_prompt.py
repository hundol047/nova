"""The entire disease catalog (1,280 real concepts, or thousands in a synthetic test-scale
catalog) must NEVER be serialized into the LLM-facing prompt text -- competition retrieval only
ever widens candidate RECALL upstream; the differential handed to build_clinical_summary() stays
bounded by the configured reasoning_top_k throughout."""

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


def test_prompt_differential_never_exceeds_reasoning_top_k_even_with_a_large_retrieval_budget():
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "200"
    os.environ["NOVA_RERANK_TOP_K"] = "30"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)

    state = PatientState(
        case_id="bound-test",
        chief_complaint="fever cough shortness of breath chest pain abdominal pain headache "
                         "dizziness rash joint pain fatigue nausea vomiting diarrhea",
    )
    differential = DifferentialEngine().update(state)
    assert len(differential) <= 25

    summary = build_clinical_summary(state, differential, safety_findings=[])
    assert len(summary.top_differential) <= 25
    # The catalog has 1,280 real concepts -- the prompt text must be a small fraction of that.
    assert len(summary.top_differential) < 1280


def test_prompt_differential_stays_at_the_legacy_size_when_competition_retrieval_is_off():
    os.environ["NOVA_LLM_PROVIDER"] = "mock"
    os.environ.pop("NOVA_COMPETITION_RETRIEVAL", None)
    get_config(reload=True)
    state = PatientState(case_id="legacy-bound-test", chief_complaint="sudden severe chest pain")
    differential = DifferentialEngine().update(state)
    assert len(differential) <= get_config().top_k_differential
