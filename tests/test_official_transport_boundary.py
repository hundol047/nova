"""The organizer interface is unpublished: the boundary must stay fail-closed and honest."""
import ast
from pathlib import Path

import pytest

from competition.official_transport import (NotConfiguredTransport, OfficialTransport, StubTransport, TransportError,
                                            TransportEvidence, TransportState)

ROOT = Path(__file__).resolve().parents[1]


def test_default_is_fail_closed_and_not_configured():
    t = NotConfiguredTransport()
    with pytest.raises(TransportError, match="NOT_CONFIGURED"):
        t.call("c1", "x")
    assert t.evidence.state == TransportState.NOT_CONFIGURED and not t.evidence.official_success


def test_stub_success_is_never_official_success():
    t = StubTransport(["ok"])
    assert t.call("c1", "x") == "ok"
    assert t.evidence.state == TransportState.RESPONSE_RECEIVED
    assert not t.evidence.official_success and not t.evidence.official_case_call_made("c1")


def test_states_are_only_reached_by_evidence():
    e = TransportEvidence()
    e.note_configured("OFFICIAL")
    assert e.state == TransportState.CONFIGURED
    e.note_attempt()
    assert e.state == TransportState.CALL_ATTEMPTED
    e.note_response("c1", "other/model", None)
    assert e.state == TransportState.RESPONSE_RECEIVED and not e.official_success
    e.note_response("c1", "openai/gpt-oss-20b", None)
    assert e.state == TransportState.MODEL_IDENTITY_VERIFIED
    e.note_response("c1", "openai/gpt-oss-20b", "4d7ae4984b7db7de8f8457170b3f1a419ee76d52")
    assert e.state == TransportState.REVISION_VERIFIED


def test_official_transport_requires_a_case_scoped_response():
    class Fake(OfficialTransport):
        kind = "OFFICIAL"
        def configured(self): return True
        def _send(self, case_id, prompt):
            return {"text": "{}", "model": "openai/gpt-oss-20b", "revision": None}
    t = Fake()
    t.call("A", "p")
    assert t.evidence.official_case_call_made("A") and not t.evidence.official_case_call_made("B")


@pytest.mark.parametrize("reply", [{"text": ""}, {"text": None}, {}, "not a mapping"])
def test_malformed_replies_fail_closed(reply):
    class Fake(StubTransport):
        def _send(self, case_id, prompt): return reply
    with pytest.raises(TransportError):
        Fake().call("c", "p")


def test_transport_exception_becomes_closed_failure():
    t = StubTransport([TimeoutError("slow")])
    with pytest.raises(TransportError):
        t.call("c", "p")
    assert t.evidence.calls_attempted == 1 and t.evidence.responses_received == 0


def test_engine_does_not_depend_on_transport():
    for path in (ROOT / "nova_agent").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                    [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            assert not any(m.startswith("competition") for m in mods), (path, mods)


def test_no_invented_organizer_contract_in_transport_module():
    text = (ROOT / "competition/official_transport.py").read_text(encoding="utf-8")
    for forbidden in ("http://", "https://", "Authorization", "Bearer", "os.environ", "getenv"):
        assert forbidden not in text


def _client(replies, **kw):
    from competition.official_transport import TransportLLMClient
    return TransportLLMClient(StubTransport(replies, **kw))


def test_transport_client_end_to_end_with_stub_is_recorded_as_stub_not_official():
    import json as _json
    from competition.adapter import NovaCompetitionAgent
    from evaluation.cases import CASES
    from evaluation.preliminary_driver import run_episode
    from nova_agent.llm_client import _deterministic_turn_output
    from nova_agent.orchestrator import DoctorAgent

    class Echo(StubTransport):
        def _send(self, case_id, prompt):  # a stub "model" that returns a syntactically valid but trivial answer
            return {"text": _json.dumps({"differential": [], "selected_action": {"type": "ASK", "key": "onset", "content": "When?"}}),
                    "model": self._model, "revision": self._revision}
    client = __import__("competition.official_transport", fromlist=["TransportLLMClient"]).TransportLLMClient(Echo())
    agent = NovaCompetitionAgent(agent=DoctorAgent(llm_client=client), preliminary=True)
    ep = run_episode(CASES[0], agent=agent)
    assert ep.wire[-1]["action_type"] == "DIAGNOSE" and not ep.violations
    ev = client.transport.evidence
    assert ev.kind == "STUB" and ev.responses_received >= 1 and CASES[0].case_id in ev.case_ids_with_response
    assert not ev.official_success and not ev.official_case_call_made(CASES[0].case_id)
    assert ep.result["llm_calls"] >= 1  # engine accounting sees real attempts, but nothing is attested as official


def test_transport_client_failure_falls_back_and_is_not_counted_as_success():
    client = _client([TimeoutError("x")])
    from evaluation.cases import CASES
    from nova_agent.orchestrator import DoctorAgent
    from nova_agent.llm_client import MockLLMClient
    agent = DoctorAgent(llm_client=client)
    state = agent.new_case("t", "chest pain", {"age": 50, "sex": "male"}, 50, preliminary=True)
    client.bind_case("t")
    agent.decide(state)
    assert state.llm_call_count == 1 and state.llm_success_count == 0 and state.llm_failure_count == 1


def test_unconfigured_transport_client_makes_no_real_call():
    from competition.official_transport import TransportLLMClient
    from nova_agent.orchestrator import DoctorAgent
    agent = DoctorAgent(llm_client=TransportLLMClient())
    state = agent.new_case("t", "chest pain", {"age": 50, "sex": "male"}, 50, preliminary=True)
    action, _, _ = agent.decide(state)
    assert state.llm_call_count == 0 and action.action_type in {"ASK", "EXAM", "DIAGNOSE"}
