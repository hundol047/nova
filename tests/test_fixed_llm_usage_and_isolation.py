"""Fixed-LLM pipeline conditions (preliminary round), verified against a LOCAL stub server only.

The stub is NOT the organizer's endpoint and proves nothing about the real model or the official wire
format; it checks what is under this code's control: every HTTP request is counted (retries included), the
per-case request/token budgets hold, the first call of a case is always attempted, a call carries the
case's own information, and cases do not influence each other."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from competition.adapter import RealLLMUnavailableError
from competition.submission_profile import build_submission_agent
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from nova_agent.config import (PRELIMINARY_CASE_INPUT_TOKENS, PRELIMINARY_MAX_LLM_CALLS_PER_CASE, get_config)
from nova_agent.llm_client import CompetitionLLMClient
from nova_agent.orchestrator import DoctorAgent

MODEL = "openai/gpt-oss-20b"


class _Stub(BaseHTTPRequestHandler):
    mode = "ok"          # ok | garbage | http500
    requests: list = []

    def log_message(self, *args):  # silence
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        type(self).requests.append(body)
        if type(self).mode == "http500":
            self.send_response(500)
            self.end_headers()
            return
        if type(self).mode == "garbage":
            content = "this is not json"
        else:
            content = json.dumps({"differential": [], "selected_action": {"type": "ASK", "key": "onset", "content": "When did it start?"}})
        payload = json.dumps({"model": MODEL, "choices": [{"message": {"content": content}}],
                              "usage": {"prompt_tokens": 1200, "completion_tokens": 80}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture()
def stub(monkeypatch, request):
    _Stub.requests = []
    _Stub.mode = "ok"
    server = HTTPServer(("127.0.0.1", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "competition")
    monkeypatch.setenv("NOVA_COMPETITION_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("NOVA_COMPETITION_API_KEY", "stub-token-not-a-secret")
    monkeypatch.setenv("NOVA_COMPETITION_MODEL", MODEL)
    monkeypatch.setenv("NOVA_LLM_MAX_RETRIES", "2")
    get_config(reload=True)

    def restore():
        server.shutdown()
        monkeypatch.undo()
        get_config(reload=True)
    request.addfinalizer(restore)
    return _Stub


def _run_case(agent, case, max_steps=60):
    obs = {"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
           "demographics": case.demographics, "vital_signs": "BP 118/74, HR 96, Temp 37.9"}
    actions = []
    for _ in range(max_steps):
        act = agent.act(obs)
        actions.append(act)
        if act["action_type"] == "DIAGNOSE":
            break
        pending = agent._pending_actions[case.case_id]
        if act["action_type"] == "SAY":
            obs = {"case_id": case.case_id, "observation_type": "say_response",
                   "content": case.answers.get(pending.key, case.default_answer)}
        else:
            obs = {"case_id": case.case_id, "observation_type": "exam_result",
                   "content": case.exam_results.get(pending.key, case.default_exam_result)}
    return actions


def test_retries_are_counted_as_requests_and_bounded_per_case(stub):
    """Every response unparseable: the client retries inside its allowance and the adapter's own bounded
    re-attempts at DIAGNOSE also stay inside the per-case request cap. With zero successful real-model
    calls the run fails loudly (RealLLMUnavailableError) instead of submitting a fallback-only answer."""
    stub.mode = "garbage"
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    agent = build_submission_agent(DoctorAgent(llm_client=CompetitionLLMClient()))
    with pytest.raises(RealLLMUnavailableError):
        _run_case(agent, case)
    assert 1 <= len(stub.requests) <= PRELIMINARY_MAX_LLM_CALLS_PER_CASE   # every HTTP request counted
    assert all(r["model"] == MODEL for r in stub.requests)


def test_server_http_errors_never_exceed_the_request_cap(stub):
    stub.mode = "http500"
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    agent = build_submission_agent(DoctorAgent(llm_client=CompetitionLLMClient()))
    with pytest.raises(RealLLMUnavailableError):
        _run_case(agent, case)
    assert len(stub.requests) <= PRELIMINARY_MAX_LLM_CALLS_PER_CASE


def test_first_call_carries_this_cases_information_and_is_always_attempted(stub):
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    agent = build_submission_agent(DoctorAgent(llm_client=CompetitionLLMClient()))
    _run_case(agent, case)
    assert stub.requests, "a case must make at least one model call"
    first_prompt = stub.requests[0]["messages"][0]["content"]
    assert case.chief_complaint.split(",")[0][:20].lower() in first_prompt.lower()


def test_successful_calls_use_server_reported_tokens_and_stay_under_the_case_ceiling(stub):
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    llm = CompetitionLLMClient()
    agent = build_submission_agent(DoctorAgent(llm_client=llm))
    _run_case(agent, case)
    n = len(stub.requests)
    assert n <= PRELIMINARY_MAX_LLM_CALLS_PER_CASE
    assert n * 1200 <= PRELIMINARY_CASE_INPUT_TOKENS + 1200    # the ceiling stops further calls


def test_cases_do_not_influence_each_other(stub):
    """Running case B alone and running it after case A on the SAME agent yield the same emitted actions
    (no cross-case state, statistics or predictions are carried over)."""
    a = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    b = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_010")

    def texts(actions):
        return [(x["action_type"], x["content"]) for x in actions]

    solo = texts(_run_case(build_submission_agent(DoctorAgent(llm_client=CompetitionLLMClient())), b))
    shared_agent = build_submission_agent(DoctorAgent(llm_client=CompetitionLLMClient()))
    _run_case(shared_agent, a)
    after = texts(_run_case(shared_agent, b))
    assert solo == after


def test_no_network_calls_outside_the_llm_client():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    # Imports/calls only (prose such as "HTTP requests" in comments is fine).
    pattern = re.compile(r"^\s*(?:import|from)\s+(?:urllib|requests|http\.client|socket|httpx|aiohttp|ftplib|smtplib|websocket)\b"
                         r"|\burlopen\s*\(", re.MULTILINE)
    offenders = []
    for base in ("nova_agent", "competition"):
        for path in (root / base).rglob("*.py"):
            if path.name == "llm_client.py":
                continue
            if pattern.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(root)))
    assert offenders == [], offenders
