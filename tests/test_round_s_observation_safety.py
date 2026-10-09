"""Round S development contracts: observation fidelity, not case-label tuning."""
from types import SimpleNamespace
import pytest
from nova_agent.state import PatientState, answer_kind
from nova_agent.matching import feature_present, feature_present_with_aliases
from nova_agent.clinical_concepts import canonical_findings_for
from nova_agent.differential import DifferentialEngine
from nova_agent.disposition import disposition_for
from nova_agent.final_decision import decide_final
from nova_agent.history_followup import followup_questions
from nova_agent.soap import build_soap

@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1')
    monkeypatch.setenv('NOVA_LLM_PROVIDER','mock')
    get_config(reload=True)
    yield
    monkeypatch.undo();get_config(reload=True)

@pytest.mark.parametrize('matcher',[feature_present, feature_present_with_aliases])
@pytest.mark.parametrize('text',[
    'I was not sweating, frightened, or standing up.',
    'No lightheadedness, chest pressure, or nausea.',
    'I am standing up for a photograph. Yesterday I was dizzy in bed.',
    'Dizziness is constant; standing up has no effect.',
])
def test_posture_is_not_a_bag_of_tokens(matcher,text):
    assert not matcher('lightheadedness on standing up',[text],scrub_negated_spans=True)
    assert 'lightheadedness on standing up' not in canonical_findings_for(text)

@pytest.mark.parametrize('text',[
    'Lightheadedness on standing up.',
    'I feel dizzy when I stand up.',
    'When I get up, I feel woozy.',
    'Standing up makes me lightheaded.',
    '일어설 때 어지러워요.',
])
def test_postural_relationship_is_preserved(text):
    assert feature_present('lightheadedness on standing up',[text],scrub_negated_spans=True)
    assert 'lightheadedness on standing up' in canonical_findings_for(text)

@pytest.mark.parametrize('feature',['fever','cough','nausea'])
def test_denied_list_has_one_scope(feature):
    assert not feature_present(feature,['I have no fever, cough, or nausea.'],scrub_negated_spans=True)

@pytest.mark.parametrize('text',['No fever, but I have nausea.','No fever, I have nausea.',
    'No fever, has nausea.','No fever; nausea persists.'])
def test_explicit_positive_clause_survives(text):
    assert feature_present('nausea',[text],scrub_negated_spans=True)
    assert not feature_present('fever',[text],scrub_negated_spans=True)

@pytest.mark.parametrize('answer',['I cannot tell you that.','I cannot say.','I would rather not answer.',
    'I prefer not to answer.','그건 알 수 없어요.','답변을 할 수 없어요.'])
@pytest.mark.parametrize('key',['family_history','medication','allergy','aggravating'])
def test_unknown_never_becomes_risk_drug_or_modifier(answer,key):
    s=PatientState(chief_complaint='Routine visit',preliminary_rules=True)
    s.record_ask(key,'Please describe.',answer)
    assert answer_kind(answer)=='unknown'
    assert not s.question_observed(key)
    assert not s.medications and not s.allergies and not s.family_history
    assert not s.pertinent_positives and not s.pertinent_negatives
    assert not any(answer in t for t in s.all_findings_text())
    assert answer in s.conversation_history[-1].result

@pytest.mark.parametrize('answer',['I cannot lift my right arm.','I cannot breathe comfortably.',
    'I take indapamide, but I cannot tell you the dose.'])
def test_real_content_is_not_unknown(answer):
    assert answer_kind(answer) is None

def test_mixed_drug_and_unknown_preserves_only_known_drug():
    s=PatientState(chief_complaint='Weakness')
    s.record_ask('medication','Medicines?','I take indapamide, but I cannot tell you the dose.')
    assert len(s.medications)==1 and 'indapamide' in s.medications[0].name
    assert s.unknown_findings

