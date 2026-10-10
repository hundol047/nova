"""Round W mechanisms: infant vitals parsing, paediatric rhythm threshold, heat-stroke exposure context, caregiver
reports, shingles distribution wording, evidenced-candidate retention, measured vital thresholds, antecedent
context weight. Engineering contracts on synthetic text, not clinical validation."""
import pytest

from nova_agent.differential import DifferentialEngine, DifferentialItem, _score_disease
from nova_agent.final_decision import decide_final, support_problems
from nova_agent.matching import feature_present_with_aliases
from nova_agent.state import PatientState
from nova_agent.vitals_parser import describe_vital_sign_abnormalities, fast_pulse_threshold, parse_vital_signs


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo()
    get_config(reload=True)


def _item(did, name, support, dangerous=True, score=1.0):
    return DifferentialItem(diagnosis=name, diagnosis_id=did, rank=1, score=score, score_ratio=0.5,
                            supporting_evidence=list(support), contradictory_evidence=[], urgency='HIGH',
                            dangerous_if_missed=dangerous, confidence_band='LOW')


# --- vitals ---------------------------------------------------------------------------------------------------------

def test_an_infant_respiratory_rate_no_longer_discards_the_whole_reading():
    v = parse_vital_signs('HR 192, RR 64, Temp 39.8, SpO2 93%')
    assert (v.heart_rate, v.respiratory_rate, v.temperature_c, v.spo2) == (192, 64, 39.8, 93)
    assert {'Marked tachycardia', 'Tachypnea', 'High fever'} <= set(describe_vital_sign_abnormalities(v, 0))


def test_one_implausible_value_is_dropped_on_its_own():
    v = parse_vital_signs('HR 300, Temp 38.2, SpO2 97%')
    assert v.heart_rate is None and v.temperature_c == 38.2 and v.spo2 == 97
    assert parse_vital_signs('HR 400') is None


def test_rhythm_review_threshold_is_age_specific():
    assert fast_pulse_threshold(40) == 150 and fast_pulse_threshold(None) == 150
    assert fast_pulse_threshold(0) == 220 and fast_pulse_threshold(5) == 180
    v = parse_vital_signs('HR 176, RR 40, Temp 39.0')
    assert 'pulse rate of 150 or more' not in describe_vital_sign_abnormalities(v, 1)
    assert 'pulse rate of 150 or more' in describe_vital_sign_abnormalities(v, 40)


# --- measured thresholds ---------------------------------------------------------------------------------------------

def _hypertensive_entry():
    return {'id': 'syn', 'typical_features': ['severe headache', 'blood pressure above 180 over 120', 'chest pain'],
            'risk_factors': [], 'confirmatory_findings': []}


@pytest.mark.parametrize('bp,supported', [('BP 124/78, HR 80', False), ('BP 210/124, HR 96', True)])
def test_numeric_vital_feature_is_decided_by_the_measurement(bp, supported):
    s = PatientState(chief_complaint='Severe headache and chest pain.', preliminary_rules=True)
    s.record_initial_vitals(bp)
    _, _, support, against, _ = _score_disease(_hypertensive_entry(), s)
    assert ('blood pressure above 180 over 120' in support) is supported
    assert ('blood pressure above 180 over 120' in against) is (not supported)


def test_unmeasured_vital_feature_is_neither_supported_nor_contradicted():
    s = PatientState(chief_complaint='Severe headache.', preliminary_rules=True)
    _, _, support, against, _ = _score_disease(_hypertensive_entry(), s)
    assert 'blood pressure above 180 over 120' not in support + against


# --- heat stroke context ---------------------------------------------------------------------------------------------

def test_heat_stroke_needs_heat_exposure_or_exertion_to_be_named():
    item = _item('onto::tier2:heat_stroke', 'Heat Stroke', ['confusion', 'hot dry skin or profuse sweating'])
    feverish = PatientState(chief_complaint='My baby is very floppy, hot and breathing fast.', preliminary_rules=True)
    assert any(p.startswith('required_context_missing') for p in support_problems(item, feverish, [item]))
    exposed = PatientState(chief_complaint='He collapsed after running a marathon in the heat.', preliminary_rules=True)
    assert not any(p.startswith('required_context_missing') for p in support_problems(item, exposed, [item]))
    denied = PatientState(chief_complaint='He is confused. He was not out in the heat.', preliminary_rules=True)
    assert any(p.startswith('required_context_missing') for p in support_problems(item, denied, [item]))


