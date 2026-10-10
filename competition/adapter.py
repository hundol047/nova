"""Competition Adapter (spec section 16) -- the ONLY place that should need to change once the
official N.O.V.A. 2026 Agent API is published.

Responsibilities (and nothing else):
  competition observation  -> internal PatientState
  internal AgentAction     -> competition action

nova_agent/'s clinical reasoning engine (state/differential/safety/missing_info/action_selector/
stop_policy/orchestrator) never imports anything from this package, and this package never
contains clinical reasoning logic -- only translation. That separation is what lets the real
competition interface replace competition/schema.py + the two translation functions below without
touching anything else in the repository.
"""

from __future__ import annotations

import logging
import sys
from typing import Dict, Optional

from nova_agent.action_selector import AgentAction
from nova_agent.config import get_config
from nova_agent.orchestrator import DoctorAgent
from nova_agent.preliminary import (detect_language, exam_request_text, explanation_text, rejection_signal,
                                    parse_first_statement, plan_say_text, same_scope_names, say_text,
                                    uncertain_explanation_text)
from nova_agent.soap import build_soap, label_alternatives, localized_name
from nova_agent.state import PatientState

from competition.schema import CompetitionAction, CompetitionObservation

log = logging.getLogger("competition.adapter")

# Heuristic, not an official threshold -- just a loud, honest signal that a real-LLM run's
# clinical reasoning quietly spent most of its turns on the deterministic fallback rather than
# the real model (spec: LLM failure must never be invisible behind a healthy-looking run).
_HIGH_FALLBACK_RATE_THRESHOLD = 0.3

# Bounded, never unlimited -- each retry here calls DoctorAgent.decide() again, which itself
# already applies its own bounded per-call retry inside the LLM client (NOVA_LLM_MAX_RETRIES).
# When the case's time/call budget is already exhausted, decide() skips the real LLM call
# entirely (see orchestrator.py's budget_exhausted check) and returns immediately, so a retry
# loop here can never itself push a case past its configured case timeout -- it just fails fast.
_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES = 2


class RealLLMUnavailableError(RuntimeError):
    """Raised by NovaCompetitionAgent.act() instead of returning a DIAGNOSE action, when a
    competition-mode (provider != mock) case reaches its final answer having never once received
    a successful real-LLM response across the whole case, even after the bounded retries above.

    This is the explicit-failure half of spec section 12: a deterministic-fallback-only result
    must never be silently returned as a normal, successful competition completion just because
    it happens to be a well-formed action. Dev/mock mode never raises this -- see the
    `in_competition_mode` gate in `act()` below; the deterministic fallback stays fully available
    there, unchanged."""


def observation_to_state(obs: CompetitionObservation, agent: DoctorAgent,
                          existing_state: Optional[PatientState],
                          pending_action: Optional[AgentAction],
                          preliminary: Optional[bool] = None) -> PatientState:
    """Translates one CompetitionObservation into a PatientState update.

    On observation_type == 'initial', starts a fresh case. Otherwise, records the environment's
    reply against `pending_action` (the action this adapter returned on the previous turn) via
    DoctorAgent.observe(), which is what actually accumulates evidence into PatientState.
    """
    if obs.observation_type == "initial" or existing_state is None:
        demographics = dict(obs.demographics or {})
        if preliminary or (preliminary is None and get_config().preliminary_rules):
            # Preliminary round: age/sex are stated inside the first patient sentence.
            for key, value in parse_first_statement(obs.chief_complaint or "").items():
                demographics.setdefault(key, value)
        state = agent.new_case(obs.case_id, obs.chief_complaint or "", demographics, obs.max_turns,
                               preliminary=preliminary)
        state.locale = detect_language(obs.chief_complaint or "")
        if obs.vital_signs:
            state.record_initial_vitals(obs.vital_signs)
        return state

    if pending_action is None:
        log.warning("Non-initial observation for case=%s with no pending action; ignoring content.", obs.case_id)
        return existing_state

    rejected = pending_action.action_type == "EXAM" and rejection_signal(obs.raw, obs.content)
    if pending_action.action_type == "EXAM" and rejected:
        # Preliminary rules: a request not on the organizer's list is rejected and costs no turn.
        existing_state.record_exam_rejected(pending_action.key)
        return existing_state
    agent.observe(existing_state, pending_action, obs.content or "")
    return existing_state


