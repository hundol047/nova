"""Round V mechanisms: disposition over-triage controls, age-specific rate thresholds, optional-feature denial weight,
bedside sign links, multilingual chest-pain and congestion wording. Engineering contracts on synthetic text, not
clinical validation."""
import pytest

from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.disposition import _alternative_corroborated, disposition_for
from nova_agent.final_decision import _generic_symptom, _risk_context, decide_final
from nova_agent.matching import feature_present_with_aliases
from nova_agent.models import VitalSigns
from nova_agent.state import PatientState
from nova_agent.vitals_parser import describe_vital_sign_abnormalities, red_flag_rules_for_age


@pytest.fixture(autouse=True)
def config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_LLM_PROVIDER', 'mock')
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL', '1')
    get_config(reload=True)
    yield
    monkeypatch.undo()
    get_config(reload=True)


def _item(did, name, support, dangerous=True, urgency='HIGH', score=1.0):
    return DifferentialItem(diagnosis=name, diagnosis_id=did, rank=1, score=score, score_ratio=0.5,
                            supporting_evidence=list(support), contradictory_evidence=[], urgency=urgency,
                            dangerous_if_missed=dangerous, confidence_band='LOW')


# --- age-specific rate thresholds (NICE NG143 Table 1) -------------------------------------------------------------

def test_toddler_rates_are_judged_with_under_5_thresholds():
    toddler = describe_vital_sign_abnormalities(VitalSigns(heart_rate=120, respiratory_rate=24), age=2)
    assert not {'Marked tachycardia', 'Tachypnea', 'Tachycardia'} & set(toddler)
    assert 'Marked tachycardia' in describe_vital_sign_abnormalities(VitalSigns(heart_rate=145), age=2)
    assert 'Tachypnea' in describe_vital_sign_abnormalities(VitalSigns(respiratory_rate=45), age=3)
    adult = describe_vital_sign_abnormalities(VitalSigns(heart_rate=120, respiratory_rate=24), age=30)
    assert {'Marked tachycardia', 'Tachypnea'} <= set(adult)
    # Unknown age keeps the adult rules; other vital rules are unchanged for children.
    assert 'Marked tachycardia' in describe_vital_sign_abnormalities(VitalSigns(heart_rate=120))
    assert 'Hypoxia' in describe_vital_sign_abnormalities(VitalSigns(spo2=90), age=2)


def test_infant_and_toddler_limits_follow_the_age_bands():
    limits = {age: {r['field']: r['value'] for r in red_flag_rules_for_age(age)} for age in (0, 1, 4)}
    assert limits[0]['heart_rate'] == 160 and limits[1]['heart_rate'] == 150 and limits[4]['heart_rate'] == 140
    assert limits[0]['respiratory_rate'] == 50 and limits[1]['respiratory_rate'] == 40


