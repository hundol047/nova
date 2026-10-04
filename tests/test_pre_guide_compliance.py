"""Pre-guide constraints; local mocks/stubs never certify organizer weights."""
from dataclasses import replace
import pytest
from nova_agent import config
from nova_agent.config import effective_max_turns, get_config
from nova_agent.state import PatientState
from nova_agent.orchestrator import DoctorAgent
from nova_agent.llm_client import MockLLMClient
from competition.adapter import NovaCompetitionAgent
from competition.schema import CompetitionObservation, CompetitionAction
from competition.provider_lock import enforce_submission_provider

@pytest.mark.parametrize('value,expected', [(None,60),(-2,60),(0,60),(999,60),(3,3),('12',12),('oops',60),(True,60),(2.5,60),({},60)])
def test_turn_budget_at_all_boundaries(value,expected):
    assert effective_max_turns(value)==expected
    s=PatientState(case_id='cap',chief_complaint='pain',max_turns=value)
    assert s.max_turns==expected
    s.max_turns=1000
    assert s.max_turns==60
    assert DoctorAgent(MockLLMClient()).new_case('cap','pain',max_turns=value).max_turns==expected
    assert CompetitionObservation(case_id='cap',observation_type='initial',max_turns=value).max_turns==expected

@pytest.mark.parametrize('provider',['competition','anthropic','openai_compatible','local','gemini','unknown'])
@pytest.mark.parametrize('url',['https://api.openai.com/v1','https://attacker.invalid/v1','http://127.0.0.1:8000/v1',''])
def test_submission_lock_cannot_be_redirected(monkeypatch,provider,url):
    monkeypatch.setattr(config,'_config',replace(get_config(),llm_provider=provider,competition_base_url=url))
    with pytest.raises(RuntimeError,match='EXTERNAL_OFFICIAL_INTERFACE_BLOCKED'):
        enforce_submission_provider()


def test_mock_is_local_only_and_no_weight_loading(monkeypatch):
    monkeypatch.setattr(config,'_config',replace(get_config(),llm_provider='mock'))
    enforce_submission_provider()
    monkeypatch.setattr(config,'_config',replace(get_config(),ml_ranker_enabled=True))
    with pytest.raises(RuntimeError,match='weights forbidden'): enforce_submission_provider()


def test_no_fifth_wire_action():
    with pytest.raises(ValueError):
        CompetitionAction(case_id='x',action_type='INSUFFICIENT_INFORMATION',content='x')


def test_case_isolation_both_orders_and_alone(monkeypatch):
    monkeypatch.setattr(config,'_config',replace(get_config(),llm_provider='mock',competition_retrieval_enabled=True))
    def run(order):
        adapter=NovaCompetitionAgent(DoctorAgent(MockLLMClient())); results={}
        for case in order:
            obs={'case_id':case,'observation_type':'initial','max_turns':8,
                 'chief_complaint':'crushing chest pain with sweating' if case=='A' else 'burning urination with frequency'}
            actions=[]
            for _ in range(8):
                a=adapter.act(obs); actions.append(a)
                if a['action_type']=='DIAGNOSE':break
                obs={'case_id':case,'observation_type':'ask_response','content':'Normal / negative.'}
            results[case]=actions
        return results
    ab=run('AB'); ba=run('BA'); b=run('B')
    assert ab['B']==ba['B']==b['B']
    assert ab['A']==ba['A']


def test_stale_client_success_cannot_credit_new_case():
    class Silent(MockLLMClient):
        def generate_turn_output(self,ctx):
            from nova_agent.llm_client import _deterministic_turn_output
            return _deterministic_turn_output(ctx)
    client=Silent();client._last_call_was_real=True;client._last_call_succeeded=True
    agent=DoctorAgent(client);state=agent.new_case('fresh','chest pain',max_turns=1)
    agent.decide(state)
    assert state.llm_success_count==0


@pytest.mark.parametrize("negative", ["no sweating", "without vomiting", "denies fever", "negative for rash"])
def test_comma_negation_does_not_invert_preceding_positive(negative):
    from nova_agent.state import _split_answer_segments, _segment_is_negated
    parts=_split_answer_segments("sharp abdominal pain, "+negative)
    assert parts == ["sharp abdominal pain", negative]
    assert not _segment_is_negated(parts[0]) and _segment_is_negated(parts[1])


def test_negative_list_keeps_its_scope():
    from nova_agent.state import _split_answer_segments, _segment_is_negated
    parts=_split_answer_segments("no fever, chills or cough")
    assert len(parts)==1 and _segment_is_negated(parts[0])


@pytest.mark.parametrize("name", ["Acute Pericarditis", "Hypertensive Emergency", "Herpes Zoster", "Peptic Ulcer Disease", "Pelvic Inflammatory Disease"])
def test_embedded_acronym_does_not_merge_distinct_diagnoses(name):
    from nova_agent.diagnosis_normalizer import same_diagnosis
    assert not same_diagnosis(name,"pulmonary_embolism")
    assert same_diagnosis(name,name)


def test_normalizer_preserves_explicit_acronym_but_not_partial_alias():
    from nova_agent.diagnosis_normalizer import same_diagnosis,normalize_diagnosis
    assert same_diagnosis("PE","pulmonary_embolism")
    assert not normalize_diagnosis("coronar").mapped