def _exhausted(state: PatientState):
    state.completion_reason = "information_exhausted"
    return None


def _urgent(final, differential: list, state: PatientState) -> bool:
    from nova_agent.disposition import disposition_for
    return disposition_for(state, final, differential).urgent


def preliminary_wire_action(case_id: str, action: AgentAction, state: PatientState, differential: list,
                            final=None) -> CompetitionAction:
    """Preliminary-round wire form of an internal action: ASK -> SAY (<= 30 characters, one
    question), EXAM -> one-maneuver request sentence, DIAGNOSE -> SOAP note + one primary diagnosis.
    Pure translation: the internal action (and so the diagnosis) is unchanged."""
    lang = state.locale or "en"
    metadata = {"key": action.key, "rationale": action.rationale, "protocol_status": "PLACEHOLDER",
                "rules": "PRELIMINARY_2026-10-06"}
    if action.action_type == "ASK":
        return CompetitionAction(case_id=case_id, action_type="SAY",
                                 content=say_text(action.key, lang, action.content, empathy=state.turn_count == 0),
                                 metadata=metadata)
    if action.action_type == "SAY":
        return CompetitionAction(case_id=case_id, action_type="SAY", content=action.content, metadata=metadata)
    if action.action_type == "EXAM":
        return CompetitionAction(case_id=case_id, action_type="EXAM",
                                 content=exam_request_text(action.key, lang, action.content), metadata=metadata)
    note = build_soap(state, differential, lang, final=final)
    return CompetitionAction(case_id=case_id, action_type="DIAGNOSE", content=str(note["text"]), metadata=metadata,
                             soap={k: str(note[k]) for k in ("S", "O", "A", "P")},
                             primary_diagnosis=str(note["primary_diagnosis"]))


def action_to_competition(case_id: str, action: AgentAction, *, real_llm_verified: Optional[bool] = None,
                           diagnosis_quality: Optional[Dict[str, bool]] = None,
                           evidence_assessment: Optional[dict] = None) -> CompetitionAction:
    """Translate internal uncertainty into the provisional, configurable wire contract.

    FORCED_FINAL_DIAGNOSIS is a completion classification, never an official action label.
    Uncertainty stays metadata; no fifth wire action is permitted.
    """
    metadata = {"key": action.key, "rationale": action.rationale}
    if real_llm_verified is not None:
        # Only ever attached to a DIAGNOSE action (see NovaCompetitionAgent.act() below) -- lets a
        # competition-readiness harness detect "this case's final answer came from a real LLM at
        # least once" programmatically, not just by grepping a stderr log line.
        metadata["real_llm_verified"] = real_llm_verified

    action_type = action.action_type
    if diagnosis_quality is not None:
        metadata["diagnosis_quality"] = diagnosis_quality

    content = action.content
    if action.action_type == "DIAGNOSE":
        assessment = evidence_assessment or {
            "internal_result": "INSUFFICIENT_INFORMATION",
            "reasons": ["evidence_assessment_unavailable"], "signals": {}, "calibrated": False}
        unsupported = assessment["internal_result"] != "SUPPORTED_DIAGNOSIS"
        forced = unsupported and action_type == "DIAGNOSE"
        metadata.update({
            "internal_result": assessment["internal_result"],
            "evidence_assessment": assessment,
            "forced_due_to_protocol": forced,
            "completion_type": "FORCED_FINAL_DIAGNOSIS" if forced else assessment["internal_result"],
            "wire_result": action_type,
            "protocol_status": "PLACEHOLDER",
        })
    return CompetitionAction(case_id=case_id, action_type=action_type, content=content,
                              metadata=metadata)