def state(text,hr):
    s=PatientState(chief_complaint=text,preliminary_rules=True)
    s.record_initial_vitals(f'BP 116/72, HR {hr}, RR 16, Temp 36.5, SpO2 98%')
    return s

@pytest.mark.parametrize('hr',[38,47,158])
def test_marked_rate_with_blackout_cannot_end_in_routine_plan(hr):
    s=state('I blacked out while sitting. I was not hot, anxious, or standing up.',hr)
    d=DifferentialEngine().update(s);f=decide_final(s,d,'information_exhausted')
    assert not any('lightheadedness on standing up' in x.supporting_evidence for x in d)
    assert f.primary_id not in {'orthostatic_hypotension','onto::tier2:orthostatic_hypotension','vasovagal_syncope','onto::tier2:ventricular_tachycardia'}
    disposition=disposition_for(s,f,d)
    assert disposition.urgent and 'unexplained_symptomatic_marked_rate' in disposition.reasons
    assert 'emergency' in build_soap(s,d,final=f)['P'].lower()
    assert not s.laboratory_tests

def test_rate_alone_does_not_invent_symptoms_or_subtype():
    from nova_agent.disposition import symptomatic_rate_concern
    assert not symptomatic_rate_concern(state('Routine athlete review. No dizziness, fainting, or blackout.',46))

def test_weak_rank_can_get_discriminating_history_from_real_rate_symptom_cluster():
    s=state('I feel lightheaded.',43)
    item=SimpleNamespace(diagnosis_id='cardiac_arrhythmia',rank=7,supporting_evidence=['pulse rate below 50'])
    assert 'associated_symptoms:loss of consciousness' in followup_questions(s,item)
    s.record_ask('associated_symptoms:loss of consciousness','Did you lose consciousness?','I cannot say.')
    assert 'associated_symptoms:loss of consciousness' not in followup_questions(s,item)

def test_generic_headache_danger_is_not_automatic_emergency():
    s=state('Dull pressing bilateral headache. No nausea, vomiting, or visual symptoms.',72)
    d=DifferentialEngine().update(s);f=decide_final(s,d,'information_exhausted')
    assert 'bilateral band-like pressure' in s.all_findings_text()
    assert not disposition_for(s,f,d).urgent

def test_mapped_exam_coverage_from_question_only(monkeypatch):
    from nova_agent.resolution import workup_coverage
    monkeypatch.setattr('nova_agent.missing_info._resolve_entry',lambda _: {'discriminating_questions':['associated_symptoms:murmur']})
    s=state('Breathless',72)
    assert 'cardiac_auscultation' in workup_coverage('synthetic',s)['pending']
    s.record_exam_rejected('cardiac_auscultation')
    assert 'cardiac_auscultation' in workup_coverage('synthetic',s)['rejected']
    s.record_exam('cardiac_auscultation','Soft systolic murmur')
    c=workup_coverage('synthetic',s)
    assert 'cardiac_auscultation' in c['observed'] and not c['disease_excluded']

@pytest.mark.parametrize('family,expected',[
    ('My father had a heart attack at 42.',True),
    ('My father has a rash.',False),
    ('I cannot tell you that.',False),
    ('No family history of heart attacks.',False),
])
def test_generic_family_risk_needs_relevant_content(family,expected):
    from nova_agent.differential import _score_disease
    from nova_agent.knowledge.retrieval import disease_by_id
    s=state('Tired',70);s.record_ask('family_history','Family illness?',family)
    assert ('family history' in _score_disease(disease_by_id('acute_coronary_syndrome'),s)[2]) is expected

@pytest.mark.parametrize('text',[
    '일어설 때 어지럽지 않아요.',
    '일어날 때 어지러움이 없어요.',
])
def test_korean_denied_postural_symptom_is_not_expanded(text):
    assert 'lightheadedness on standing up' not in canonical_findings_for(text)
    assert not feature_present('lightheadedness on standing up',[text],scrub_negated_spans=True)

