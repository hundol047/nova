"""New generic clinical counterfactuals and actual fixture SDK interactions.

No official case UUIDs, names, exact opening maps, keys or live model requests.
"""
import json
from types import SimpleNamespace
import pytest

from test_official_sdk_adapter import FakeServer, FakeClient, nova_sdk, engine_config
from competition.nova_sdk_adapter import OfficialEncounter, Turn
from nova_agent.state import PatientState, Demographics


@pytest.mark.parametrize('feature,report,present',[
 ('neck stiffness','경부 강직(-)',False),('neck stiffness','경부 강직(+)',True),
 ('crackles on auscultation','수포음(-/-), 천명음(-/-)',False),
 ('wheeze','천명음(-/-)',False),('tremor','손 떨림(-)',False),
 ('diffuse goiter','갑상선 미만성 비대(+), 결절(-), 압통(-)',True),
 ('diffuse goiter','갑상선 미만성 비대(-)',False),
 ('rebound tenderness','rebound insomnia',False),('rebound tenderness','rebound(+)',True),
 ('rebound tenderness','rebound(-)',False),('neck stiffness','no neck stiffness',False),
 ('crackles on auscultation','crackles are absent; tremor is present',False),
])
def test_report_notation_projects_only_actual_assertions(feature,report,present):
    from nova_agent.matching import feature_present_with_aliases
    s=PatientState(case_id='notation',chief_complaint='')
    s.record_exam('exam',report)
    assert feature_present_with_aliases(feature,s.all_findings_text(include_context=False,include_family=False),scrub_negated_spans=True)==present
    assert s.physical_examinations['exam']==report


@pytest.mark.parametrize('text,expected',[
 ('살이 빠지고 식욕이 늘었어요','increased appetite'),
 ('더위를 못 견뎌요','heat intolerance'),('손이 떨려요','tremor'),
 ('낮에 졸려요','daytime sleepiness'),('안절부절(+)','restlessness'),
 ('반사 항진(+)','hyperreflexia'),('약 복용 후 졸려요','sleepiness after medication'),
])
def test_general_korean_observations_reach_clinical_state(text,expected):
    from nova_agent.clinical_concepts import canonical_findings_for
    assert expected in canonical_findings_for(text)
    if '졸려' in text:
        s=PatientState(case_id='sleep',chief_complaint=text)
        assert 'altered mental status' not in s.all_findings_text()


@pytest.mark.parametrize('text,present',[
 ('낮에 졸려요',False),
 ('졸려하지만 대답이 늦지 않아요',False),
 ('졸려하면서 반응이 느려요',True),
])
def test_sleepiness_and_actual_slowed_responsiveness_are_distinct(text,present):
    s=PatientState(case_id='responsiveness',chief_complaint=text)
    assert ('altered mental status' in s.all_findings_text())==present


@pytest.mark.parametrize('text',[
 '어머니는 손이 떨려요','과거에는 손이 떨렸어요','손 떨림(-)',
 '졸피뎀을 안 먹어요','수면제를 복용하지 않아요',
])
def test_relative_historical_and_denied_findings_do_not_become_current(text):
    from nova_agent.clinical_concepts import canonical_findings_for
    facts=canonical_findings_for(text)
    assert 'tremor' not in facts and 'sedative use' not in facts


def clinical_encounter(history=''):
    from competition.adapter import NovaCompetitionAgent
    from nova_agent.orchestrator import DoctorAgent
    e=OfficialEncounter(FakeClient(FakeServer()),{},sleep=lambda _:None,log=lambda _:None)
    e.opening='45세 여자입니다. 잘 먹는데 체중이 줄었어요.';e.vitals='BP 118/72, HR 94, RR 16, Temp 36.7, SpO2 98%'
    e.engine=NovaCompetitionAgent(DoctorAgent(),preliminary=True)
    e.engine.act({'case_id':'synthetic','observation_type':'initial','chief_complaint':e.opening,'vital_signs':e.vitals})
    e.pstate=e.engine.state('synthetic')
    if history:
        e.pstate.record_ask('associated_symptoms','불편한 증상을 알려주세요',history)
        e.turns.append(Turn('SAY','불편한 증상을 알려주세요',history,'associated_symptoms',1))
    return e


