import json
import pytest
from nova_agent.state import PatientState
from nova_agent.differential import DifferentialEngine, DifferentialItem, _score_disease
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.language import normalize_clinical_text
from nova_agent.decision_quality import assess_decision
from evaluation.sealed_cases import read_cases, load_frozen_cases
from evaluation.reliability import summarize_reliability


def bundle(tmp_path):
    path=tmp_path/'cases.json'
    data={'author':'test author','provenance':'synthetic test fixture, not independent',
          'cases':[{'case_id':'external','chief_complaint':'headache','demographics':{},
                    'ground_truth_diagnosis':'diagnosis outside catalog','critical_override':False}]}
    path.write_text(json.dumps(data))
    return path,data


def test_external_freeze_detects_modified_labels_and_defaults_unknown(tmp_path):
    path,data=bundle(tmp_path)
    cases,metadata=read_cases(path)
    assert cases[0].default_test_result=='Unknown / not provided.'
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(metadata))
    assert load_frozen_cases(path,manifest)[0][0].case_id=='external'
    data['cases'][0]['ground_truth_diagnosis']='different answer';path.write_text(json.dumps(data))
    with pytest.raises(ValueError):load_frozen_cases(path,manifest)


def test_external_duplicate_case_and_invalid_action_rejected(tmp_path):
    path,data=bundle(tmp_path)
    data['cases']*=2;path.write_text(json.dumps(data))
    with pytest.raises(ValueError):read_cases(path)
    data['cases']=data['cases'][:1];data['cases'][0]['test_results']={'invented_test':'positive'}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):read_cases(path)


def test_korean_negation_preserves_original_and_routes_positive_complaint():
    from nova_agent.chief_complaint import route
    s=PatientState(chief_complaint='흉통 없음; 호흡곤란')
    findings=s.all_findings_text()
    assert s.chief_complaint=='흉통 없음; 호흡곤란'
    assert any('no chest pain' in text for text in findings)
    assert route(s.chief_complaint).primary_tag=='dyspnea'
    assert normalize_clinical_text('SOB')=='dyspnea'


def test_korean_vital_signs_and_negative_named_test():
    s=PatientState()
    s.record_exam('vital_signs','혈압 120/80, 맥박 75, 호흡수 16, 체온 37.0')
    assert s.vital_signs[-1].sbp==120
    s.record_test('beta_hcg','음성')
    assert 'positive beta-hCG' not in _score_disease(disease_by_id('ectopic_pregnancy'),s)[2]


def test_family_symptoms_do_not_become_patient_findings():
    s=PatientState(chief_complaint='fatigue',family_history=['mother has photophobia and nausea'])
    result=_score_disease(disease_by_id('migraine'),s)
    assert 'photophobia' not in result[2] and 'nausea' not in result[2]


def test_unmapped_high_self_confidence_is_not_a_verified_probability():
    d=DifferentialItem(diagnosis='Outside catalog',diagnosis_id='novel:outside',rank=1,
        score=5,score_ratio=.9,supporting_evidence=['reported finding'],confidence_band='HIGH',
        urgency='LOW',dangerous_if_missed=False)
    quality=assess_decision(PatientState(),[d])
    assert quality['band']=='LOW' and quality['probability'] is None
    assert quality['catalog_status']=='outside_catalog'


def test_forced_diagnosis_does_not_claim_full_readiness():
    from nova_agent.stop_policy import StopPolicy
    result=StopPolicy().evaluate(PatientState(turn_count=58,max_turns=60),[],[])
    assert result.forced and result.readiness_score==0


def test_existing_medication_text_and_symptoms_are_not_asked_again():
    from nova_agent.missing_info import MissingInformationAnalyzer
    s=PatientState(medication_text=['warfarin'],associated_symptoms=['nausea'])
    candidates=MissingInformationAnalyzer().analyze(s,[],[])
    assert not any(c.key in {'medication','associated_symptoms'} for c in candidates)


def test_reliability_groups_exclude_unscored_and_do_not_claim_calibration():
    report=summarize_reliability([{'correct':True,'decision_quality':{'band':'HIGH'}},
        {'correct':False,'decision_quality':{'band':'HIGH'}},
        {'correct':False,'scoring_expected':False,'decision_quality':{'band':'HIGH'}}])
    assert report['by_evidence_band']['HIGH']['observed_accuracy']==.5
    assert report['by_evidence_band']['HIGH']['n']==2
    assert report['calibrated_probabilities'] is False


