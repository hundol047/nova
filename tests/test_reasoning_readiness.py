"""Protocol regressions; invented observations here are not clinical cases."""
from nova_agent.clinical_summary import build_clinical_summary
from nova_agent.evidence_grounding import grounded_quotes, distinct_support_count
from nova_agent.state import PatientState
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_schema import AgentTurnOutput, DifferentialItemOutput, SelectedActionOutput
from nova_agent.llm_client import build_reasoning_prompt


def test_history_and_medication_survive_without_becoming_current_symptoms():
    s = PatientState(case_id='unit', chief_complaint='rash', demographics={'pregnant': False})
    for key, text in [('past_medical_history', 'Previous surgery in 2010'),
                      ('family_history', 'Father had hypertension'),
                      ('medication', 'Stopped medicine X yesterday'),
                      ('allergy', 'Penicillin caused a rash')]:
        s.record_ask(key, key, text)
    summary = build_clinical_summary(s, [], [])
    rendered = summary.to_text()
    for text in ['Previous surgery in 2010', 'Father had hypertension',
                 'Stopped medicine X yesterday', 'Penicillin caused a rash', 'not pregnant']:
        assert text in rendered
    assert 'Father had hypertension' not in summary.important_positive_findings


def test_grounding_rejects_hallucinated_negated_history_and_duplicate_fragments():
    s = PatientState(case_id='unit', chief_complaint='violet plaques. Spiral-shaped cells. No fever.')
    s.family_history = ['cough']
    assert grounded_quotes(['fever', 'cough', 'unobserved biopsy', 'violet plaques'], s, positive=True) == ['violet plaques']
    assert distinct_support_count(['violet', 'violet plaques'], s) == 1
    assert distinct_support_count(['violet plaques', 'Spiral-shaped cells'], s) == 2
    assert grounded_quotes(['no fever'], s, positive=False) == ['no fever']


class QuoteClient:
    def __init__(self, support, dangerous=False):
        self.support = support
        self.dangerous = dangerous
    def generate_turn_output(self, ctx):
        return AgentTurnOutput(differential=[DifferentialItemOutput(
            diagnosis='Protocol-only condition Z', rank=1, confidence='MEDIUM',
            supporting_evidence=self.support, dangerous_if_missed=self.dangerous)],
            selected_action=SelectedActionOutput(type='DIAGNOSE', content='Protocol-only condition Z'))


def isolated_agent(client):
    agent = DoctorAgent(llm_client=client)
    agent.differential_engine.update = lambda state: []
    agent.safety_layer.assess = lambda state, diff: []
    return agent


def test_novel_name_survives_final_gate_with_two_observed_assertions():
    agent = isolated_agent(QuoteClient(['violet plaques', 'Spiral-shaped cells'], dangerous=True))
    s = agent.new_case('unit', 'violet plaques. Spiral-shaped cells.')
    s.turn_count = 3
    action, _, _ = agent.decide(s)
    assert action.action_type == 'DIAGNOSE'
    assert action.content == 'Protocol-only condition Z'


def test_forced_novel_diagnosis_cannot_use_invented_support():
    agent = isolated_agent(QuoteClient(['unobserved biopsy', 'unobserved scan']))
    s = agent.new_case('unit', 'vague symptoms', max_turns=3)
    action, _, _ = agent.decide(s)
    assert action.content == 'unknown'


def test_forced_novel_diagnosis_keeps_dangerous_alternatives_unresolved():
    class Client(QuoteClient):
        def generate_turn_output(self, ctx):
            result = super().generate_turn_output(ctx)
            result.differential.append(DifferentialItemOutput(
                diagnosis='Protocol-only dangerous alternative Y', rank=2,
                confidence='LOW', dangerous_if_missed=True))
            return result
    agent = isolated_agent(Client(['violet plaques', 'Spiral-shaped cells']))
    s = agent.new_case('unit', 'violet plaques. Spiral-shaped cells.', max_turns=3)
    action, _, _ = agent.decide(s)
    assert action.action_type == 'DIAGNOSE'
    assert action.content == 'unknown'


def test_forced_novel_diagnosis_uses_its_own_key():
    agent = isolated_agent(QuoteClient(['violet plaques', 'Spiral-shaped cells']))
    s = agent.new_case('unit', 'violet plaques. Spiral-shaped cells.', max_turns=3)
    action, _, diff = agent.decide(s)
    assert action.content == 'Protocol-only condition Z'
    assert action.key == diff[0].diagnosis_id


def test_prompt_exposes_additional_actions_and_keeps_followup_reason():
    captured = {}
    class Client:
        def generate_turn_output(self, ctx):
            captured['prompt'] = build_reasoning_prompt(ctx)
            return AgentTurnOutput(selected_action=SelectedActionOutput(
                type='TEST', key='ct_chest_angio', content='CTA chest',
                reason='Distinguish the remaining vascular causes'))
    agent = isolated_agent(Client())
    s = agent.new_case('unit', 'unclassified symptom')
    action, _, _ = agent.decide(s)
    assert 'TEST:ct_chest_angio' in captured['prompt']
    assert action.key == 'ct_chest_angio'
    assert 'Distinguish' in action.rationale
    s.record_test('ct_chest_angio', 'source result')
    agent.decide(s)
    assert 'TEST:ct_chest_angio' not in captured['prompt']
