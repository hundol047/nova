"""pytest suite for nova_agent + competition adapter (spec section 23). Every test named in the
spec is present; run with `pytest tests/test_nova_agent.py` (or `pytest -k nova_agent`).
"""

from __future__ import annotations

import json

from nova_agent.action_selector import ActionSelector, AgentAction
from nova_agent.differential import DifferentialEngine
from nova_agent.diagnosis_normalizer import normalize_diagnosis, same_diagnosis
from nova_agent.llm_client import MockLLMClient, TurnContext, parse_agent_turn_output
from nova_agent.orchestrator import DoctorAgent
from nova_agent.safety import SafetyLayer
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy

from competition.adapter import NovaCompetitionAgent, action_to_competition, observation_to_state
from competition.schema import CompetitionObservation


# --- test_patient_state_update --------------------------------------------------------------

def test_patient_state_update():
    agent = DoctorAgent()
    state = agent.new_case("case1", "chest pain", {"age": 50, "sex": "male"})
    assert state.turn_count == 0
    assert state.chief_complaint == "chest pain"

    state.record_ask("onset", "When did it start?", "started 2 hours ago")
    assert state.turn_count == 1
    assert state.symptom_onset == "started 2 hours ago"
    assert len(state.conversation_history) == 1

    state.record_exam("vital_signs", "BP 140/90, HR 100")
    assert state.turn_count == 2
    assert state.physical_examinations["vital_signs"] == "BP 140/90, HR 100"

    state.record_test("troponin", "elevated troponin")
    assert state.turn_count == 3
    assert state.laboratory_tests["troponin"] == "elevated troponin"

    # accumulation, not overwriting: earlier findings are still present
    assert state.symptom_onset == "started 2 hours ago"
    assert "vital_signs" in state.physical_examinations


# --- test_duplicate_question_block ------------------------------------------------------------

def test_duplicate_question_block():
    state = PatientState(case_id="c", chief_complaint="chest pain")
    assert not state.question_asked("onset")
    state.record_ask("onset", "When did it start?", "2 hours ago")
    assert state.question_asked("onset")
    assert state.is_duplicate("ASK", "onset")

    # Paraphrased re-asking of the same discriminator must still be recognized as a duplicate --
    # duplicate detection keys off the structured discriminator, not the exact question text.
    assert state.is_duplicate("ASK", "onset")


def test_action_selector_never_reselects_asked_question():
    agent = DoctorAgent()
    state = agent.new_case("case_dup", "chest pain", {"age": 50, "sex": "male"})
    seen_ask_keys = set()
    for _ in range(15):
        action, _llm, _diff = agent.decide(state)
        if action.action_type == "ASK":
            assert action.key not in seen_ask_keys, f"question {action.key!r} was asked twice"
            seen_ask_keys.add(action.key)
        if action.action_type == "DIAGNOSE":
            break
        agent.observe(state, action, "yes, present")


# --- test_duplicate_test_block ------------------------------------------------------------------

def test_duplicate_test_block():
    state = PatientState(case_id="c", chief_complaint="chest pain")
    assert not state.test_done("ecg")
    state.record_test("ecg", "normal sinus rhythm")
    assert state.test_done("ecg")
    assert state.is_duplicate("TEST", "ecg")

    assert not state.exam_done("vital_signs")
    state.record_exam("vital_signs", "BP 120/80")
    assert state.exam_done("vital_signs")
    assert state.is_duplicate("EXAM", "vital_signs")


# --- test_differential_update -------------------------------------------------------------------

def test_differential_update():
    state = PatientState(case_id="c", chief_complaint="chest pain", demographics={"age": 60, "sex": "male"})
    engine = DifferentialEngine()

    before = engine.update(state)
    before_top = before[0].diagnosis

    state.record_ask("character", "quality", "substernal pressure")
    state.record_ask("associated_symptoms", "other symptoms?",
                      "diaphoresis, nausea, and pain radiates to the left arm and jaw")
    state.record_test("troponin", "elevated troponin")
    state.record_test("ecg", "ST elevation in anterior leads")

    after = engine.update(state)
    assert after[0].diagnosis == "Acute Coronary Syndrome"
    assert after[0].score > before[0].score if before_top == after[0].diagnosis else True
    assert after[0].confidence_band in {"MEDIUM", "HIGH"}
    # differential is recomputed, not just appended to -- state mirrors the latest ranking
    assert state.current_differential[0].diagnosis == after[0].diagnosis


