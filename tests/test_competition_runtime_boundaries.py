"""Local HTTP stubs verify wiring only. They NEVER verify real gpt-oss weights or official API."""
import json
import shutil
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from dataclasses import replace
from nova_agent import config as config_module
from competition.adapter import NovaCompetitionAgent, RealLLMUnavailableError
from nova_agent.config import get_config
from nova_agent.llm_client import CompetitionLLMClient, MockLLMClient
from nova_agent.orchestrator import DoctorAgent

ROOT = Path(__file__).resolve().parents[1]
CONTENT = json.dumps({"differential": [], "selected_action": {
    "type": "ASK", "key": "onset", "content": "When did symptoms start?"}})


@contextmanager
def stub(*, model="openai/gpt-oss-20b", content=CONTENT, delay=0, fail_first=False):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            if fail_first and len(requests) == 1:
                self.send_response(503); self.end_headers(); return
            if delay:
                time.sleep(delay)
            payload = json.dumps({"model": model, "choices": [{"message": {"content": content}}]}).encode()
            try:
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.mark.parametrize("model,content", [("another-model", CONTENT), (None, CONTENT),
    ("openai/gpt-oss-20b", json.dumps({"selected_action": {"type": "ASK", "content": ""}})),
                                          ("openai/gpt-oss-20b", "ready")])
def test_preflight_requires_correct_identity_and_structured_parse(model, content):
    with stub(model=model, content=content) as (url, requests):
        client = CompetitionLLMClient(); client.base_url = url; client.max_retries = 1
        assert client.preflight()[0] is False
        assert len(requests) == 2
        state = DoctorAgent(llm_client=client).new_case("bad", "chest pain")
        DoctorAgent(llm_client=client).decide(state)
        assert state.llm_success_count == 0


def test_timeout_is_bounded_and_retry_recovers():
    with stub(delay=0.15) as (url, requests):
        client = CompetitionLLMClient(); client.base_url = url; client.timeout = 0.03; client.max_retries = 1
        start = time.monotonic()
        assert client.preflight()[0] is False
        assert time.monotonic() - start < 1
        assert len(requests) == 2
    with stub(fail_first=True) as (url, requests):
        client.base_url = url; client.timeout = 1
        assert client.preflight()[0] is True
        assert len(requests) == 2


@pytest.mark.parametrize("budget", [False, True])
def test_real_call_gate_rejects_unattempted_or_budget_skipped_call(monkeypatch, budget):
    monkeypatch.setattr(config_module, "_config", replace(get_config(), llm_provider="competition",
                       case_timeout_seconds=1e-12 if budget else None))
    adapter = NovaCompetitionAgent(DoctorAgent(llm_client=MockLLMClient()))
    with pytest.raises(RealLLMUnavailableError, match="ZERO successful"):
        adapter.act({"case_id": "no_call", "observation_type": "initial", "chief_complaint": "chest pain", "max_turns": 1})


def test_preflight_success_does_not_credit_new_case(monkeypatch):
    monkeypatch.setattr(config_module, "_config", replace(get_config(), llm_provider="competition"))
    with stub() as (url, _):
        client = CompetitionLLMClient(); client.base_url = url; client.max_retries = 0
        assert client.preflight()[0]
        adapter = NovaCompetitionAgent(DoctorAgent(llm_client=client))
        obs = {"case_id": "one", "observation_type": "initial", "chief_complaint": "chest pain", "max_turns": 1}
        assert adapter.act(obs)["metadata"]["real_llm_verified"] is True
        assert adapter._states["one"].llm_success_count == 1
        client.base_url = "http://127.0.0.1:1/v1"
        with pytest.raises(RealLLMUnavailableError):
            adapter.act(dict(obs, case_id="two"))


@pytest.mark.parametrize("mode", ["mock", "unreachable", "stub"])
def test_isolated_submission_runtime_modes(tmp_path, mode):
    isolated = tmp_path / "package"
    shutil.copytree(ROOT / "submission", isolated, ignore=shutil.ignore_patterns("*.zip", "__pycache__"))
    def run(endpoint):
        env = {"PATH": "/usr/bin:/bin", "NOVA_LLM_PROVIDER": "mock" if mode == "mock" else "competition",
               "NOVA_COMPETITION_BASE_URL": endpoint, "NOVA_LLM_MAX_RETRIES": "0", "NOVA_LLM_TIMEOUT_SECONDS": "1"}
        observations = [{"case_id": "isolated", "observation_type": "initial", "chief_complaint": "chest pain", "max_turns": 3},
                        {"case_id": "isolated", "observation_type": "ask_response", "content": "No additional symptoms."},
                        {"case_id": "isolated", "observation_type": "exam_result", "content": "Normal findings."}]
        proc = subprocess.run([sys.executable, "run.py"], cwd=isolated, env=env,
            input="\n".join(json.dumps(x) for x in observations) + "\n", capture_output=True, text=True, timeout=15)
        if mode != "mock":
            assert proc.returncode == 1 and "NOT READY" in proc.stderr
            assert not proc.stdout.strip()
        else:
            assert proc.returncode == 0, proc.stderr
            actions = [json.loads(x) for x in proc.stdout.splitlines()]
            assert actions[-1]["action_type"] == "DIAGNOSE"
            assert actions[-1]["metadata"].get("real_llm_verified") == (True if mode == "stub" else None)
    if mode == "stub":
        with stub() as (url, requests):
            run(url)
            assert len(requests) == 0  # pre-guide submission must not contact even a local stub
            assert all(r["model"] == "openai/gpt-oss-20b" for r in requests)
    else:
        run("http://127.0.0.1:1/v1")


def test_submission_runtime_sync_and_official_schema_honesty():
    from competition.schema import OFFICIAL_API_STATUS, SCHEMA_STATUS
    assert OFFICIAL_API_STATUS == "NOT VERIFIED" and SCHEMA_STATUS == "PLACEHOLDER"
    for name in ("nova_agent", "competition"):
        files = lambda p: {f.relative_to(p): f.read_bytes() for f in p.rglob("*")
                          if f.is_file() and "__pycache__" not in f.parts}
        assert files(ROOT / name) == files(ROOT / "submission" / name)


def test_schema_blocks_official_readiness_even_with_valid_stub():
    with stub() as (url, _):
        proc = subprocess.run([sys.executable, "scripts/preflight_competition.py"], cwd=ROOT,
            env={"PATH": "/usr/bin:/bin", "NOVA_LLM_PROVIDER": "competition", "NOVA_COMPETITION_BASE_URL": url},
            capture_output=True, text=True, timeout=15)
    assert proc.returncode == 1 and "NOT READY" in proc.stdout
    assert "PASS  real_llm_success_count_at_least_1" in proc.stdout
    assert "FAIL  official_competition_schema" in proc.stdout
