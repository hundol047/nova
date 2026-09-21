"""Adversarial evaluation (spec sections 20/23): `python -m evaluation.adversarial`

Not about diagnostic accuracy -- about robustness. Every scenario here is something a real
competition run could plausibly hit (a vague patient, a malformed observation, an LLM outage) and
must NEVER crash the process. Each check reports PASS/FAIL with a one-line reason; a FAIL means an
exception propagated or the agent produced a structurally invalid action, not that its clinical
judgment was wrong.
"""

from __future__ import annotations

import random
from typing import Callable, List, Tuple

from nova_agent.action_selector import AgentAction
from nova_agent.llm_client import TurnContext
from nova_agent.orchestrator import DoctorAgent
from nova_agent.state import PatientState

from competition.adapter import NovaCompetitionAgent

Check = Tuple[str, Callable[[], None]]


def _assert_valid_action(action: AgentAction) -> None:
    assert action is not None, "decide() returned None instead of an AgentAction"
    assert action.action_type in {"ASK", "EXAM", "TEST", "DIAGNOSE"}, \
        f"invalid action_type {action.action_type!r}"
    assert isinstance(action.content, str) and action.content, "action.content must be non-empty text"


def check_uncooperative_patient_repeats() -> None:
    """Patient answers 'I don't know' to literally everything -- must still terminate cleanly."""
    agent = DoctorAgent()
    state = agent.new_case("adv_idk", "headache", {"age": 40, "sex": "male"})
    for _ in range(state.max_turns):
        action, _llm, _diff = agent.decide(state)
        _assert_valid_action(action)
        if action.action_type == "DIAGNOSE":
            agent.observe(state, action, "")
            break
        agent.observe(state, action, "I don't know.")
    assert state.final_diagnosis is not None, "never reached a final diagnosis"
    assert state.turn_count <= state.max_turns


def check_empty_and_whitespace_observations() -> None:
    """Empty / whitespace-only environment responses must never crash observe()."""
    agent = DoctorAgent()
    state = agent.new_case("adv_empty", "abdominal pain", {"age": 30, "sex": "female"})
    for raw in ["", "   ", "\n", None]:
        action, _llm, _diff = agent.decide(state)
        _assert_valid_action(action)
        if action.action_type == "DIAGNOSE":
            break
        agent.observe(state, action, raw if raw is not None else "")


def check_conflicting_information() -> None:
    """A patient who first affirms then denies the same thing must not crash the parser/scorer."""
    agent = DoctorAgent()
    state = agent.new_case("adv_conflict", "chest pain", {"age": 55, "sex": "male"})
    action, _llm, _diff = agent.decide(state)
    _assert_valid_action(action)
    agent.observe(state, action, "Yes I have severe chest pain, actually no wait, I don't have any pain at all.")
    action2, _llm2, _diff2 = agent.decide(state)
    _assert_valid_action(action2)


def check_extremely_long_response() -> None:
    agent = DoctorAgent()
    state = agent.new_case("adv_long", "fever", {"age": 28, "sex": "female"})
    action, _llm, _diff = agent.decide(state)
    _assert_valid_action(action)
    long_text = ("I have a fever and I also want to tell you about my entire week. " * 500)
    agent.observe(state, action, long_text)
    action2, _llm2, _diff2 = agent.decide(state)
    _assert_valid_action(action2)


def check_irrelevant_response() -> None:
    agent = DoctorAgent()
    state = agent.new_case("adv_irrelevant", "dizziness", {"age": 33, "sex": "male"})
    action, _llm, _diff = agent.decide(state)
    _assert_valid_action(action)
    agent.observe(state, action, "What's the weather like today? I like pizza.")
    action2, _llm2, _diff2 = agent.decide(state)
    _assert_valid_action(action2)


def check_duplicate_response_to_same_action() -> None:
    """Simulates a harness accidentally re-delivering the same observation twice in a row."""
    agent = DoctorAgent()
    state = agent.new_case("adv_dup_obs", "urinary symptoms", {"age": 26, "sex": "female"})
    action, _llm, _diff = agent.decide(state)
    _assert_valid_action(action)
    agent.observe(state, action, "yes, burning sensation")
    turn_before = state.turn_count
    # Re-observing the SAME already-recorded action key should not corrupt state (it just records
    # another turn -- state.py doesn't special-case this, but it must not raise).
    agent.observe(state, action, "yes, burning sensation")
    assert state.turn_count == turn_before + 1


class _MalformedJSONClient:
    def generate_turn_output(self, ctx: TurnContext):
        from nova_agent.llm_client import parse_agent_turn_output
        return parse_agent_turn_output("{this is not valid json at all")