# --- caregiver reports ----------------------------------------------------------------------------------------------

@pytest.mark.parametrize('text,sex,age,relation', [
    ('My husband collapsed after a marathon', 'male', 34, 'husband'),
    ('Dad has become confused since his new tablet', 'male', 81, 'dad'),
    ('My 14-month-old son is burning hot', 'male', 1, 'son'),
    ('우리 아들이 열이 나요', 'male', 5, '아들'),
    ('My husband collapsed', 'female', 34, None),     # relation does not fit the patient
    ('My father fainted at 60.', 'female', 30, None),  # family history of a young woman
    ('I have chest pain', 'male', 50, None)])
def test_caregiver_relation_is_the_patient_only_when_demographics_fit(text, sex, age, relation):
    from nova_agent.evidence_scope import detect_proxy_relation
    assert detect_proxy_relation(text, sex, age) == relation


def test_caregiver_report_is_patient_evidence_but_other_relatives_stay_family():
    from nova_agent.evidence_scope import proxy_scope
    text = 'My husband collapsed after a marathon; he is confused. His father had a stroke.'
    assert not feature_present_with_aliases('confusion', [text])
    with proxy_scope('husband'):
        assert feature_present_with_aliases('confusion', [text])
        assert not feature_present_with_aliases('stroke', ['His father had a stroke.'])


def test_caregiver_switch_off_keeps_the_family_reading(monkeypatch):
    from nova_agent.config import get_config
    from nova_agent.evidence_scope import proxy_scope
    monkeypatch.setenv('NOVA_PROXY_REPORT', '0')
    get_config(reload=True)
    with proxy_scope('husband'):
        assert not feature_present_with_aliases('confusion', ['My husband is confused.'])


# --- shingles wording ------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('feature,text,expected', [
    ('band-like blistering rash', 'a blistery rash in the same strip', True),
    ('band-like blistering rash', 'little blisters along the same line', True),
    ('band-like blistering rash', 'clusters of blisters', True),
    ('band-like blistering rash', 'no blisters along the line', False),
    ('band-like blistering rash', 'a rash on my arm', False),
    ('burning pain on one side of body', 'Burning pain in a strip around my right side', True),
    ('burning pain on one side of body', 'A burning band of pain on the left side of my chest wall', True),
    ('burning pain on one side of body', 'burning when I pee', False)])
def test_shingles_distribution_wording(feature, text, expected):
    assert feature_present_with_aliases(feature, [text]) is expected


# --- retention, antecedent context -----------------------------------------------------------------------------------

def test_evidenced_ontology_candidate_survives_a_reshuffled_rerank(monkeypatch):
    s = PatientState(chief_complaint='Burning pain in a strip around my right side, and now little blisters along '
                                     'the same line.', preliminary_rules=True)
    first = DifferentialEngine().update(s)
    assert first[0].diagnosis_id == 'onto::tier2:herpes_zoster'
    import nova_agent.candidate_generator as cg
    monkeypatch.setattr(cg, '_broaden_with_open_world', lambda *a, **k: None)  # this turn's rerank lists nothing
    second = DifferentialEngine().update(s)
    assert any(d.diagnosis_id == 'onto::tier2:herpes_zoster' for d in second)


def test_antecedent_context_ranks_like_a_risk_factor():
    from nova_agent.differential import RISK_FACTOR_WEIGHT
    entry = {'id': 'syn', 'typical_features': ['recent cold'], 'risk_factors': [], 'confirmatory_findings': []}
    s = PatientState(chief_complaint='Ear ache, started after a cold.', preliminary_rules=True)
    assert _score_disease(entry, s)[0] == pytest.approx(RISK_FACTOR_WEIGHT)


def test_collapse_with_a_very_slow_pulse_is_a_symptomatic_rate_concern():
    from nova_agent.disposition import symptomatic_rate_concern
    s = PatientState(chief_complaint='I collapsed suddenly in my armchair.', preliminary_rules=True)
    s.record_initial_vitals('BP 102/64, HR 34, RR 16, Temp 36.5, SpO2 96%')
    assert symptomatic_rate_concern(s)
    calm = PatientState(chief_complaint='My pulse was 46 at a check; I run marathons and feel fine.', preliminary_rules=True)
    calm.record_initial_vitals('BP 118/70, HR 46, RR 12, Temp 36.6, SpO2 99%')
    assert not symptomatic_rate_concern(calm)
