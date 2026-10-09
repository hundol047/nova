"""Round U follow-up mechanisms: spelling, observed wording, list/alternative features, discriminated naming,
retrieval vocabulary. Engineering contracts on synthetic text, not clinical validation."""
import pytest

from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.final_decision import decide_final, discriminated_by_answers, support_problems
from nova_agent.matching import and_branches, feature_present_with_aliases, or_branches, us_spelling
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


@pytest.mark.parametrize('british,american', [
    ('watery diarrhoea', 'watery diarrhea'), ('pitting oedema', 'pitting edema'), ('Haemoptysis', 'hemoptysis'),
    ('hyperkalaemia', 'hyperkalemia'), ('anaemia', 'anemia'), ('dyspnoea', 'dyspnea'), ('oesophagus', 'esophagus')])
def test_british_spelling_is_the_same_word(british, american):
    assert us_spelling(british).lower() == american


@pytest.mark.parametrize('word', ['four hours', 'your', 'shoe', 'does', 'aerobic', 'canoe', 'Michael'])
def test_spelling_normalisation_leaves_other_words(word):
    assert us_spelling(word) == word


def test_british_spelling_matches_and_negation_still_applies():
    assert feature_present_with_aliases('diarrhea', ['Watery diarrhoea since last night'])
    assert not feature_present_with_aliases('diarrhea', ['No diarrhoea at all'])
    assert feature_present_with_aliases('leg swelling', ['pitting oedema to the knees'])


@pytest.mark.parametrize('text,expected', [
    ('I passed out without any warning while sitting', True),
    ('I never passed out without any warning', False),
    ('I did not pass out', False),
    ('My father passed out without warning', False),
])
def test_alias_containing_a_negation_word(text, expected):
    assert feature_present_with_aliases('syncope without warning', [text]) is expected


def test_or_and_feature_branches():
    assert or_branches('pain relieved or worsened by eating') == ('pain relieved by eating', 'pain worsened by eating')
    assert or_branches('calf pain or tenderness') == ()
    assert and_branches('nausea and vomiting') == ('nausea', 'vomiting')
    assert and_branches('headache with nausea and vomiting') == ()
    assert and_branches('known diabetes and insulin') == ()


def _diff(state):
    return DifferentialEngine().update(state)


def test_list_feature_observed_across_two_statements_counts_once():
    s = PatientState(chief_complaint='I am very thirsty and have nausea.', preliminary_rules=True)
    s.record_ask('associated_symptoms', 'Anything else?', 'I keep vomiting.')
    dka = next(d for d in _diff(s) if d.diagnosis_id == 'diabetic_ketoacidosis')
    assert dka.supporting_evidence.count('nausea and vomiting') == 1


def test_dka_observed_wording_reaches_existing_features():
    s = PatientState(chief_complaint='My insulin pump stopped yesterday. I am very thirsty and have stomach pain.',
                     preliminary_rules=True)
    s.record_ask('past_medical_history', 'Any illnesses?', 'Type 1 diabetes.')
    s.record_exam('general_appearance', 'Deep laboured breathing and dry mucous membranes.')
    dka = next(d for d in _diff(s) if d.diagnosis_id == 'diabetic_ketoacidosis')
    for phrase in ('known diabetes', 'missed insulin doses', 'kussmaul breathing', 'abdominal pain'):
        assert phrase in dka.supporting_evidence
    s2 = PatientState(chief_complaint='My father has type 1 diabetes. I am thirsty.', preliminary_rules=True)
    dka2 = next((d for d in _diff(s2) if d.diagnosis_id == 'diabetic_ketoacidosis'), None)
    assert dka2 is None or 'known diabetes' not in dka2.supporting_evidence


def test_exam_observation_turns_an_earlier_bare_no_into_a_conflict():
    s = PatientState(chief_complaint='Sudden severe belly pain.', preliminary_rules=True)
    s.record_ask('associated_symptoms:lying still', 'Are you lying still?', 'No.')
    assert 'no lying still' in s.pertinent_negatives
    s.record_exam('general_appearance', 'Lying very still, grey.')
    assert 'no lying still' not in s.pertinent_negatives
    assert 'conflicting answer: lying still' in s.unknown_findings


def _item(did, name, score, support, dangerous=False, against=()):
    return DifferentialItem(diagnosis=name, diagnosis_id=did, rank=1, score=score, score_ratio=0.5,
                            supporting_evidence=list(support), contradictory_evidence=list(against), urgency='LOW',
                            dangerous_if_missed=dangerous, confidence_band='LOW')


def _answered_state(answer='No.'):
    s = PatientState(chief_complaint='Bad tummy since last night.', preliminary_rules=True)
    s.record_ask('associated_symptoms', 'Anything else?', 'diarrhea')
    s.record_ask('associated_symptoms:palpitations', 'Any palpitations?', answer)
    return s


