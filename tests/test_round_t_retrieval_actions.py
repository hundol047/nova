"""Observed concept expansion and useful actions without diagnostic danger bonuses."""
from dataclasses import replace
from unittest.mock import patch
import pytest
from nova_agent import retrieval_pipeline as rp
from nova_agent.ontology.registry import get_default_catalog
from nova_agent.open_world import OpenWorldRetriever
from nova_agent.differential import DifferentialItem
from nova_agent.missing_info import MissingInformationAnalyzer
from nova_agent.state import PatientState
from nova_agent.safety import SafetyFinding

@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER','mock');monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    get_config(reload=True)
    yield
    monkeypatch.undo();get_config(reload=True)


def item(id='acute_abdomen',support=()):
    return DifferentialItem(diagnosis_id=id,diagnosis=id,rank=1,score=3 if support else 0,
        score_ratio=1 if support else 0,supporting_evidence=list(support),urgency='CRITICAL',
        dangerous_if_missed=True,confidence_band='LOW')


def test_danger_does_not_change_diagnostic_score():
    from tests.test_reranker_topk_bound import _candidate
    low=_candidate('same',score=.7,dangerous=False)
    high=_candidate('same',score=.7,dangerous=True,urgency='CRITICAL')
    assert rp._rerank_score(low,3)==rp._rerank_score(high,3)


def test_query_expansion_is_bounded_observed_and_does_not_create_denied_or_family_signal():
    retriever=OpenWorldRetriever(get_default_catalog())
    with patch.object(retriever,'retrieve',wraps=retriever.retrieve) as lookup:
        result=rp.retrieve_high_recall(retriever,chief_complaint='Passing urine burns. My aunt has palpitations. I have no fever.')
    query=' '.join(c.args[0] for c in lookup.call_args_list if c.args[0]!='Passing urine burns. My aunt has palpitations. I have no fever.')
    assert 'dysuria' in query and 'palpitations' not in query and 'fever' not in query
    assert len(result)<=150 and len(lookup.call_args_list)<=6


def test_unmatched_wording_does_not_erase_available_bedside_examination():
    s=PatientState(chief_complaint='An unexplained sensation',preliminary_rules=True)
    actions=MissingInformationAnalyzer().analyze(s,[item()],[])
    assert any(a.action_type=='ASK' for a in actions)
    assert any(a.key=='abdominal_exam' and a.action_type=='EXAM' for a in actions)
    assert not any(a.action_type=='TEST' for a in actions)

@pytest.mark.parametrize('supported,flagged',[(True,False),(False,True)])
def test_supported_or_actively_flagged_condition_keeps_its_exam(supported,flagged):
    s=PatientState(chief_complaint='An unexplained sensation',preliminary_rules=True)
    flags=[SafetyFinding(diagnosis_id='acute_abdomen',condition='Acute abdomen',reason='observed sign',
        evidence=['guarding'],source='symptom_keyword')] if flagged else []
    actions=MissingInformationAnalyzer().analyze(s,[item(support=['guarding'] if supported else [])],flags)
    assert any(a.key=='abdominal_exam' and a.action_type=='EXAM' for a in actions)

@pytest.mark.parametrize('diagnosis,exam',[('ischemic_stroke','neuro_exam'),('acute_abdomen','abdominal_exam')])
def test_zero_score_with_actual_complaint_routing_remains_investigable(diagnosis,exam):
    s=PatientState(chief_complaint='New wording not yet matched by a scoring feature',preliminary_rules=True)
    candidate=item(diagnosis);candidate.candidate_sources=['symptom_match','safety_candidate']
    actions=MissingInformationAnalyzer().analyze(s,[candidate],[])
    assert any(a.action_type=='EXAM' and a.key==exam for a in actions)


def test_possible_caregiver_report_investigated_without_assigning_symptoms_to_patient():
    from nova_agent.clinical_presentation import build_clinical_presentation
    from nova_agent.differential import DifferentialEngine
    s=PatientState(chief_complaint="My wife's left arm went weak and her speech became slurred.",preliminary_rules=True)
    presentation=build_clinical_presentation(s)
    assert presentation.unattributed_symptoms
    differential=DifferentialEngine().update(s)
    assert not any('slurred speech' in d.supporting_evidence for d in differential)
    actions=MissingInformationAnalyzer().analyze(s,differential,[])
    assert any(a.key=='neuro_exam' for a in actions)
    s.record_exam('neuro_exam','Left arm weakness with dysarthria.')
    assert any(d.diagnosis_id=='ischemic_stroke' and d.supporting_evidence for d in DifferentialEngine().update(s))


def test_relative_and_explicit_self_complaint_is_not_a_proxy_report():
    from nova_agent.clinical_presentation import build_clinical_presentation
    s=PatientState(chief_complaint='My uncle has an irregular heartbeat. I have a sore finger.')
    assert not build_clinical_presentation(s).unattributed_symptoms


def test_addressed_minimum_workup_does_not_hide_an_unperformed_proxy_exam(monkeypatch):
    import nova_agent.resolution as resolution
    s=PatientState(chief_complaint="My wife's left arm is weak and her speech is slurred.",preliminary_rules=True)
    # 'Addressed' is a coverage decision, not evidence excluding a disease.
    monkeypatch.setattr(resolution,'is_resolved',lambda *args:True)
    first=item('cardiac_arrhythmia',support=['irregular heartbeat'])
    stroke=item('ischemic_stroke');stroke.rank=2
    actions=MissingInformationAnalyzer().analyze(s,[first,stroke],[])
    neuro=next(a for a in actions if a.action_type=='EXAM' and a.key=='neuro_exam')
    assert neuro.decision_changing_value>0
    s.record_exam('neuro_exam','Not assessed.')
    assert not s.exam_observed('neuro_exam')
    assert not any(a.key=='neuro_exam' for a in MissingInformationAnalyzer().analyze(s,[first,stroke],[]))
