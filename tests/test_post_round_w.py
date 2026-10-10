"""Post-Round-W mechanisms: sepsis high-risk signs, infant meningitis signs, Korean caregiver/collapse wording, chest
pressure similes, anatomical sex compatibility, decision certainty metadata and the EXAM utility contract.
Engineering contracts on synthetic text, not clinical validation."""
import pytest

from nova_agent.clinical_concepts import is_objective_only_feature
from nova_agent.differential import DifferentialEngine, DifferentialItem, _score_disease
from nova_agent.final_decision import decide_final
from nova_agent.matching import feature_present_with_aliases
from nova_agent.state import PatientState


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo()
    get_config(reload=True)


def _item(did, name, support, score, dangerous=False):
    return DifferentialItem(diagnosis=name, diagnosis_id=did, rank=1, score=score, score_ratio=0.5,
                            supporting_evidence=list(support), contradictory_evidence=[], urgency='HIGH',
                            dangerous_if_missed=dangerous, confidence_band='LOW')


def _entry(did):
    from nova_agent.knowledge.retrieval import disease_by_id
    return disease_by_id(did)


# --- sepsis high-risk signs (NICE NG51) ------------------------------------------------------------------------------

def test_sepsis_signs_are_examination_findings_never_questions():
    assert is_objective_only_feature('mottled skin on examination')
    assert is_objective_only_feature('grunting on examination')
    assert not is_objective_only_feature('temperature below 36 degrees')  # decided by the measurement instead


@pytest.mark.parametrize('text,expected', [
    ("his skin looks blotchy", True), ("Lethargic, mottled skin, cool hands.", True),
    ("No mottling, skin pink and warm.", False)])
def test_mottled_skin_wording(text, expected):
    assert feature_present_with_aliases('mottled skin on examination', [text]) is expected


def test_korean_mottled_skin_supports_sepsis():
    s = PatientState(chief_complaint='아기 피부가 얼룩덜룩하고 축 처져요.', preliminary_rules=True)
    assert 'mottled skin on examination' in _score_disease(_entry('sepsis'), s)[2]


@pytest.mark.parametrize('vitals,supported', [('HR 170, Temp 35.4', True), ('HR 170, Temp 39.2', False)])
def test_low_temperature_supports_sepsis_and_fever_does_not_contradict_it(vitals, supported):
    s = PatientState(chief_complaint='My baby is floppy and not feeding.', preliminary_rules=True)
    s.record_initial_vitals(vitals)
    _, _, support, against, _ = _score_disease(_entry('sepsis'), s)
    assert ('temperature below 36 degrees' in support) is supported
    assert 'temperature below 36 degrees' not in against


# --- infant meningitis signs (NICE NG143 / NG240) --------------------------------------------------------------------

@pytest.mark.parametrize('text,expected', [
    ('the soft spot on his head is bulging', True), ('Anterior fontanelle tense and bulging.', True),
    ('the soft spot on top of his head looks swollen', True), ('숫구멍이 볼록하게 튀어나왔어요', True),
    ('Fontanelle soft and flat.', False), ('Fontanelle is not bulging.', False), ('No bulging fontanelle.', False)])
def test_bulging_fontanelle_wording(text, expected):
    assert feature_present_with_aliases('bulging fontanelle on examination', [text]) is expected


@pytest.mark.parametrize('text,expected', [
    ('a high-pitched cry', True), ("won't stop screaming in a shrill way", True), ('날카롭게 울어요', True),
    ('she cries a lot', False), ('No high-pitched cry.', False)])
def test_high_pitched_cry_wording(text, expected):
    assert feature_present_with_aliases('high-pitched cry on examination', [text]) is expected


def test_infant_meningitis_signs_lead_the_differential():
    s = PatientState(case_id='m', chief_complaint='My 5-month-old has a high fever, the soft spot on his head is '
                                                  'bulging and he keeps vomiting.',
                     demographics={'age': 0, 'sex': 'male'}, preliminary_rules=True)
    s.record_initial_vitals('HR 178, RR 48, Temp 39.4, SpO2 97%')
    assert DifferentialEngine().update(s)[0].diagnosis_id == 'meningitis'