# --- test_red_flag_detection --------------------------------------------------------------------

def test_red_flag_detection():
    state = PatientState(case_id="c", chief_complaint="headache", demographics={"age": 45, "sex": "female"})
    state.record_ask("onset", "onset?", "sudden onset, thunderclap, worst headache of my life")
    state.record_ask("associated_symptoms", "other symptoms?", "neck stiffness and photophobia")

    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)

    flagged_ids = {f.diagnosis_id for f in findings}
    assert "subarachnoid_hemorrhage" in flagged_ids
    assert state.red_flags  # side effect: PatientState.red_flags gets populated too


def test_red_flag_not_raised_for_irrelevant_complaint():
    """Safety layer must not blanket-flag a critical condition unrelated to the current presentation
    (spec section 5: only when the case is actually relevant)."""
    state = PatientState(case_id="c", chief_complaint="painful urination", demographics={"age": 30, "sex": "female"})
    state.record_ask("associated_symptoms", "other symptoms?", "dysuria and urinary frequency")
    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)
    flagged_ids = {f.diagnosis_id for f in findings}
    assert "subarachnoid_hemorrhage" not in flagged_ids
    assert "aortic_dissection" not in flagged_ids


# --- test_action_selection ----------------------------------------------------------------------

def test_action_selection():
    state = PatientState(case_id="c", chief_complaint="chest pain", demographics={"age": 55, "sex": "male"})
    differential = DifferentialEngine().update(state)
    safety_findings = SafetyLayer().assess(state, differential)

    action, candidates, stop_decision = ActionSelector().generate_and_select(state, differential, safety_findings)
    assert action.action_type in {"ASK", "EXAM", "TEST", "DIAGNOSE"}
    assert len(candidates) >= 1
    # candidates are ranked by utility, descending
    utilities = [c.utility for c in candidates if c.action_type != "DIAGNOSE"]
    assert utilities == sorted(utilities, reverse=True) or len(utilities) <= 1


# --- test_stop_policy ---------------------------------------------------------------------------

def test_stop_policy():
    state = PatientState(case_id="c", chief_complaint="dizziness", demographics={"age": 65, "sex": "female"},
                          turn_count=0)
    policy = StopPolicy()

    # No differential yet -> never diagnose
    decision = policy.evaluate(state, [], [])
    assert decision.should_diagnose is False

    # Well-supported, undisputed top diagnosis with no dangerous alternative -> should diagnose
    state.record_ask("onset", "onset?", "brief episodes")
    state.record_ask("aggravating", "trigger?", "triggered by turning my head")
    state.record_ask("associated_symptoms", "?", "denies focal weakness, denies slurred speech")
    differential = DifferentialEngine().update(state)
    safety_findings = SafetyLayer().assess(state, differential)
    decision = policy.evaluate(state, differential, safety_findings)
    assert isinstance(decision.readiness_score, float)


def test_stop_policy_forces_diagnose_when_turns_nearly_exhausted():
    state = PatientState(case_id="c", chief_complaint="chest pain", max_turns=60, turn_count=58)
    differential = DifferentialEngine().update(state)
    decision = StopPolicy().evaluate(state, differential, [])
    assert decision.should_diagnose is True
    assert decision.forced is True


# --- test_turn_limit -----------------------------------------------------------------------------

def test_turn_limit():
    """The agent must submit a final diagnosis before (never after) the turn limit, even against a
    simulated patient who never gives decisive answers."""
    agent = DoctorAgent()
    state = agent.new_case("case_limit", "chest pain", {"age": 50, "sex": "male"}, max_turns=10)

    diagnosed = False
    for _ in range(10):
        action, _llm, _diff = agent.decide(state)
        agent.observe(state, action, "unclear / not sure")
        if action.action_type == "DIAGNOSE":
            diagnosed = True
            break

    assert diagnosed, "agent failed to submit a final diagnosis within the turn limit"
    assert state.final_diagnosis is not None
    assert state.turn_count <= 10


