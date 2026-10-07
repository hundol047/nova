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
from nova_agent.config import (PRELIMINARY_CASE_INPUT_TOKENS, PRELIMINARY_CASE_OUTPUT_TOKENS,
                               PRELIMINARY_CASE_SECONDS, PRELIMINARY_MAX_LLM_CALLS_PER_CASE,
                               PRELIMINARY_MAX_TURNS, effective_max_turns, get_config)
from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.knowledge.retrieval import retrieve_turn_context
from nova_agent.knowledge.licensed_reference_store import retrieve_licensed_references
from nova_agent.llm_client import BaseLLMClient, TurnContext, get_llm_client
from nova_agent.llm_schema import AgentTurnOutput
from nova_agent.safety import SafetyLayer
from nova_agent.safety_validator import SafetyValidator, build_candidate_pool
from nova_agent.state import Demographics, DifferentialSnapshot, PatientState
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG
from nova_agent.uncertainty import assess_evidence

log = logging.getLogger("nova_agent.orchestrator")

# Round E: candidate_sources a diagnosis can be reached through with NO real diagnostic evidence
# of its own (mirrors candidate_generator.py's own `trimmable_only_sources` and safety.py's
# `_NO_EVIDENCE_ONLY_SOURCES` -- kept in sync with those, never a separate list that could drift).
# Used only to compute PatientState.pending_diagnosis_quality's `fallback_candidate_selected` flag.
_NO_REAL_EVIDENCE_SOURCES = {"safety_candidate", "contextual_safety", "zero_evidence_fallback",
                             "ontology_broadening", "ontology_retrieval"}