@pytest.mark.parametrize('procedure,text,present',[
    ('ct_chest_angio','Definite right upper lobar filling defect.',True),
    ('ct_chest_angio','Filling defect in a segmental artery.',True),
    ('ct_chest_angio','No right upper lobar filling defect.',False),
    ('ct_chest_angio','Possible right upper lobar filling defect.',False),
    ('ct_chest_angio','Motion artifact mimics a segmental filling defect.',False),
    ('ct_chest_angio','Aortic filling defect at a segmental branch.',False),
    ('ct_abdomen','Filling defect in a segmental artery.',False),
])
def test_actual_procedure_context_and_assertion(procedure,text,present):
    s=PatientState(chief_complaint='Breathless')
    s.record_test(procedure,text)
    feature='filling defect in the pulmonary artery'
    assert (feature in s.objective_findings_text()) is present

def test_reported_study_is_not_observed_study():
    s=PatientState(chief_complaint='My friend had a segmental filling defect.')
    assert 'filling defect in the pulmonary artery' not in s.objective_findings_text()

@pytest.mark.parametrize('target,denial',[
    ('sudden onset dyspnea','no sudden onset rapid regular palpitations'),
    ('pain worse lying flat or breathing in','no pain eased by leaning forward'),
])
def test_negation_cannot_borrow_other_symptoms_qualifiers(target,denial):
    from nova_agent.matching import feature_denied,explicitly_denied_in_findings
    assert not feature_denied(target,[denial])
    assert not explicitly_denied_in_findings(target,[denial])

def test_absence_sign_does_not_negate_a_following_observation():
    from nova_agent.matching import explicitly_denied_in_findings
    text='Absent breath sounds on the left and tracheal deviation.'
    assert not explicitly_denied_in_findings('tracheal deviation',[text])
    assert feature_present('tracheal deviation',[text],scrub_negated_spans=True)

def test_denying_absent_sounds_cannot_confirm_absent_sounds():
    from nova_agent.differential import _score_phrase
    positive,negative,missing=[],[],[]
    score=_score_phrase('absent breath sounds',2.5,['Clear breath sounds bilaterally.'],
                        ['denies absent breath sounds'],positive,negative,missing,objective=True)
    assert score < 0 and not positive and negative==['absent breath sounds']

@pytest.mark.parametrize('feature',['fever','cough','nausea'])
def test_distributed_denial_is_retained_as_negative_evidence(feature):
    from nova_agent.matching import feature_denied
    assert feature_denied(feature,['no fever, cough or nausea'])

def test_distribution_is_not_temporal_spreading():
    assert not feature_present('pain spreading across abdomen',['Pain across my abdomen is severe.'],scrub_negated_spans=True)
    assert feature_present('pain spreading across abdomen',['Pain is spreading across my abdomen.'],scrub_negated_spans=True)

def test_posture_suffix_belongs_to_preceding_measurement():
    from nova_agent.clinical_concepts import orthostatic_drop
    assert orthostatic_drop('BP 134/82 lying, 104/66 standing')
    assert not orthostatic_drop('BP 124/78 lying, 126/80 standing')

def test_positive_absence_sign_is_supported_without_negating_next_sign():
    from nova_agent.differential import _score_phrase
    positive,negative,missing=[],[],[]
    assert _score_phrase('absent breath sounds',2.5,
        ['Absent breath sounds on the left and tracheal deviation.'],[],positive,negative,missing,objective=True)==2.5
    assert positive==['absent breath sounds'] and not negative

def test_postposed_not_found_does_not_make_a_positive_sign():
    assert not feature_present('absent breath sounds',['Absent breath sounds were not found.'],scrub_negated_spans=True)

def test_explicit_no_nausea_still_supports_the_absence_feature():
    from nova_agent.differential import _score_phrase
    p,n,m=[],[],[]
    assert _score_phrase('no nausea',1.0,[],['no nausea'],p,n,m)==1.0
    assert p==['no nausea'] and not n