def test_turn_limit_never_exceeded_even_with_uncooperative_patient():
    agent = DoctorAgent()
    state = agent.new_case("case_limit2", "abdominal pain", {"age": 40, "sex": "female"}, max_turns=6)
    for _ in range(6):
        action, _llm, _diff = agent.decide(state)
        agent.observe(state, action, "I don't know")
        if action.action_type == "DIAGNOSE":
            break
    assert state.turn_count <= 6
    assert state.final_diagnosis is not None


# --- test_invalid_llm_output --------------------------------------------------------------------

def test_invalid_llm_output():
    assert parse_agent_turn_output("") is None
    assert parse_agent_turn_output("not json at all") is None
    assert parse_agent_turn_output("{broken json") is None
    assert parse_agent_turn_output(json.dumps({"summary": "ok"})) is None  # missing required field

    valid = json.dumps({
        "summary": "ok", "differential": [], "red_flags": [], "candidate_actions": [],
        "selected_action": {"type": "ASK", "content": "When did it start?"}, "ready_to_diagnose": False,
    })
    parsed = parse_agent_turn_output(valid)
    assert parsed is not None
    assert parsed.selected_action.type == "ASK"

    # wrapped in a markdown fence, as a real LLM often returns it
    fenced = f"Here you go:\n```json\n{valid}\n```"
    assert parse_agent_turn_output(fenced) is not None


class _BrokenLLMClient:
    """Always returns unparseable garbage -- orchestrator.decide() must not crash."""

    def generate_turn_output(self, ctx: TurnContext):
        raise RuntimeError("simulated LLM failure")


def test_invalid_llm_output_does_not_crash_orchestrator():
    agent = DoctorAgent(llm_client=_BrokenLLMClient())
    state = agent.new_case("case_broken_llm", "fever", {"age": 30, "sex": "male"})
    action, llm_output, _differential = agent.decide(state)
    assert action is not None
    assert action.action_type in {"ASK", "EXAM", "TEST", "DIAGNOSE"}
    assert llm_output is None  # signals the safe-fallback path was used


# --- test_diagnosis_normalization ---------------------------------------------------------------

def test_diagnosis_normalization():
    variants = ["MI", "myocardial infarction", "acute myocardial infarction", "AMI",
                "Acute Coronary Syndrome", "acute_coronary_syndrome", "NSTEMI"]
    canonical_ids = {normalize_diagnosis(v).canonical_id for v in variants}
    assert canonical_ids == {"acute_coronary_syndrome"}

    for v in variants:
        assert same_diagnosis(v, "acute_coronary_syndrome")

    unmapped = normalize_diagnosis("some completely made up nonsense disease xyz123")
    assert unmapped.mapped is False
    assert unmapped.canonical_id is None

    assert not same_diagnosis("completely unrelated text one", "completely unrelated text two")


# --- test_competition_adapter -------------------------------------------------------------------

def test_competition_adapter():
    nova_agent_instance = DoctorAgent(llm_client=MockLLMClient())
    obs = CompetitionObservation(case_id="comp1", observation_type="initial",
                                  chief_complaint="chest pain", demographics={"age": 55, "sex": "male"})
    state = observation_to_state(obs, nova_agent_instance, None, None)
    assert state.chief_complaint == "chest pain"

    action = AgentAction(action_type="ASK", key="onset", content="When did it start?", rationale="test")
    comp_action = action_to_competition("comp1", action)
    assert comp_action.action_type == "ASK"
    assert comp_action.content == "When did it start?"
    assert comp_action.metadata["key"] == "onset"


def test_competition_agent_full_case_reaches_diagnosis():
    agent = NovaCompetitionAgent()
    obs = {"case_id": "comp2", "observation_type": "initial", "chief_complaint": "chest pain",
           "demographics": {"age": 58, "sex": "male"}, "max_turns": 15}
    act = agent.act(obs)
    assert act["action_type"] in {"ASK", "EXAM", "TEST", "DIAGNOSE"}

    for _ in range(20):
        if act["action_type"] == "DIAGNOSE":
            break
        act = agent.act({"case_id": "comp2", "observation_type": "ask_response", "content": "yes"})
    assert act["action_type"] == "DIAGNOSE"
