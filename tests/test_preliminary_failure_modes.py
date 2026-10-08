"""Malformed model output, timeouts and network failures never break the preliminary wire contract."""
import socket
import urllib.error

import pytest

from competition.adapter import NovaCompetitionAgent
from evaluation.preliminary_dev_cases import PRELIM_KO_CASES
from evaluation.preliminary_driver import run_episode
from nova_agent.llm_client import BaseLLMClient, MockLLMClient, parse_agent_turn_output
from nova_agent.llm_schema import AgentTurnOutput, SelectedActionOutput
from nova_agent.orchestrator import DoctorAgent

CASE = {c.case_id: c for c in PRELIM_KO_CASES}["PrelimKo_Abd_Appendicitis"]


class _Failing(BaseLLMClient):
    def __init__(self, behaviour):
        self.behaviour = behaviour

    def generate_turn_output(self, ctx):
        self._last_call_was_real, self._last_call_succeeded = True, False
        return self.behaviour(ctx)


def _agent(behaviour):
    return NovaCompetitionAgent(agent=DoctorAgent(llm_client=_Failing(behaviour)), preliminary=True)


def _raise(exc):
    def f(ctx):
        raise exc
    return f


@pytest.mark.parametrize("exc", [TimeoutError("t"), socket.timeout("t"), ConnectionResetError(), ConnectionRefusedError(),
                                 urllib.error.URLError("down"), OSError("net"), ValueError("bad json"), RuntimeError("x")])
def test_network_and_parse_failures_still_end_in_a_valid_preliminary_diagnosis(exc):
    ep = run_episode(CASE, agent=_agent(_raise(exc)))
    assert ep.wire[-1]["action_type"] == "DIAGNOSE" and not ep.violations
    assert all(w["action_type"] in {"SAY", "EXAM", "DIAGNOSE"} for w in ep.wire)
    assert ep.result["interactions"] <= 50 and ep.result["soap_unsupported"] == 0


@pytest.mark.parametrize("make", [
    lambda ctx: AgentTurnOutput(selected_action=SelectedActionOutput(type="TEST", key="ecg", content="ECG")),
    lambda ctx: AgentTurnOutput(selected_action=SelectedActionOutput(type="ASK", key="not_a_catalog_key", content="???")),
    lambda ctx: AgentTurnOutput(selected_action=SelectedActionOutput(type="EXAM", key="made_up_exam", content="x")),
    lambda ctx: AgentTurnOutput(selected_action=SelectedActionOutput(type="DIAGNOSE", key="", content="")),
])
def test_invalid_model_selections_never_reach_the_wire(make):
    ep = run_episode(CASE, agent=_agent(make))
    assert ep.wire[-1]["action_type"] == "DIAGNOSE" and not ep.violations
    assert not any(w["action_type"] == "TEST" for w in ep.wire)


@pytest.mark.parametrize("garbage", ["", "null", "[]", "{", "not json at all", '{"selected_action": 5}',
                                     '{"selected_action": {"type": "TEST", "content": "x"}', "```json\n```", "\x00\x01"])
def test_malformed_model_text_is_rejected_by_the_parser_not_crashed(garbage):
    try:
        out = parse_agent_turn_output(garbage)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"parser must not raise: {exc!r}")
    assert out is None or isinstance(out, AgentTurnOutput)


def test_slow_model_is_cut_off_by_the_case_time_budget(monkeypatch):
    """With the per-case time budget exhausted the engine stops calling the model and finishes deterministically."""
    from nova_agent.config import get_config
    monkeypatch.setenv("NOVA_CASE_TIMEOUT_SECONDS", "0.001")
    get_config(reload=True)

    calls = []

    def slow(ctx):
        calls.append(1)
        raise TimeoutError("would block")

    try:
        ep = run_episode(CASE, agent=_agent(slow))
    finally:
        monkeypatch.undo()
        get_config(reload=True)
    assert ep.wire[-1]["action_type"] == "DIAGNOSE" and not calls and not ep.violations


def test_mock_is_deterministic_run_to_run():
    a = run_episode(CASE, agent=NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True))
    b = run_episode(CASE, agent=NovaCompetitionAgent(agent=DoctorAgent(llm_client=MockLLMClient()), preliminary=True))
    assert [(w["action_type"], w["content"]) for w in a.wire] == [(w["action_type"], w["content"]) for w in b.wire]