# --- Korean caregiver / collapse, chest-pressure similes -------------------------------------------------------------

def test_korean_caregiver_with_honorific_is_the_patient():
    from nova_agent.evidence_scope import detect_proxy_relation
    assert detect_proxy_relation('아버지께서 갑자기 쓰러지셨어요', 'male', 78) == '아버지'


def test_korean_collapse_is_a_symptomatic_rate_concern():
    from nova_agent.disposition import symptomatic_rate_concern
    s = PatientState(chief_complaint='갑자기 쓰러졌어요.', preliminary_rules=True)
    s.record_initial_vitals('BP 100/60, HR 36, RR 16, Temp 36.5, SpO2 96%')
    assert symptomatic_rate_concern(s)


@pytest.mark.parametrize('text,expected', [
    ('It feels like an elephant is sitting on my chest', True), ('a heavy weight pressing on my chest', True),
    ('my chest feels as if something is pressing on it', True), ('the cat was sitting on my chest this morning', False)])
def test_chest_pressure_similes(text, expected):
    s = PatientState(chief_complaint=text, preliminary_rules=True)
    assert ('substernal pressure' in _score_disease(_entry('acute_coronary_syndrome'), s)[2]) is expected


# --- anatomical sex compatibility ------------------------------------------------------------------------------------

@pytest.mark.parametrize('did,sex,expected', [
    ('ectopic_pregnancy', 'male', True), ('onto::tier2:ovarian_torsion', 'male', True),
    ('onto::tier2:testicular_torsion', 'female', True), ('ectopic_pregnancy', 'female', False),
    ('ectopic_pregnancy', None, False), ('onto::tier2:testicular_torsion', '', False),
    ('appendicitis', 'male', False), ('onto::tier2:gu_breast_abscess', 'male', False)])
def test_anatomical_incompatibility_needs_a_recorded_sex(did, sex, expected):
    from nova_agent.anatomic_compat import incompatible
    assert incompatible(did, sex) is expected


@pytest.mark.parametrize('sex,present', [('male', False), ('female', True), (None, True)])
def test_ectopic_pregnancy_is_not_a_candidate_for_a_male(sex, present):
    s = PatientState(case_id='a', chief_complaint='Sharp pain in my right lower belly since last night.',
                     demographics={'age': 22, 'sex': sex}, preliminary_rules=True)
    assert any(d.diagnosis_id == 'ectopic_pregnancy' for d in DifferentialEngine().update(s)) is present


