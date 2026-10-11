"""Round X mechanisms: Korean hyperglycaemia wording, a young child's meningism in a carer's words, the speaker's own
health statement versus a caregiver report, subarachnoid-haemorrhage naming context, and anchors for a dangerous
meningitis alternative. Engineering contracts on synthetic text, not clinical validation."""
import pytest

from nova_agent.differential import DifferentialItem, _score_disease
from nova_agent.final_decision import support_problems
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


def _entry(did):
    from nova_agent.knowledge.retrieval import disease_by_id
    return disease_by_id(did)


def _support(did, text):
    return _score_disease(_entry(did), PatientState(chief_complaint=text, preliminary_rules=True))[2]


def _item(did, support, score=1.0, dangerous=True):
    return DifferentialItem(diagnosis=did, diagnosis_id=did, rank=1, score=score, score_ratio=0.5,
                            supporting_evidence=list(support), contradictory_evidence=[], urgency='HIGH',
                            dangerous_if_missed=dangerous, confidence_band='LOW')


@pytest.mark.parametrize('text,features', [
    ('요즘 갈증이 너무 심하고 밤에도 소변 보러 자꾸 깨요.', {'polydipsia', 'polyuria'}),
    ('목이 계속 말라서 물을 엄청 마셔요. 숨이 깊어요.', {'polydipsia', 'kussmaul breathing'}),
    ('화장실을 계속 가요.', {'polyuria'})])
def test_korean_hyperglycaemia_wording(text, features):
    assert features <= set(_support('diabetic_ketoacidosis', text))


def test_korean_denial_still_cancels():
    assert 'polyuria' not in _support('diabetic_ketoacidosis', '소변이나 체중 변화는 없어요.')


@pytest.mark.parametrize('text', ['세 살 아들이 열이 나고 목을 못 숙이고 빛을 싫어해요.',
                                  'My 2-year-old has a fever, won\'t let me bend her neck forward and cries when the light is on.'])
def test_carer_described_meningism(text):
    assert {'neck stiffness', 'photophobia'} <= set(_support('meningitis', text))


@pytest.mark.parametrize('text,sex,age,relation', [
    ("My father had an irregular heartbeat. I'm just here for a check-up and feel well.", 'male', 50, None),
    ('Mum has atrial fibrillation; I have no symptoms myself.', 'female', 44, None),
    ('My husband collapsed and I called an ambulance', 'male', 60, 'husband'),
    ("My 14-month-old son is burning hot and I'm worried", 'male', 1, 'son'),
    ('우리 아들이 열이 나요. 제가 해열제를 먹였어요', 'male', 5, '아들'),
    ('어머니가 부정맥이 있어요. 저는 괜찮아요', 'female', 46, None)])
def test_own_health_statement_keeps_the_relative_as_family(text, sex, age, relation):
    from nova_agent.evidence_scope import detect_proxy_relation
    assert detect_proxy_relation(text, sex, age) == relation


def test_subarachnoid_haemorrhage_is_named_only_with_a_reported_headache():
    item = _item('subarachnoid_hemorrhage', ['neck stiffness', 'photophobia', 'vomiting'], 2.4)
    child = PatientState(chief_complaint='My 2-year-old has a fever and a stiff neck and hates the light.', preliminary_rules=True)
    assert any(p.startswith('required_context_missing') for p in support_problems(item, child, [item]))
    for text in ('The worst headache of my life came on suddenly, my neck is stiff.',
                 '머리가 깨질 듯이 아프고 목이 뻣뻣해요 and I vomited'):
        adult = PatientState(chief_complaint=text, preliminary_rules=True)
        assert not any(p.startswith('required_context_missing') for p in support_problems(item, adult, [item]))


@pytest.mark.parametrize('support,anchored', [(['photophobia'], False), (['photophobia', 'headache'], False),
                                              (['photophobia', 'fever'], True), (['neck stiffness'], True)])
def test_meningitis_alternative_needs_an_anchor(support, anchored):
    from nova_agent.disposition import _alternative_anchored
    assert _alternative_anchored(_item('meningitis', support)) is anchored


def test_alternative_anchor_switch_off(monkeypatch):
    from nova_agent.config import get_config
    from nova_agent.disposition import _alternative_anchored
    monkeypatch.setenv('NOVA_ALTERNATIVE_ANCHORS', '0')
    get_config(reload=True)
    assert _alternative_anchored(_item('meningitis', ['photophobia']))