def test_catalog_extension_rejects_override_and_unknown_actions(tmp_path):
    from nova_agent.knowledge.extensions import load_extension
    entry={'id':'new_condition','name':'Test condition','evidence_level':'test_fixture',
           'sources':['https://example.org/test-fixture'],'dangerous':False,'urgency':'LOW',
           'typical_features':['example finding'],'discriminating_tests':['cbc']}
    path=tmp_path/'extension.json';path.write_text(json.dumps([entry]))
    assert load_extension(path,{'existing'})[0]['id']=='new_condition'
    with pytest.raises(ValueError):load_extension(path,{'new_condition'})
    entry['discriminating_tests']=['invented'];path.write_text(json.dumps([entry]))
    with pytest.raises(ValueError):load_extension(path,set())


def test_alternative_and_coexisting_labels_are_evaluation_only():
    from evaluation.cases import SyntheticCase
    case=SyntheticCase(case_id='multiple',chief_complaint='unspecified',demographics={},
        ground_truth_diagnosis='primary outside catalog',acceptable_diagnoses=['alternate accepted name'],
        coexisting_diagnoses=['other condition'],critical_override=True)
    assert case.critical and len(case.acceptable_diagnoses)==1
    from nova_agent.diagnosis_normalizer import same_diagnosis
    assert same_diagnosis('primary outside catalog','primary outside catalog')
    assert not same_diagnosis('unrelated external disease','primary outside catalog')


def test_simulator_scores_outside_catalog_and_companion_diagnoses():
    from evaluation.cases import SyntheticCase
    from evaluation.simulator import run_case
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.action_selector import AgentAction
    from nova_agent.state import DifferentialSnapshot
    class ScriptedAgent(DoctorAgent):
        def decide(self,state):
            state.current_differential=[DifferentialSnapshot(diagnosis='External condition B',rank=1,
                confidence_band='LOW',urgency='LOW',dangerous_if_missed=False)]
            return AgentAction(action_type='DIAGNOSE',key='novel:external',content='External condition A',rationale='test fixture'),None,[]
    case=SyntheticCase(case_id='external-pair',chief_complaint='unspecified',demographics={},
        ground_truth_diagnosis='primary label',acceptable_diagnoses=['External condition A'],
        coexisting_diagnoses=['External condition B'],critical_override=False)
    result=run_case(ScriptedAgent(),case)
    assert result.correct and result.coexisting_differential_recall==1


def test_strict_live_validation_rejects_fallback_or_budget_skipped_turns():
    from evaluation.real_llm_benchmark import all_decisions_real
    state=PatientState(turn_count=3,llm_success_count=1,llm_failure_count=2,llm_fallback_count=2)
    assert not all_decisions_real(state)
    state.llm_failure_count=state.llm_fallback_count=0
    assert not all_decisions_real(state)
    state.llm_success_count=3
    assert all_decisions_real(state)
    assert not all_decisions_real(PatientState())


@pytest.mark.parametrize('field,value', [
    ('critical_override', None), ('critical_override', 'false'),
    ('critical_override', 0), ('scoring_expected', 'false'),
    ('case_id', '  '), ('chief_complaint', ''),
    ('ground_truth_diagnosis', '\t'), ('acceptable_diagnoses', ['']),
    ('coexisting_diagnoses', [' ']), ('relevant_test_ids', ['invented_test']),
])
def test_external_cases_reject_ambiguous_or_invalid_metadata(tmp_path, field, value):
    path, data = bundle(tmp_path)
    data['cases'][0][field] = value
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        read_cases(path)


@pytest.mark.parametrize('author', [[], {}, 12, '   '])
def test_external_provenance_requires_nonempty_text(tmp_path, author):
    path, data = bundle(tmp_path)
    data['author'] = author
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        read_cases(path)


def test_external_cases_reject_whitespace_duplicate_ids_and_nonobjects(tmp_path):
    path, data = bundle(tmp_path)
    data['cases'].append({**data['cases'][0], 'case_id': ' external '})
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='Duplicate'):
        read_cases(path)
    data['cases'] = [None]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='JSON object'):
        read_cases(path)


@pytest.mark.parametrize('field,value', [
    ('typical_features', ['']), ('confirmatory_findings', ['  ']),
    ('aliases', ['']), ('id', ' asthma'), ('id', 'novel:asthma'),
    ('sources', ['https://']), ('sources', ['https:///missing-host']),
    ('sources', ['https://bad host/path']), ('sources', ['https://example.org:bad']),
    ('sources', ['https://user:password@example.org']),
])
def test_extension_rejects_empty_evidence_and_malformed_sources(tmp_path, field, value):
    from nova_agent.knowledge.extensions import load_extension
    entry = {'id': 'new_condition', 'name': 'Test condition', 'evidence_level': 'test_fixture',
             'sources': ['https://example.org/test'], 'dangerous': False, 'urgency': 'LOW',
             'typical_features': ['example finding']}
    entry[field] = value
    path = tmp_path / 'extension.json'
    path.write_text(json.dumps([entry]))
    with pytest.raises(ValueError):
        load_extension(path, set())
