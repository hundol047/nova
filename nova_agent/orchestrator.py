"""Doctor Agent orchestrator: ties PatientState, the differential/safety/missing-info/action-
selection engines, and the (optional) LLM layer into one per-turn decision loop.

`decide()` never raises: any failure anywhere in the pipeline is caught and replaced with a safe
fallback action (spec section 20), and a hard remaining-turns check guarantees a DIAGNOSE is
always produced before the turn limit is reached (spec section 11).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from nova_agent.action_selector import ActionSelector, AgentAction
from nova_agent.clinical_summary import build_clinical_summary
from nova_agent.config import get_config
from nova_agent.differential import DifferentialEngine, DifferentialItem
from nova_agent.llm_client import LLMClient, TurnContext, get_llm_client
from nova_agent.llm_schema import AgentTurnOutput
from nova_agent.safety import SafetyLayer
from nova_agent.state import Demographics, PatientState
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG

log = logging.getLogger("nova_agent.orchestrator")


class DoctorAgent:
    def __init__(self, llm_client: Optional[LLMClient] = None, lang: str = "en") -> None:
        self.llm_client = llm_client or get_llm_client()
        self.lang = lang
        self.differential_engine = DifferentialEngine()
        self.safety_layer = SafetyLayer()
        self.action_selector = ActionSelector()

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
            differential = self.differential_engine.update(state)
            safety_findings = self.safety_layer.assess(state, differential)
            deterministic_action, candidates, stop_decision = self.action_selector.generate_and_select(
                state, differential, safety_findings, lang=self.lang,
            )
            summary = build_clinical_summary(state, differential, safety_findings)
            ctx = TurnContext(summary=summary, differential=differential, safety_findings=safety_findings,
                               candidates=candidates, chosen_action=deterministic_action, stop_decision=stop_decision)
            llm_output = self.llm_client.generate_turn_output(ctx)
            final_action = self._reconcile(deterministic_action, llm_output, state, stop_decision.should_diagnose)
            return final_action, llm_output, differential
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

    # --- reconciliation / fallback -------------------------------------------------------------

    def _reconcile(self, deterministic_action: AgentAction, llm_output: Optional[AgentTurnOutput],
                    state: PatientState, deterministic_ready_to_diagnose: bool) -> AgentAction:
        """The deterministic engine is always the source of truth for safety-relevant behavior.
        The LLM layer (when it's the real Anthropic client) may only select an action that the
        deterministic candidate list already offered -- never something novel -- and may only
        choose DIAGNOSE early if the deterministic stop policy also agrees it's time."""
        if llm_output is None:
            return deterministic_action

        picked = llm_output.selected_action
        if picked.type != deterministic_action.action_type or picked.content != deterministic_action.content:
            log.info("LLM selected_action diverged from deterministic choice for case=%s turn=%s; "
                      "keeping the deterministic action (candidates-only policy).", state.case_id, state.turn_count)
            return deterministic_action
        if picked.type == "DIAGNOSE" and not deterministic_ready_to_diagnose:
            log.info("LLM chose DIAGNOSE before the deterministic stop policy agreed; overriding.")
            return deterministic_action
        if state.is_duplicate(picked.type, deterministic_action.key):
            return deterministic_action
        return deterministic_action  # same type/content as deterministic_action; return it directly

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