def supported_thyroid():
    e=clinical_encounter('더위를 못 견뎌요; 식욕이 늘었어요; 손이 떨려요; 심장이 두근거려요')
    text='양측 대칭성 미만성 비대(+), 결절(-), 압통(-); 안구 돌출(+)'
    e.pstate.record_exam('thyroid_exam',text,request_text='갑상선을 촉진하겠습니다')
    e.turns.append(Turn('EXAM','갑상선을 촉진하겠습니다',text,'thyroid_exam',2))
    return e


def test_supported_correction_owns_record_communication_and_safety():
    e=supported_thyroid();d,f=e._engine_final()
    e.final_consult={'primary_diagnosis':'Graves disease','short_name':'폐렴','urgent':True,
                    'evidence':['손이 떨려요'],'plan':{'treatment':'unsafe drug 400mg','disposition':'즉시 응급실','tests':'폐렴 검사'}}
    e._accepted_primary=e._validated_primary(d,f);e._diagnosis_checked=True
    assert e._accepted_primary=='Graves disease'
    assert e._resolved_decision(f).primary_id=='clinical:graves_disease'
    e._explain(d,f);note,diagnosis=e.official_record(d,f)
    spoken=[t.text for t in e.turns if t.category in ('explanation','plan_explanation')]
    assert '그레이브스' in spoken[0] and all('폐렴' not in s for s in spoken)
    assert diagnosis in note['A']['evidence'] and 'TSH' in note['P']['tests']
    assert '400mg' not in json.dumps(note) and '응급실' not in note['P']['disposition']
    assert not e._urgent(d,f) and note['O']['tests']==''
    assert all(len(s)<=30 for s in spoken) and len(spoken)==3
    assert '1~2주' in spoken[1] and '고열' in spoken[2]


@pytest.mark.parametrize('history,exam',[
 ('어머니에게 갑상선 질환이 있어요','갑상선 비대(-)'),
 ('심장이 두근거려요','갑상선 비대(-)'),
 ('더위를 안 타요; 식욕이 없어요; 손 떨림(-)','갑상선 미만성 비대(-); 안구 돌출(-)'),
])
def test_graves_requires_multiple_current_facts_and_a_discriminator(history,exam):
    e=clinical_encounter(history);e.pstate.record_exam('thyroid_exam',exam)
    e.final_consult={'primary_diagnosis':'Graves disease','evidence':[history],'urgent':True}
    d,f=e._engine_final();assert e._validated_primary(d,f)==''


def test_parenthetical_specific_cause_cannot_bypass_its_support_requirements():
    e=clinical_encounter('食欲增加; increased appetite; heat intolerance; weight loss')
    e.pstate.record_exam('thyroid_exam','Diffuse goiter(-); eye proptosis(-)')
    e.final_consult={'primary_diagnosis':'Hyperthyroidism (Graves disease)','evidence':['weight loss']}
    d,f=e._engine_final();assert e._validated_primary(d,f)==''


def test_prior_advisory_survives_final_invalid_then_pending_response():
    e=supported_thyroid();e.remember_advisory({'primary_diagnosis':'Graves disease','evidence':['손이 떨려요']},'followup')
    ids=[]
    def fail(messages,**kw):
        ids.append(kw['request_id'])
        raise nova_sdk.NovaError('INVALID_API_RESPONSE' if len(ids)==1 else 'REQUEST_PENDING',503)
    e.client.chat=fail;d,f=e._engine_final();e._final_consult(d,f)
    assert len(ids)==4 and len(set(ids))==1
    assert e._validated_primary(d,f)=='Graves disease'
    # New contradictory actual findings must invalidate that earlier proposal.
    e.pstate.record_exam('thyroid_exam','갑상선 미만성 비대(-); 안구 돌출(-)',request_text='갑상선을 촉진하겠습니다')
    e.pstate.pertinent_positives=[];e.pstate.associated_symptoms=[]
    assert e._validated_primary([],None)==''