def test_pediatric_thresholds_switch_restores_adult_rules(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_PEDIATRIC_VITALS', '0')
    get_config(reload=True)
    assert 'Marked tachycardia' in describe_vital_sign_abnormalities(VitalSigns(heart_rate=120), age=2)


def test_febrile_toddler_with_normal_for_age_rates_is_not_urgent_by_vitals():
    s = PatientState(chief_complaint='My toddler has a fever and pulls at his ear.', preliminary_rules=True)
    s.demographics.age = 2
    s.record_initial_vitals('HR 120, RR 24, Temp 38.4, SpO2 99%')
    d = DifferentialEngine().update(s)
    disp = disposition_for(s, decide_final(s, d, 'information_exhausted'), d)
    assert not any(r.startswith('observed_vital_red_flag:') for r in disp.reasons)
    s2 = PatientState(chief_complaint='My toddler has a fever.', preliminary_rules=True)
    s2.demographics.age = 2
    s2.record_initial_vitals('HR 168, RR 52, Temp 39.6, SpO2 99%')
    d2 = DifferentialEngine().update(s2)
    assert disposition_for(s2, decide_final(s2, d2, 'information_exhausted'), d2).urgent


# --- disposition: sourced non-emergency labels and context-only alternatives --------------------------------------

def test_sourced_non_emergency_tier2_label_alone_is_not_urgent():
    s = PatientState(chief_complaint='My big toe is red and swollen.', preliminary_rules=True)
    s.record_initial_vitals('BP 128/80, HR 82, RR 14, Temp 37.0, SpO2 98%')
    gout = _item('onto::tier2:gout', 'Acute Gout Flare', ['big toe joint involvement', 'night onset'], urgency='URGENT')
    final = decide_final(s, [gout], 'supported')
    assert not disposition_for(s, final, [gout]).urgent
    # An unsourced Tier-2 label keeps its metadata urgency, and a red-flag vital still escalates the sourced one.
    dvt = _item('onto::tier2:deep_vein_thrombosis', 'Deep Vein Thrombosis', ['unilateral calf swelling'])
    assert disposition_for(s, decide_final(s, [dvt], 'supported'), [dvt]).urgent
    s2 = PatientState(chief_complaint='My big toe is red and swollen.', preliminary_rules=True)
    s2.record_initial_vitals('BP 84/50, HR 128, RR 24, Temp 39.4, SpO2 96%')
    assert disposition_for(s2, decide_final(s2, [gout], 'supported'), [gout]).urgent


def test_disposition_switch_restores_metadata_urgency(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_DISPOSITION_V2', '0')
    get_config(reload=True)
    s = PatientState(chief_complaint='My big toe is red and swollen.', preliminary_rules=True)
    gout = _item('onto::tier2:gout', 'Acute Gout Flare', ['big toe joint involvement'], urgency='URGENT')
    assert disposition_for(s, decide_final(s, [gout], 'supported'), [gout]).urgent


def test_inference_or_context_only_support_does_not_corroborate_a_dangerous_alternative():
    s = PatientState(chief_complaint='It burns when I pee.', preliminary_rules=True)
    assert not _alternative_corroborated(_item('sepsis', 'Sepsis', ['suspected infection source']), s)
    assert not _alternative_corroborated(_item('sepsis', 'Sepsis', ['suspected infection source', 'recent infection']), s)
    assert _alternative_corroborated(_item('sepsis', 'Sepsis', ['suspected infection source', 'fever']), s)


def test_the_selected_diagnosis_is_not_also_counted_as_its_own_alternative():
    s = PatientState(chief_complaint='Crushing chest pain.', preliminary_rules=True)
    acs = _item('acute_coronary_syndrome', 'Acute Coronary Syndrome', ['substernal pressure', 'diaphoresis'],
                urgency='CRITICAL')
    final = decide_final(s, [acs], 'supported')
    reasons = disposition_for(s, final, [acs]).reasons
    assert 'urgent_working_diagnosis:acute_coronary_syndrome' in reasons
    assert not any(r.startswith('supported_dangerous_alternative:acute_coronary_syndrome') for r in reasons)


# --- matching -----------------------------------------------------------------------------------------------------

def test_spot_is_not_spotting():
    assert not feature_present_with_aliases('vaginal bleeding', ['The sore spot on my ribs hurts if I push on it.'])
    assert feature_present_with_aliases('vaginal bleeding', ['I have had some spotting since Monday.'])


def test_situational_context_does_not_make_a_shared_symptom_specific():
    assert _generic_symptom('chest pain after trauma')
    assert _generic_symptom('chest pain')
    from nova_agent.final_decision import _antecedent_context
    assert _antecedent_context('recent cold') and _antecedent_context('recent trauma')
    assert not _antecedent_context('recent onset confusion') and not _risk_context('recent cold')


def test_antecedent_context_alone_does_not_name_but_discriminates_with_current_findings():
    from nova_agent.final_decision import support_problems
    s = PatientState(chief_complaint='Cough after a cold.', preliminary_rules=True)
    alone = _item('acute_bronchitis', 'Acute Bronchitis', ['recent viral illness'], dangerous=False, urgency='LOW')
    assert support_problems(alone, s, [alone]) == ['antecedent_context_only']
    myo = _item('onto::tier2:myocarditis', 'Myocarditis', ['chest pain', 'palpitations', 'recent viral illness'])
    assert 'only_nonspecific_support' not in support_problems(myo, s, [myo])


def test_denial_of_the_core_symptom_refutes_its_qualified_form_only_for_short_plain_denials():
    from nova_agent.differential import _core_symptom_denied
    assert _core_symptom_denied('sudden onset dyspnea', ['no shortness of breath'], [])
    assert not _core_symptom_denied('sudden onset dyspnea', ['not short of breath at rest when sitting still'], [])
    assert not _core_symptom_denied('sudden onset dyspnea', [], ['I am short of breath'])


def test_optional_feature_denial_weighs_less_than_a_positive_feature(monkeypatch):
    from nova_agent.config import get_config
    from nova_agent.differential import CONTRADICTION_PENALTY, DENIAL_V2_CAP, DENIAL_V2_SCALE
    assert CONTRADICTION_PENALTY * DENIAL_V2_SCALE < 1.0
    assert DENIAL_V2_CAP == pytest.approx(1.5 * CONTRADICTION_PENALTY)
    s = PatientState(chief_complaint='Burning when I pee and going often.', preliminary_rules=True)
    s.record_ask('associated_symptoms:urgency', 'Do you feel a sudden urge?', 'No.')
    on = {d.diagnosis_id: d.score for d in DifferentialEngine().update(s)}
    monkeypatch.setenv('NOVA_DENIAL_V2', '0')
    get_config(reload=True)
    off = {d.diagnosis_id: d.score for d in DifferentialEngine().update(s)}
    if 'uncomplicated_cystitis' in on and 'uncomplicated_cystitis' in off:
        assert on['uncomplicated_cystitis'] >= off['uncomplicated_cystitis']


# --- bedside sign links -------------------------------------------------------------------------------------------

@pytest.mark.parametrize('feature,exam', [
    ('third heart sound', 'cardiac_auscultation'), ('grouped vesicles on a red base', 'skin_exam'),
    ('neck stiffness', 'meningeal_signs'), ('calf swelling', 'extremity_exam'), ('pitting edema', 'extremity_exam')])
def test_physical_signs_link_to_existing_catalog_exams(feature, exam):
    from nova_agent.clinical_concepts import bedside_exam_for_feature
    from nova_agent.taxonomy import EXAM_CATALOG
    assert bedside_exam_for_feature(feature) == exam and exam in EXAM_CATALOG


def test_reported_symptoms_are_not_linked_to_an_exam():
    from nova_agent.clinical_concepts import bedside_exam_for_feature
    assert bedside_exam_for_feature('ear pain') is None
    assert bedside_exam_for_feature('night time pain') is None


# --- multilingual wording -----------------------------------------------------------------------------------------

@pytest.mark.parametrize('text,features', [
    ('胸が締め付けられるように痛くて、左腕に広がります', {'substernal pressure', 'radiates to arm or jaw'}),
    ('가슴이 꽉 조이고 왼쪽 팔로 퍼져요', {'substernal pressure', 'radiates to arm or jaw'}),
    ('The pain is in my knee', set())])
def test_japanese_and_korean_pressure_and_spread_wording(text, features):
    from nova_agent.feature_relations import observed_pressure_features
    assert set(observed_pressure_features(text)) == features


@pytest.mark.parametrize('text,feature', [
    ('누우면 숨이 막혀서 앉아서 자요', 'unable to lie flat'),
    ('발목이 퉁퉁 부었어요', 'leg swelling'),
    ('계단을 오르면 숨이 차요', 'shortness of breath on exertion')])
def test_korean_congestion_wording_reaches_existing_phrases(text, feature):
    from nova_agent.multilingual_concepts import english_evidence_for
    assert feature in english_evidence_for(text)


def test_extra_pillows_is_orthopnea_wording():
    assert feature_present_with_aliases('unable to lie flat', ['I need four pillows to sleep now'])


def test_bare_no_to_a_qualified_form_of_a_reported_symptom_is_a_conflict_not_a_denial():
    s = PatientState(chief_complaint='I get breathless walking to the shop.', preliminary_rules=True)
    s.record_ask('associated_symptoms:worsening shortness of breath', 'Is the breathlessness getting worse?', 'No.')
    assert 'no worsening shortness of breath' not in s.pertinent_negatives
    assert 'conflicting answer: worsening shortness of breath' in s.unknown_findings
    s2 = PatientState(chief_complaint='My ankles are puffy.', preliminary_rules=True)
    s2.record_ask('associated_symptoms:worsening shortness of breath', 'Any breathlessness getting worse?', 'No.')
    assert 'no worsening shortness of breath' in s2.pertinent_negatives


def test_sitting_up_to_breathe_at_night_is_orthopnea_wording():
    assert feature_present_with_aliases('unable to lie flat', ['at night I have to sit up to breathe'])
    assert not feature_present_with_aliases('unable to lie flat', ['I do not have to sit up to breathe'])


def test_one_denied_optional_feature_does_not_undo_a_saturated_pattern():
    """Four observed features of one hypothesis keep it above a two-feature competitor after one bare denial."""
    from nova_agent.differential import _soft_saturate, DENIAL_V2_SCALE, CONTRADICTION_PENALTY
    assert _soft_saturate(4.0 - DENIAL_V2_SCALE * CONTRADICTION_PENALTY) > _soft_saturate(2.0)


def _synthetic_scores(answers, explicit=()):
    from nova_agent.differential import _score_disease
    entry = {'id': 'synthetic_pattern', 'typical_features': ['distinctive scarlet markings', 'coarse silver scales',
             'grey fingertips', 'amber halo', 'unilateral swelling'], 'risk_factors': [], 'confirmatory_findings': []}
    s = PatientState(chief_complaint='distinctive scarlet markings; coarse silver scales; grey fingertips; amber halo',
                     preliminary_rules=True)
    base = _score_disease(entry, s)[0]
    for feature in answers:
        s.record_ask(f'associated_symptoms:{feature}', f'Any {feature}?', 'No.')
    s.pertinent_negatives.extend(f'no {f}' for f in explicit)
    return base, _score_disease(entry, s)


def test_bare_no_denial_is_half_weight_inside_the_saturated_class():
    from nova_agent.differential import CONTRADICTION_PENALTY
    base, (score, _, _, contra, _) = _synthetic_scores(['unilateral swelling'])
    assert 'unilateral swelling' in contra
    assert base - CONTRADICTION_PENALTY / 2 <= score < base
    # The same denial in the patient's own words keeps the full contradiction.
    base2, (score2, *_rest) = _synthetic_scores([], explicit=['unilateral swelling'])
    assert score2 == pytest.approx(base2 - CONTRADICTION_PENALTY)


def test_bare_no_does_not_override_the_same_feature_in_the_patients_words():
    from nova_agent.differential import _score_disease
    entry = {'id': 'syn', 'typical_features': ['prodrome of lightheadedness', 'pallor'], 'risk_factors': [],
             'confirmatory_findings': []}
    s = PatientState(chief_complaint='I fainted.', preliminary_rules=True)
    s.record_ask('associated_symptoms:prodrome of lightheadedness', 'Lightheaded first?', 'No.')
    s.record_ask('character', 'Describe it.', 'I felt lightheaded and then fainted.')
    _, _, support, contra, _ = _score_disease(entry, s)
    assert 'prodrome of lightheadedness' in support and 'prodrome of lightheadedness' not in contra
    s2 = PatientState(chief_complaint='I fainted.', preliminary_rules=True)
    s2.record_ask('associated_symptoms', 'Anything else?', 'I was not lightheaded beforehand at all.')
    assert 'prodrome of lightheadedness' not in _score_disease(entry, s2)[2]


def test_reassuring_absence_from_a_bare_no_counts_half():
    from nova_agent.differential import _score_disease
    entry = {'id': 'syn', 'typical_features': ['no chest pain'], 'risk_factors': [], 'confirmatory_findings': []}
    s = PatientState(chief_complaint='I nearly fainted.', preliminary_rules=True)
    s.record_ask('associated_symptoms:chest pain', 'Any chest pain?', 'No.')
    s2 = PatientState(chief_complaint='I nearly fainted.', preliminary_rules=True)
    s2.pertinent_negatives.append('no chest pain')
    assert 0 < _score_disease(entry, s)[0] < _score_disease(entry, s2)[0]


def test_score_ties_are_broken_by_present_findings_not_insertion_order():
    from nova_agent.differential import _rank_key
    observed = (2.0, 0, {}, ['melena', 'lightheadedness'])
    absence = (2.0, 0, {}, ['lightheadedness on standing up', 'no chest pain'])
    assert _rank_key(observed) > _rank_key(absence)


def test_tier2_cause_on_the_same_observations_yields_to_a_near_tied_curated_syndrome():
    s = PatientState(chief_complaint='My whole tummy is rigid and it hurts to move.', preliminary_rules=True)
    s.record_exam('abdominal_exam', 'Board-like rigidity, rebound tenderness.')
    cause = _item('onto::tier2:perforated_viscus', 'Perforated Viscus',
                  ['rigid board-like abdomen', 'rebound tenderness', 'lying still'], score=2.48)
    syndrome = _item('acute_abdomen', 'Acute Abdomen (Surgical Abdomen)', ['rebound tenderness', 'rigid abdomen'],
                     score=2.32)
    decision = decide_final(s, [cause, syndrome], 'supported')
    assert decision.primary_id == 'acute_abdomen'
    assert any(r.startswith('leader:specific_cause_without_discriminating_observation') for r in decision.reasons)
    # A clear lead, or an observed confirmatory finding of the cause, keeps the specific cause.
    far = _item('acute_abdomen', 'Acute Abdomen (Surgical Abdomen)', ['rebound tenderness', 'rigid abdomen'], score=1.5)
    assert decide_final(s, [cause, far], 'supported').primary_id == 'onto::tier2:perforated_viscus'

def test_an_observed_confirmatory_finding_keeps_the_specific_cause(monkeypatch):
    import nova_agent.final_decision as fd
    real = fd._entry
    monkeypatch.setattr(fd, '_entry', lambda did: {'confirmatory_findings': ['guarding with a hard abdominal wall']}
                        if did == 'onto::tier2:perforated_viscus' else real(did))
    s = PatientState(chief_complaint='My whole tummy is rigid and it hurts to move.', preliminary_rules=True)
    s.record_exam('abdominal_exam', 'Guarding with a hard abdominal wall, rebound tenderness.')
    cause = _item('onto::tier2:perforated_viscus', 'Perforated Viscus',
                  ['rigid board-like abdomen', 'rebound tenderness', 'lying still'], score=2.48)
    syndrome = _item('acute_abdomen', 'Acute Abdomen (Surgical Abdomen)', ['rebound tenderness', 'rigid abdomen'],
                     score=2.32)
    assert decide_final(s, [cause, syndrome], 'supported').primary_id == 'onto::tier2:perforated_viscus'


def test_a_near_tied_competitor_from_another_organ_system_is_not_a_broader_syndrome():
    s = PatientState(chief_complaint='Breathless, ankles swollen, crackles.', preliminary_rules=True)
    hf = _item('onto::tier2:heart_failure_acute', 'Acute Decompensated Heart Failure',
               ['worsening shortness of breath', 'leg swelling', 'crackles in lungs'], score=2.40)
    pneumonia = _item('pneumonia', 'Community-Acquired Pneumonia', ['crackles on auscultation', 'dyspnea'], score=2.20)
    assert decide_final(s, [hf, pneumonia], 'supported').primary_id == 'onto::tier2:heart_failure_acute'


def test_hierarchy_switch_off_names_the_leader(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv('NOVA_HIERARCHY_V2', '0')
    get_config(reload=True)
    s = PatientState(chief_complaint='Rigid tummy.', preliminary_rules=True)
    cause = _item('onto::tier2:perforated_viscus', 'Perforated Viscus', ['rigid board-like abdomen', 'rebound tenderness'],
                  score=2.48)
    syndrome = _item('acute_abdomen', 'Acute Abdomen', ['rebound tenderness', 'rigid abdomen'], score=2.32)
    assert decide_final(s, [cause, syndrome], 'supported').primary_id == 'onto::tier2:perforated_viscus'


@pytest.mark.parametrize('feature,text', [('pleuritic chest pain', 'The pain is worse when taking a breath.'),
                                          ('recent surgery', 'Three weeks after hip surgery the ache began.')])
def test_inspiratory_pain_and_operation_wording(feature, text):
    assert feature_present_with_aliases(feature, [text])