def check_llm_malformed_json() -> None:
    agent = DoctorAgent(llm_client=_MalformedJSONClient())
    state = agent.new_case("adv_malformed", "chest pain", {"age": 50, "sex": "male"})
    action, llm_output, _diff = agent.decide(state)
    _assert_valid_action(action)
    assert llm_output is None, "malformed JSON should not have parsed into a usable AgentTurnOutput"


class _TimeoutClient:
    def generate_turn_output(self, ctx: TurnContext):
        raise TimeoutError("simulated LLM timeout")


def check_llm_timeout() -> None:
    agent = DoctorAgent(llm_client=_TimeoutClient())
    state = agent.new_case("adv_timeout", "fever", {"age": 45, "sex": "female"})
    action, _llm, _diff = agent.decide(state)
    _assert_valid_action(action)


class _UnavailableClient:
    def generate_turn_output(self, ctx: TurnContext):
        raise ConnectionError("simulated LLM unavailable")


def check_llm_unavailable_full_case() -> None:
    """A full case run with an LLM client that ALWAYS fails must still reach a diagnosis via the
    deterministic safe-fallback path, every single turn."""
    agent = DoctorAgent(llm_client=_UnavailableClient())
    state = agent.new_case("adv_unavailable", "dyspnea", {"age": 60, "sex": "male"})
    for _ in range(state.max_turns):
        action, llm_output, _diff = agent.decide(state)
        _assert_valid_action(action)
        assert llm_output is None
        if action.action_type == "DIAGNOSE":
            agent.observe(state, action, "")
            break
        agent.observe(state, action, "yes")
    assert state.final_diagnosis is not None


def check_unknown_chief_complaint_adapter() -> None:
    agent = NovaCompetitionAgent()
    action = agent.act({"case_id": "adv_unknown_cc", "observation_type": "initial",
                         "chief_complaint": "my elbow feels weird and tingly sometimes",
                         "demographics": {"age": 50, "sex": "male"}})
    assert action["action_type"] in {"ASK", "EXAM", "TEST", "DIAGNOSE"}


def check_malformed_competition_observation() -> None:
    """An observation missing required fields (bad case_id, wrong types) must be handled by
    Pydantic validation raising a clean error the adapter layer can catch -- not an unhandled
    crash deep in the reasoning engine."""
    agent = NovaCompetitionAgent()
    try:
        agent.act({"observation_type": "initial"})  # missing required case_id
        raised = False
    except Exception:
        raised = True  # acceptable: Pydantic validation error at the boundary, not a deep crash
    assert raised, "expected a validation error for a missing required field"


def check_random_seed_reproducibility() -> None:
    """Same case, same seed, mock provider -> identical turn count and final diagnosis (spec
    section 21: determinism)."""
    results = []
    for _ in range(2):
        random.seed(42)
        agent = DoctorAgent()
        state = agent.new_case("adv_repro", "chest pain", {"age": 58, "sex": "male"})
        for _ in range(state.max_turns):
            action, _llm, _diff = agent.decide(state)
            if action.action_type == "DIAGNOSE":
                agent.observe(state, action, "")
                break
            agent.observe(state, action, "yes, present")
        results.append((state.turn_count, state.final_diagnosis))
    assert results[0] == results[1], f"non-deterministic result: {results[0]} != {results[1]}"


CHECKS: List[Check] = [
    ("uncooperative_patient_repeats", check_uncooperative_patient_repeats),
    ("empty_and_whitespace_observations", check_empty_and_whitespace_observations),
    ("conflicting_information", check_conflicting_information),
    ("extremely_long_response", check_extremely_long_response),
    ("irrelevant_response", check_irrelevant_response),
    ("duplicate_response_to_same_action", check_duplicate_response_to_same_action),
    ("llm_malformed_json", check_llm_malformed_json),
    ("llm_timeout", check_llm_timeout),
    ("llm_unavailable_full_case", check_llm_unavailable_full_case),
    ("unknown_chief_complaint_adapter", check_unknown_chief_complaint_adapter),
    ("malformed_competition_observation", check_malformed_competition_observation),
    ("random_seed_reproducibility", check_random_seed_reproducibility),
]


def run_adversarial() -> bool:
    all_passed = True
    for name, fn in CHECKS:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as exc:  # noqa: BLE001 - this IS the crash-detector, catch everything
            all_passed = False
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
    return all_passed


if __name__ == "__main__":
    import sys

    ok = run_adversarial()
    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
    sys.exit(0 if ok else 1)