def test_pending_retry_never_spends_submission_reserve():
    e=supported_thyroid();e.deadline=e.clock()+16;calls=[]
    def fail(messages,**kw):calls.append(kw['request_id']);raise nova_sdk.NovaError('REQUEST_PENDING',503)
    e.client.chat=fail
    assert e.chat([{'role':'user','content':'fixture'}],max_tokens=100,effort='low',required=True,case_relevant=True) is None
    assert len(calls)==1


def test_unknown_final_still_escalates_actual_measured_hypoxemia():
    e=clinical_encounter('불편한 원인은 잘 모르겠어요')
    e.pstate.record_exam('respiratory_exam','산소포화도 86%, 호흡 30회/분')
    assert e._urgent([],None)
    assert e.pstate.latest_vital_signs().spo2==86


def test_partial_exam_vitals_preserve_unremeasured_fields_and_accept_actual_remeasurement():
    s=PatientState(case_id='partial-vitals',chief_complaint='')
    s.record_initial_vitals('BP 118/72, HR 166, RR 16, Temp 36.7, SpO2 98%')
    s.record_exam('respiratory_exam','SpO2 97%')
    assert s.latest_vital_signs().heart_rate==166 and s.latest_vital_signs().spo2==97
    s.record_exam('pulse_exam','HR 82')
    assert s.latest_vital_signs().heart_rate==82 and s.latest_vital_signs().spo2==97
    s.record_exam('unrelated_exam','Previously HR 45 years ago; current appearance normal')
    assert s.latest_vital_signs().heart_rate==82


def test_known_growth_records_and_pediatric_context_replace_generic_turns():
    from nova_agent.clinical_interview import next_clinical_action,relevant_substance_question
    s=PatientState(case_id='growth',chief_complaint='9세 남아. 1년 전 키 121cm, 현재 키 127cm. 또래보다 키가 작아요.',demographics=Demographics(age=9,sex='male'))
    action=next_clinical_action(s)
    assert action is not None and '이전' not in action[2] and '1년 동안' not in action[2]
    assert not relevant_substance_question(s,'흡연이나 음주를 하시나요?')
    s.demographics.age=16;assert relevant_substance_question(s,'흡연이나 음주를 하시나요?')


def test_dated_height_is_not_misread_as_annual_growth_velocity():
    from nova_agent.clinical_profiles import growth_velocity
    assert growth_velocity('1년 전 키 121cm, 현재 키 127cm')==6
    assert growth_velocity('1년 전 키 121cm') is None
    assert growth_velocity('1년에 5cm 자랐어요')==5
    assert growth_velocity('일 년 전 키 121cm, 현재 키 127cm')==6


def test_quantitative_growth_answer_uses_only_the_actual_question_interval():
    from nova_agent.clinical_profiles import profile_observations
    s=PatientState(case_id='growth-qa',chief_complaint='short stature',demographics=Demographics(age=9))
    s.record_ask('associated_symptoms:growth velocity','1년 동안 키가 얼마나 컸나요?','5cm 자랐어요')
    assert 'preserved prepubertal growth velocity' in profile_observations(s)
    other=PatientState(case_id='undated-height',chief_complaint='short stature',demographics=Demographics(age=9))
    other.record_ask('associated_symptoms:height','키가 얼마인가요?','121cm')
    assert 'preserved prepubertal growth velocity' not in profile_observations(other)


def test_latin_drug_name_with_korean_postposition_is_current_exposure():
    from nova_agent.clinical_concepts import canonical_findings_for
    assert 'sedative use' in canonical_findings_for('zopiclone을 복용해요')
    assert 'sedative use' not in canonical_findings_for('zopiclone을 안 먹어요')


