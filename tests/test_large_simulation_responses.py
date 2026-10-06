from evaluation.cases import SyntheticCase
from evaluation.large_simulation.responses import resolve, MISSING


def make_case(**kwargs):
    return SyntheticCase(case_id='responses', chief_complaint='symptom', demographics={},
                         ground_truth_diagnosis='unknown', **kwargs)


def test_cxr_alias_delivers_recorded_result_without_diagnosis_access():
    case = make_case(test_results={'chest_xray': 'left-sided consolidation'})
    assert resolve(case, 'TEST', 'cxr') == 'chest_xray: left-sided consolidation'
    case.ground_truth_diagnosis = 'pneumonia'
    assert resolve(case, 'TEST', 'cxr') == 'chest_xray: left-sided consolidation'


def test_panel_delivers_supplied_components_and_preserves_conflicts():
    case = make_case(test_results={'cbc': 'hemoglobin 13 g/dL', 'hemoglobin': '6 g/dL',
                                  'wbc': 'WBC elevated', 'potassium': '6.4 mmol/L'})
    assert resolve(case, 'TEST', 'cbc') == 'cbc: hemoglobin 13 g/dL; wbc: WBC elevated; hemoglobin: 6 g/dL'
    assert resolve(case, 'TEST', 'bmp') == 'potassium: 6.4 mmol/L'


def test_missing_data_and_non_equivalent_imaging_are_not_normal_or_guessed():
    case = make_case(test_results={'ct_chest': 'abnormal'})
    assert resolve(case, 'TEST', 'ct_chest_angio') == MISSING
    assert resolve(case, 'TEST', 'ct_aorta') == MISSING
    assert resolve(case, 'EXAM', 'lung_auscultation') == MISSING
    assert resolve(case, 'ASK', 'onset') == MISSING


def test_exact_responses_still_return_unchanged_and_medication_alias_works():
    case = make_case(answers={'medications': 'warfarin'}, exam_results={'neuro_exam': 'unilateral weakness'})
    assert resolve(case, 'ASK', 'medication') == 'medications: warfarin'
    assert resolve(case, 'EXAM', 'neuro_exam') == 'unilateral weakness'
