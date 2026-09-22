"""Doctor Agent orchestrator (spec sections 2/13/20).

Turn pipeline: Patient State -> Clinical Summary -> Local RAG -> LLM Differential Reasoning ->
LLM Candidate Actions -> Deterministic Safety Validation -> Utility/Relevance Scoring ->
ASK/EXAM/TEST/DIAGNOSE -> Observation -> State Update.

`decide()` never raises: any failure anywhere in the pipeline is caught and replaced with a safe
fallback action (spec section 20), and a hard remaining-turns check guarantees a DIAGNOSE is
always produced before the turn limit is reached (spec section 11), regardless of what the LLM
layer does or doesn't produce.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from nova_agent.action_selector import ActionSelector, AgentAction
from nova_agent.chief_complaint import classify as classify_chief_complaint
from nova_agent.clinical_summary import build_clinical_summary
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.knowledge.retrieval import retrieve_turn_context
from nova_agent.llm_client import BaseLLMClient, TurnContext, get_llm_client
from nova_agent.llm_schema import AgentTurnOutput
from nova_agent.safety import SafetyLayer
from nova_agent.safety_validator import SafetyValidator, build_candidate_pool
from nova_agent.state import Demographics, DifferentialSnapshot, PatientState
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG

log = logging.getLogger("nova_agent.orchestrator")


class DoctorAgent:
    def __init__(self, llm_client: Optional[BaseLLMClient] = None, lang: str = "en") -> None:
        self.llm_client = llm_client or get_llm_client()
        self.lang = lang
        self.differential_engine = DifferentialEngine()
        self.safety_layer = SafetyLayer()
        self.action_selector = ActionSelector()
        self.safety_validator = SafetyValidator()

    def new_case(self, case_id: str, chief_complaint: str, demographics: Optional[dict] = None,
                 max_turns: Optional[int] = None) -> PatientState:
        return PatientState(
            case_id=case_id, chief_complaint=chief_complaint,
            demographics=Demographics(**(demographics or {})),
            max_turns=max_turns or get_config().max_turns,
        )

    # --- core turn loop -----------------------------------------------------------------------

    def decide(self, state: PatientState) -> Tuple[AgentAction, Optional[AgentTurnOutput], List[DifferentialItem]]:
        try:
            # 1. Patient State (given) -> deterministic prior differential + safety findings.
            #    These are ALWAYS computed (never delegated to the LLM) -- they are what
            #    safety_validator.py checks the LLM's output against.
            deterministic_differential = self.differential_engine.update(state)
            safety_findings = self.safety_layer.assess(state, deterministic_differential)
            deterministic_action, candidates, stop_decision = self.action_selector.generate_and_select(
                state, deterministic_differential, safety_findings, lang=self.lang,
            )

            # 2. Clinical Summary (structured, not raw transcript).
            summary = build_clinical_summary(state, deterministic_differential, safety_findings)

            # Case budget (spec section 20): graceful degradation, never a crash or a silent
            # overrun, as a configured per-case time/LLM-call budget runs out -- off by default
            # (NOVA_CASE_TIMEOUT_SECONDS/NOVA_MAX_LLM_CALLS unset) since no official limit is
            # published. When exhausted, skip RAG retrieval and the real LLM call and go straight
            # to the deterministic action/stop-decision already computed above; the existing
            # turn-count-based forced-diagnose mechanism (stop_policy.py) still independently
            # guarantees a DIAGNOSE within the turn limit regardless of this budget.
            cfg = get_config()
            budget_exhausted = (
                (cfg.case_timeout_seconds is not None and state.case_elapsed_seconds >= cfg.case_timeout_seconds)
                or (cfg.max_llm_calls_per_case is not None and state.llm_call_count >= cfg.max_llm_calls_per_case)
            )

            if budget_exhausted:
                retrieved_context: List[dict] = []
                llm_output = None
            else:
                # 3. Local RAG: only the current chief complaint / top differential / candidate tests.
                tag = classify_chief_complaint(state.chief_complaint)
                candidate_test_ids = [c.key for c in candidates if c.action_type == "TEST"]
                retrieved_context = retrieve_turn_context(
                    tag, [d.diagnosis_id for d in deterministic_differential], candidate_test_ids,
                )

                # 4/5. LLM Differential Reasoning + LLM Candidate Actions (one combined call).
                ctx = TurnContext(summary=summary, differential=deterministic_differential,
                                   safety_findings=safety_findings, candidates=candidates,
                                   chosen_action=deterministic_action, stop_decision=stop_decision,
                                   retrieved_context=retrieved_context)
                llm_output = self.llm_client.generate_turn_output(ctx)

                # LLM reliability metrics (spec: a failing real LLM must never be invisible behind
                # a healthy-looking deterministic fallback) -- folded into this CASE's
                # PatientState right after the call, not accumulated on the (possibly
                # cross-case-shared) client itself. Deliberately INSIDE this branch: when the
                # budget check above skipped the call entirely, self.llm_client._last_call_was_real
                # still holds whatever a PRIOR turn's real call last set it to, so reading it
                # outside this branch would double-count a call that was never made this turn.
                if getattr(self.llm_client, "_last_call_was_real", False):
                    state.llm_call_count += 1
                    if getattr(self.llm_client, "_last_call_succeeded", False):
                        state.llm_success_count += 1
                    else:
                        state.llm_failure_count += 1
                        state.llm_fallback_count += 1
                    latency = getattr(self.llm_client, "_last_call_latency_seconds", None)
                    if latency is not None:
                        state.llm_total_latency_seconds += latency
                        state.llm_latency_sample_count += 1
                    input_tokens = getattr(self.llm_client, "_last_call_input_tokens", None)
                    output_tokens = getattr(self.llm_client, "_last_call_output_tokens", None)
                    if input_tokens is not None and output_tokens is not None:
                        state.llm_total_input_tokens += input_tokens
                        state.llm_total_output_tokens += output_tokens
                        state.llm_token_usage_available = True

            # 6/7. Deterministic Safety Validation + Structured Action Validation.
            merged_differential = self.safety_validator.merge_differential(
                llm_output, deterministic_differential, safety_findings,
            )
            candidate_pool = build_candidate_pool(candidates)
            result = self.safety_validator.validate_action(
                state, llm_output, candidate_pool, deterministic_action, merged_differential, stop_decision,
            )

            # The validated (possibly LLM-authored, possibly safety-merged) differential is what
            # PatientState/logging/clinical_summary see from here on.
            state.current_differential = [
                DifferentialSnapshot(diagnosis=d.diagnosis, rank=d.rank, confidence_band=d.confidence_band,
                                      urgency=d.urgency, dangerous_if_missed=d.dangerous_if_missed)
                for d in result.differential
            ]
            return result.action, llm_output, result.differential
        except Exception:  # noqa: BLE001 - a single bad turn must never kill the whole case/run
            log.exception("decide() failed for case=%s turn=%s; using safe fallback.", state.case_id, state.turn_count)
            return self._safe_fallback(state), None, []

    def observe(self, state: PatientState, action: AgentAction, result: str = "") -> None:
        """Records the environment's response to `action` into PatientState. For DIAGNOSE, `result`
        is an optional rationale string rather than an environment observation."""
        try:
            if action.action_type == "ASK":
                state.record_ask(action.key, action.content, result)
            elif action.action_type == "EXAM":
                if action.key not in EXAM_CATALOG:
                    raise ValueError(f"Unknown EXAM key: {action.key!r}")
                state.record_exam(action.key, result)
            elif action.action_type == "TEST":
                if action.key not in TEST_CATALOG:
                    raise ValueError(f"Unknown TEST key: {action.key!r}")
                state.record_test(action.key, result)
            elif action.action_type == "DIAGNOSE":
                state.record_diagnose(action.content, result)
            else:
                raise ValueError(f"Unknown action type: {action.action_type!r}")
        except Exception:
            log.exception("observe() failed for case=%s action=%s; recording as a no-op ASK turn "
                          "to keep turn accounting consistent.", state.case_id, action)
            state.record_ask("fallback_unrecorded", "(unrecordable action)", "")

    # --- fallback --------------------------------------------------------------------------------

    def _safe_fallback(self, state: PatientState) -> AgentAction:
        if state.remaining_turns <= 1:
            diagnosis = state.current_differential[0].diagnosis if state.current_differential else \
                (state.chief_complaint or "Undifferentiated presentation")
            return AgentAction(action_type="DIAGNOSE", key="fallback", content=diagnosis,
                                rationale="Safe fallback: forced diagnose to respect the turn limit after an "
                                          "internal error.")
        if not state.symptom_onset and not state.question_asked("onset"):
            return AgentAction(action_type="ASK", key="onset", content="When did the symptoms start?",
                                rationale="Safe fallback after an internal error: ask a baseline history question.")
        if not state.exam_done("vital_signs"):
            return AgentAction(action_type="EXAM", key="vital_signs", content="Vital signs (BP/HR/RR/Temp/SpO2)",
                                rationale="Safe fallback after an internal error: obtain vital signs.")
        diagnosis = state.current_differential[0].diagnosis if state.current_differential else \
            (state.chief_complaint or "Undifferentiated presentation")
        return AgentAction(action_type="DIAGNOSE", key="fallback", content=diagnosis,
                            rationale="Safe fallback: no further safe fallback action available.")
