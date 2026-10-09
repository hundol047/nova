"""Development contrasts: source/subject/capability, never a case-id ranking patch."""
import pytest

from nova_agent.evidence_scope import evidence_clauses, patient_evidence_text
from nova_agent.state import PatientState
from nova_agent.matching import feature_present, feature_present_with_aliases
from nova_agent.clinical_concepts import canonical_findings_for
from nova_agent.clinical_presentation import build_clinical_presentation
from nova_agent.differential import DifferentialEngine
from nova_agent.final_decision import decide_final
from nova_agent.disposition import disposition_for


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo(); get_config(reload=True)


@pytest.mark.parametrize('text',[
    'My sister has an irregular heartbeat. I have a sore finger.',
    'I have a sore finger, but my brother has an irregular heartbeat.',
    '아버지는 irregular heartbeat가 있습니다. 저는 손가락이 아파요.',
    'A colleague had an irregular heartbeat years ago.',
    'My neighbor has an irregular heartbeat.',
    'My father had fever and cough; he also had an irregular heartbeat.',
])
def test_other_subject_cannot_supply_patient_support(text):
    s=PatientState(chief_complaint=text, preliminary_rules=True)
    for matcher in (feature_present, feature_present_with_aliases):
        assert not matcher('irregular heartbeat', [text], scrub_negated_spans=True)
        assert not matcher('irregular heartbeat', s.all_findings_text(include_family=False), scrub_negated_spans=True)
    # Vocabulary normalization does not assign a subject. State projection
    # must precede it for real clinical observations.
    assert 'irregular heartbeat' not in canonical_findings_for(patient_evidence_text(text))
    d=DifferentialEngine().update(s)
    assert not any('irregular heartbeat' in x.supporting_evidence for x in d)
    final=decide_final(s,d,'information_exhausted')
    assert final.primary_id!='cardiac_arrhythmia'


@pytest.mark.parametrize('text',[
    'My sister has a cough but I have an irregular heartbeat.',
    'My dad had fever and I now have an irregular heartbeat.',
    'My father says I have an irregular heartbeat.',
    '어머니는 열이 있어요. 저는 irregular heartbeat가 있어요.',
    'My mother has a rash; my irregular heartbeat started today.',
])
def test_explicit_patient_switch_preserved(text):
    assert feature_present_with_aliases('irregular heartbeat',[text],scrub_negated_spans=True)
    s=PatientState(chief_complaint=text)
    d=DifferentialEngine().update(s)
    assert any('irregular heartbeat' in x.supporting_evidence for x in d)


@pytest.mark.parametrize('text',[
    'I had an irregular heartbeat years ago.',
    '저는 과거에 irregular heartbeat가 있었어요.',
])
def test_past_symptom_is_context_not_current_observation(text):
    s=PatientState(chief_complaint=text)
    assert 'irregular heartbeat' in patient_evidence_text(text,allow_historical=True)
    assert 'irregular heartbeat' not in patient_evidence_text(text,allow_historical=False)
    assert not any('irregular heartbeat' in x.supporting_evidence for x in DifferentialEngine().update(s))
    assert s.chief_complaint==text


def test_clause_provenance_keeps_original_offsets_and_family_list():
    text='My aunt had cough and fever years ago; now I have nausea.'
    clauses=evidence_clauses(text,source='associated_symptoms')
    assert all(text[c.span[0]:c.span[1]]==c.text and c.source=='associated_symptoms' for c in clauses)
    assert any(c.experiencer=='FAMILY' and c.temporality=='HISTORICAL' for c in clauses)
    projected=patient_evidence_text(text,allow_historical=False)
    assert len(projected)==len(text) and 'nausea' in projected
    assert 'cough' not in projected and 'fever' not in projected


def test_unbound_pronoun_requires_source_context():
    assert evidence_clauses('Her speech is slurred.',default_subject='UNSPECIFIED')[0].experiencer=='UNSPECIFIED'
    s=PatientState(chief_complaint='Observation by caregiver')
    s.record_exam('neuro_exam','Her speech is slurred.')
    assert 'slurred speech' in s.objective_findings_text()


def test_volunteered_relative_and_patient_in_one_answer():
    text='My brother has an irregular heartbeat and I have nausea.'
    s=PatientState(chief_complaint='Sore finger')
    s.record_ask('associated_symptoms','Other symptoms?',text)
    assert any('irregular heartbeat' in t for t in s.family_history)
    assert any('nausea' in t for t in s.pertinent_positives)
    assert not any('irregular heartbeat' in t for t in s.pertinent_positives)
    assert s.conversation_history[-1].result==text


@pytest.mark.parametrize('text',[
    'Passing urine stings.', 'I pass urine in small amounts.',
    'I can pass urine normally.', 'I cannot walk, but I can pass urine.',
    'I have difficulty starting to pass urine.', 'No inability to pass urine.',
    'I am not unable to pass urine.', 'I cannot say whether I can pass urine.',
])
@pytest.mark.parametrize('matcher',[feature_present,feature_present_with_aliases])
def test_voiding_is_not_inability(text,matcher):
    assert not matcher('unable to pass urine',[text],scrub_negated_spans=True)


@pytest.mark.parametrize('text',['I am unable to pass urine.','I cannot pass urine.','Inability to pass urine.'])
@pytest.mark.parametrize('matcher',[feature_present,feature_present_with_aliases])
def test_real_inability_is_preserved(text,matcher):
    assert matcher('unable to pass urine',[text],scrub_negated_spans=True)