class NovaCompetitionAgent:
    """Stateful per-process entrypoint a competition runtime can drive directly: one
    `act(observation)` call per turn, holding each case's PatientState internally by case_id.

    This is intentionally the thinnest possible wrapper around DoctorAgent -- if the competition
    harness instead calls nova_agent directly (or a different integration shape is required), the
    reasoning engine underneath (DoctorAgent) is unaffected either way.
    """

    def __init__(self, agent: Optional[DoctorAgent] = None, preliminary: Optional[bool] = None) -> None:
        self.agent = agent or DoctorAgent()
        # Preliminary-round rules (SAY/EXAM/DIAGNOSE only, <= 30-character SAY, SOAP note, closing
        # explanation). None follows NovaConfig.preliminary_rules (ON for the competition provider).
        self.preliminary = get_config().preliminary_rules if preliminary is None else bool(preliminary)
        self._states: Dict[str, PatientState] = {}
        self._pending_actions: Dict[str, AgentAction] = {}
        self._emitted_actions: Dict[str, int] = {}
        self._closing_done: Dict[str, set] = {}
        self._final: Dict[str, object] = {}

    def act(self, observation: dict) -> dict:
        case_id = observation.get("case_id") if isinstance(observation, dict) else None
        try:
            result = self._act(observation)
        except Exception:
            if isinstance(case_id, str):
                self.close_case(case_id)
            raise
        if result["action_type"] == "DIAGNOSE":
            self.close_case(result["case_id"])
        return result

    # Standard safety history asked before the diagnosis if the encounter has not covered it: these
    # change management (drug interactions, comorbid risk) and the rubric credits what is actually asked.
    _CORE_HISTORY = ("past_medical_history", "medication", "allergy")

    def _closing_action(self, case_id: str, state: PatientState, differential: list) -> Optional[AgentAction]:
        """What to do between "the engine is ready to diagnose" and the DIAGNOSE submission:
        (1) any unasked core safety history, (2) tell the patient the working diagnosis, (3) tell
        the patient the next step. ("Writing an education plan is not explaining" -- it must happen
        in dialogue.) Each step needs turn budget; none is attempted once the time budget is nearly
        spent. DIAGNOSE itself costs no turn."""
        if self._time_nearly_up(state):
            return None
        done = self._closing_done.setdefault(case_id, set())
        remaining = state.remaining_turns
        if remaining >= 5:
            for category in self._CORE_HISTORY:
                if not state.question_asked(category) and category not in done:
                    done.add(category)  # at most one attempt per category
                    from nova_agent.taxonomy import QUESTION_CATALOG
                    return AgentAction(action_type="ASK", key=category, content=QUESTION_CATALOG[category]["text_en"],
                                       rationale="Standard safety history before the diagnosis.")
        final = self._final_decision(case_id, state, differential)
        top = final.item
        lang = state.locale or "en"
        if "dx" not in done and remaining >= 3:
            done.add("dx")
            # Round Q: the explanation commits to the SAME final decision the SOAP and primary will use.
            self._final[case_id] = final
            if top is None:
                return AgentAction(action_type="SAY", key="explanation", content=uncertain_explanation_text(lang),
                                   rationale="No specific diagnosis is supported yet; say so plainly.")
            from nova_agent.soap import _entry_for
            entry = _entry_for(top.diagnosis_id)
            label = localized_name(entry, top.diagnosis, lang)
            names = same_scope_names(label) + (same_scope_names(top.diagnosis) if lang != "ko" else [])
            if lang == "en":
                names = [n.lower() for n in names]
            return AgentAction(action_type="SAY", key="explanation", content=explanation_text(names[0], lang, names[1:]),
                               rationale="Explain the working diagnosis to the patient before submitting the note.")
        if "plan" not in done and remaining >= 2:
            done.add("plan")
            urgent = _urgent(final, differential, state)
            return AgentAction(action_type="SAY", key="plan_explanation", content=plan_say_text(urgent, lang),
                               rationale="Tell the patient the next step and when to return.")
        return None

    def _final_decision(self, case_id: str, state: PatientState, differential: list):
        """The committed decision once the explanation was given; otherwise decided now from this differential."""
        from nova_agent.final_decision import decide_final
        cached = self._final.get(case_id)
        if cached is not None:
            return cached
        return decide_final(state, differential, state.completion_reason or "supported")

    @staticmethod
    def _time_nearly_up(state: PatientState) -> bool:
        return state.time_nearly_up()

    def close_case(self, case_id: str) -> None:
        """Drop patient-derived state on completion/error; retain no patient tombstones."""
        self._states.pop(case_id, None)
        self._pending_actions.pop(case_id, None)
        self._emitted_actions.pop(case_id, None)
        self._closing_done.pop(case_id, None)
        self._final.pop(case_id, None)

    def _act(self, observation: dict) -> dict:
        obs = CompetitionObservation.model_validate(observation)
        if obs.observation_type != "initial" and obs.case_id not in self._states:
            raise ValueError("A fresh initial observation is required for this case")
        if obs.observation_type == "initial":
            self.close_case(obs.case_id)
        state = observation_to_state(obs, self.agent, self._states.get(obs.case_id),
                                      self._pending_actions.get(obs.case_id), preliminary=self.preliminary)
        self._states[obs.case_id] = state
        from nova_agent.evidence_scope import proxy_scope
        with proxy_scope(state.proxy_relation):  # Round W: SOAP/disposition after decide() see the same subject
            return self._act_with_state(obs, state)

    def _act_with_state(self, obs, state: PatientState) -> dict:
        if self._emitted_actions.get(obs.case_id, 0) >= state.max_turns:
            raise RuntimeError("Interaction budget exhausted; no further action may be emitted")

        bind_case = getattr(self.agent.llm_client, "bind_case", None)
        if callable(bind_case):  # transport-backed clients attribute model-call evidence to this case
            bind_case(obs.case_id)
        action, _llm_output, _differential = self.agent.decide(state)
        in_competition_mode = get_config().llm_provider != "mock"
        if state.preliminary_rules and action.action_type == "TEST":
            # There is no TEST action in the preliminary round; never emit one (defensive: the
            # selector already filters it). Fall back to a still-unasked general question.
            log.warning("TEST suppressed for case=%s under preliminary rules.", obs.case_id)
            fallback_key = next((k for k in ("associated_symptoms", "past_medical_history", "medication")
                                 if not state.question_asked(k)), None)
            action = (AgentAction(action_type="ASK", key=fallback_key, content=fallback_key,
                                  rationale="TEST unavailable in the preliminary round")
                      if fallback_key else
                      _exhausted(state) or AgentAction(action_type="DIAGNOSE", key=getattr(action, "key", "unknown"),
                                  content=_differential[0].diagnosis if _differential else "Undifferentiated presentation",
                                  rationale="TEST unavailable; diagnosing on the available evidence"))

        if action.action_type == "DIAGNOSE" and in_competition_mode and state.real_llm_ever_succeeded is not True:
            # Required flow (spec section 12): bounded retry -> real LLM retry -> if it succeeds,
            # proceed normally -> if every attempt still fails, an explicit runtime failure, never
            # a disguised deterministic-only "success". Re-calling decide() on the same
            # (unmutated -- observe() has not run yet for this turn) state re-attempts the real
            # LLM call fresh each time, so a retry that lands after a transient outage clears is
            # indistinguishable from having succeeded on the first try.
            for _ in range(_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES):
                if state.real_llm_ever_succeeded:
                    break
                action, _llm_output, _differential = self.agent.decide(state)
            if state.real_llm_ever_succeeded is not True:
                # Every real-LLM attempt this case failed, even after this bounded retry -- the
                # only available answer is deterministic-fallback-only. Dev/mock mode never
                # reaches this branch (in_competition_mode is False there), so its existing
                # fallback behavior is completely unchanged.
                self._pending_actions.pop(obs.case_id, None)
                raise RealLLMUnavailableError(
                    f"case={obs.case_id}: reached DIAGNOSE with ZERO successful real-LLM calls "
                    f"({state.llm_call_count} attempted across the case and "
                    f"{_DIAGNOSE_ZERO_LLM_SUCCESS_RETRIES} additional bounded retries, all failed). "
                    "Competition mode does not permit a deterministic-fallback-only submission -- "
                    "this is a runtime failure, not a completion. Run "
                    "scripts/preflight_competition.py before submitting."
                )

        if state.preliminary_rules and action.action_type == "DIAGNOSE":
            closing = self._closing_action(obs.case_id, state, _differential or [])
            if closing is not None:
                self._pending_actions[obs.case_id] = closing
                self._emitted_actions[obs.case_id] = self._emitted_actions.get(obs.case_id, 0) + 1
                return preliminary_wire_action(obs.case_id, closing, state, _differential or []).model_dump()

        final = None
        if state.preliminary_rules and action.action_type == "DIAGNOSE":
            # Round Q: one final decision drives the primary, the SOAP note, the explanation and the metadata.
            final = self._final_decision(obs.case_id, state, _differential or [])
            action = AgentAction(action_type="DIAGNOSE", key=final.primary_id, content=final.label(state.locale or "en"),
                                 rationale=action.rationale)
            # Assess the actually submitted working diagnosis, not the rank-one
            # proposal rejected by final_decision. The two axes have explicit names.
            from nova_agent.uncertainty import assess_evidence
            state.evidence_assessment = assess_evidence(state, _differential or [],
                                                        selected_id=final.primary_id).model_dump()

        self._pending_actions[obs.case_id] = action
        real_llm_verified: Optional[bool] = None
        if action.action_type == "DIAGNOSE":
            self._pending_actions.pop(obs.case_id, None)
            real_llm_verified = state.real_llm_ever_succeeded
            if not (in_competition_mode and real_llm_verified is False):
                # The ZERO-success case above either already raised or (after a successful retry)
                # no longer applies here -- this branch is the ordinary "some real LLM evidence
                # exists" path, dev/mock included.
                fallback_rate = state.llm_fallback_rate
                if fallback_rate is not None and fallback_rate >= _HIGH_FALLBACK_RATE_THRESHOLD:
                    print(
                        f"WARNING: {state.llm_fallback_count}/{state.llm_call_count} turns used "
                        f"deterministic fallback for case={obs.case_id} (fallback rate "
                        f"{fallback_rate:.0%}) -- the configured LLM provider may not be reliably "
                        "reachable; run scripts/preflight_competition.py before submitting.",
                        file=sys.stderr,
                    )

        # Read `pending_diagnosis_quality` (staged by decide() this same call), NOT the
        # `final_diagnosis_*` fields -- those are only populated once observe() later records this
        # DIAGNOSE action (on the NEXT act() call, when the environment's reply arrives), so they
        # would still be stale/unset here.
        diagnosis_quality = dict(state.pending_diagnosis_quality or {}) if action.action_type == "DIAGNOSE" else None
        wire = action_to_competition(obs.case_id, action, real_llm_verified=real_llm_verified,
                                    diagnosis_quality=diagnosis_quality,
                                    evidence_assessment=state.evidence_assessment)
        if state.preliminary_rules:
            prelim = preliminary_wire_action(obs.case_id, action, state, _differential or [], final=final)
            prelim.metadata.update(wire.metadata)
            if final is not None:
                prelim.metadata["final_decision"] = final.as_metadata()
                from nova_agent.disposition import disposition_for
                prelim.metadata["disposition"] = disposition_for(state, final, _differential or []).as_metadata()
                from nova_agent.resolution import workup_coverage
                prelim.metadata["workup_coverage"] = {
                    d.diagnosis_id: workup_coverage(d.diagnosis_id, state)
                    for d in (_differential or [])[:5] if d.dangerous_if_missed}
                if final.undifferentiated:
                    prelim.metadata["completion_type"] = "UNDIFFERENTIATED_INSUFFICIENT_INFORMATION"
            wire = prelim
        result = wire.model_dump()
        if action.action_type == "DIAGNOSE":
            # Existing real_llm_verified is legacy DEVELOPMENT structured-parse telemetry.
            # It cannot attest organizer model identity, revision, or official call semantics.
            result["metadata"]["call_accounting"] = {
                "OFFICIAL_CALL_RESPONSE_RECEIVED": "NOT_VERIFIED",
                "INTERNAL_STRUCTURED_OUTPUT_VALID": state.llm_success_count > 0,
                "successful_development_structured_calls": state.llm_success_count,
                "official_successful_case_llm_calls": None,
            }
        if action.action_type != "DIAGNOSE":  # DIAGNOSE costs no turn in the preliminary round
            self._emitted_actions[obs.case_id] = self._emitted_actions.get(obs.case_id, 0) + 1
        return result
