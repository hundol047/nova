"""Hardening of the preliminary-round heuristics: refusal detection, the adaptive time guard, the
always-on submission profile, and the 'suspected ...' feature rule behind the legacy Fever05 fix."""

from __future__ import annotations

import time

import pytest

from competition.submission_profile import build_submission_agent
from evaluation.generalization_dev_cases_round_m import ROUND_M_CASES
from nova_agent.config import PRELIMINARY_CASE_SECONDS, PRELIMINARY_MAX_TURNS
from nova_agent.llm_client import MockLLMClient
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import SAY_MAX_CHARS, detect_language, rejection_signal, say_text
from nova_agent.state import ConversationTurn, PatientState


# ---- refusal detection -------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,content", [
    ({"rejected": True}, "x"), ({"status": "Rejected"}, "x"), ({"status": "not supported"}, "x"),
    ({"error": "unknown exam"}, "x"), ({"ok": False}, "x"), ({"success": False}, "x"),
    (None, ""), (None, "   "),
    (None, "Request rejected: not on the list"), (None, "This examination cannot be performed"),
    (None, "unsupported exam"), (None, "no such examination"), (None, "The request is not in the allowed list"),
    (None, "지원하지 않는 진찰입니다"), (None, "해당 검사는 허용되지 않습니다"),
    (None, "該当の診察は対応していません"), (None, "不支持该检查"),
])
def test_refusals_are_detected(raw, content):
    assert rejection_signal(raw, content)


@pytest.mark.parametrize("content", [
    "Breath sounds not available on the left, crackles heard", "clear breath sounds bilaterally",
    "Unable to hear heart sounds due to noise", "right lower quadrant tenderness with rebound",
    "복부 우하복부 압통, 반발통 있음", "No rash, no obvious infection source",
    "The patient denied the request for a rectal exam but the abdomen is soft, non-tender, " + "x" * 160,
])
def test_clinical_findings_are_not_mistaken_for_refusals(content):
    assert not rejection_signal({"status": "ok", "ok": True}, content)


# ---- adaptive time guard -------------------------------------------------------------------------------
def _state(limit=PRELIMINARY_CASE_SECONDS, elapsed=0.0, turns=0):
    state = PatientState(case_id="t", chief_complaint="cough", time_limit_seconds=limit)
    state.case_started_at_unix = time.time() - elapsed
    for i in range(turns):
        state.performed_actions.append(ConversationTurn(turn=i + 1, action_type="ASK", content="q", key="onset", result="x"))
    return state


def test_time_guard_is_off_without_a_limit_and_quiet_for_a_fast_case():
    assert not _state(limit=None, elapsed=10_000).time_nearly_up()
    assert not _state(elapsed=60, turns=20).time_nearly_up()  # 3 s per turn: nowhere near the budget


def test_fixed_fraction_still_applies():
    assert _state(elapsed=PRELIMINARY_CASE_SECONDS * 0.86, turns=1).time_nearly_up()


def test_slow_turns_force_the_diagnosis_before_the_fixed_fraction():
    # 60 s per turn: after 15 turns 900 s are gone (below 0.85 x 1200 = 1020 s) but the closing dialogue
    # (4 turns x 90 s) would no longer fit in the remaining budget.
    slow = _state(elapsed=900, turns=15)
    assert slow.case_elapsed_seconds < PRELIMINARY_CASE_SECONDS * 0.85 and slow.time_nearly_up()
    assert not _state(elapsed=300, turns=15).time_nearly_up()  # 20 s per turn is fine


# ---- always-on submission profile -----------------------------------------------------------------------
def test_submission_profile_forces_the_rules_on_regardless_of_environment(monkeypatch):
    monkeypatch.setenv("NOVA_PRELIMINARY_RULES", "0")
    monkeypatch.setenv("NOVA_LLM_PROVIDER", "mock")
    from nova_agent.config import get_config
    get_config.cache_clear() if hasattr(get_config, "cache_clear") else None
    agent = build_submission_agent(DoctorAgent(llm_client=MockLLMClient()))
    assert agent.preliminary is True
    case = next(c for c in ROUND_M_CASES if c.case_id == "RoundM_044")
    first = agent.act({"case_id": case.case_id, "observation_type": "initial", "chief_complaint": case.chief_complaint,
                       "demographics": case.demographics, "vital_signs": "BP 118/74, HR 96"})
    state = agent._states[case.case_id]
    assert state.preliminary_rules and state.max_turns == PRELIMINARY_MAX_TURNS
    assert first["action_type"] in {"SAY", "EXAM"} and len(first["content"]) <= SAY_MAX_CHARS * 2
    if first["action_type"] == "SAY":
        assert len(first["content"]) <= SAY_MAX_CHARS


def test_unsupported_scripts_fall_back_to_a_short_english_say():
    for text in ("Болит голова", "أشعر بصداع", "ปวดหัว", "Me duele la cabeza"):
        assert detect_language(text) == "en"
    assert len(say_text("onset", "en")) <= SAY_MAX_CHARS


# ---- inference features ------------------------------------------------------------------------------------
def test_symptom_denials_do_not_refute_a_suspected_source_feature():
    from nova_agent.differential import _score_phrase
    sup, con, mis = [], [], []
    delta = _score_phrase("suspected infection source", 1.0, ["no rash", "denies cough"],
                          ["cough", "burning with urination", "abdominal pain", "rash"], sup, con, mis)
    assert delta == 0.0 and not con and mis == ["suspected infection source"]


def test_mondo_synonyms_are_opt_in():
    from nova_agent.config import get_config
    assert get_config().mondo_synonyms_enabled is False
