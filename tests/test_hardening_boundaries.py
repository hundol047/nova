"""Synthetic boundary evidence, never an organizer transport certification."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from competition.adapter import NovaCompetitionAgent, action_to_competition
from nova_agent.action_selector import AgentAction
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.config import effective_max_turns

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("provider", ["mock", "competition", "anthropic", "openai_compatible", "local", "gemini", "unknown"])
@pytest.mark.parametrize("endpoint", ["https://unauthorized.invalid/v1", "http://127.0.0.1:9/redirect"])
def test_official_entrypoint_never_contacts_any_transport(provider, endpoint):
    env = dict(os.environ, NOVA_LLM_PROVIDER=provider, NOVA_COMPETITION_BASE_URL=endpoint,
               NOVA_OPENAI_BASE_URL=endpoint, HTTP_PROXY=endpoint, HTTPS_PROXY=endpoint,
               ALL_PROXY=endpoint, NOVA_LEARNING_ENABLED="true", NOVA_AUTO_TRAIN="true",
               NOVA_COMPETITION_API_KEY="synthetic-fixture-only")
    code = """import runpy,sys
def guard(event,args):
    if event in ('socket.connect','urllib.Request'):
        raise AssertionError('UNAUTHORIZED_NETWORK_ATTEMPT')
sys.addaudithook(guard)
sys.argv=['run.py','--official','--provider','mock']
runpy.run_path('run.py',run_name='__main__')
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "submission", env=env,
                            input='{"case_id":"private_fixture"}\n', text=True, capture_output=True, timeout=10)
    assert result.returncode == 1 and "EXTERNAL_OFFICIAL_INTERFACE_BLOCKED" in result.stderr
    assert not result.stdout and "UNAUTHORIZED_NETWORK_ATTEMPT" not in result.stderr


def run_cases(order, interleaved=False):
    adapter = NovaCompetitionAgent(DoctorAgent(MockLLMClient()))
    actions = {c: [] for c in order}
    observations = {c: dict(case_id=c, observation_type="initial", max_turns=8,
                           chief_complaint="chest pressure and sweating" if c == "A" else "burning urination") for c in order}
    queue = list(order)
    while queue:
        c = queue[0]
        action = adapter.act(observations[c]); actions[c].append(action)
        if action["action_type"] == "DIAGNOSE":
            queue.pop(0)
            assert c not in adapter._states and c not in adapter._pending_actions
            assert c not in adapter._emitted_actions
        else:
            observations[c] = dict(case_id=c, observation_type="ask_response", content="Normal / negative.")
            if interleaved: queue.append(queue.pop(0))
    return actions


def test_full_case_isolation_and_interleaving():
    a, b = run_cases("A")["A"], run_cases("B")["B"]
    for order, interleaved in [("AB", False), ("BA", False), ("AB", True), ("BA", True)]:
        result = run_cases(order, interleaved)
        assert result == {"A": a, "B": b}


def test_reused_id_exception_cleanup_and_unknown_continuation(monkeypatch):
    adapter = NovaCompetitionAgent(DoctorAgent(MockLLMClient()))
    obs = dict(case_id="reuse", observation_type="initial", chief_complaint="fever", max_turns=1)
    assert adapter.act(obs) == adapter.act(obs)
    with pytest.raises(ValueError, match="initial"):
        adapter.act(dict(case_id="reuse", observation_type="ask_response", content="yes"))
    def fail(state): raise RuntimeError("synthetic exception")
    monkeypatch.setattr(adapter.agent, "decide", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        adapter.act(obs)
    assert not adapter._states and not adapter._pending_actions and not adapter._emitted_actions


def test_development_compatibility_redirect_does_not_forward_credential():
    # This is a retained DEVELOPMENT HTTP helper, not an organizer auth/route assumption.
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.request import Request
    from urllib.error import HTTPError
    from nova_agent.llm_client import CompetitionLLMClient
    observed = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            observed.append((self.path, self.headers.get("X-Synthetic-Credential")))
            self.send_response(302 if self.path == "/redirect" else 200)
            if self.path == "/redirect": self.send_header("Location", "/destination")
            self.end_headers()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        request = Request(f"http://127.0.0.1:{server.server_port}/redirect", headers={"X-Synthetic-Credential": "fixture"})
        with pytest.raises(HTTPError) as result: CompetitionLLMClient()._open_request(request)
        assert result.value.code == 302
        assert observed == [("/redirect", "fixture")]
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.mark.parametrize("limit", [None, 0, -1, 1, 40, 59, 60, 61, 100, 10**100, "invalid", [], True])
def test_actual_emissions_cannot_exceed_requested_hard_cap(monkeypatch, limit):
    agent = DoctorAgent(MockLLMClient())
    monkeypatch.setattr(agent, "decide", lambda state: (AgentAction(action_type="ASK", key="onset", content="When?", rationale="fixture"), None, []))
    adapter = NovaCompetitionAgent(agent)
    obs = dict(case_id="budget", observation_type="initial", chief_complaint="pain", max_turns=limit)
    count = 0
    for _ in range(effective_max_turns(limit)):
        assert adapter.act(obs)["action_type"] == "ASK"
        count += 1
        obs = dict(case_id="budget", observation_type="ask_response", content="No change")
    with pytest.raises(RuntimeError, match="budget exhausted"):
        adapter.act(obs)
    assert count <= 60 and not adapter._states


@pytest.mark.parametrize("action", ["OOD", "UNKNOWN", "INSUFFICIENT_INFORMATION", "UNSUPPORTED_DIAGNOSIS"])
def test_no_unofficial_action_passes_adapter(action):
    # Bypass the internal model to prove the adapter independently rejects it too.
    value = AgentAction.model_construct(action_type=action, key="fixture", content="fixture", rationale="fixture")
    with pytest.raises(ValueError): action_to_competition("case", value)


def test_local_parser_error_does_not_emit_unbudgeted_ask():
    result = subprocess.run([sys.executable, "-m", "competition.local_runner"], cwd=ROOT / "submission",
        env=dict(os.environ, NOVA_LLM_PROVIDER="mock"), input="not json\n", text=True, capture_output=True, timeout=10)
    assert result.returncode == 1 and not result.stdout


@pytest.mark.parametrize("throws", [False, True])
def test_bounded_final_retry_and_exception_cleanup(monkeypatch, throws):
    from dataclasses import replace
    from nova_agent import config
    from competition.adapter import RealLLMUnavailableError
    class Failed(MockLLMClient):
        calls = 0
        def generate_turn_output(self, context):
            self.calls += 1
            self._last_call_was_real = True
            self._last_call_succeeded = False
            if throws: raise RuntimeError("fixture unavailable")
            return super().generate_turn_output(context)
    client = Failed()
    client._last_call_was_real = client._last_call_succeeded = True  # stale preflight
    monkeypatch.setattr(config, "_config", replace(config.get_config(), llm_provider="competition"))
    adapter = NovaCompetitionAgent(DoctorAgent(client))
    with pytest.raises(RealLLMUnavailableError):
        adapter.act(dict(case_id="failure", observation_type="initial", chief_complaint="chest pain", max_turns=1))
    assert client.calls == 3  # first attempt + two internal retries; no patient action emitted
    assert not adapter._states and not adapter._pending_actions and not adapter._emitted_actions
