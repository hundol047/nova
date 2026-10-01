"""Regression coverage for the review fixes; no blind benchmark cases are copied here."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from nova_agent.chief_complaint import route
from nova_agent.state import PatientState
from nova_agent.resolution import is_resolved, reassuring_result
from nova_agent.differential import DifferentialItem
from nova_agent.stop_policy import StopPolicy
from nova_agent.action_selector import AgentAction, ScoredCandidate
from nova_agent.llm_schema import AgentTurnOutput, SelectedActionOutput
from nova_agent.safety_validator import SafetyValidator, build_candidate_pool
from nova_agent.stop_policy import StopDecision
from evaluation.cases import SyntheticCase
from evaluation.simulator import _relevant_test_ids


@pytest.mark.parametrize('text,tag', [
    ('No chest pain but I am short of breath', 'dyspnea'),
    ('Denies fever. My speech is slurred', 'focal_neurology'),
    ('No headache; vaginal bleeding since yesterday', 'pelvic_pain'),
    ('Black stools this morning', 'gi_bleeding'),
    ('I have no energy', 'weakness'),
    ('No fever and I feel dizzy', 'dizziness'),
    ('가슴 통증은 없어요. 숨이 차요', 'dyspnea'),
])
def test_routing_affirmed_symptoms(text, tag):
    assert route(text).primary_tag == tag


def test_multiple_symptoms_do_not_become_single_high_confidence_route():
    routing = route('Chest pain and chest pressure with fever')
    assert routing.confidence != 'HIGH'
    assert 'fever' in {routing.primary_tag, *routing.secondary_tags}
    assert route('No chest pain or fever').match_type == 'none'


@pytest.mark.parametrize('result', ['', 'pending', 'not available', 'normal but inconclusive',
    'abnormal / positive', 'normal ECG with ST elevation', 'not normal', 'not negative'])
def test_workup_completion_alone_never_resolves(result):
    state = PatientState(chief_complaint='chest pain')
    state.record_test('ecg', result)
    state.record_test('troponin', result)
    assert not is_resolved('acute_coronary_syndrome', ['denies nausea'], state)


def test_unrecorded_model_claim_cannot_resolve_dangerous_diagnosis():
    state = PatientState()
    assert not is_resolved('pulmonary_embolism', ['Pulmonary embolism ruled out'], state)
    state.record_test('ct_chest_angio', 'Cannot exclude pulmonary embolism')
    assert not is_resolved('pulmonary_embolism', [], state)
    state.record_test('ct_chest_angio', 'No evidence of pulmonary embolism')
    assert is_resolved('pulmonary_embolism', [], state)


def item(did, danger=False):
    return DifferentialItem(diagnosis=did, diagnosis_id=did, rank=1, score=1,
        score_ratio=.8, confidence_band='HIGH', dangerous_if_missed=danger,
        urgency='HIGH', supporting_evidence=['observed evidence'])


def test_zero_information_gain_cannot_bypass_safety():
    state = PatientState(turn_count=5)
    decision = StopPolicy().evaluate(state, [item('gerd'), item('acute_coronary_syndrome', True)], [], 0)
    assert not decision.should_diagnose


def test_blocked_diagnosis_does_not_return_same_diagnosis():
    state = PatientState(turn_count=5)
    action = AgentAction(action_type='DIAGNOSE', key='gerd', content='GERD', rationale='test')
    output = AgentTurnOutput(selected_action=SelectedActionOutput(type='DIAGNOSE', key='gerd', content='GERD'))
    pool = build_candidate_pool([ScoredCandidate(action_type='TEST', key='ecg', content='ECG', utility=1, components={})])
    result = SafetyValidator().validate_action(state, output, pool, action,
        [item('gerd'), item('acute_coronary_syndrome', True)],
        StopDecision(should_diagnose=True, forced=False, reason='test', readiness_score=1))
    assert result.action.action_type == 'TEST'
    assert result.action.key == 'ecg'


def test_test_relevance_independent_of_agent_rankings():
    case = SyntheticCase(case_id='review', chief_complaint='headache', demographics={}, ground_truth_diagnosis='migraine')
    assert _relevant_test_ids(case) == _relevant_test_ids(case, {'acute_coronary_syndrome', 'sepsis'})
    case.relevant_test_ids = ['ecg']
    assert 'ecg' in _relevant_test_ids(case)


def test_require_real_rejects_mock():
    process = subprocess.run([sys.executable, '-m', 'evaluation.real_llm_benchmark', '--require-real', '--provider', 'mock'],
        capture_output=True, text=True)
    assert process.returncode != 0
    assert 'mock is not verification' in process.stderr


def test_no_call_is_not_a_verified_competition_case(monkeypatch):
    from competition.adapter import NovaCompetitionAgent, RealLLMUnavailableError
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'competition')
    get_config(reload=True)
    class NoCallAgent(DoctorAgent):
        def decide(self, state):
            return AgentAction(action_type='DIAGNOSE', key='gerd', content='GERD', rationale='test'), None, []
    from nova_agent.llm_client import MockLLMClient
    agent = NovaCompetitionAgent(NoCallAgent(llm_client=MockLLMClient()))
    try:
        with pytest.raises(RealLLMUnavailableError):
            agent.act({'case_id':'zero', 'observation_type':'initial', 'chief_complaint':'chest pain'})
    finally:
        monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
        get_config(reload=True)

@pytest.mark.parametrize('text,expected', [('potassium 6.8',6.8), ('K+ 6.5 mmol/L',6.5),
    ('K: 4.2 mEq/L',4.2), ('potassium 3.5-5.0',None), ('potassium 7.2 mg/dL',None),
    ('potassium 7.2 hemolyzed sample',None), ('previous potassium 8.0',None)])
def test_potassium_values_units_and_unreliable_samples(text, expected):
    from nova_agent.electrolyte_evidence import extract_potassium_mmol_l
    assert extract_potassium_mmol_l(text) == expected


def test_objective_potassium_survives_unrelated_symptom_denial():
    from nova_agent.differential import DifferentialEngine
    state = PatientState(chief_complaint='weakness')
    state.record_test('bmp', 'potassium 6.8 mmol/L')
    state.record_test('ecg', 'peaked T waves')
    state.record_ask('associated_symptoms', 'Any other symptoms?', 'No confusion or seizures')
    result = DifferentialEngine().update(state)
    assert result[0].diagnosis_id == 'severe_electrolyte_disorder'
