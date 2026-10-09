import pytest
from nova_agent.clinical_concepts import canonical_findings_for
from nova_agent.final_decision import _generic_symptom


@pytest.mark.parametrize('text', ['There is tightness beneath my sternum.',
                                 'Squeezing behind the breastbone starts at rest.',
                                 'There is chest pressure.', 'Tightness across my chest.',
                                 'A heavy weight on my chest.', 'Pressure started deep in my chest.',
                                 'Crushing chest discomfort.'])
def test_pressure_requires_observed_sensation_and_anatomy(text):
    assert 'substernal pressure' in canonical_findings_for(text)


@pytest.mark.parametrize('text', ['Pressure traveling into my right shoulder.',
                                 'An ache spreading to the jaw.', 'Pain into both arms.'])
def test_radiation_preserves_a_sensation_relation(text):
    assert 'radiates to arm or jaw' in canonical_findings_for(text)


@pytest.mark.parametrize('text', ['A rash spreading to my right shoulder.',
    'No squeezing behind my breastbone.', 'My uncle reports tightness beneath his sternum.',
    'Squeezing behind the breastbone cannot be confirmed.', 'An anatomical chart of the sternum.'])
def test_context_cannot_invent_pressure_or_spread(text):
    assert not {'substernal pressure','radiates to arm or jaw'} & set(canonical_findings_for(text))


@pytest.mark.parametrize('phrase,expected', [('vomiting and diarrhea',True),
    ('vomiting and abdominal pain',True),('nausea with fatigue',True),
    ('chest pain with unilateral calf swelling',False),('epigastric pain radiating to back',False),
    ('episodic high blood pressure',False)])
def test_catalog_conjunction_is_not_automatically_discriminating(phrase,expected):
    assert _generic_symptom(phrase) is expected


@pytest.mark.parametrize('text,expected', [('속이 불편하고 토했어요.',True),
    ('토하고 설사해요.',True),('토하지 않았어요.',False),('토요일에 피곤했어요.',False),
    ('어머니가 토했어요. 저는 피곤해요.',False)])
def test_korean_vomiting_keeps_predicate_and_subject(text,expected):
    assert ('vomiting' in canonical_findings_for(text)) is expected


@pytest.mark.parametrize('bp,urgent', [('116/72',False),('78/44',True)])
def test_generic_compound_alternative_and_observed_instability_are_separate(monkeypatch,bp,urgent):
    from nova_agent.config import get_config
    from nova_agent.state import PatientState
    from nova_agent.differential import DifferentialEngine
    from nova_agent.final_decision import decide_final
    from nova_agent.disposition import disposition_for
    monkeypatch.setenv('NOVA_COMPETITION_RETRIEVAL','1');get_config(reload=True)
    try:
        # Isolate the generic conjunction mechanism from unrelated anatomical
        # qualifier matching in other catalog profiles.
        s=PatientState(chief_complaint='Vomiting and diarrhea.', preliminary_rules=True)
        s.record_initial_vitals(f'BP {bp}, HR 76, RR 16, Temp 36.6, SpO2 98%')
        d=DifferentialEngine().update(s);f=decide_final(s,d)
        assert disposition_for(s,f,d).urgent is urgent
        assert not s.laboratory_tests
    finally:
        monkeypatch.undo();get_config(reload=True)
