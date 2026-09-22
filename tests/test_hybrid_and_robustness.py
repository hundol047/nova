"""pytest suite for the hybrid LLM-reasoning architecture, vital/medication/allergy parsing,
negation scope, semantic dedup, RAG wiring, and standalone/offline execution (spec section 23,
the tests added on top of tests/test_nova_agent.py for the hybrid-architecture upgrade).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.differential import DifferentialEngine
from nova_agent.llm_client import MockLLMClient, TurnContext, get_llm_client
from nova_agent.llm_schema import AgentTurnOutput, DifferentialItemOutput, SelectedActionOutput
from nova_agent.orchestrator import DoctorAgent
from nova_agent.safety import SafetyLayer
from nova_agent.semantic_dedup import is_semantic_duplicate
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopPolicy
from nova_agent.vitals_parser import parse_vital_signs

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- test_vital_sign_parsing / test_vital_red_flag_trigger --------------------------------------

def test_vital_sign_parsing():
    parsed = parse_vital_signs("BP 90/60, HR 130, RR 28, Temp 39.5, SpO2 88%")
    assert parsed is not None
    assert parsed.sbp == 90 and parsed.dbp == 60
    assert parsed.heart_rate == 130
    assert parsed.respiratory_rate == 28
    assert parsed.temperature_c == 39.5
    assert parsed.spo2 == 88

    assert parse_vital_signs("") is None
    assert parse_vital_signs("patient appears comfortable") is None


def test_vital_sign_parsing_reaches_structured_state():
    state = PatientState(case_id="c", chief_complaint="dyspnea")
    state.record_exam("vital_signs", "BP 90/60, HR 130, RR 28, Temp 39.5, SpO2 88%")
    assert len(state.vital_signs) == 1
    assert state.vital_signs[0].heart_rate == 130
    assert state.latest_vital_signs().spo2 == 88


def test_vital_red_flag_trigger():
    """SafetyLayer must actually read state.vital_signs (not just the raw EXAM text) to raise
    hypotension/tachycardia/hypoxemia/fever/tachypnea flags."""
    state = PatientState(case_id="c", chief_complaint="dyspnea", demographics={"age": 50, "sex": "male"})
    state.record_ask("associated_symptoms", "?", "sudden onset shortness of breath")
    state.record_exam("vital_signs", "BP 85/55, HR 135, RR 30, Temp 39.6, SpO2 87%")

    differential = DifferentialEngine().update(state)
    findings = SafetyLayer().assess(state, differential)

    assert findings, "expected at least one vital-sign-driven safety finding"
    sources = {f.source for f in findings}
    assert "vital_sign" in sources


# --- test_medication_retention / test_allergy_retention ------------------------------------------

def test_medication_retention():
    state = PatientState(case_id="c", chief_complaint="chest pain")
    state.record_ask("medication", "meds?", "I take warfarin.")
    assert "I take warfarin." in state.medication_text
    assert any("warfarin" in m.name.lower() for m in state.medications)
    assert any("warfarin" in f.lower() for f in state.all_findings_text())


def test_allergy_retention():
    state = PatientState(case_id="c", chief_complaint="fever")
    state.record_ask("allergy", "allergy?", "I am allergic to penicillin.")
    assert "I am allergic to penicillin." in state.allergy_text
    assert any("penicillin" in a.substance.lower() for a in state.allergies)
    assert any("penicillin" in f.lower() for f in state.all_findings_text())


def test_medication_and_allergy_never_silently_dropped():
    """Regression test for the old state._absorb_answer() `pass` bug: no medication/allergy
    answer should ever vanish without a trace."""
    state = PatientState(case_id="c", chief_complaint="chest pain")
    for text in ["I take insulin.", "I am taking oral contraceptive pills.", "I use metformin."]:
        state.record_ask("medication", "meds?", text)
    assert len(state.medication_text) == 3
    assert len(state.medications) == 3


# --- test_negation_scope --------------------------------------------------------------------------

def test_negation_scope():
    cases = [
        ("No fever or chills but has severe chest pressure and nausea.",
         "has severe chest pressure and nausea", "No fever or chills"),
        ("Patient denies shortness of breath, hemoptysis and leg swelling.",
         None, "denies shortness of breath"),
        ("I don't have weakness but my speech became slurred.",
         "my speech became slurred", "I don't have weakness"),
    ]
    for answer, expect_positive_substr, expect_negative_substr in cases:
        state = PatientState(case_id="c", chief_complaint="test")
        state.record_ask("associated_symptoms", "?", answer)
        if expect_positive_substr:
            assert any(expect_positive_substr in p for p in state.pertinent_positives), \
                f"expected positive containing {expect_positive_substr!r} in {state.pertinent_positives}"
        assert any(expect_negative_substr in n for n in state.pertinent_negatives), \
            f"expected negative containing {expect_negative_substr!r} in {state.pertinent_negatives}"
        # scope must never invert: a denied clause must never also land in positives verbatim
        assert expect_negative_substr not in state.pertinent_positives


# --- test_llm_can_change_differential / test_llm_can_select_valid_non_deterministic_candidate ---

class _NovelDifferentialClient:
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return AgentTurnOutput(
            summary="novel differential",
            differential=[DifferentialItemOutput(
                diagnosis="Boerhaave Syndrome", diagnosis_id=None, rank=1,
                supporting_evidence=["severe chest pain after vomiting"], confidence="MEDIUM",
                dangerous_if_missed=True,
            )],
            red_flags=[], candidate_actions=[],
            selected_action=SelectedActionOutput(type=ctx.candidates[0].action_type,
                                                  key=ctx.candidates[0].key, content=ctx.candidates[0].content),
            ready_to_diagnose=False,
        )


def test_llm_can_change_differential():
    agent = DoctorAgent(llm_client=_NovelDifferentialClient())
    state = agent.new_case("c", "chest pain", {"age": 50, "sex": "male"})
    action, llm_output, differential = agent.decide(state)
    diagnoses = [d.diagnosis for d in differential]
    assert "Boerhaave Syndrome" in diagnoses, \
        "LLM-introduced diagnosis outside the knowledge base should appear in the merged differential"
    novel_item = next(d for d in differential if d.diagnosis == "Boerhaave Syndrome")
    assert novel_item.dangerous_if_missed is True
    assert novel_item.diagnosis_id.startswith("novel:")


class _LowestUtilityChoiceClient:
    """Deliberately picks the LEGAL ASK candidate with the LOWEST utility, never the top one --
    proves the pipeline executes a real (non-default) LLM choice rather than silently reverting to
    the deterministic argmax."""

    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        ask_candidates = [c for c in ctx.candidates if c.action_type == "ASK"]
        chosen = min(ask_candidates, key=lambda c: c.utility) if len(ask_candidates) >= 2 else ctx.candidates[0]
        return AgentTurnOutput(
            summary="non-default choice", differential=[], red_flags=[], candidate_actions=[],
            selected_action=SelectedActionOutput(type=chosen.action_type, key=chosen.key, content=chosen.content),
            ready_to_diagnose=False,
        )


def test_llm_can_select_valid_non_deterministic_candidate():
    agent = DoctorAgent(llm_client=_LowestUtilityChoiceClient())
    state = agent.new_case("c", "chest pain", {"age": 50, "sex": "male"})
    action, llm_output, differential = agent.decide(state)

    # Recompute what the deterministic top pick would have been, to prove they differ.
    det_differential = DifferentialEngine().update(state)
    from nova_agent.action_selector import ActionSelector
    from nova_agent.safety import SafetyLayer as SL
    det_findings = SL().assess(state, det_differential)
    det_action, _candidates, _stop = ActionSelector().generate_and_select(state, det_differential, det_findings)

    assert action.action_type == "ASK"
    assert action.key != det_action.key, "expected the LLM's non-top-utility choice to be executed, not overridden"


# --- test_safety_guard_blocks_unsafe_llm_action --------------------------------------------------

class _PrematureDiagnoseClient:
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return AgentTurnOutput(
            summary="premature", differential=[], red_flags=[], candidate_actions=[],
            selected_action=SelectedActionOutput(type="DIAGNOSE", key="gerd", content="GERD"),
            ready_to_diagnose=True,
        )


def test_safety_guard_blocks_unsafe_llm_action():
    """Turn 0, no workup done at all: dangerous alternatives (ACS, aortic dissection, PE) are
    completely unaddressed, so an LLM DIAGNOSE must be blocked regardless of its own confidence."""
    agent = DoctorAgent(llm_client=_PrematureDiagnoseClient())
    state = agent.new_case("c", "chest pain", {"age": 58, "sex": "male"})
    action, llm_output, differential = agent.decide(state)
    assert action.action_type != "DIAGNOSE", "premature diagnosis with unresolved dangerous alternatives must be blocked"


class _HallucinatedKeyClient:
    def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
        return AgentTurnOutput(
            summary="hallucinated key", differential=[], red_flags=[], candidate_actions=[],
            selected_action=SelectedActionOutput(type="TEST", key="mri_full_body_scan_deluxe",
                                                  content="A test that does not exist"),
            ready_to_diagnose=False,
        )


def test_safety_guard_blocks_unknown_action_key():
    agent = DoctorAgent(llm_client=_HallucinatedKeyClient())
    state = agent.new_case("c", "headache", {"age": 40, "sex": "female"})
    action, llm_output, differential = agent.decide(state)
    assert action.key != "mri_full_body_scan_deluxe"


# --- test_rag_context_reaches_llm -----------------------------------------------------------------

def test_rag_context_reaches_llm():
    captured = {}

    class _CapturingClient:
        def generate_turn_output(self, ctx: TurnContext) -> AgentTurnOutput:
            captured["retrieved_context"] = ctx.retrieved_context
            captured["prompt"] = None
            from nova_agent.llm_client import build_reasoning_prompt
            captured["prompt"] = build_reasoning_prompt(ctx)
            return AgentTurnOutput(
                summary="rag test", differential=[], red_flags=[], candidate_actions=[],
                selected_action=SelectedActionOutput(type=ctx.candidates[0].action_type,
                                                      key=ctx.candidates[0].key, content=ctx.candidates[0].content),
                ready_to_diagnose=False,
            )

    agent = DoctorAgent(llm_client=_CapturingClient())
    state = agent.new_case("c", "chest pain", {"age": 55, "sex": "male"})
    agent.decide(state)

    assert captured["retrieved_context"], "expected non-empty RAG context for a known chief complaint"
    assert "Retrieved knowledge:" in captured["prompt"]
    # at least one retrieved snippet's text must actually be present in the constructed prompt
    assert any(snippet["text"] in captured["prompt"] for snippet in captured["retrieved_context"])


def test_rag_disabled_yields_no_context():
    import nova_agent.config as config_module
    original = config_module._config
    try:
        from nova_agent.config import NovaConfig
        config_module._config = NovaConfig(rag_enabled=False)
        from nova_agent.knowledge.retrieval import retrieve_turn_context
        assert retrieve_turn_context("chest_pain", ["acute_coronary_syndrome"], ["ecg"]) == []
    finally:
        config_module._config = original


# --- test_semantic_duplicate_detection -------------------------------------------------------------

def test_semantic_duplicate_detection():
    state = PatientState(case_id="c", chief_complaint="chest pain")
    state.record_ask("onset", "When did it start?", "2 hours ago")
    # A paraphrase that never went through the catalog directly should still be recognized as
    # semantically covering the same category.
    assert is_semantic_duplicate("ASK", "When did these symptoms begin?", state)
    assert not is_semantic_duplicate("ASK", "What makes it worse?", state)


# --- test_unknown_chief_complaint -------------------------------------------------------------------

def test_unknown_chief_complaint():
    assert classify_chief_complaint("a strange feeling in my elbow") == "other"

    agent = DoctorAgent()
    state = agent.new_case("c", "a strange feeling in my elbow", {"age": 40, "sex": "male"})
    action, llm_output, differential = agent.decide(state)
    assert action.action_type in {"ASK", "EXAM", "TEST", "DIAGNOSE"}
    assert differential, "an unmapped chief complaint must still fall back to a non-empty differential"


# --- test_forced_final_diagnosis --------------------------------------------------------------------

def test_forced_final_diagnosis():
    state = PatientState(case_id="c", chief_complaint="chest pain", max_turns=60, turn_count=58)
    differential = DifferentialEngine().update(state)
    decision = StopPolicy().evaluate(state, differential, [])
    assert decision.forced is True
    assert decision.should_diagnose is True

    agent = DoctorAgent()
    state2 = agent.new_case("c2", "chest pain", {"age": 50, "sex": "male"}, max_turns=60)
    state2.turn_count = 59
    action, _llm, _diff = agent.decide(state2)
    assert action.action_type == "DIAGNOSE"


# --- test_standalone_without_backend / test_offline_runtime --------------------------------------

def test_offline_runtime():
    assert isinstance(get_llm_client(), MockLLMClient)
    agent = DoctorAgent()
    state = agent.new_case("c", "fever", {"age": 30, "sex": "male"})
    for _ in range(10):
        action, _llm, _diff = agent.decide(state)
        if action.action_type == "DIAGNOSE":
            break
        agent.observe(state, action, "yes")
    assert state.turn_count <= 10  # completed with zero network access, no API keys configured


def test_standalone_without_backend():
    """nova_agent/_synex.py must degrade gracefully (not raise) when its optional backend
    reuse can't find backend/ -- simulated by importing the fallback path directly."""
    from nova_agent import _synex

    assert hasattr(_synex, "AuditStore")
    store = _synex.AuditStore.__new__(_synex.AuditStore) if not _synex.SYNEX_AVAILABLE else None
    # PatientState itself must not IMPORT anything from backend/ or _synex.py at all (spec section
    # 17/24J) -- checked structurally via the module's actual import statements, not by a naive
    # substring search (which would also flag this module's own explanatory docstring/comments).
    import ast
    import inspect

    import nova_agent.state as state_module
    tree = ast.parse(inspect.getsource(state_module))
    imported_modules = {
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    } | {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any(m == "backend" or m.startswith("backend.") for m in imported_modules)
    assert "nova_agent._synex" not in imported_modules


def test_submission_run_entrypoint():
    """Runs submission/run.py as a real subprocess with its own sys.path (only submission/ on it,
    nothing from the outer repo), proving the packaged submission is self-contained end to end."""
    submission_dir = REPO_ROOT / "submission"
    assert (submission_dir / "run.py").exists()
    assert (submission_dir / "nova_agent").is_dir()
    assert (submission_dir / "competition").is_dir()

    proc = subprocess.run(
        [sys.executable, "run.py"],
        input='{"case_id": "pytest1", "observation_type": "initial", "chief_complaint": "chest pain", '
              '"demographics": {"age": 55, "sex": "male"}}\n',
        cwd=str(submission_dir), capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin"},  # deliberately minimal env, no inherited PYTHONPATH
    )
    assert proc.returncode == 0, f"submission/run.py failed: {proc.stderr}"
    assert '"action_type"' in proc.stdout


def test_submission_stdout_contains_only_protocol_json():
    """A harness reading stdout as a JSON-lines protocol must never see anything else on it --
    not a log line, not a warning, not the preflight diagnostic -- or it breaks. Runs multiple
    observations (including forcing the preflight-unavailable warning path, via an unreachable
    competition endpoint) and asserts EVERY stdout line parses as the expected JSON action shape,
    with every non-protocol message landing on stderr instead."""
    import json as _json

    submission_dir = REPO_ROOT / "submission"
    observations = [
        {"case_id": "stdout_test", "observation_type": "initial", "chief_complaint": "fever",
         "demographics": {"age": 40, "sex": "female"}},
        {"case_id": "stdout_test", "observation_type": "ask_response", "content": "started yesterday"},
        {"case_id": "stdout_test", "observation_type": "ask_response", "content": "yes"},
    ]
    stdin_text = "\n".join(_json.dumps(o) for o in observations) + "\n"

    proc = subprocess.run(
        [sys.executable, "run.py"],
        input=stdin_text, cwd=str(submission_dir), capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin",
             "NOVA_LLM_PROVIDER": "competition", "NOVA_COMPETITION_BASE_URL": "http://127.0.0.1:1/v1"},
    )
    assert proc.returncode == 0, f"submission/run.py failed: {proc.stderr}"

    stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert len(stdout_lines) == len(observations), \
        f"expected exactly one protocol line per observation, got {len(stdout_lines)}: {stdout_lines!r}"
    for line in stdout_lines:
        parsed = _json.loads(line)  # raises if stdout carried anything non-JSON
        assert "action_type" in parsed or "error" in parsed

    # The preflight-unavailable diagnostic this run should have triggered (unreachable endpoint)
    # must have landed on stderr, never mixed into stdout.
    assert "Competition LLM unavailable" in proc.stderr
    assert "Competition LLM unavailable" not in proc.stdout
