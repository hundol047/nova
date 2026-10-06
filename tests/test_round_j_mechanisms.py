"""Fresh mechanism controls; no blind answers or case IDs in the runtime."""
import pytest
from nova_agent import config
from nova_agent.differential import _score_disease, DifferentialEngine, DifferentialItem
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.state import PatientState
from nova_agent.missing_info import MissingInformationAnalyzer
from nova_agent.resolution import is_resolved

@pytest.fixture(autouse=True)
def competition(monkeypatch):
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    monkeypatch.setattr(config,'_config',None)


def test_objective_absence_is_positive_support_for_an_absence_feature():
    s=PatientState(case_id='sign',chief_complaint='breathing discomfort')
    s.record_exam('lung_auscultation','absent breath sounds; tracheal deviation')
    _,_,support,contra,_=_score_disease(disease_by_id('tension_pneumothorax'),s)
    assert 'absent breath sounds' in support
    assert 'absent breath sounds' not in contra
    s.physical_examinations['lung_auscultation']='clear breath sounds'
    assert 'absent breath sounds' not in _score_disease(disease_by_id('tension_pneumothorax'),s)[2]


def test_typical_saturation_does_not_hide_new_negative_evidence():
    entry=dict(id='synthetic',typical_features=['nausea','vomiting','fever','rash','headache'],risk_factors=[],confirmatory_findings=[])
    s=PatientState(case_id='saturation',chief_complaint='nausea vomiting fever rash headache')
    before=_score_disease(entry,s)[0]
    s.pertinent_negatives=['fever']
    assert _score_disease(entry,s)[0] <= before-1.2


def test_unavailable_result_does_not_complete_a_safety_workup():
    s=PatientState(case_id='pending',chief_complaint='chest pressure')
    s.record_test('ecg','result pending');s.record_test('troponin','sample unavailable')
    assert not is_resolved('acute_coronary_syndrome',[],s)


def test_soft_reassurance_alone_does_not_resolve_critical_alternative():
    s=PatientState(case_id='soft',chief_complaint='new unilateral weakness')
    s.record_exam('neuro_exam','normal neurological exam')
    assert not is_resolved('ischemic_stroke',['normal neurological exam'],s)


def test_later_specific_symptoms_can_introduce_a_diagnosis_outside_initial_route():
    s=PatientState(case_id='late-symptoms',chief_complaint='difficult breathing')
    s.record_ask('associated_symptoms','Additional symptoms?','tingling around the mouth or fingers')
    s.record_ask('character','Describe the feeling?','sudden onset intense anxiety or fear')
    d=DifferentialEngine().update(s)
    assert any(x.diagnosis_id=='panic_attack' and x.supporting_evidence for x in d)


def test_available_discriminator_survives_partial_negative_workup():
    s=PatientState(case_id='competing',chief_complaint='dizziness and slurred speech')
    s.record_test('ct_head','no hemorrhage');s.record_test('glucose_point_of_care','glucose 105 mg/dL')
    s.record_exam('neuro_exam','focal neurological deficit and ataxia')
    leading=DifferentialItem(diagnosis='Migraine',diagnosis_id='migraine',rank=1,score=4,score_ratio=.7,urgency='ROUTINE',dangerous_if_missed=False,confidence_band='HIGH',supporting_evidence=['headache'])
    stroke=DifferentialItem(diagnosis='Stroke',diagnosis_id='ischemic_stroke',rank=2,score=3,score_ratio=.3,urgency='CRITICAL',dangerous_if_missed=True,confidence_band='MEDIUM',supporting_evidence=['slurred speech','ataxia'])
    candidates=MissingInformationAnalyzer().analyze(s,[leading,stroke],[])
    assert any(c.key=='mri_brain' and 'ischemic_stroke' in c.disease_ids_discriminated for c in candidates)


def test_confirmatory_finding_cannot_be_earned_by_history():
    s=PatientState(case_id='history',chief_complaint='fatigue')
    s.family_history=['acute infarct and diffusion restriction']
    r=_score_disease(disease_by_id('ischemic_stroke'),s)
    assert not set(r[2]) & {'acute infarct','diffusion restriction'}


def test_unknown_unasked_absent_and_objective_contradiction_differ():
    from nova_agent.differential import _evidence_status
    e=dict(confirmatory_findings=['diagnostic marker'],discriminating_tests=['cbc'],discriminating_exams=[])
    s=PatientState(case_id='states',chief_complaint='unwell')
    assert _evidence_status(e,s,[],[],['diagnostic marker'])['diagnostic marker']=='NOT_ASKED'
    s.record_test('cbc','sample unavailable')
    assert _evidence_status(e,s,[],[],['diagnostic marker'])['diagnostic marker']=='UNKNOWN'
    assert _evidence_status(e,s,[],['rash'],[])['rash']=='ABSENT'
    s.record_test('cbc','no diagnostic marker')
    assert _evidence_status(e,s,[],['diagnostic marker'],[])['diagnostic marker']=='OBJECTIVELY_CONTRADICTED'