def test_existing_supplied_thyroid_lab_support_is_preserved_without_inventing_results():
    from nova_agent.differential import _entry_for_candidate_id,_score_disease
    from nova_agent.clinical_profiles import profile_problems,thyroid_function_supported
    s=PatientState(case_id='provided-labs',chief_complaint='')
    entry=_entry_for_candidate_id('onto::tier2:hyperthyroidism')
    assert 'suppressed TSH with raised free T4' in entry['confirmatory_findings']
    assert entry['discriminating_questions']==['associated_symptoms:weight loss despite good appetite','associated_symptoms:palpitations','associated_symptoms:heat intolerance','associated_symptoms:tremor']
    assert not thyroid_function_supported(s)
    s.record_test('provided_thyroid','suppressed TSH with raised free T4')
    assert thyroid_function_supported(s) and profile_problems(entry,s)==[]
    assert 'suppressed TSH with raised free T4' in _score_disease(entry,s)[2]
    s.record_test('provided_thyroid','elevated TSH with low free T4')
    assert not thyroid_function_supported(s)


def test_all_three_complete_sdk_fixtures_preserve_calls_and_closing_consistency():
    from scripts.evaluate_official_fixture_efficiency import run
    r=run()
    assert r['mean_topic_coverage']==1
    assert r['mean_turns']<15 and r['mean_doctor_physical_requests']<=3
    for case in r['cases']:
        assert case['primary']==case['expected']
        assert not case['unsafe_emergency_disposition']
        assert case['duplicate_questions_exact']==case['age_inappropriate_social_questions']==case['nfc_or_test_violations']==0
        # v36 uses a third, policy-owned SAY to actually deliver timed follow-up
        # and specific precautions; urgent cases still close in two turns.
        assert len(case['communication']) == 3
        assert any('주' in s or '개월' in s for s in case['communication'])
        assert any('즉시' in s or '조기' in s for s in case['communication'])


def test_thyroid_examination_precedes_more_low_value_history():
    from nova_agent.clinical_interview import next_clinical_action
    e=clinical_encounter('체중 감소; 식욕이 늘었어요; 더위를 못 견뎌요; 심장이 두근거려요')
    action=next_clinical_action(e.pstate)
    assert action[0]=='EXAM' and action[1]=='thyroid_exam'


def test_urgent_correction_spoken_next_step_matches_immediate_disposition():
    e=supported_thyroid();e.pstate.record_exam('respiratory','SpO2 86%')
    e.final_consult={'primary_diagnosis':'Graves disease','evidence':['손이 떨려요']}
    d,f=e._engine_final();e._accepted_primary=e._validated_primary(d,f);e._diagnosis_checked=True
    e._explain(d,f);note,_=e.official_record(d,f)
    spoken=[t.text for t in e.turns if t.category=='plan_explanation']
    assert '지금 응급실' in spoken[-1] and '응급실' in note['P']['disposition']
    assert len(spoken[-1])<=30


@pytest.mark.parametrize('opening,expected',[
 ('Severe chest pain and trouble sleeping tonight.',None),
 ('Insomnia with current fever and confusion.',None),
 ('Insomnia; no chest pain and no shortness of breath.','sleep'),
])
def test_acute_and_negated_acute_concerns_do_not_misroute(opening,expected):
    from nova_agent.clinical_interview import interview_family
    s=PatientState(case_id='mixed-context',chief_complaint=opening,demographics=Demographics(age=56))
    assert interview_family(s)==expected


def test_frozen_32_case_pipeline_proxy_and_no_fake_lab_results():
    from scripts.evaluate_rubric_proxy import run
    r=run()
    assert r['metrics']['cases']==32
    assert r['metrics']['reference_compatible']==32
    assert r['metrics']['urgency_matches']==32
    assert r['metrics']['unperformed_test_results']==0
    assert 2 <= r['metrics']['mean_closing_turns'] <= 3
    assert r['metrics']['precautions_present'] == r['metrics']['cases']
