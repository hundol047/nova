#!/usr/bin/env python3
"""End-to-end smoke of a built submission ZIP over REAL HTTP through the vendored official SDK.

A local stdlib HTTP server plays the organizer API (POST /_nova/ready, GET /v1/session, POST /v1/session/actions,
POST /v1/chat/completions) with a synthetic patient and a scripted Doctor model; the ZIP is extracted into a fresh
directory made read-only and `python -I run.py` runs from an unrelated cwd with an unwritable HOME and
NOVA_GUIDELINES_DIR unset -- the way the organizer container starts it (offline apart from the API).
Checks: exit 0, ready before any case access (else 409 MODEL_NOT_READY), at least one Doctor call, no TEST action,
every SAY/EXAM <= 30 NFC characters, the 15-field record and one main diagnosis.

NOT the organizer server, NOT gpt-oss-20b, NOT a score.

    python scripts/smoke_official_http.py submission/submission.zip
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unicodedata
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RECORD_FIELDS = {"S": ("cc", "hpi", "pmh", "fh", "sh", "ros"), "O": ("exam", "tests"), "A": ("evidence", "differential"),
                 "P": ("tests", "treatment", "disposition", "follow_up", "education")}
TOKEN = "smoke-run-token"


class State:
    def __init__(self):
        self.ready = False
        self.turns = 0
        self.store = {}
        self.events = []
        self.chat_calls = 0
        self.record = None
        self.diagnosis = None
        self.errors = []
        self.deadline = None


def make_handler(state: State):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _error(self, code, err):
            self._send(code, {"error": {"code": err}})

        def _auth(self):
            if self.headers.get("Authorization") != "Bearer " + TOKEN:
                self._error(401, "UNAUTHORIZED")
                return False
            return True

        def do_GET(self):
            if not self._auth():
                return
            if self.path != "/v1/session":
                return self._error(404, "NOT_FOUND")
            if not state.ready:
                state.errors.append("session before ready")
                return self._error(409, "MODEL_NOT_READY")
            self._send(200, {"session_id": "smoke", "status": "active", "turns_remaining": 50 - state.turns,
                             "initial": {"opening": "나는 마흔다섯 살 남자이다. 이틀 전부터 기침과 열이 나서 왔다.",
                                         "vital_signs": "혈압 : 126/80 mmHg\n맥박 : 98 회/분\n호흡 : 22 회/분\n체온 : 38.4°C"},
                             "available_actions": ["SAY", "EXAM", "DIAGNOSE"], "deadline": state.deadline})

        def do_POST(self):
            if not self._auth():
                return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/_nova/ready":
                state.ready = True
                return self._send(200, {"ready": True})
            if not state.ready:
                state.errors.append(f"{self.path} before ready")
                return self._error(409, "MODEL_NOT_READY")
            if self.path == "/v1/chat/completions":
                state.chat_calls += 1
                system = body["messages"][0]["content"]
                if '"questions"' in system:
                    content = json.dumps({"differential": [{"name": "지역사회획득 폐렴", "why": "기침, 발열"}],
                                          "questions": ["가래가 나오나요?", "숨이 차나요?"],
                                          "exams": ["폐 청진을 하겠습니다"]}, ensure_ascii=False)
                elif "primary_diagnosis" in system:
                    content = json.dumps({"primary_diagnosis": "지역사회획득 폐렴", "short_name": "폐렴", "urgent": False,
                                          "evidence": ["이틀 전부터 기침과 열"], "differential": [],
                                          "plan": {"tests": "흉부 X선", "treatment": "항생제 고려", "disposition": "외래",
                                                   "follow_up": "2-3일 후", "education": "호흡곤란 시 내원"}}, ensure_ascii=False)
                else:
                    content = "그런 증상이 있으신가요?"
                return self._send(200, {"id": "x", "object": "chat.completion", "model": "openai/gpt-oss-20b",
                                        "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                                     "finish_reason": "stop"}],
                                        "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280}})
            if self.path != "/v1/session/actions":
                return self._error(404, "NOT_FOUND")
            rid = body.get("request_id")
            if rid in state.store:
                return self._send(200, state.store[rid])
            action = body.get("action")
            if action == "TEST":
                state.errors.append("TEST sent")
                return self._error(400, "ACTION_NOT_AVAILABLE")
            if action == "DIAGNOSE":
                note = body.get("note")
                if not isinstance(note, dict) or {k: set(v) for k, v in note.items()} != {k: set(v) for k, v in RECORD_FIELDS.items()}:
                    state.errors.append("bad record")
                    return self._error(400, "INVALID_RECORD_FIELDS")
                state.record, state.diagnosis = note, body.get("diagnosis")
                response = {"status": "completed", "record_digest": "smoke", "score_status": "not_scored", "turn": state.turns}
                state.store[rid] = response
                return self._send(200, response)
            content = unicodedata.normalize("NFC", body.get("content", ""))
            if not content or len(content) > 30:
                state.turns += 1
                state.errors.append(f"bad length {len(content)}")
                return self._error(400, "CONTENT_TOO_LONG")
            state.turns += 1
            if action == "SAY":
                response = {"status": "OK", "content": "네, 그래요." if "?" in content else "알겠어요.",
                            "turn": state.turns, "turns_remaining": 50 - state.turns}
            else:
                response = {"status": "OK", "result": "우하엽 수포음(+)" if "폐" in content else "특이 소견(-)",
                            "turn": state.turns, "turns_remaining": 50 - state.turns}
            state.events.append((action, content))
            state.store[rid] = response
            return self._send(200, response)
    return Handler


def main():
    zip_path = Path(sys.argv[1]).resolve()
    state = State()
    state.deadline = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "pkg"
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(pkg)
        for p in [pkg, *pkg.rglob("*")]:
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        cwd = Path(tmp) / "elsewhere"
        cwd.mkdir()
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent-home",
               "NOVA_API_BASE": f"http://127.0.0.1:{server.server_address[1]}", "NOVA_RUN_TOKEN": TOKEN,
               "NOVA_SESSION_ID": "smoke", "TMPDIR": tmp}
        proc = subprocess.run([sys.executable, "-I", str(pkg / "run.py")], cwd=cwd, env=env, capture_output=True,
                              text=True, timeout=600)
        for p in [pkg, *pkg.rglob("*")]:
            p.chmod(p.stat().st_mode | stat.S_IWUSR)
    server.shutdown()
    report = {"exit_code": proc.returncode, "ready_before_case_access": not any("before ready" in e for e in state.errors),
              "doctor_calls": state.chat_calls, "turns": state.turns, "test_actions": sum(1 for a, _ in state.events if a == "TEST"),
              "max_action_chars": max((len(c) for _, c in state.events), default=0),
              "record_fields_ok": state.record is not None, "diagnosis": state.diagnosis, "errors": state.errors,
              "stderr_tail": proc.stderr.strip().splitlines()[-5:]}
    ok = (proc.returncode == 0 and not state.errors and state.chat_calls >= 1 and state.record is not None
          and bool((state.diagnosis or "").strip()) and report["max_action_chars"] <= 30)
    report["pass"] = ok
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
