"""Official N.O.V.A. SDK integration (nova_sdk 1.0.1): the adapter honours the organizer contract.

A fake server reproduces the documented semantics -- request_id replay, 50 turns, 30-character SAY/EXAM, EXAM
refusals charging one turn (2026-10-11 server behaviour), 503 model failures charging none, the 15-field record --
with a synthetic patient. No organizer sample case text is used here."""
import json
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Load only the SDK from staging. Inserting all of submission/ into sys.path
# could silently test stale staged packages instead of the edited root source.
import importlib.util
if "nova_sdk" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("nova_sdk", ROOT / "submission/nova_sdk.py")
    _sdk_module = importlib.util.module_from_spec(_spec)
    sys.modules["nova_sdk"] = _sdk_module
    _spec.loader.exec_module(_sdk_module)
import nova_sdk  # noqa: E402

from competition import nova_sdk_adapter as A  # noqa: E402


@pytest.fixture(autouse=True)
def engine_config(monkeypatch):
    from nova_agent.config import get_config
    monkeypatch.setenv("NOVA_COMPETITION_RETRIEVAL", "1")
    monkeypatch.setenv("NOVA_PRELIMINARY_RULES", "1")
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    get_config(reload=True)
    yield
    monkeypatch.undo()
    get_config(reload=True)


PATIENT = {
    "언제": "석 달 전부터요.", "약": "아니요, 먹는 약은 없어요.", "병": "특별한 병은 없어요.", "알레르기": "없어요.",
    "가족": "어머니가 갑상선 약을 드세요.", "흡연": "담배는 안 피워요.", "땀": "네, 더위를 많이 타고 땀이 나요.",
    "두근": "가슴이 자주 두근거려요.", "체중": "칠 킬로 빠졌어요.",
}


