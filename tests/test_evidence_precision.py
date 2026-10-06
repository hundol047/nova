"""Development regressions: polarity, provenance, lab anchoring and identity.

No frozen benchmark text is used here. These test evidence semantics, not clinical accuracy.
"""
import pytest
from nova_agent.state import PatientState
from nova_agent.objective_evidence import normalize_objective_evidence
from nova_agent.differential import _score_disease
from nova_agent.diagnosis_normalizer import same_diagnosis, normalize_diagnosis


def labs(**values):
    s=PatientState(case_id='precision',chief_complaint='assessment')
    s.laboratory_tests.update(values)
    return normalize_objective_evidence(s)


@pytest.mark.parametrize('text', ['not elevated troponin','no elevated troponin detected',
                                  'troponin is not elevated','negative troponin'])
def test_negated_abnormal_troponin_is_not_positive(text):
    assert labs(troponin=text)['lab.troponin'].interpretation == 'normal'


def test_conflicting_unordered_lab_statements_are_not_automatically_positive():
    assert labs(troponin='elevated troponin; normal troponin')['lab.troponin'].interpretation == 'unknown'


def test_reference_range_word_normal_is_not_a_normal_result():
    assert labs(lipase='Lipase above the upper limit of normal')['lab.lipase'].interpretation == 'high'
    assert labs(troponin='Troponin not normal')['lab.troponin'].interpretation == 'unknown'


@pytest.mark.parametrize('text', ['negative leukocyte esterase; no nitrites',
                                  'leukocyte esterase negative; nitrites negative'])
def test_negative_urine_markers_do_not_support_infection(text):
    f=labs(urinalysis=text)
    assert f['lab.urinalysis_infection'].interpretation == 'normal'


def test_mixed_urine_markers_remain_independent():
    f=labs(urinalysis='negative leukocyte esterase; positive nitrites')
    assert f['lab.leukocyte_esterase'].interpretation == 'normal'
    assert f['lab.nitrites'].interpretation == 'high'


@pytest.mark.parametrize('key,text,lab,value', [
 ('bmp','Na: 141; K: 6.7','lab.potassium',6.7),
 ('cbc','Hb: 6.6 g/dL','lab.hemoglobin',6.6),
 ('bmp','Na: 128; K: 4.2','lab.sodium',128),
])
def test_analyte_abbreviations_keep_their_own_values(key,text,lab,value):
    assert labs(**{key:text})[lab].value==value


def test_missing_analyte_value_does_not_capture_neighbor():
    assert labs(bmp='potassium pending, sodium 139')['lab.potassium'].value is None


def test_unknown_specimen_value_is_not_used():
    assert labs(potassium='potassium 7.2; specimen hemolyzed')['lab.potassium'].interpretation == 'unknown'


def test_cross_analyte_allowed_units_do_not_override_wrong_unit():
    assert labs(bmp='creatinine 98 umol/L; glucose 105 mg/dL')['lab.creatinine'].value == pytest.approx(98/88.4)
    assert labs(bmp='creatinine 98 mmol/L; glucose 105 mg/dL')['lab.creatinine'].value is None


def test_mg_per_liter_is_not_mg_per_deciliter():
    from nova_agent.unit_safety import unit_present
    assert not unit_present('creatinine 15 mg/L','mg/dl')


def test_confirmatory_lab_aliases_do_not_double_count_one_measurement():
    s=PatientState(case_id='duplicate',chief_complaint='assessment')
    s.laboratory_tests['troponin']='elevated troponin'
    a=dict(id='test', typical_features=[], risk_factors=[],confirmatory_findings=['elevated troponin'])
    b={**a,'confirmatory_findings':['elevated troponin','troponin elevated']}
    assert _score_disease(a,s)[:2] == _score_disease(b,s)[:2]


def test_history_is_not_current_confirmation():
    s=PatientState(case_id='history',chief_complaint='checkup')
    s.family_history=['parent had ST elevation during a heart attack']
    entry=dict(id='test', typical_features=[], risk_factors=[],confirmatory_findings=['ST elevation'])
    assert _score_disease(entry,s)[2] == []


def test_partial_confirmatory_word_overlap_is_not_confirmation():
    s=PatientState(case_id='partial',chief_complaint='assessment')
    s.physical_examinations['exam']='regular heart rhythm'
    entry=dict(id='test', typical_features=[],risk_factors=[],confirmatory_findings=['irregular heart rhythm'])
    assert _score_disease(entry,s)[2] == []


def test_reassuring_exam_requires_complete_phrase():
    """A focal neurologic deficit must not partially match stroke's reassuring phrases."""
    from nova_agent.knowledge.retrieval import disease_by_id

    focal = PatientState(case_id='stroke-focal', chief_complaint='headache')
    focal.record_exam('neuro_exam', 'Left leg weakness with a focal neurological deficit')
    entry = disease_by_id('ischemic_stroke')
    _score, _max_possible, _supporting, contradictory, _missing = _score_disease(entry, focal)
    assert 'no focal neurological deficit' not in contradictory
    assert 'normal neurologic exam' not in contradictory

    normal = PatientState(case_id='stroke-normal', chief_complaint='headache')
    normal.record_exam('neuro_exam', 'normal neurologic exam, no focal neurological deficit')
    _score, _max_possible, _supporting, contradictory, _missing = _score_disease(entry, normal)
    assert 'no focal neurological deficit' in contradictory