def test_top_competitor_split_beats_broad_shared_coverage(monkeypatch):
    import nova_agent.missing_info as mi
    entries={
        'a':dict(discriminating_tests=['ecg']),
        'b':dict(discriminating_tests=['ecg','bmp']),
        'c':dict(discriminating_tests=['ecg']),
    }
    monkeypatch.setattr(mi,'_resolve_entry',lambda did:entries.get(did))
    d=[DifferentialItem(diagnosis=i,diagnosis_id=i,rank=n,score=4-n/10,score_ratio=.5,urgency='ROUTINE',dangerous_if_missed=False,confidence_band='MEDIUM',supporting_evidence=['observed']) for n,i in enumerate(entries,1)]
    actions=mi.MissingInformationAnalyzer().analyze(PatientState(case_id='split',chief_complaint='unwell'),d,[])
    broad=next(a for a in actions if a.key=='ecg');specific=next(a for a in actions if a.key=='bmp')
    assert broad.top_competitor_separation==0
    assert specific.top_competitor_separation>0
    assert specific.specificity_gain>broad.specificity_gain
    assert specific.decision_changing_value>broad.decision_changing_value


def test_decisive_critical_alternative_blocks_stop_and_selects_its_test(monkeypatch):
    from nova_agent.action_selector import ActionSelector
    from nova_agent.stop_policy import StopPolicy
    from nova_agent.missing_info import CandidateInfo
    s=PatientState(case_id='late-confirm',chief_complaint='slurred speech and ataxia')
    s.record_test('ct_head','no hemorrhage');s.record_test('glucose_point_of_care','glucose 109 mg/dL')
    lead=DifferentialItem(diagnosis='Migraine',diagnosis_id='migraine',rank=1,score=6,score_ratio=.95,urgency='ROUTINE',dangerous_if_missed=False,confidence_band='HIGH',supporting_evidence=['headache'])
    alternative=DifferentialItem(diagnosis='Stroke',diagnosis_id='ischemic_stroke',rank=2,score=2.5,score_ratio=.12,urgency='CRITICAL',dangerous_if_missed=True,confidence_band='LOW',supporting_evidence=['ataxia','slurred speech'])
    decision=StopPolicy().evaluate(s,[lead,alternative],[],0,best_decision_value=1)
    assert not decision.should_diagnose
    action,_,_=ActionSelector().generate_and_select(s,[lead,alternative],[])
    assert action.action_type!='DIAGNOSE'
    assert any(a.key=='mri_brain' for a in MissingInformationAnalyzer().analyze(s,[lead,alternative],[]))


def test_completed_confirmatory_workup_allows_low_value_stop():
    from nova_agent.stop_policy import StopPolicy
    s=PatientState(case_id='mature',chief_complaint='chest pressure')
    s.record_test('ecg','ST elevation');s.record_test('troponin','elevated troponin')
    d=DifferentialItem(diagnosis='ACS',diagnosis_id='acute_coronary_syndrome',rank=1,score=7,score_ratio=.4,urgency='CRITICAL',dangerous_if_missed=True,confidence_band='MEDIUM',supporting_evidence=['ST elevation','elevated troponin'])
    assert StopPolicy().evaluate(s,[d],[],.05,best_decision_value=0).should_diagnose


def test_catalog_core_hit_preserves_deep_evidence_and_actions():
    from nova_agent.candidate_generator import _concept_to_kb_entry
    from nova_agent.ontology.registry import get_default_catalog
    concept=get_default_catalog().get_condition('core:ischemic_stroke')
    entry=_concept_to_kb_entry(concept)
    assert entry==disease_by_id('ischemic_stroke')
    assert entry['confirmatory_findings'] and entry['minimum_workup']


def test_source_syndrome_roles_preserve_evidence_without_causal_or_rank_claim():
    from nova_agent.syndrome_relationships import supported_source_syndrome_pairs
    def item(did,rank):
        return DifferentialItem(diagnosis=did,diagnosis_id=did,rank=rank,score=2,score_ratio=.2,urgency='URGENT',dangerous_if_missed=True,confidence_band='LOW',supporting_evidence=['observed evidence'])
    source=item('pyelonephritis',1);systemic=item('sepsis',2)
    result=supported_source_syndrome_pairs([source,systemic])
    assert len(result)==1 and result[0]['causality']=='UNCONFIRMED'
    assert (source.rank,systemic.rank)==(1,2)
    source.supporting_evidence=[]
    assert supported_source_syndrome_pairs([source,systemic])==[]
