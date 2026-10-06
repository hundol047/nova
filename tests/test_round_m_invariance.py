"""Round M invariance tests: a diagnosis must not change when only the WORDING or the ORDER of the same
evidence changes (paraphrase, evidence order, knowledge-base file order, candidate order)."""

from __future__ import annotations

import itertools
import os

import pytest

from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from evaluation.simulator import run_case
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState


@pytest.fixture(autouse=True)
def _competition_config():
    saved = dict(os.environ)
    os.environ["NOVA_LLM_PROVIDER"] = "competition"
    os.environ["NOVA_COMPETITION_RETRIEVAL"] = "true"
    get_config(reload=True)
    yield
    os.environ.clear()
    os.environ.update(saved)
    get_config(reload=True)


_CASES = {c.case_id: c for c in ROUND_M_CASES}


@pytest.mark.parametrize("a,b", [("RoundM_082", "RoundM_083"), ("RoundM_086", "RoundM_087"), ("RoundM_080", "RoundM_081")])
def test_paraphrased_presentations_reach_the_same_diagnosis(a, b):
    agent = DoctorAgent()
    first = run_case(agent, _CASES[a])
    second = run_case(agent, _CASES[b])
    assert first.final_diagnosis == second.final_diagnosis, (first.final_diagnosis, second.final_diagnosis)
    assert first.correct and second.correct


def _ranking(symptoms, history):
    state = PatientState(case_id="order", chief_complaint="chest pressure")
    state.symptoms = list(symptoms)
    state.past_medical_history = list(history)
    return [(d.diagnosis_id, round(d.score, 4)) for d in DifferentialEngine().update(state)]


def test_evidence_order_does_not_change_the_ranking():
    symptoms = ["pressure when walking uphill", "sweating", "nausea", "pain spreading to the left arm"]
    history = ["smoker", "high cholesterol"]
    baseline = _ranking(symptoms, history)
    for perm in itertools.islice(itertools.permutations(symptoms), 6):
        assert _ranking(perm, history[::-1]) == baseline


def test_knowledge_base_file_order_does_not_change_the_top_of_the_ranking(monkeypatch):
    import nova_agent.candidate_generator as cg
    symptoms = ["pressure when walking uphill", "sweating", "nausea", "pain spreading to the left arm"]
    baseline = _ranking(symptoms, ["smoker"])
    original = cg.all_diseases

    def reversed_catalog():
        items = list(original().items())
        return dict(reversed(items))

    monkeypatch.setattr(cg, "all_diseases", reversed_catalog)
    shuffled = _ranking(symptoms, ["smoker"])
    assert shuffled[0] == baseline[0]
    assert {d for d, _ in shuffled[:5]} == {d for d, _ in baseline[:5]}


def test_candidate_order_does_not_change_the_top_diagnosis(monkeypatch):
    import nova_agent.differential as de
    symptoms = ["pressure when walking uphill", "sweating", "nausea", "pain spreading to the left arm"]
    baseline = _ranking(symptoms, ["smoker"])
    original = de.generate_candidates
    monkeypatch.setattr(de, "generate_candidates", lambda *a, **k: list(reversed(original(*a, **k))))
    assert _ranking(symptoms, ["smoker"])[0] == baseline[0]