@pytest.mark.parametrize('name,key', [('Ectopic Pregnancy','ectopic_pregnancy'),
 ('Benign Paroxysmal Positional Vertigo','bppv')])
def test_explicit_identity_is_not_lost_because_catalog_contains_duplicate_name(name,key):
    assert same_diagnosis(name,key)


def test_ambiguous_abbreviation_still_cannot_resolve_without_id():
    assert not normalize_diagnosis('MS').mapped
    assert not same_diagnosis('MS','tier2:multiple_sclerosis')


def test_long_negation_scope_cannot_reappear_as_affirmative():
    from nova_agent.matching import feature_present
    assert not feature_present('focal consolidation', ['No radiological evidence to suggest focal consolidation'], scrub_negated_spans=True)
    assert feature_present('pleural effusion', ['No radiological evidence to suggest focal consolidation, but pleural effusion is present'], scrub_negated_spans=True)


def test_exact_word_boundary_prevents_substring_symptom_match():
    from nova_agent.matching import feature_present
    assert not feature_present('rash', ['car crash yesterday'], strict=True)


def test_appendiceal_imaging_support_requires_affirmative_objective_report():
    from nova_agent.knowledge.retrieval import disease_by_id
    entry=disease_by_id('appendicitis')
    positive=PatientState(case_id='scan',chief_complaint='abdominal discomfort')
    positive.imaging['ct_abdomen']='Report describes an inflamed appendix.'
    negative=PatientState(case_id='scan-negative',chief_complaint='abdominal discomfort')
    negative.imaging['ct_abdomen']='No evidence of an inflamed appendix.'
    history=PatientState(case_id='scan-family',chief_complaint='checkup')
    history.family_history=['A relative had an inflamed appendix.']
    assert 'appendiceal inflammation' in _score_disease(entry,positive)[2]
    assert 'appendiceal inflammation' not in _score_disease(entry,negative)[2]
    assert 'appendiceal inflammation' not in _score_disease(entry,history)[2]


def test_absences_and_risk_factors_alone_cannot_establish_diagnosis():
    from nova_agent.differential import DifferentialItem, has_positive_diagnostic_support
    item=DifferentialItem(diagnosis='Uncomplicated Cystitis (Lower UTI)',
        diagnosis_id='uncomplicated_cystitis', rank=1, score=2, score_ratio=.2,
        supporting_evidence=['no fever','no flank pain','female sex'], urgency='LOW',
        dangerous_if_missed=False, confidence_band='LOW')
    assert not has_positive_diagnostic_support(item)
    item.supporting_evidence.append('dysuria')
    assert has_positive_diagnostic_support(item)


@pytest.mark.parametrize('finding,expected', [
    ('Lightheadedness occurred immediately before collapse.', True),
    ('Lightheadedness appeared after collapse.', False),
    ('No lightheadedness before collapse.', False),
    ('Lightheadedness now; nausea before collapse.', False),
])
def test_prodrome_requires_affirmative_preceding_symptom(finding, expected):
    from nova_agent.matching import feature_present
    assert feature_present('prodrome of lightheadedness', [finding],
                           scrub_negated_spans=True) is expected


@pytest.mark.parametrize('answer,positive,negative', [
    ('cough, no fever, no vomiting', 'cough', 'no fever'),
    ('no rash, has cough', 'has cough', 'no rash'),
    ('dizziness, denies headache', 'dizziness', 'denies headache'),
])
def test_comma_polarity_keeps_both_assertions(answer, positive, negative):
    state = PatientState(case_id='clause-test', chief_complaint='assessment')
    state.record_ask('associated_symptoms', '?', answer)
    assert positive in state.pertinent_positives
    assert negative in state.pertinent_negatives


def test_alias_dictionary_has_no_silently_overwritten_keys():
    """A duplicate key in a dict literal silently drops the earlier entry. FEATURE_ALIASES now lives in
    matching.py (shared by differential.py and candidate_generator.py) and the ported PR #15 aliases in
    pr15_feature_aliases.py; the property is checked on both literals."""
    import ast
    from pathlib import Path
    root = Path(__file__).parents[1] / 'nova_agent'
    for filename, name in (('matching.py', 'FEATURE_ALIASES'), ('pr15_feature_aliases.py', 'PR15_FEATURE_ALIASES')):
        tree = ast.parse((root / filename).read_text())
        node = next(n.value for n in tree.body
                    if (isinstance(n, ast.AnnAssign) and getattr(n.target, 'id', '') == name)
                    or (isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') == name))
        keys = [ast.literal_eval(k) for k in node.keys]
        assert len(keys) == len(set(keys)), (filename, [k for k in keys if keys.count(k) > 1])


def test_reassuring_family_history_is_not_current_exam():
    from nova_agent.knowledge.retrieval import disease_by_id
    state = PatientState(case_id='history-normal', chief_complaint='weakness')
    state.family_history = ['Parent had a normal neurologic exam']
    assert not _score_disease(disease_by_id('ischemic_stroke'), state)[3]


def test_negated_normal_exam_is_not_reassuring():
    from nova_agent.knowledge.retrieval import disease_by_id
    state = PatientState(case_id='abnormal-exam', chief_complaint='weakness')
    state.record_exam('neuro_exam', 'Not a normal neurologic exam')
    assert 'normal neurologic exam' not in _score_disease(disease_by_id('ischemic_stroke'), state)[3]
