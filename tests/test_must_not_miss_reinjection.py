"""Must-not-miss preservation across the FULL competition pipeline (retrieval -> rerank ->
candidate_generator pool -> differential), on top of the unit-level reranker reinjection contract
already covered by tests/test_reranker_topk_bound.py. This is the end-to-end guarantee: enabling
high-recall retrieval must never cause a must-not-miss (CROSS_CUTTING_DANGEROUS_DIAGNOSES) or
strongly-evidenced Tier-1 diagnosis to disappear from the final differential."""

from __future__ import annotations

import os

import pytest

from nova_agent.chief_complaint import CROSS_CUTTING_DANGEROUS_DIAGNOSES
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


def _differential_ids(chief_complaint: str):
    state = PatientState(case_id="must-not-miss-test", chief_complaint=chief_complaint)
    return {d.diagnosis_id for d in DifferentialEngine().update(state)}


def test_must_not_miss_diagnoses_survive_a_full_competition_turn():
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "200"
    os.environ["NOVA_RERANK_TOP_K"] = "30"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)

    ids_present = _differential_ids("sudden severe chest pain radiating to the back")
    for must_not_miss_id in CROSS_CUTTING_DANGEROUS_DIAGNOSES:
        assert must_not_miss_id in ids_present, (
            f"{must_not_miss_id} was lost from the final differential under competition retrieval"
        )


def test_strongly_evidenced_tier1_diagnosis_survives_a_full_competition_turn():
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    os.environ["NOVA_RETRIEVAL_TOP_K"] = "200"
    os.environ["NOVA_RERANK_TOP_K"] = "30"
    os.environ["NOVA_REASONING_TOP_K"] = "25"
    get_config(reload=True)

    ids_present = _differential_ids("sudden severe chest pain radiating to the back")
    assert "aortic_dissection" in ids_present
    assert "acute_coronary_syndrome" in ids_present