def test_anatomical_switch_off(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_ANATOMIC_COMPAT', '0')
    get_config(reload=True)
    s = PatientState(case_id='a', chief_complaint='Sharp pain in my right lower belly since last night.',
                     demographics={'age': 22, 'sex': 'male'}, preliminary_rules=True)
    assert any(d.diagnosis_id == 'ectopic_pregnancy' for d in DifferentialEngine().update(s))


# --- decision certainty (calibration metadata) -----------------------------------------------------------------------

def _decision(scores):
    s = PatientState(chief_complaint='Burning pain in a strip around my right side, and now little blisters along '
                                     'the same line.', preliminary_rules=True)
    diff = DifferentialEngine().update(s)
    leader = diff[0]
    rival = _item('gerd', 'GERD', ['burning'], scores * leader.score)
    return decide_final(s, [leader, rival])


def test_close_rival_makes_the_named_diagnosis_provisional():
    d = _decision(0.95)
    assert d.certainty == 'PROVISIONAL' and d.close_alternatives == ('gerd',)
    meta = d.as_metadata()
    assert meta['certainty'] == 'PROVISIONAL' and meta['close_alternatives'] == ['gerd']
    assert meta['support'] == 'SUPPORTED'  # the decision itself is unchanged


def test_clear_leader_is_leading():
    assert _decision(0.5).certainty == 'LEADING'


def test_certainty_switch_off(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_DECISION_CERTAINTY', '0')
    get_config(reload=True)
    assert _decision(0.95).certainty == 'LEADING'


# --- EXAM utility contract -------------------------------------------------------------------------------------------

def _exam_utilities(cc, demo, vitals='BP 120/74, HR 76, RR 14, Temp 36.8, SpO2 99%'):
    from nova_agent.action_selector import ActionSelector
    from nova_agent.safety import SafetyLayer
    s = PatientState(case_id='e', chief_complaint=cc, demographics=demo, preliminary_rules=True)
    s.record_initial_vitals(vitals)
    for key in ('onset', 'associated_symptoms', 'past_medical_history'):
        s.record_ask(key, key, 'No.')
    d = DifferentialEngine().update(s)
    _, scored, _ = ActionSelector().generate_and_select(s, d, SafetyLayer().assess(s, d))
    return {c.key: c.utility for c in scored if c.action_type == 'EXAM'}


def test_useful_exam_is_offered_for_the_hypotheses_in_play():
    u = _exam_utilities('Crushing pressure in my chest for an hour, sweaty and sick.', {'age': 61, 'sex': 'male'})
    assert 'cardiac_auscultation' in u and u['cardiac_auscultation'] > 0
    uti = _exam_utilities('Burning when I pee and going all the time.', {'age': 28, 'sex': 'female'})
    assert 'costovertebral_tenderness' in uti  # pyelonephritis vs cystitis


@pytest.mark.parametrize('cc', ['Itchy red eye with crusting this morning.',
                                'Pain and swelling in my big toe since last night.'])
def test_exam_for_catalog_padding_only_is_suppressed(cc):
    u = _exam_utilities(cc, {'age': 40, 'sex': 'male'})
    assert not {'abdominal_exam', 'cardiac_auscultation'} & set(u)


def test_exam_utility_switch_off_restores_the_time_critical_exemption(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_EXAM_UTILITY_V2', '0')
    get_config(reload=True)
    u = _exam_utilities('Itchy red eye with crusting this morning.', {'age': 40, 'sex': 'male'})
    assert {'abdominal_exam', 'cardiac_auscultation'} <= set(u)


# --- Korean family history vs caregiver, subsumed dangerous alternative ---------------------------------------------

def test_korean_topic_relative_without_possessive_stays_family_history():
    from nova_agent.evidence_scope import detect_proxy_relation
    assert detect_proxy_relation('어머니는 irregular heartbeat가 있어요. 저는 지금 아픈 곳이 없어요.', 'female', 46) is None
    assert detect_proxy_relation('우리 아들이 열이 나요', 'male', 5) == '아들'


def test_alternative_made_only_of_a_part_of_the_named_finding_is_not_urgent():
    from nova_agent.disposition import _subsumed_by_selected
    zoster = _item('onto::tier2:herpes_zoster', 'Shingles', ['band-like blistering rash', 'burning pain on one side of body'], 2.0)
    meningitis = _item('meningitis', 'Meningitis', ['rash'], 0.6, dangerous=True)
    assert _subsumed_by_selected(meningitis, zoster)
    febrile = _item('meningitis', 'Meningitis', ['rash', 'fever'], 0.9, dangerous=True)
    assert not _subsumed_by_selected(febrile, zoster)
    gout = _item('onto::tier2:gout', 'Gout', ['sudden hot red swollen joint'], 1.5)
    septic = _item('onto::tier2:septic_arthritis', 'Septic arthritis', ['hot swollen painful joint'], 1.0, dangerous=True)
    assert not _subsumed_by_selected(septic, gout)  # similar, not a literal part: stays a dangerous alternative


def test_subsumed_switch_off(monkeypatch):
    from nova_agent.config import get_config
    from nova_agent.disposition import _subsumed_by_selected
    monkeypatch.setenv('NOVA_DISPOSITION_SUBSUMED', '0')
    get_config(reload=True)
    zoster = _item('onto::tier2:herpes_zoster', 'Shingles', ['band-like blistering rash'], 2.0)
    assert not _subsumed_by_selected(_item('meningitis', 'Meningitis', ['rash'], 0.6, dangerous=True), zoster)