class DoctorAgent:
    def __init__(self, llm_client: Optional[BaseLLMClient] = None, lang: str = "en") -> None:
        self.llm_client = llm_client or get_llm_client()
        self.lang = lang
        self.differential_engine = DifferentialEngine()
        self.safety_layer = SafetyLayer()
        self.action_selector = ActionSelector()
        self.safety_validator = SafetyValidator()

    def new_case(self, case_id: str, chief_complaint: str, demographics: Optional[dict] = None,
                 max_turns: Optional[int] = None, preliminary: Optional[bool] = None) -> PatientState:
        """``preliminary`` applies the preliminary-round rules (50 turns, 20 minutes, no TEST, a
        bounded number of model calls); None follows ``NovaConfig.preliminary_rules``."""
        cfg = get_config()
        prelim = cfg.preliminary_rules if preliminary is None else bool(preliminary)
        ceiling = PRELIMINARY_MAX_TURNS if prelim else 60
        return PatientState(
            case_id=case_id, chief_complaint=chief_complaint,
            demographics=Demographics(**(demographics or {})),
            max_turns=effective_max_turns(max_turns, min(cfg.max_turns, ceiling), ceiling),
            preliminary_rules=prelim,
            time_limit_seconds=PRELIMINARY_CASE_SECONDS if prelim else None,
        )

    # --- core turn loop -----------------------------------------------------------------------

    def decide(self, state: PatientState) -> Tuple[AgentAction, Optional[AgentTurnOutput], List[DifferentialItem]]:
        # One decision = one memo scope for pure string normalisation (see matching.evaluation_scope); the
        # scope is discarded when this call returns, so nothing patient-derived is retained across cases.
        from nova_agent.matching import evaluation_scope
        with evaluation_scope():
            return self._decide(state)

    def _decide(self, state: PatientState) -> Tuple[AgentAction, Optional[AgentTurnOutput], List[DifferentialItem]]:
        # Never reuse a prior turn's confidence if this turn fails partway through.
        state.pending_diagnosis_quality = None
        state.evidence_assessment = {"internal_result": "INSUFFICIENT_INFORMATION",
                                     "reasons": ["turn_not_evaluated"], "signals": {}, "calibrated": False}
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
            if state.preliminary_rules and not budget_exhausted:
                budget_exhausted = not self._preliminary_llm_call_due(state, deterministic_action)

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

                # Broad retrieval reaches the real reasoning prompt, without replacing core safety.
                # Competition retrieval mode already feeds its own dependency-light retrieval
                # (retrieval_pipeline/open_world) into the differential the prompt is built from, and
                # the submission package never ships the repository-level learning/ package this
                # legacy catalog context needs -- so it applies to the non-competition path only.
                # Never under the preliminary-round rules either: the competition path must not import or
                # run the repository-level learning/ package (it is not shipped, and a missing import must not
                # be the reason it is skipped).
                if not cfg.competition_retrieval_enabled and not state.preliminary_rules:
                    try:
                        from nova_agent.catalog_context import retrieve_catalog_context
                        retrieved_context.append(retrieve_catalog_context(state))
                    except Exception:
                        log.exception("Catalog retrieval unavailable; retaining core safety reasoning")
                        retrieved_context.append({"source": "catalog_retrieval_unavailable",
                                                  "text": "Expanded catalog unavailable; do not claim expanded coverage."})

                # 4/5. LLM Differential Reasoning + LLM Candidate Actions (one combined call).
                ctx = TurnContext(summary=summary, differential=deterministic_differential,
                                   safety_findings=safety_findings, candidates=candidates,
                                   chosen_action=deterministic_action, stop_decision=stop_decision,
                                   retrieved_context=retrieved_context,
                                   max_attempts=(self._attempt_allowance(state, deterministic_action)
                                                 if state.preliminary_rules else None),
                                   external_references=retrieve_licensed_references(
                                       [d.diagnosis for d in deterministic_differential], candidate_test_ids,
                                   ) if cfg.rag_enabled else [])
                # Clear telemetry before this case call; a previous case/preflight cannot count.
                self.llm_client._last_call_was_real = False
                self.llm_client._last_call_succeeded = False
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
                    state.llm_http_attempts += int(getattr(self.llm_client, "_last_call_attempts", 1) or 1)
                    if getattr(self.llm_client, "_last_call_tokens_estimated", False):
                        state.llm_tokens_estimated = True
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
                llm_output, deterministic_differential, safety_findings, state=state,
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
            # Legacy (non-competition) retrieval only: abstain with "unknown" when the chosen label lacks
            # positive current support or its required localizing context (PR #15 guard, verified by its
            # own tests). In competition retrieval mode the Round E/M forced-diagnosis behaviour applies
            # unchanged -- an abstention cannot score, and that mode's accuracy was measured without it.
            if result.action.action_type == "DIAGNOSE" and not get_config().competition_retrieval_enabled:
                from nova_agent.safety_validator import selected_diagnosis_item
                from nova_agent.knowledge.retrieval import disease_by_id
                from nova_agent.evidence_grounding import distinct_support_count
                from nova_agent.resolution import is_resolved
                item = selected_diagnosis_item(result.action.content, result.differential)
                from nova_agent.differential import has_positive_diagnostic_support, has_required_diagnostic_context
                novel_ready = (item is not None and (disease_by_id(item.diagnosis_id) is not None or (
                    item.confidence_band != 'LOW' and
                    distinct_support_count(item.supporting_evidence, state) >= get_config().stop_policy.min_evidence_items
                    and not any(d.dangerous_if_missed and d.diagnosis_id != item.diagnosis_id
                                and not is_resolved(d.diagnosis_id, d.contradictory_evidence, state)
                                for d in result.differential))))
                if (not item or not has_positive_diagnostic_support(item)
                        or not has_required_diagnostic_context(item, state) or not novel_ready):
                    result.action = AgentAction(action_type="DIAGNOSE", key="unknown", content="unknown",
                                                rationale="Insufficient diagnostic evidence; clinical review required. "
                                                "Unresolved dangerous alternatives remain in the differential.")
                else:
                    # Forced completion can retain a deterministic key with an LLM-proposed
                    # name. Keep the externally visible action internally consistent.
                    result.action.key = item.diagnosis_id

            state.evidence_assessment = assess_evidence(
                state, deterministic_differential,
                result.action.key if result.action.action_type == "DIAGNOSE" else None,
            ).model_dump()

            # Round E: stage forced/low-evidence diagnosis metadata for PatientState.
            # record_diagnose() to pick up (see that field's own docstring) -- computed here, not
            # inside record_diagnose() itself, because only decide() has stop_decision and the
            # full DifferentialItem (with fallback_candidate/candidate_sources) in scope; observe()
            # only ever sees the already-decided action/result text.
            if result.action.action_type == "DIAGNOSE":
                diagnosed_item = next(
                    (d for d in result.differential if d.diagnosis_id == result.action.key),
                    result.differential[0] if result.differential else None,
                )
                state.pending_diagnosis_quality = {
                    "forced_due_to_turn_limit": bool(stop_decision.forced),
                    "zero_evidence_at_diagnosis": bool(diagnosed_item and diagnosed_item.fallback_candidate),
                    "fallback_candidate_selected": bool(
                        diagnosed_item and diagnosed_item.candidate_sources
                        and set(diagnosed_item.candidate_sources).issubset(_NO_REAL_EVIDENCE_SOURCES)
                    ),
                }
            return result.action, llm_output, result.differential
        except Exception:  # noqa: BLE001 - a single bad turn must never kill the whole case/run
            log.exception("decide() failed for case=%s turn=%s; using safe fallback.", state.case_id, state.turn_count)
            return self._safe_fallback(state), None, []

    def _preliminary_llm_call_due(self, state: PatientState, deterministic_action: AgentAction,
                                  estimated_input_tokens: int = 0) -> bool:
        """Preliminary-round model-call schedule. The fixed model is capped per session and its
        usage is part of the efficiency score, but a case with NO model call scores 0. So: always
        call on the first turn and on the turn that would submit the diagnosis, otherwise only every
        4th turn, never beyond PRELIMINARY_MAX_LLM_CALLS_PER_CASE HTTP requests (retries included; one
        slot stays reserved for the final turn) and never beyond the per-case token ceilings. The
        deterministic engine decides every other turn unaided. Budgets are fixed per case -- never
        derived from what other cases consumed -- so a case's behaviour does not depend on its neighbours."""
        cap = PRELIMINARY_MAX_LLM_CALLS_PER_CASE
        spent = state.llm_http_attempts
        first_or_final = state.llm_call_count == 0 or deterministic_action.action_type == "DIAGNOSE"
        if first_or_final:
            within_requests = spent < cap
        else:
            within_requests = spent < cap - 1 and state.turn_count % 4 == 0
        within_tokens = (state.llm_total_input_tokens + estimated_input_tokens <= PRELIMINARY_CASE_INPUT_TOKENS
                         and state.llm_total_output_tokens <= PRELIMINARY_CASE_OUTPUT_TOKENS)
        # The very first call of a case is the REQUIRED one: only the request cap can stop it.
        return within_requests and (within_tokens or state.llm_call_count == 0)

    def _attempt_allowance(self, state: PatientState, deterministic_action: AgentAction) -> int:
        """Requests this logical call may spend including retries: all that remain for the first/final
        call, otherwise all but the slot reserved for the final diagnosis."""
        remaining = PRELIMINARY_MAX_LLM_CALLS_PER_CASE - state.llm_http_attempts
        if state.llm_call_count == 0 or deterministic_action.action_type == "DIAGNOSE":
            return max(1, remaining)
        return max(1, remaining - 1)

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
            elif action.action_type == "SAY":
                state.record_say(action.content, result, action.key)
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
            return AgentAction(action_type="DIAGNOSE", key="unknown", content="unknown",
                                rationale="Safe fallback: forced diagnose to respect the turn limit after an "
                                          "internal error.")
        if not state.symptom_onset and not state.question_asked("onset"):
            return AgentAction(action_type="ASK", key="onset", content="When did the symptoms start?",
                                rationale="Safe fallback after an internal error: ask a baseline history question.")
        if not state.exam_done("vital_signs"):
            return AgentAction(action_type="EXAM", key="vital_signs", content="Vital signs (BP/HR/RR/Temp/SpO2)",
                                rationale="Safe fallback after an internal error: obtain vital signs.")
        return AgentAction(action_type="DIAGNOSE", key="unknown", content="unknown",
                            rationale="Safe fallback: no further safe fallback action available.")
