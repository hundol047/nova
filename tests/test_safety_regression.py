"""Safety-regression pytest suite added for the hybrid-candidate-expansion / novel-diagnosis /
LLM-differential-hardening upgrade (spec sections 6/7/9/10/29). Each test name here matches one the
task spec explicitly required, so this file is a direct, checkable record that every named
regression is actually covered -- not just described in a docstring elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nova_agent.action_canonicalizer import canonicalize_action
from nova_agent.config import get_config
from nova_agent.llm_client import CompetitionLLMClient, MockLLMClient, get_llm_client
from nova_agent.llm_schema import AgentTurnOutput, DifferentialItemOutput, SelectedActionOutput
from nova_agent.resolution import is_resolved
from nova_agent.safety_validator import SafetyValidator, build_candidate_pool
from nova_agent.state import PatientState
from nova_agent.stop_policy import StopDecision

from evaluation.scoring import score_case
from evaluation.simulator import CaseResult

REPO_ROOT = Path(__file__).resolve().parents[1]


def _reload_config_with_env(**env_overrides):
    """Sets env vars, forces nova_agent.config to reload, and returns a restore callback."""
    import nova_agent.config as config_module

    original_config = config_module._config
    original_env = {k: os.environ.get(k) for k in env_overrides}
    for k, v in env_overrides.items():
        os.environ[k] = v
    get_config(reload=True)

    def restore():
        for k, v in original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config_module._config = original_config

    return restore


# --- test_novel_dangerous_diagnosis_remains_unresolved / _not_auto_resolved --------------------

def test_novel_dangerous_diagnosis_remains_unresolved():
    """resolution.is_resolved(): the actual bug fixed in spec section 6 -- a diagnosis_id with no
    knowledge-base entry (a novel LLM-introduced diagnosis) must default to unresolved, never to
    resolved-because-there-was-nothing-to-check."""
    state = PatientState(case_id="c", chief_complaint="chest pain")
    assert is_resolved("novel:boerhaave_syndrome", [], state) is False
    # Contradictory evidence is still the one legitimate way to resolve even a novel diagnosis.
    assert is_resolved("novel:boerhaave_syndrome", ["endoscopy ruled out esophageal rupture"], state) is True


def test_novel_dangerous_diagnosis_not_auto_resolved():
    """Full safety_validator.validate_action(): a novel, dangerous, unresolved diagnosis in the
    merged differential must block a DIAGNOSE for a different diagnosis, exactly as a known
    dangerous diagnosis would."""
    state = PatientState(case_id="c", chief_complaint="chest pain", demographics={"age": 50, "sex": "male"})
    differential = [
        DifferentialItemOutput(
            diagnosis="Boerhaave Syndrome", diagnosis_id=None, rank=1,
            supporting_evidence=["severe chest pain after forceful vomiting"], confidence="MEDIUM",
            dangerous_if_missed=True,
        ),
        DifferentialItemOutput(
            diagnosis="GERD", diagnosis_id="gerd", rank=2,
            supporting_evidence=["burning sensation"], confidence="LOW", dangerous_if_missed=False,
        ),
    ]
    llm_output = AgentTurnOutput(
        summary="s", differential=differential, red_flags=[], candidate_actions=[],
        selected_action=SelectedActionOutput(type="DIAGNOSE", key="gerd", content="GERD"),
        ready_to_diagnose=True,
    )
    validator = SafetyValidator()
    merged = validator.merge_differential(llm_output, [], [])
    novel_item = next(d for d in merged if d.diagnosis == "Boerhaave Syndrome")
    assert novel_item.diagnosis_id.startswith("novel:")

    # deterministic_action is required and used as the fallback if the LLM's action is rejected.
    from nova_agent.action_selector import AgentAction

    fallback_action = AgentAction(action_type="ASK", key="onset", content="When did it start?", rationale="fallback")
    result = validator.validate_action(
        state, llm_output, build_candidate_pool([]), fallback_action, merged,
        StopDecision(should_diagnose=True, forced=False, reason="", readiness_score=1.0),
    )
    assert result.overridden is True
    assert result.action.action_type != "DIAGNOSE"


# --- test_diagnosis_key_content_consistency / test_diagnose_key_content_mismatch_blocked -------

def test_diagnosis_key_content_consistency():
    """safety_validator.validate_action(): key and content resolving to two DIFFERENT known
    diagnoses (spec section 9's exact example) must be blocked outright, never guessed at."""
    from nova_agent.action_selector import AgentAction

    state = PatientState(case_id="c", chief_complaint="chest pain", demographics={"age": 50, "sex": "male"})
    llm_output = AgentTurnOutput(
        summary="s", differential=[], red_flags=[], candidate_actions=[],
        selected_action=SelectedActionOutput(type="DIAGNOSE", key="gerd", content="Acute Myocardial Infarction"),
        ready_to_diagnose=True,
    )
    fallback_action = AgentAction(action_type="ASK", key="onset", content="When did it start?", rationale="fallback")
    validator = SafetyValidator()
    result = validator.validate_action(
        state, llm_output, build_candidate_pool([]), fallback_action, [],
        StopDecision(should_diagnose=True, forced=False, reason="", readiness_score=1.0),
    )
    assert result.overridden is True
    assert "inconsistent" in result.override_reason.lower()
    assert result.action.action_type != "DIAGNOSE"


def test_diagnose_key_content_mismatch_blocked():
    """End-to-end through DoctorAgent.decide(): the same mismatch, but exercised through the real
    turn pipeline rather than calling safety_validator directly."""
    from nova_agent.orchestrator import DoctorAgent

    class _MismatchedKeyContentClient:
        def generate_turn_output(self, ctx):
            return AgentTurnOutput(
                summary="s", differential=[], red_flags=[], candidate_actions=[],
                selected_action=SelectedActionOutput(type="DIAGNOSE", key="gerd", content="Acute Myocardial Infarction"),
                ready_to_diagnose=True,
            )

    agent = DoctorAgent(llm_client=_MismatchedKeyContentClient())
    state = agent.new_case("c", "painful urination", {"age": 30, "sex": "female"})
    action, _llm_output, _differential = agent.decide(state)
    assert action.action_type != "DIAGNOSE"


# --- test_llm_differential_rank_normalization ---------------------------------------------------

def test_llm_differential_rank_normalization():
    """merge_differential() must survive a deliberately malformed LLM differential: duplicate
    ranks, rank=0, rank=999, and more items than top_k_differential -- producing a clean,
    sequential 1..K ranking with no gaps or duplicate ranks (spec section 10)."""
    top_k = get_config().top_k_differential
    messy = [
        DifferentialItemOutput(diagnosis=f"Novel Disease {i}", diagnosis_id=None, rank=rank,
                                supporting_evidence=["evidence"], confidence="LOW")
        for i, rank in enumerate([0, 0, 999, 3, 3, 1, 1000, 2] + [50] * (top_k + 5))
    ]
    llm_output = AgentTurnOutput(
        summary="s", differential=messy, red_flags=[], candidate_actions=[],
        selected_action=SelectedActionOutput(type="ASK", key="onset", content="When did it start?"),
        ready_to_diagnose=False,
    )
    merged = SafetyValidator().merge_differential(llm_output, [], [])
    assert len(merged) <= top_k
    ranks = [d.rank for d in merged]
    assert ranks == list(range(1, len(merged) + 1)), f"expected clean sequential ranks, got {ranks}"
    assert len(set(d.diagnosis_id for d in merged)) == len(merged), "no duplicate diagnosis_id in the final list"


# --- test_duplicate_diagnosis_alias_merge --------------------------------------------------------

def test_duplicate_diagnosis_alias_merge():
    """Two differential entries that resolve to the SAME diagnosis (one via explicit diagnosis_id,
    one via free-text 'diagnosis' that normalizes to the same canonical id) must be merged into one
    entry with pooled evidence, not appear twice or silently drop one's evidence."""
    llm_output = AgentTurnOutput(
        summary="s",
        differential=[
            DifferentialItemOutput(diagnosis="MI", diagnosis_id="acute_coronary_syndrome", rank=1,
                                    supporting_evidence=["ST elevation"], confidence="HIGH", dangerous_if_missed=True),
            DifferentialItemOutput(diagnosis="Acute Coronary Syndrome", diagnosis_id="acute_coronary_syndrome", rank=2,
                                    supporting_evidence=["elevated troponin"], confidence="HIGH", dangerous_if_missed=True),
        ],
        red_flags=[], candidate_actions=[],
        selected_action=SelectedActionOutput(type="ASK", key="onset", content="When did it start?"),
        ready_to_diagnose=False,
    )
    merged = SafetyValidator().merge_differential(llm_output, [], [])
    acs_entries = [d for d in merged if d.diagnosis_id == "acute_coronary_syndrome"]
    assert len(acs_entries) == 1, "duplicate diagnosis entries must be merged, not left side by side"
    assert "ST elevation" in acs_entries[0].supporting_evidence
    assert "elevated troponin" in acs_entries[0].supporting_evidence


# --- test_dangerous_workup_does_not_require_every_optional_test ---------------------------------

def test_dangerous_workup_does_not_require_every_optional_test():
    """A dangerous diagnosis with a minimum_workup subset (e.g. ACS: ECG + troponin) must be
    considered resolved once that subset is done, even if OTHER optional discriminating tests
    (e.g. CXR) were never performed -- the fix for spec section 7's unnecessary-testing problem."""
    from nova_agent.knowledge.retrieval import disease_by_id

    entry = disease_by_id("acute_coronary_syndrome")
    assert entry.get("minimum_workup"), "this test assumes acute_coronary_syndrome has a minimum_workup subset"
    assert set(entry["minimum_workup"]).issubset(set(entry.get("discriminating_tests", []))), \
        "minimum_workup should be a genuine subset for this test to be meaningful"

    state = PatientState(case_id="c", chief_complaint="chest pain", demographics={"age": 55, "sex": "male"})
    for test_id in entry["minimum_workup"]:
        state.record_test(test_id, "abnormal / positive")

    # Something in discriminating_tests but NOT in minimum_workup must remain undone.
    untouched = set(entry.get("discriminating_tests", [])) - set(entry["minimum_workup"])
    assert untouched, "expected at least one optional discriminating test beyond the minimum workup"
    for test_id in untouched:
        assert not state.test_done(test_id)

    assert is_resolved("acute_coronary_syndrome", [], state) is True


# --- test_competition_provider_preflight / does_not_silently_mock -------------------------------

def test_competition_provider_preflight():
    """CompetitionLLMClient.preflight() against an endpoint nothing is listening on must return
    (False, <a clear, non-empty reason>) -- never raise, never silently report ready."""
    client = CompetitionLLMClient()
    client.base_url = "http://127.0.0.1:1"  # port 1 -- nothing binds there
    client.timeout = 2.0
    ok, reason = client.preflight()
    assert ok is False
    assert reason and isinstance(reason, str)


def test_competition_provider_does_not_silently_mock():
    """get_llm_client() with NOVA_LLM_PROVIDER=competition must actually construct a
    CompetitionLLMClient -- never silently fall back to MockLLMClient just because the provider
    string was set (spec section 2's core concern: a competition harness must not run an entire
    case on the mock provider without anyone noticing)."""
    restore = _reload_config_with_env(NOVA_LLM_PROVIDER="competition")
    try:
        client = get_llm_client()
        assert isinstance(client, CompetitionLLMClient)
        assert not isinstance(client, MockLLMClient)
    finally:
        restore()


# --- test_dynamic_novel_question_candidate / test_dynamic_test_canonicalization -----------------

def test_dynamic_novel_question_candidate():
    """action_canonicalizer.canonicalize_action(): an LLM-proposed ASK with a key/content that
    isn't a literal catalog id must still be mapped onto a real QUESTION_CATALOG category by
    keyword overlap (spec section 5's hybrid candidate expansion), not rejected outright."""
    state = PatientState(case_id="c", chief_complaint="chest pain")
    action = canonicalize_action(
        "ASK", "pain_quality_novel_key",
        "Can you describe the quality of the pain -- sharp, dull, or pressure-like?", state,
    )
    assert action is not None
    assert action.action_type == "ASK"
    assert action.key == "character"

    # Already-asked categories must not be re-offered even via canonicalization.
    state.record_ask("character", action.content, "pressure-like")
    assert canonicalize_action("ASK", "pain_quality_novel_key", "describe the quality of the pain", state) is None


def test_dynamic_test_canonicalization():
    """The exact example from spec section 5: an LLM proposing 'CTA chest' (not a literal catalog
    key) must canonicalize onto the real ct_chest_angio taxonomy entry."""
    state = PatientState(case_id="c", chief_complaint="shortness of breath")
    action = canonicalize_action("TEST", "cta_chest_novel", "Order a CTA chest to evaluate for PE", state)
    assert action is not None
    assert action.action_type == "TEST"
    assert action.key == "ct_chest_angio"

    # A plausible-sounding but non-existent test must never be invented.
    assert canonicalize_action("TEST", "mri_full_body_scan_deluxe", "A test that does not exist", state) is None


# --- test_submission_dependency_real_llm ----------------------------------------------------------

def test_submission_dependency_real_llm():
    """The competition/local/openai_compatible LLM providers must work with NOTHING beyond
    `pydantic` installed -- no `openai` package dependency anywhere in the real-LLM HTTP path
    (spec section 3): submission/requirements.txt must not require it, and llm_client.py's HTTP
    client must not import it."""
    requirements_text = (REPO_ROOT / "submission" / "requirements.txt").read_text(encoding="utf-8")
    live_requirement_lines = [
        line.strip() for line in requirements_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not any("openai" in line.lower() for line in live_requirement_lines), \
        f"submission/requirements.txt must not hard-depend on the openai package: {live_requirement_lines}"

    import inspect

    import nova_agent.llm_client as llm_client_module

    source = inspect.getsource(llm_client_module)
    assert "import openai" not in source
    assert "from openai" not in source


# --- test_all_case_accuracy_metric / test_critical_recall_metric --------------------------------

def _make_result(case_id, *, correct, scoring_expected=True, critical=False, critical_miss=False) -> CaseResult:
    return CaseResult(
        case_id=case_id, category="synthetic", scoring_expected=scoring_expected,
        ground_truth="x", final_diagnosis="x" if correct else "y", correct=correct, turns=5,
        ask_count=2, exam_count=1, test_count=1, duplicate_actions=0, unnecessary_tests=0,
        critical=critical, critical_miss=critical_miss, malformed_turns=0, failed_to_diagnose=False,
    )


def test_all_case_accuracy_metric():
    """evaluation.benchmark.compute_summary(): all_case_diagnostic_accuracy must be computed over
    EVERY case (scored and unscored alike), so excluding a hard case can never silently inflate it
    -- unlike scored_diagnostic_accuracy, which legitimately excludes scoring_expected=False cases."""
    from evaluation.benchmark import compute_summary

    results = [
        _make_result("a", correct=True),
        _make_result("b", correct=True),
        _make_result("c", correct=False),
        _make_result("d", correct=False, scoring_expected=False),  # ambiguous/unscored, and wrong
    ]
    summary = compute_summary(results)
    assert summary["all_case_diagnostic_accuracy"] == pytest.approx(2 / 4)
    assert summary["scored_diagnostic_accuracy"] == pytest.approx(2 / 3)
    assert summary["unscored_case_names"] == ["d"]


def test_critical_recall_metric():
    """critical_diagnosis_recall must be computed only over cases whose ground truth is a critical
    (can't-miss) diagnosis, as correct/total-critical -- independent of the non-critical cases in
    the same batch."""
    from evaluation.benchmark import compute_summary

    results = [
        _make_result("a", correct=True, critical=True),
        _make_result("b", correct=False, critical=True, critical_miss=True),
        _make_result("c", correct=True, critical=True),
        _make_result("d", correct=False, critical=False),  # non-critical: must not affect recall
    ]
    summary = compute_summary(results)
    assert summary["critical_diagnosis_recall"] == pytest.approx(2 / 3)
    assert summary["critical_miss_rate"] == pytest.approx(1 / 3)
    assert score_case(results[1]) < score_case(results[0])  # the critical miss must score worse


# --- test_submission_source_sync ------------------------------------------------------------------

def _read_py_files(root: Path) -> dict:
    files = {}
    for path in root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[path.relative_to(root)] = path.read_bytes()
    return files


def test_submission_source_sync():
    """submission/nova_agent and submission/competition must be byte-identical copies of the root
    nova_agent/ and competition/ packages (spec sections 16/23/24): submission/ is never
    hand-edited, only regenerated by scripts/build_nova_submission.py. This test is what a CI job
    runs to catch drift before it ships a stale submission."""
    for package in ("nova_agent", "competition"):
        root_files = _read_py_files(REPO_ROOT / package)
        submission_files = _read_py_files(REPO_ROOT / "submission" / package)
        root_paths = set(root_files)
        submission_paths = set(submission_files)
        missing_in_submission = root_paths - submission_paths
        extra_in_submission = submission_paths - root_paths
        assert not missing_in_submission, (
            f"submission/{package} is missing files present in root {package}/: {missing_in_submission}. "
            "Run `python scripts/build_nova_submission.py`."
        )
        assert not extra_in_submission, (
            f"submission/{package} has stale extra files no longer in root {package}/: {extra_in_submission}. "
            "Run `python scripts/build_nova_submission.py`."
        )
        differing = {p for p in root_paths if root_files[p] != submission_files[p]}
        assert not differing, (
            f"submission/{package} has drifted from root {package}/ in: {differing}. "
            "Run `python scripts/build_nova_submission.py`."
        )
