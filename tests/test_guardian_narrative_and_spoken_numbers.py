"""Guardian-narrated openings and spoken Korean quantities (found in a real preliminary-server sample trace).

Generic language handling, not a case lookup: the opening below is a synthetic paraphrase with different names and
numbers from any public sample.
"""
import pytest

from nova_agent.korean_numbers import normalize_spoken_numbers, sino_number


@pytest.fixture(autouse=True)
def _preliminary_engine(monkeypatch):
    # Scoped to this module's tests: module-level os.environ edits leak into every later test.
    monkeypatch.setenv("NOVA_PRELIMINARY_RULES", "1")
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "1")
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    from nova_agent.config import get_config
    get_config(reload=True)
    yield
    monkeypatch.undo()
    get_config(reload=True)

OPENING = ("이름은 박서준이고, 일곱 살 남자아이이다. 아빠 박민수, 마흔 살이 보호자로 함께 왔다. 아빠는 서준이 키가 또래에 "
           "비해 작은 것 같아 걱정이 된다고 말했다. 반 친구들보다 서준이 키가 작아 보인다고 한다. 아빠가 집에서 재보니 "
           "일 년 전에는 백십 센티미터였고 지금은 백십오 센티미터 정도였다. 일 년 동안 오 센티미터 정도 자랐다.")


def _state(opening=OPENING):
    from competition.adapter import NovaCompetitionAgent
    from nova_agent.llm_client import MockLLMClient
    from nova_agent.orchestrator import DoctorAgent
    agent = NovaCompetitionAgent(DoctorAgent(llm_client=MockLLMClient()), preliminary=True)
    agent.act({"case_id": "g", "observation_type": "initial", "chief_complaint": normalize_spoken_numbers(opening),
               "vital_signs": "혈압: 100/60 mmHg", "max_turns": 50})
    return agent.state("g")


def test_spoken_korean_quantities_become_digits_only_before_units():
    assert sino_number("백오") == 105 and sino_number("십육") == 16 and sino_number("오십") == 50
    assert normalize_spoken_numbers("지금은 백오 센티미터, 십육 점 오 키로그람") == "지금은 105 cm, 16.5 kg"
    assert normalize_spoken_numbers("칠 킬로 빠졌어요") == "7 kg 빠졌어요"
    # A syllable that is also a numeral, without a unit, is ordinary text.
    for text in ("이름은 김도현이고", "일 년 동안", "이 증상", "수술 이 일 전"):
        assert normalize_spoken_numbers(text) == text


def test_declared_guardian_narration_is_patient_evidence_but_guardian_facts_are_not():
    from nova_agent.evidence_scope import evidence_clauses
    clauses = {c.text.strip(): c.experiencer for c in evidence_clauses(OPENING) if c.text.strip(". ")}
    assert clauses["아빠는 서준이 키가 또래에 비해 작은 것 같아 걱정이 된다고 말했다"] == "PATIENT"
    assert clauses["아빠 박민수, 마흔 살이 보호자로 함께 왔다"] == "FAMILY"
    # Without a declared guardian, a relative's condition stays family history.
    plain = {c.text.strip(): c.experiencer for c in evidence_clauses("엄마는 갑상선 질환이 있다.") if c.text.strip(". ")}
    assert plain["엄마는 갑상선 질환이 있다"] == "FAMILY"
    owned = "엄마 김지영이 보호자로 왔다. 엄마의 키는 작다."
    own = [c for c in evidence_clauses(owned) if "엄마의 키" in c.text]
    assert own and all(c.experiencer != "PATIENT" for c in own)


def test_guardian_narrated_growth_complaint_routes_to_the_growth_interview_with_measured_velocity():
    from nova_agent.clinical_interview import interview_family, next_clinical_action
    from nova_agent.clinical_profiles import profile_observations
    state = _state()
    assert state.demographics.age == 7
    assert interview_family(state) == "growth"
    assert "preserved prepubertal growth velocity" in profile_observations(state)
    assert "short stature" in state.all_findings_text(include_context=False, include_family=False)
    kind, key, text, _ = next_clinical_action(state)
    assert kind == "SAY" and text == "두통이 자주 있나요?"  # risk screen before routine growth history


def test_late_bloomer_parent_is_family_delayed_puberty_not_short_parental_stature():
    import re
    from nova_agent.clinical_profiles import _LATE_BLOOMER, _RELATION
    late = "아빠가 중학교 때까지 작았고 수염도 늦게 났는데, 고등학교에 들어가서 갑자기 많이 컸다고 해요."
    assert re.search(_LATE_BLOOMER, late) and re.search(_RELATION, late)
    assert not re.search(_LATE_BLOOMER, "엄마 키는 백육십오 센티미터예요.")


def test_object_particle_follows_the_final_consonant():
    from competition.nova_sdk_adapter import _object_particle
    assert _object_particle("성장속도 유지") == "를" and _object_particle("작은 키") == "를"
    assert _object_particle("체중 감소") == "를" and _object_particle("손 떨림") == "을"