def test_single_generic_symptom_named_only_after_competitors_are_discriminated():
    s = _answered_state()
    leader = _item('gastroenteritis', 'Acute Gastroenteritis', 1.0, ['diarrhea'])
    contradicted = _item('hyperthyroidism', 'Hyperthyroidism', 0.2, ['diarrhea'], against=['palpitations'])
    assert discriminated_by_answers(leader, s, [leader, contradicted])
    assert decide_final(s, [leader, contradicted]).primary_id == 'gastroenteritis'
    # A competitor sharing the symptom that was never contradicted keeps the case undifferentiated.
    open_competitor = _item('hyperthyroidism', 'Hyperthyroidism', 0.5, ['diarrhea'])
    assert not discriminated_by_answers(leader, s, [leader, open_competitor])
    # A tie is never broken this way.
    tie = _item('ibs', 'Irritable Bowel Syndrome', 1.0, ['diarrhea'], against=['x'])
    assert not discriminated_by_answers(leader, s, [leader, tie])
    # A dangerous candidate with positive support blocks it.
    danger = _item('gi_bleeding', 'Gastrointestinal Bleeding', 0.3, ['tachycardia'], dangerous=True)
    assert not discriminated_by_answers(leader, s, [leader, contradicted, danger])


def test_unknown_answers_never_discriminate_and_danger_is_never_named_this_way():
    s = _answered_state("I don't know.")
    leader = _item('gastroenteritis', 'Acute Gastroenteritis', 1.0, ['diarrhea'])
    assert not discriminated_by_answers(leader, s, [leader])
    assert decide_final(s, [leader]).primary_id == 'unknown'
    s2 = _answered_state()
    dangerous = _item('sepsis', 'Sepsis', 1.0, ['fever'], dangerous=True)
    assert not discriminated_by_answers(dangerous, s2, [dangerous])


def test_replacing_a_blocked_leader_needs_a_non_generic_observation():
    s = PatientState(chief_complaint='Low belly pain and vomiting.', preliminary_rules=True)
    blocked = _item('ectopic_pregnancy', 'Ectopic Pregnancy', 2.3, ['lower abdominal pain', 'unilateral pelvic pain'],
                    dangerous=True)
    generic_pair = _item('acute_pancreatitis', 'Acute Pancreatitis', 2.0, ['nausea', 'vomiting'])
    decision = decide_final(s, [blocked, generic_pair])
    assert decision.primary_id == 'unknown'
    assert any('required_context_missing' in r for r in decision.reasons)


def test_pain_alone_is_not_a_pregnancy_context():
    s = PatientState(chief_complaint='Sudden lower abdominal pain on one side.', preliminary_rules=True)
    item = _item('ectopic_pregnancy', 'Ectopic Pregnancy', 2.0, ['lower abdominal pain', 'unilateral pelvic pain'],
                 dangerous=True)
    assert any(p.startswith('required_context_missing') for p in support_problems(item, s, [item]))
    s2 = PatientState(chief_complaint='Lower abdominal pain and my period is six weeks late.', preliminary_rules=True)
    assert not any(p.startswith('required_context_missing') for p in support_problems(item, s2, [item]))


@pytest.mark.parametrize('text,expected', [
    ('short of breath', 'dyspnea'), ('I passed out', 'syncope'), ('가슴 통증', 'chest pain'),
    ('胸が締めつけられて冷や汗が出ます', 'chest pain')])
def test_retrieval_vocabulary_maps_observed_wording_to_existing_phrases(text, expected):
    from nova_agent.retrieval_vocabulary import MAX_TERMS, observed_vocabulary_terms
    terms = observed_vocabulary_terms(text)
    assert expected in terms and len(terms) <= MAX_TERMS


@pytest.mark.parametrize('text', ['My father passed out', 'I do not have chest pain', 'Years ago I had chest pain'])
def test_retrieval_vocabulary_ignores_negated_family_and_past_wording(text):
    from nova_agent.retrieval_vocabulary import observed_vocabulary_terms
    assert observed_vocabulary_terms(text) == ()


def test_examined_focal_deficit_supports_stroke_and_negation_does_not():
    s = PatientState(chief_complaint='Sudden dizziness and double vision.', preliminary_rules=True)
    s.record_exam('neuro_exam', 'Focal neurological deficit.')
    stroke = next(d for d in _diff(s) if d.diagnosis_id == 'ischemic_stroke')
    assert 'focal neurological deficit on examination' in stroke.supporting_evidence
    s2 = PatientState(chief_complaint='Sudden dizziness.', preliminary_rules=True)
    s2.record_exam('neuro_exam', 'No focal neurological deficit.')
    stroke2 = next((d for d in _diff(s2) if d.diagnosis_id == 'ischemic_stroke'), None)
    assert stroke2 is None or 'focal neurological deficit on examination' not in stroke2.supporting_evidence


def test_sulfonylurea_class_includes_bnf_names():
    assert feature_present_with_aliases('sulfonylurea use', ['glibenclamide, took two by mistake'])
    assert feature_present_with_aliases('sulfonylurea use', ['I take gliclazide'])
