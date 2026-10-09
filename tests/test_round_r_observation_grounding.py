"""Language assertions must conserve observations and never invent a second finding."""
import pytest
from nova_agent.state import PatientState, answer_kind
from nova_agent.matching import feature_present_with_aliases
from nova_agent.multilingual_concepts import english_evidence_for

@pytest.mark.parametrize('answer,feature', [
    ("My calves have muscle cramps but I don't know the cause", 'muscle cramps'),
    ('Dysuria, frequency and urgency without vaginal discharge', 'dysuria'),
])
def test_mixed_answer_keeps_observed_positive(answer, feature):
    s=PatientState()
    s.record_ask('associated_symptoms','Any other symptoms?',answer)
    assert answer_kind(answer) is None
    assert feature_present_with_aliases(feature,s.all_findings_text(),scrub_negated_spans=True)
    assert not any(feature_present_with_aliases(feature,[n]) for n in s.pertinent_negatives)

def test_drug_is_preserved_when_dose_is_unknown():
    s=PatientState()
    s.record_ask('medication','What medicines do you take?',"I take furosemide but I cannot remember the dose")
    assert len(s.medications)==1 and 'furosemide' in s.medications[0].name
    assert s.unknown_findings

def test_disjunctive_yes_is_not_two_observations():
    s=PatientState()
    s.record_ask('associated_symptoms:vomiting or diarrhea','Vomiting or diarrhea?','Yes')
    assert s.ambiguous_findings == ['vomiting or diarrhea']
    assert not s.question_observed('associated_symptoms:vomiting or diarrhea')
    assert not feature_present_with_aliases('vomiting',s.all_findings_text())
    assert not feature_present_with_aliases('diarrhea',s.all_findings_text())
    assert s.conversation_history[-1].result=='Yes'

def test_muscle_cramp_is_not_a_seizure_but_separate_seizure_survives():
    assert 'seizure' not in english_evidence_for('종아리에 근육 경련이 있어요')
    assert 'muscle cramps' in english_evidence_for('종아리에 근육 경련이 있어요')
    assert 'seizure' in english_evidence_for('근육 경련이 있었어요. 이후 전신 경련이 있었어요.')

@pytest.mark.parametrize('text,present', [
    ('I am urinating repeatedly and my stomach has pain',False),
    ('I have pain when urinating',True),
    ('It burns when I pee',True),
])
def test_urinary_pain_requires_a_relation(text,present):
    assert feature_present_with_aliases('pain on urinating',[text]) is present

@pytest.mark.parametrize('text', [
    'I urinate repeatedly and my stomach has pain',
    'There is stomach pain and I am urinating repeatedly',
])
def test_urinary_alias_cannot_create_an_infection_source(text):
    assert not feature_present_with_aliases('suspected infection source',[text])

@pytest.mark.parametrize('text', ['I nearly fainted','I almost passed out','near syncope'])
def test_presyncope_is_not_loss_of_consciousness(text):
    assert not feature_present_with_aliases('syncope',[text])
    assert not feature_present_with_aliases('brief loss of consciousness',[text])

def test_separate_actual_faint_survives_presyncope_filter():
    assert feature_present_with_aliases('syncope',['Yesterday I nearly fainted; today I passed out'])

def test_later_observation_replaces_an_unknown_exam_result():
    s=PatientState()
    s.record_exam('cardiac_auscultation','Not assessed.')
    assert not s.exam_observed('cardiac_auscultation')
    s.record_exam('cardiac_auscultation','Regular rhythm, no murmur.')
    assert s.exam_observed('cardiac_auscultation')
