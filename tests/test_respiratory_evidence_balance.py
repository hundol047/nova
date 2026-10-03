"""Clinical evidence categories, not fixed benchmark answers."""
from nova_agent.state import PatientState
from nova_agent.differential import _score_disease, DifferentialEngine
from nova_agent.knowledge.retrieval import disease_by_id


def test_crackles_alone_are_not_confirmatory_pneumonia_evidence():
    state=PatientState(case_id='exam-only',chief_complaint='cough',physical_examinations={'lung_auscultation':'bibasal crackles'})
    entry=disease_by_id('pneumonia')
    assert 'crackles on auscultation' in entry['typical_features']
    assert not set(_score_disease(entry,state)[2]) & set(entry['confirmatory_findings'])


def test_obstructive_airway_symptoms_are_not_missing_from_profile():
    state=PatientState(case_id='obstruction',chief_complaint='cough and dyspnea',physical_examinations={'lung_auscultation':'wheeze'},past_medical_history=['COPD'])
    supported=_score_disease(disease_by_id('asthma_copd_exacerbation'),state)[2]
    assert {'cough','dyspnea','wheeze','COPD'} <= set(supported)


def test_imaging_supported_infection_stays_in_differential():
    state=PatientState(case_id='imaging',chief_complaint='productive cough and fever',imaging={'cxr':'new focal consolidation'})
    assert DifferentialEngine().update(state)[0].diagnosis_id=='pneumonia'


def test_denied_cough_and_dyspnea_do_not_support_obstruction():
    state=PatientState(case_id='negative',chief_complaint='routine follow up',pertinent_negatives=['no cough','no dyspnea'])
    supporting=_score_disease(disease_by_id('asthma_copd_exacerbation'),state)[2]
    assert not {'cough','dyspnea'} & set(supporting)


def test_regional_airspace_opacity_is_imaging_support_not_crackles():
    state=PatientState(case_id='opacity',chief_complaint='cough',imaging={'cxr':'left lower lobe airspace opacity'})
    assert 'infiltrate' in _score_disease(disease_by_id('pneumonia'),state)[2]


def test_worsening_breathlessness_is_distinct_from_stable_symptoms():
    entry=disease_by_id('asthma_copd_exacerbation')
    state=PatientState(case_id='worsening',chief_complaint='increasing breathlessness')
    assert 'worsening dyspnea' in _score_disease(entry,state)[2]
    for text in ['stable breathlessness', 'no worsening breathlessness']:
        state=PatientState(case_id='stable',chief_complaint=text)
        assert 'worsening dyspnea' not in _score_disease(entry,state)[2]


def test_denied_airspace_opacity_is_not_pneumonia_support():
    state=PatientState(case_id='no-opacity',chief_complaint='cough',imaging={'cxr':'no airspace opacity'})
    assert 'infiltrate' not in _score_disease(disease_by_id('pneumonia'),state)[2]