def test_dysuria_reaches_routing_and_candidate_without_retention_support():
    s=PatientState(chief_complaint='Passing urine stings. I need to go repeatedly.',preliminary_rules=True)
    assert 'dysuria' in canonical_findings_for(s.chief_complaint)
    assert 'urinary_symptoms' in build_clinical_presentation(s).symptoms
    d=DifferentialEngine().update(s)
    assert any(x.diagnosis_id=='uncomplicated_cystitis' for x in d)
    assert not any('unable to pass urine' in x.supporting_evidence for x in d)


@pytest.mark.parametrize('text',['I blacked out while seated.','I nearly fainted.','I lost consciousness while seated.'])
def test_rate_concern_is_urgent_without_claiming_a_rhythm_cause(text):
    s=PatientState(chief_complaint=text,preliminary_rules=True)
    s.record_initial_vitals('BP 118/70, HR 39, RR 16, Temp 36.6, SpO2 98%')
    d=DifferentialEngine().update(s);final=decide_final(s,d,'information_exhausted')
    assert final.primary_id not in {'cardiac_arrhythmia','onto::tier2:ventricular_tachycardia'}
    assert disposition_for(s,final,d).urgent


@pytest.mark.parametrize('feature,text',[('syncope','My father fainted.'),('dysuria','My sister says peeing hurts.')])
def test_alias_does_not_bypass_subject_projection(feature,text):
    assert not feature_present_with_aliases(feature,[text],scrub_negated_spans=True)

@pytest.mark.parametrize('text,feature',[
    ('Sore throat and runny nose, brother has a fever.', 'sore throat'),
    ('구토와 설사가 시작됐어요, family meal last night', 'vomiting'),
])
def test_first_relative_cue_does_not_erase_preceding_patient_clause(text,feature):
    s=PatientState(chief_complaint=text)
    assert feature_present_with_aliases(feature,s.all_findings_text(include_context=False),scrub_negated_spans=True)


def test_known_illness_and_treatment_are_not_current_episode_support():
    from nova_agent.differential import DifferentialItem
    from nova_agent.final_decision import support_problems
    item=DifferentialItem(diagnosis_id='hypoglycemia',diagnosis='Hypoglycemia',score=4,rank=1,
        dangerous_if_missed=True,score_ratio=1.0,urgency='CRITICAL',confidence_band='LOW',
        supporting_evidence=['known diabetes on insulin','insulin use'])
    s=PatientState(chief_complaint='I take insulin for my diabetes.')
    assert 'no_positive_support' in support_problems(item,s,[item])
    item.supporting_evidence.append('documented diagnosis')
    assert 'no_positive_support' not in support_problems(item,s,[item])

@pytest.mark.parametrize('feature,text',[
    ('coughing up blood','Coughing up thick green sputum.'),
    ('coughed up blood','Coughed up white mucus.'),
    ('blood in urine','Urine is cloudy.'),
    ('bloody diarrhea','Watery diarrhea after lunch.'),
])
@pytest.mark.parametrize('matcher',[feature_present,feature_present_with_aliases])
def test_partial_overlap_cannot_invent_blood(feature,text,matcher):
    assert not matcher(feature,[text],scrub_negated_spans=True)

@pytest.mark.parametrize('text',['I coughed up blood.','Bloody sputum with my cough.','Hemoptysis.'])
def test_explicit_blood_remains_available_to_final_support_guard(text):
    from nova_agent.final_decision import _REQUIRED_CONTEXT
    assert _REQUIRED_CONTEXT['hemoptysis'][1](PatientState(chief_complaint=text),None)

@pytest.mark.parametrize('text,expected',[
    ('My blood pressure was recorded while I was coughing up mucus.',False),
    ('The blood sample was lost because I coughed up phlegm.',False),
    ('I coughed up a little blood.',True),
    ('The sputum contains blood.',True),
    ('I have blood-streaked phlegm.',True),
])
def test_expelled_blood_must_belong_to_the_respiratory_assertion(text,expected):
    from nova_agent.matching import feature_present
    assert feature_present('coughing up blood',[text],scrub_negated_spans=True) is expected

@pytest.mark.parametrize('dangerous',[False,True])
def test_lone_nonspecific_symptom_cannot_name_a_cause_regardless_of_danger(dangerous):
    from nova_agent.differential import DifferentialItem
    from nova_agent.final_decision import support_problems
    from nova_agent.state import PatientState
    item=DifferentialItem(diagnosis_id='pneumonia',diagnosis='Pneumonia',rank=1,score=1,
        score_ratio=.1,confidence_band='LOW',supporting_evidence=['productive cough'],
        dangerous_if_missed=dangerous,urgency='ROUTINE')
    assert 'single_nonspecific_support' in support_problems(item,PatientState(chief_complaint='Cough'),[item])
    item.supporting_evidence.append('documented diagnosis')
    assert 'single_nonspecific_support' not in support_problems(item,PatientState(chief_complaint='Cough'),[item])

@pytest.mark.parametrize('text',[
    'There is blood in my sputum.','The sputum is blood-stained.',
    'Blood was coughed up.','There is blood in the phlegm.',
])
def test_true_respiratory_blood_relations_survive_partial_match_guard(text):
    from nova_agent.matching import feature_present_with_aliases
    assert feature_present_with_aliases('coughing up blood',[text])