def test_bare_no_to_conjunction_does_not_deny_each_component():
    s=state('Pain on urinating',76)
    s.record_ask('associated_symptoms:fever and chills','Fever and chills?','No.')
    assert s.action_outcomes[-1].status=='UNKNOWN'
    assert not s.pertinent_negatives
    assert 'fever and chills' in s.unknown_findings

def test_bare_denial_cannot_erase_measured_fever():
    s=PatientState(chief_complaint='Flank pain',preliminary_rules=True)
    s.record_initial_vitals('BP 124/78, HR 95, Temp 38.7')
    s.record_ask('associated_symptoms:fever or chills','Fever or chills?','No.')
    assert not s.pertinent_negatives
    assert any('conflicting' in f for f in s.unknown_findings)
    assert 'Fever' in s.vital_sign_findings

@pytest.mark.parametrize('feature',['sudden onset dyspnea','sudden onset palpitations'])
def test_shared_onset_does_not_create_a_different_symptom(feature):
    assert not feature_present_with_aliases(feature,['sudden onset severe headache'])
    assert feature_present_with_aliases(feature,[feature])

def test_generic_symptom_denial_stays_in_the_bounded_symptom_evidence_class():
    from nova_agent.differential import _score_disease, CONTRADICTION_PENALTY
    entry={'id':'synthetic_pattern','typical_features':['distinctive scarlet markings','coarse silver scales',
          'vomiting','unilateral swelling'],'risk_factors':[],'confirmatory_findings':[]}
    s=PatientState(chief_complaint='distinctive scarlet markings; coarse silver scales')
    original=_score_disease(entry,s)[0]
    s.pertinent_negatives=['no vomiting']
    score,_,_,contra,_=_score_disease(entry,s)
    assert 'vomiting' in contra
    assert original-CONTRADICTION_PENALTY < score < original
    # A specific contradiction remains full-strength, outside the symptom cap.
    s.pertinent_negatives=['no unilateral swelling']
    assert _score_disease(entry,s)[0]==pytest.approx(original-CONTRADICTION_PENALTY)

def test_objective_confirmation_still_outranks_symptom_pattern_with_generic_denial():
    from nova_agent.differential import _score_disease
    s=PatientState(chief_complaint='distinctive scarlet markings; coarse silver scales')
    s.pertinent_negatives=['no vomiting']
    s.laboratory_tests['marker']='diagnostic marker positive'
    symptoms={'id':'synthetic_pattern','typical_features':['distinctive scarlet markings','coarse silver scales','vomiting'],
              'risk_factors':[],'confirmatory_findings':[]}
    objective={'id':'synthetic_objective','typical_features':[],'risk_factors':[],
               'confirmatory_findings':['diagnostic marker positive']}
    assert _score_disease(objective,s)[0] > _score_disease(symptoms,s)[0]

def test_a_conflict_with_observed_symptom_keeps_the_full_penalty():
    from nova_agent.differential import _score_disease, CONTRADICTION_PENALTY
    entry={'id':'synthetic_conflict','typical_features':['distinctive scarlet markings','coarse silver scales',
          'vomiting'],'risk_factors':[],'confirmatory_findings':[]}
    s=PatientState(chief_complaint='distinctive scarlet markings; coarse silver scales; vomiting')
    before=_score_disease(entry,s)[0]
    s.pertinent_negatives=['no vomiting']
    after=_score_disease(entry,s)[0]
    assert after <= before-CONTRADICTION_PENALTY

def test_undifferentiated_soap_does_not_claim_missing_information_is_none():
    s=state('Dizziness',76)
    ds=DifferentialEngine().update(s)
    final=decide_final(s,ds,'information_exhausted')
    assert final.undifferentiated
    soap=build_soap(s,ds,final=final)
    assert 'Missing discriminating evidence: none' not in soap['A']