class FakeServer:
    """Server-side behaviour of the official API (only what the adapter relies on)."""

    def __init__(self, minutes=30, fail=None, chat_reply=None, reject_exam=None, doctor_empty=0):
        self.turns, self.limit, self.closed = 0, 50, False
        self.deadline = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.store = {}            # request_id -> stored response (replay)
        self.fail = list(fail or [])  # queued NovaError codes to raise before processing / after processing
        self.chat_reply = chat_reply
        self.reject_exam = reject_exam or (lambda text: None)
        self.doctor_empty = doctor_empty
        self.chat_calls, self.events, self.record, self.diagnosis = 0, [], None, None

    def session(self):
        return {"session_id": "s", "status": "active", "turns_remaining": self.limit - self.turns,
                "initial": {"opening": "나는 서른두 살 여자이다. 석 달 사이 살이 많이 빠져서 왔다.",
                            "vital_signs": "혈압 : 138/72 mmHg\n맥박 : 102 회/분\n호흡 : 19 회/분\n체온 : 36.9°C"},
                "available_actions": ["SAY", "EXAM", "DIAGNOSE"], "deadline": self.deadline.isoformat()}

    def action(self, body):
        rid = body["request_id"]
        if rid in self.store:
            return self.store[rid]
        if self.closed:
            raise nova_sdk.NovaError("SESSION_CLOSED", 409)
        if self.fail and self.fail[0][0] == "before":
            _, code = self.fail.pop(0)
            raise nova_sdk.NovaError(code, 503)
        kind = body["action"]
        if kind == "TEST":
            raise nova_sdk.NovaError("ACTION_NOT_AVAILABLE", 400)
        if kind == "DIAGNOSE":
            assert set(body["note"]) == set(nova_sdk.RECORD_FIELDS)
            self.record, self.diagnosis, self.closed = body["note"], body["diagnosis"], True
            response = {"status": "completed", "record_digest": "x", "score_status": "pending", "turn": self.turns}
            self.store[rid] = response
            return response
        if self.turns >= self.limit:
            raise nova_sdk.NovaError("TURN_LIMIT_REACHED", 409)
        content = unicodedata.normalize("NFC", body["content"])
        if len(content) > 30:
            self.turns += 1
            raise nova_sdk.NovaError("CONTENT_TOO_LONG", 400)
        if kind == "EXAM":
            refusal = self.reject_exam(content)
            if refusal:
                self.turns += 1
                self.events.append(("EXAM", content, refusal))
                raise nova_sdk.NovaError(refusal, 422)
            result = "갑상선 미만성 비대(+)" if "갑상" in content else "특이 소견(-)"
            self.turns += 1
            response = {"status": "OK", "result": result, "turn": self.turns, "turns_remaining": self.limit - self.turns}
        else:
            answer = next((v for k, v in PATIENT.items() if k in content), "잘 모르겠어요.")
            self.turns += 1
            response = {"status": "OK", "content": answer, "turn": self.turns, "turns_remaining": self.limit - self.turns}
        self.events.append((kind, content, response.get("content") or response.get("result")))
        self.store[rid] = response
        if self.fail and self.fail[0][0] == "after":  # the response is lost on the way back
            _, code = self.fail.pop(0)
            raise nova_sdk.NovaError(code)
        return response

    def chat(self, body):
        self.chat_calls += 1
        if self.doctor_empty > 0:
            self.doctor_empty -= 1
            raise nova_sdk.NovaError("PROVIDER_RESPONSE_INVALID", 503)
        system = body["messages"][0]["content"]
        if self.chat_reply is not None:
            content = self.chat_reply(system, body["messages"][-1]["content"])
        elif '"questions"' in system:
            content = json.dumps({"differential": [{"name": "갑상샘항진증", "why": "체중 감소"}],
                                  "questions": ["더위를 많이 타고 땀이 나나요?", "가슴이 두근거리나요?"],
                                  "exams": ["갑상선을 촉진하겠습니다", "전신 진찰을 다 하겠습니다"]}, ensure_ascii=False)
        elif "primary_diagnosis" in system:
            content = json.dumps({"primary_diagnosis": "갑상샘항진증", "short_name": "갑상샘항진증", "urgent": False,
                                  "evidence": ["석 달 전부터 체중 감소", "환자가 말하지 않은 복통"],
                                  "differential": [{"name": "당뇨병", "reason": "체중 감소 감별"}],
                                  "plan": {"tests": "갑상선 기능 검사", "treatment": "검사 후 결정", "disposition": "외래",
                                           "follow_up": "1주 후", "education": "증상 악화 시 내원"}}, ensure_ascii=False)
        else:
            content = "땀이 많이 나시나요?"
        return {"model": "openai/gpt-oss-20b", "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


class FakeClient(nova_sdk.Client):
    """The official SDK client with its HTTP transport replaced by FakeServer (validation code stays official)."""

    def __init__(self, server):
        super().__init__(api_base="http://nova.test", token="t", session_id="s")
        self.server = server

    def _request(self, method, path, body=None):
        if path == "/v1/session":
            return self.server.session()
        if path == "/v1/session/actions":
            return self.server.action(body)
        if path == "/v1/chat/completions":
            return self.server.chat(body)
        raise nova_sdk.NovaError("NOT_FOUND", 404)


def run(server, prepared=None):
    encounter = A.OfficialEncounter(FakeClient(server), prepared or {}, sleep=lambda s: None, log=lambda m: None)
    result = encounter.run()
    return encounter, result


def test_full_encounter_follows_the_official_contract():
    server = FakeServer()
    enc, result = run(server)
    assert result["status"] == "completed"
    assert set(server.record) == {"S", "O", "A", "P"}
    for section, fields in nova_sdk.RECORD_FIELDS.items():
        assert set(server.record[section]) == set(fields)
        assert all(isinstance(v, str) for v in server.record[section].values())
    assert server.diagnosis.strip() and "\n" not in server.diagnosis
    assert enc.stats.case_relevant_successful >= 1 and server.chat_calls >= 1
    assert all(len(text) <= 30 for kind, text, _ in server.events)
    assert not any(kind == "TEST" for kind, _, _ in server.events)
    assert server.turns <= 50


def test_record_is_grounded_in_the_transcript():
    server = FakeServer()
    run(server)
    record = server.record
    subjective_objective = " ".join(list(record["S"].values()) + list(record["O"].values()))
    assert "복통" not in subjective_objective              # an LLM claim nobody said never enters S/O
    assert "환자가 말하지 않은 복통" not in record["A"]["evidence"]  # ungrounded assessment evidence is dropped
    for kind, text, reply in server.events:
        if kind == "SAY" and reply and text not in ("갑상샘항진증 가능성이 있어요.",):
            from nova_agent.korean_numbers import normalize_spoken_numbers
            reply = normalize_spoken_numbers(reply)  # spoken quantities are recorded as digits ("칠 킬로" -> "7 kg")
            assert reply in " ".join(record["S"].values()) or reply in record["P"]["education"] or "설명" in text


def test_rejected_exam_uses_a_turn_and_yields_no_finding():
    server = FakeServer(reject_exam=lambda text: "EXAM_NOT_SPECIFIC" if "갑상" in text else None)
    enc, _ = run(server)
    rejected = [e for e in server.events if e[0] == "EXAM" and e[2] == "EXAM_NOT_SPECIFIC"]
    assert rejected and enc.exam_rejections == len(rejected)
    assert "갑상선 미만성 비대" not in server.record["O"]["exam"]
    assert sum(1 for e in server.events if e[0] == "EXAM" and "갑상" in e[1]) == 1  # never re-sent
    assert enc.turns_left == 50 - server.turns


def test_lost_response_is_replayed_with_the_same_request_id():
    server = FakeServer(fail=[("after", "API_UNAVAILABLE")])
    enc, _ = run(server)
    say_events = [e for e in server.events if e[0] == "SAY"]
    assert server.turns == len([e for e in server.events if e[0] in ("SAY", "EXAM")])  # no double-charged turn


def test_server_side_model_failure_is_retried_as_a_new_request_without_a_turn():
    server = FakeServer(fail=[("before", "PATIENT_RESPONSE_INVALID")])
    run(server)
    assert server.turns == len([e for e in server.events if e[0] in ("SAY", "EXAM")])


def test_empty_doctor_answers_are_retried():
    server = FakeServer(doctor_empty=2)
    enc, _ = run(server)
    assert enc.stats.empty_retries >= 2 and enc.stats.case_relevant_successful >= 1


def test_encounter_stops_gathering_near_the_server_deadline_and_still_submits():
    server = FakeServer(minutes=3)  # 180 s left: below the gathering margin
    enc, result = run(server)
    assert result["status"] == "completed"
    assert server.turns <= A.CLOSING_TURN_RESERVE
    assert all(t.category in A.COMMUNICATION_CATEGORIES for t in enc.turns)
    assert any(t.category == 'understanding_check' for t in enc.turns)
    assert not any(kind == 'EXAM' for kind, _, _ in server.events)


def test_deadline_parsing():
    assert A.parse_deadline("2026-10-11T07:59:39+00:00") == datetime(2026, 10, 11, 7, 59, 39, tzinfo=timezone.utc).timestamp()
    assert A.parse_deadline("2026-10-11T07:59:39Z") is not None
    assert A.parse_deadline(None) is None and A.parse_deadline("not a date") is None


def test_doctor_unavailable_still_submits_a_record():
    def broken(system, user):
        return ""
    server = FakeServer(chat_reply=broken)
    enc, result = run(server)
    assert result["status"] == "completed" and enc.stats.case_relevant_successful == 0
    assert server.diagnosis.strip()


@pytest.mark.parametrize("text,ok", [("심장 청진을 하겠습니다", True), ("양손을 앞으로 뻗게 해 떨림을 보겠습니다", True),
                                     ("눈, 귀, 코, 목을 관찰하겠습니다", False), ("신체검진 다 해 주세요", False),
                                     ("수면 일지를 작성하겠습니다", False), ("혈액검사를 하겠습니다", False),
                                     ("갑상선을 촉진하고 심장도 청진하겠습니다 그리고 폐도", False)])
def test_single_maneuver_filter(text, ok):
    assert A._single_maneuver(text) is ok


def test_engine_exam_phrasings_are_single_short_maneuvers():
    from nova_agent.preliminary import _EXAM_REQUEST
    for key, table in _EXAM_REQUEST.items():
        assert A.fits(table["ko"]), key


def test_official_limits_are_per_case_and_separate_from_the_internal_target():
    from nova_agent import config
    assert (config.OFFICIAL_SESSION_DOCTOR_CALLS, config.OFFICIAL_SESSION_INPUT_TOKENS,
            config.OFFICIAL_SESSION_OUTPUT_TOKENS) == (200, 500_000, 100_000)
    assert config.OFFICIAL_MAX_TURNS == 50 and config.OFFICIAL_SAY_EXAM_MAX_CHARS == 30
    assert A.DOCTOR_CALL_TARGET < config.OFFICIAL_SESSION_DOCTOR_CALLS


def test_vendored_sdk_is_the_organizer_file():
    import hashlib
    data = (ROOT / "submission" / "nova_sdk.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == "fdd65302e82791ed862c22fe5a014ef443ab331d8986ec7c72b3923add6bc871"
    assert nova_sdk.__version__ == "1.0.1"


def test_submission_entrypoint_runs_the_official_flow():
    text = (ROOT / "submission" / "run.py").read_text(encoding="utf-8")
    assert "run_agent(prepare, consult)" in text and "provider_lock" not in text


@pytest.mark.parametrize("text,age,sex", [("나는 서른두 살 여자이다.", 32, "female"), ("저는 예순두 살 여자이다.", 62, "female"),
                                          ("여섯 살 남자아이이다. 엄마는 서른일곱 살", 6, "male"), ("45세 남자", 45, "male")])
def test_korean_word_ages(text, age, sex):
    from nova_agent.preliminary import parse_first_statement
    assert parse_first_statement(text) == {"age": age, "sex": sex}


def test_korean_labelled_vitals():
    from nova_agent.vitals_parser import parse_vital_signs
    v = parse_vital_signs("혈압 : 138/72 mmHg\n맥박 : 102 회/분\n호흡 : 19 회/분\n체온 : 36.9°C")
    assert (v.sbp, v.dbp, v.heart_rate, v.respiratory_rate, v.temperature_c) == (138, 72, 102, 19, 36.9)


def test_no_public_sample_answer_maps_in_runtime():
    pattern = re.compile(r"\bC0[13]\b|\bC10\b|박선희|최윤정|김도현|수면제 의존|체질성 성장지연|그레이브스")
    for package in ("nova_agent", "competition"):
        for path in (ROOT / package).rglob("*.py"):
            assert not pattern.search(path.read_text(encoding="utf-8")), path


def test_requirements_are_exact_pins():
    lines = [l.strip() for l in (ROOT / "submission" / "requirements.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    assert lines and all(re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][A-Za-z0-9.\-]*", l) for l in lines)
