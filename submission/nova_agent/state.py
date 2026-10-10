"""Patient State Manager (spec section 2).

Holds everything the Doctor Agent has learned about the current case, accumulated turn by turn.
Uses nova_agent's own standalone Medication/Allergy/VitalSigns models (nova_agent/models.py) --
no dependency on the vendored SynexAgent backend (spec section 17).
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from nova_agent.models import Allergy, Medication, VitalSigns
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG
from nova_agent.vitals_parser import describe_vital_sign_abnormalities, parse_vital_signs

ActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE", "SAY"]


def normalize_key(text: str) -> str:
    """Collapse whitespace/punctuation/case so trivially-different phrasings of the same free
    text hash identically. Used as a last-resort fallback when a piece of content does not match
    any catalog entry (normal path is the catalog id itself, which is already stable)."""
    lowered = text.strip().lower()
    lowered = re.sub(r"[^\w\s가-힣]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


# Clause boundaries a real free-text answer uses to contrast an affirmed finding against a denied
# one in the SAME sentence (e.g. "No fever or chills but has severe chest pressure", "I don't have
# weakness but my speech became slurred") -- splitting only on ';' (the original implementation)
# missed every one of these, silently losing or misclassifying half the answer.
_CLAUSE_SPLIT_PATTERN = re.compile(
    r";|\n|(?<=\w)\.(?=\s+[a-z])|(?<=\w)\s+but\s+|(?<=\w)\s+however\s+|(?<=\w)\s+although\s+|(?<=\w)\s+except\s+(?:that\s+)?"
    r"|,\s*(?=(?:but\s+)?(?:I\s+)?(?:don'?t know|do not know|cannot remember|can't remember|not sure|cannot tell|can't tell|cannot say))"
    r"|\s+and\s+(?=(?:I\s+)?(?:don'?t know|do not know|cannot remember|can't remember|cannot tell|can't tell|cannot say))"
    r"|하지만|그러나|그런데|근데|でも|しかし|だが|但是|不过|但",
    re.IGNORECASE,
)

_NEGATION_MARKERS = [
    "denies", "denied", "no ", "none", "negative for", "not present", "without",
    "don't have", "doesn't have", "do not have", "does not have",
    "didn't have", "did not have", "never had", "not experiencing", "not having",
    # Korean
    "아니", "없습니다", "없어요", "없음", "안 아파요", "하지 않아요", "부인함",
    # Japanese
    "ない", "ありません", "認めない", "否定", "していない",
    # Chinese (simplified). Deliberately NOT bare "不" -- Chinese uses no word-spacing, and "不" is
    # a substring of many unrelated words that do NOT mean a symptom is denied (e.g. "不适"
    # discomfort, "不规则" irregular) -- a bare single-character marker would misclassify a
    # POSITIVE finding as negated. The multi-character markers below are specific enough to avoid
    # that false-positive class the same way English "no " (with a trailing space, not bare "no")
    # already avoids matching inside unrelated words like "corner".
    "没有", "无", "否认", "未出现",
]


def _split_answer_segments(answer: str) -> List[str]:
    """Splits a free-text answer into clause-level segments so a single sentence that both affirms
    and denies findings can be classified segment-by-segment instead of as one all-or-nothing
    unit."""
    if not answer:
        return []
    segments: List[str] = []
    for part in _CLAUSE_SPLIT_PATTERN.split(answer):
        part = part.strip().rstrip(".").strip()
        if not part:
            continue
        if re.search(r"\b(?:denies|no|without|not|negative for)\b", part, re.IGNORECASE):
            # A comma-list may switch polarity mid-clause ("palpitations just before,
            # no aura, no tongue biting").  Split at the marker rather than classifying
            # the whole list as negative; otherwise the positive lead-in can incorrectly
            # support a feature such as "no palpitations before the episode".
            pieces = re.split(
                r",\s*(?=(?:denies\b|no\b|without\b|not\b|negative\s+for\b))|(?<=\w)\s+(?=without\b)",
                part, flags=re.IGNORECASE,
            )
            for piece in pieces:
                segments.extend(_expand_mixed_leading_no(piece.strip()))
        else:
            segments.extend(_expand_mixed_leading_no(part))
    return segments


def _segment_is_negated(segment: str) -> bool:
    lowered = segment.lower()
    return any(marker in lowered for marker in _NEGATION_MARKERS)


_MIXED_POSITIVE_CUE = re.compile(
    r"\b(?:has|have|reports?|with|pain|nausea|vomit(?:ing)?|fever|diarr(?:hea|hoea)|"
    r"weakness|cough|dyspnea|sweat(?:ing)?|dizzy|headache|low|mild|sharp|worse)\b"
    r"|恶心|呕吐|低烧|低热|腹泻|疼|痛|无力|咳嗽|微热| nausea | 구역 | 구토 | 미열",
    re.IGNORECASE,
)


def _expand_mixed_leading_no(segment: str) -> List[str]:
    """Scope a leading ``no X`` to X when a comma-list continues with positive findings."""
    match = re.match(r"^\s*(no\s+[^,;]+),\s*(.+)$", segment, re.IGNORECASE)
    if not match:
        return [segment]
    negative_head, remainder = match.groups()
    if re.search(r"\b(?:no|denies|without|not)\b|없(?:음|어요|습니다)|没有|无|否认", remainder, re.IGNORECASE):
        return [segment]
    if not _MIXED_POSITIVE_CUE.search(remainder):
        return [segment]
    # "no fever, chills or cough": a disjunction continues the negative list ("none of these"); only a
    # remainder with its own positive predicate ("no rash, has cough") escapes the leading "no".
    if re.search(r"\bor\b|\bnor\b", remainder, re.IGNORECASE) and not re.search(
            r"\b(?:has|have|reports?|with)\b", remainder, re.IGNORECASE):
        return [segment]
    return [negative_head.strip(), remainder.strip()]


class Demographics(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = None
    pregnant: Optional[bool] = None


_MODIFIER_LEAD = re.compile(r"^\s*(?:worse|better|relieved|eased|eases|helps|helped|aggravated|brought on|triggered|"
                            r"makes? it|nothing|none|no\b|not\b)", re.IGNORECASE)


def _contextualise_modifier(category: str, segment: str) -> str:
    """'twisting and pressing on it' answered to an AGGRAVATING question -> 'worse with twisting and pressing on it';
    to a RELIEVING question -> 'relieved by ...'. Empty when off, not a modifier question, or already explicit."""
    from nova_agent.config import get_config
    if category not in ("aggravating", "relieving") or not get_config().concepts_v2_enabled:
        return ""
    if not segment or _MODIFIER_LEAD.search(segment):
        return ""
    return ("worse with " if category == "aggravating" else "relieved by ") + segment.strip()


def _with_canonical_concepts(texts: List[str]) -> List[str]:
    """Append canonical knowledge-base phrases for clinical wording found in ``texts`` (see
    nova_agent/clinical_concepts.py); the original texts are kept unchanged."""
    from nova_agent.config import get_config
    if not get_config().concept_normalization_enabled:
        return texts
    from nova_agent.clinical_concepts import canonical_findings_for
    out = list(texts)
    for text in texts:
        out += [c for c in canonical_findings_for(text) if c not in out]
    return out


# --- Round Q: what a bare answer means depends on the question actually asked ---------------------------------------
# A reply that is ONLY yes / no / don't-know carries no content of its own. It is attached to the single feature the
# actual question asked about (when the question asked about one), and otherwise is not stored as a finding at all.
_ANSWER_UNKNOWN = re.compile(
    r"\b(?:don'?t know|do not know|not sure|unsure|no idea|can'?t remember|cannot remember|can'?t recall|"
    r"don'?t remember|do not remember|can'?t say|cannot say|cannot recall|"
    r"(?:cannot|can'?t|unable to) tell (?:you|that|whether)|"
    r"(?:prefer|would rather) not (?:to )?(?:answer|say)|decline to answer)\b|"
    r"모르겠|몰라|기억(?:이)? ?안|잘 모르|알 수 없|답(?:변)?(?:을|은)?\s*(?:못|할 수 없|하기 싫)", re.IGNORECASE)
_ANSWER_BARE_NO = re.compile(
    r"^(?:no|nope|nah|none|not really|never|no,? never|no,? not (?:really|at all)|"
    r"(?:no,? )?i (?:don'?t|do not)(?: have (?:that|any|it|them))?|"
    r"아니요|아뇨|아니오|아니|없어요|없습니다|없어|아니요,? ?(?:그런 ?(?:건|것은?) ?)?없(?:어요|습니다))$", re.IGNORECASE)
_ANSWER_BARE_YES = re.compile(
    r"^(?:yes|yeah|yep|yup|i do|i have|i did|yes,? i (?:do|have|did)(?: (?:that|it))?|"
    r"네|예|있어요|있습니다|네,? ?있어요|맞아요)$", re.IGNORECASE)


def answer_kind(answer: str) -> Optional[str]:
    """'unknown' | 'no' | 'yes' for a reply that carries nothing but that; None for a reply with content."""
    text = re.sub(r"\s+", " ", (answer or "").strip()).rstrip(" .!?~")
    if not text:
        return "unknown"
    # Unknown is a clause assertion, not a veto over everything else in the answer.
    # Preserve "I take furosemide, but I cannot remember the dose" as content.
    parts = _split_answer_segments(text)
    if _ANSWER_UNKNOWN.search(text) and all(_ANSWER_UNKNOWN.search(p) for p in parts):
        return "unknown"
    if _ANSWER_BARE_NO.match(text):
        return "no"
    if _ANSWER_BARE_YES.match(text):
        return "yes"
    return None


_EXAM_RESULT_UNKNOWN = re.compile(
    r"\b(?:result unknown|unknown|not (?:done|performed|available|assessed|possible)|unavailable|unable to (?:assess|examine|perform)|"
    r"could not be (?:assessed|examined|performed)|pending)\b|확인 불가|알 수 없", re.IGNORECASE)


class ActionOutcome(BaseModel):
    """Round Q: what an ASK / EXAM actually produced. ``faithful`` is False when the question that was actually put
    to the patient was a generic fallback rather than the detailed discriminator the selector intended."""
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["ASK", "EXAM"]
    key: str
    status: Literal["OBSERVED", "UNKNOWN", "REJECTED", "UNAVAILABLE"]
    targets: List[str] = Field(default_factory=list)
    faithful: bool = True
    raw: str = ""


class ConversationTurn(BaseModel):
    turn: int
    action_type: ActionType
    content: str
    result: str = ""
    key: str = ""  # catalog key the action used (ask category / exam id / test id); "" for SAY/DIAGNOSE
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DifferentialSnapshot(BaseModel):
    """Lightweight mirror of a differential.DifferentialItem stored on PatientState so the
    clinical summary and logging layers don't need to import differential.py's ranking engine."""

    diagnosis: str
    rank: int
    confidence_band: str
    urgency: str
    dangerous_if_missed: bool
    diagnosis_id: str = ""


class RedFlag(BaseModel):
    condition: str
    reason: str
    severity: str


class PatientState(BaseModel):
    """Everything accumulated about the current case (spec section 2)."""

    case_id: str = "case"
    # UI/output locale only -- "en" | "ko" | "ja" | "zh". Never affects internal reasoning: every
    # canonical diagnosis_id/concept tag/lab.* key stays identical regardless of this value (spec:
    # internal reasoning language and display language are strictly separated). Persisted with the
    # case (not just passed once at creation) since a production backend constructs a fresh
    # DoctorAgent(lang=...) on every decide() call -- see nova_service.py's own module docstring on
    # why -- so this is the only place that value can durably live between turns.
    locale: str = "en"
    demographics: Demographics = Field(default_factory=Demographics)
    # Round W: relation word of a caregiver's first statement that denotes the patient ("husband"), or None.
    proxy_relation: Optional[str] = None

    chief_complaint: str = ""
    symptoms: List[str] = Field(default_factory=list)
    symptom_onset: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    pertinent_positives: List[str] = Field(default_factory=list)
    pertinent_negatives: List[str] = Field(default_factory=list)
    ambiguous_findings: List[str] = Field(default_factory=list)

    past_medical_history: List[str] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    allergies: List[Allergy] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    social_history: List[str] = Field(default_factory=list)

    # Raw-fact preservation (spec section 4/24C): a free-text medication/allergy answer is ALWAYS
    # kept here verbatim, even when structured extraction into `medications`/`allergies` above is
    # only a best-effort guess (e.g. "I am taking oral contraceptive pills" isn't a clean drug
    # name) -- so downstream reasoning (differential/safety) never loses the clinical fact just
    # because it didn't fit the structured model cleanly.
    medication_text: List[str] = Field(default_factory=list)
    allergy_text: List[str] = Field(default_factory=list)
    raw_history_facts: List[str] = Field(default_factory=list)

    physical_examinations: Dict[str, str] = Field(default_factory=dict)
    vital_signs: List[VitalSigns] = Field(default_factory=list)
    # Descriptive labels (e.g. "Marked tachycardia") derived from the latest structured vital
    # signs via the same thresholds safety.py's vital_sign_red_flags uses -- lets the differential
    # engine's keyword matcher credit a disease's vital-sign-phrased typical_features from
    # structured numbers, not only from literal prose (see vitals_parser.describe_vital_sign_abnormalities).
    vital_sign_findings: List[str] = Field(default_factory=list)
    laboratory_tests: Dict[str, str] = Field(default_factory=dict)
    imaging: Dict[str, str] = Field(default_factory=dict)

    initial_vitals_text: Optional[str] = None
    rejected_exams: List[str] = Field(default_factory=list)
    # Round Q: per-action outcomes, features answered "don't know", and detailed questions that went out only as a
    # generic fallback (never re-sent, never counted as having asked the detailed discriminator).
    action_outcomes: List[ActionOutcome] = Field(default_factory=list)
    unknown_findings: List[str] = Field(default_factory=list)
    unfaithful_questions: List[str] = Field(default_factory=list)
    # Round Q: features denied ONLY by a bare "No" (retracted into a conflict if the patient later reports them).
    bare_denials: List[str] = Field(default_factory=list)
    # Round Q: why the encounter is ending ("supported" | "information_exhausted" | "budget"), set by the selector
    # whenever it returns DIAGNOSE. Completion is not support: see nova_agent/final_decision.py.
    completion_reason: Optional[str] = None
    performed_actions: List[ConversationTurn] = Field(default_factory=list)
    asked_questions: List[str] = Field(default_factory=list)
    completed_examinations: List[str] = Field(default_factory=list)
    completed_tests: List[str] = Field(default_factory=list)
    conversation_history: List[ConversationTurn] = Field(default_factory=list)

    current_differential: List[DifferentialSnapshot] = Field(default_factory=list)
    red_flags: List[RedFlag] = Field(default_factory=list)

    turn_count: int = 0
    max_turns: int = 60
    # Preliminary-round rules (2026 organizer briefing): no TEST action exists, vital signs arrive
    # with the first patient statement, and a case has a wall-clock limit. Off for every legacy
    # caller, so all existing development benchmarks keep their exact behavior.
    preliminary_rules: bool = False
    time_limit_seconds: Optional[float] = None
    model_config = ConfigDict(validate_assignment=True)

    @field_validator("max_turns", mode="before")
    @classmethod
    def cap_max_turns(cls, value):
        from nova_agent.config import effective_max_turns
        return effective_max_turns(value)

    final_diagnosis: Optional[str] = None
    final_diagnosis_rationale: Optional[str] = None

    # Round E (defect: forced/low-evidence diagnosis must never look like a confidently
    # evidence-supported NORMAL_DIAGNOSIS). Distinct, independently-readable flags recorded once a
    # DIAGNOSE action is actually taken (see record_diagnose() below) -- None until then, never a
    # default of False, so "not yet diagnosed" is never confused with "diagnosed normally":
    #   - forced_due_to_turn_limit: StopPolicy's hard remaining-turns fallback fired (StopDecision.
    #     forced) -- the case would not otherwise have been ready to diagnose yet.
    #   - zero_evidence_at_diagnosis: the diagnosed item was differential.py's own
    #     fallback_candidate (candidate_generator.py's whole-catalog zero-evidence fallback) --
    #     literally nothing matched anything; this is an UNKNOWN_PRESENTATION forced through.
    #   - fallback_candidate_selected: the diagnosed item's OWN candidate_sources were entirely
    #     evidence-free sources (safety_candidate/contextual_safety/zero_evidence_fallback/
    #     ontology_broadening/ontology_retrieval) -- broader than zero_evidence_at_diagnosis (which
    #     requires the WHOLE differential to be the catalog fallback): this can be true even when
    #     other, better-evidenced candidates existed elsewhere in the differential.
    # Populated from orchestrator.DoctorAgent.decide()'s own already-computed StopDecision/
    # differential via `pending_diagnosis_quality` (transient, cleared once consumed) rather than
    # widening decide()'s/observe()'s public signatures.
    final_diagnosis_forced_due_to_turn_limit: Optional[bool] = None
    final_diagnosis_zero_evidence_at_diagnosis: Optional[bool] = None
    final_diagnosis_fallback_candidate_selected: Optional[bool] = None
    pending_diagnosis_quality: Optional[Dict[str, bool]] = None
    # JSON-safe internal epistemic result; no protocol labels or patient transcript copies.
    evidence_assessment: Optional[dict] = None
    # Retrieval provenance only. Not observations, exclusions, or diagnostic scores.
    retrieval_safety_watch: List[str] = Field(default_factory=list)

    # Wall-clock case start (spec: graceful degradation as a per-case time budget runs out).
    # time.time()-based (not perf_counter) since it must be meaningful even if PatientState is
    # constructed and later resumed across separate calls, not just within one process lifetime.
    case_started_at_unix: float = Field(default_factory=time.time)

    @property
    def case_elapsed_seconds(self) -> float:
        return time.time() - self.case_started_at_unix

    def time_nearly_up(self) -> bool:
        """Preliminary round (20 minutes per case; a case never submitted scores 0): True once the fixed
        safety fraction of the budget is spent, OR once the measured seconds per turn show that the
        closing dialogue plus the final submission would no longer fit. Always False without a limit."""
        from nova_agent.config import (PRELIMINARY_CLOSING_TURNS, PRELIMINARY_TIME_HARD_FRACTION,
                                       PRELIMINARY_TIME_SAFETY_FRACTION)
        if self.time_limit_seconds is None:
            return False
        elapsed = self.case_elapsed_seconds
        if elapsed >= self.time_limit_seconds * PRELIMINARY_TIME_SAFETY_FRACTION:
            return True
        turns = len(self.performed_actions)
        if turns >= 3:  # need a few samples before the average means anything
            per_turn = elapsed / turns
            return elapsed + PRELIMINARY_CLOSING_TURNS * per_turn * 1.5 >= self.time_limit_seconds * PRELIMINARY_TIME_HARD_FRACTION
        return False

    # LLM call reliability (spec: an evaluation run must never look "normal" while the real LLM is
    # actually failing every turn and the agent is silently riding the deterministic fallback).
    # Only incremented for a REAL LLM provider attempt -- MockLLMClient never touches these, since
    # it makes no real call at all (see orchestrator.decide() / llm_client.BaseLLMClient).
    llm_call_count: int = 0
    # HTTP requests actually sent to the model INCLUDING retries (llm_call_count is logical calls); the fixed
    # model's session caps count requests. Tokens are server-reported when available, else estimated.
    llm_http_attempts: int = 0
    llm_tokens_estimated: bool = False
    llm_success_count: int = 0
    llm_failure_count: int = 0
    llm_fallback_count: int = 0
    llm_total_latency_seconds: float = 0.0
    llm_latency_sample_count: int = 0
    llm_total_input_tokens: int = 0
    llm_total_output_tokens: int = 0
    # True only once at least one real call actually reported a usage block -- distinguishes
    # "token usage unavailable from this endpoint" (stay None/0, never estimated) from "zero
    # tokens used", per spec: never display an estimate as if it were a real reported value.
    llm_token_usage_available: bool = False

    @property
    def remaining_turns(self) -> int:
        return max(0, self.max_turns - self.turn_count)

    @property
    def llm_success_rate(self) -> Optional[float]:
        return (self.llm_success_count / self.llm_call_count) if self.llm_call_count else None

    @property
    def llm_fallback_rate(self) -> Optional[float]:
        return (self.llm_fallback_count / self.llm_call_count) if self.llm_call_count else None

    @property
    def real_llm_ever_succeeded(self) -> Optional[bool]:
        """None when no real LLM call was ever attempted this case (mock provider, or a
        case-budget that skipped every turn) -- not applicable, not a pass/fail signal either way.
        True once at least one real call succeeded; False when calls were attempted but every
        single one failed even after bounded retry (spec: a competition-mode case that never got a
        single real-LLM success must be distinguishable from one that did, not just visible as "some
        fallback rate" -- see competition/adapter.py's DIAGNOSE-time check)."""
        if self.llm_call_count == 0:
            return None
        return self.llm_success_count > 0

    @property
    def llm_avg_latency_seconds(self) -> Optional[float]:
        return (self.llm_total_latency_seconds / self.llm_latency_sample_count) if self.llm_latency_sample_count else None

    # --- duplicate-detection helpers -----------------------------------------------------------

    def question_asked(self, discriminator: str) -> bool:
        return f"ask:{discriminator}" in self.asked_questions

    def question_attempted(self, discriminator: str) -> bool:
        """Asked faithfully OR already sent as a generic fallback: either way, not to be sent again."""
        return self.question_asked(discriminator) or discriminator in self.unfaithful_questions

    def question_observed(self, discriminator: str) -> bool:
        """A faithfully asked question with an interpretable answer, not merely an attempt."""
        if not self.question_asked(discriminator):
            return False
        outcomes = [o for o in self.action_outcomes if o.action_type == "ASK" and o.key == discriminator]
        return not outcomes or (outcomes[-1].status == "OBSERVED" and outcomes[-1].faithful)

    def exam_observed(self, exam_id: str) -> bool:
        """An examination that actually produced a result (not rejected, not 'result unknown')."""
        if exam_id not in self.completed_examinations or exam_id in self.rejected_exams:
            return False
        outcomes = [o for o in self.action_outcomes if o.action_type == "EXAM" and o.key == exam_id]
        return not outcomes or outcomes[-1].status == "OBSERVED"

    def exam_done(self, exam_id: str) -> bool:
        return exam_id in self.completed_examinations

    def test_done(self, test_id: str) -> bool:
        return test_id in self.completed_tests

    def is_duplicate(self, action_type: ActionType, key: str) -> bool:
        if action_type == "ASK":
            return self.question_attempted(key)
        if action_type == "EXAM":
            return self.exam_done(key)
        if action_type == "TEST":
            return self.test_done(key)
        return False

    # --- record-keeping --------------------------------------------------------------------------

    def record_ask(self, discriminator: str, question_text: str, answer: str, faithful: bool = True) -> None:
        """``faithful=False``: the question actually put to the patient was a generic fallback, not the detailed
        discriminator -- the generic category is recorded as asked, the detailed one only as attempted."""
        self.turn_count += 1
        category, _, detail = discriminator.partition(":")
        if faithful or not detail:
            key = f"ask:{discriminator}"
        else:
            key = f"ask:{category}"
            if discriminator not in self.unfaithful_questions:
                self.unfaithful_questions.append(discriminator)
        if key not in self.asked_questions:
            self.asked_questions.append(key)
        turn = ConversationTurn(turn=self.turn_count, action_type="ASK", content=question_text, result=answer, key=discriminator)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)
        target = detail.replace("_", " ").strip() if (detail and faithful) else None
        from nova_agent.config import get_config
        kind = answer_kind(answer) if get_config().answer_grounding_enabled else None
        ambiguous_yes = kind == "yes" and target and re.search(r"\bor\b|또는|혹은", target, re.I)
        ambiguous_no = kind == "no" and target and re.search(r"\band\b|그리고", target, re.I)
        self.action_outcomes.append(ActionOutcome(
            action_type="ASK", key=discriminator, status="UNKNOWN" if kind == "unknown" or ambiguous_yes or ambiguous_no else "OBSERVED",
            targets=[target] if target else [], faithful=faithful or not detail, raw=answer or ""))
        self._absorb_answer(discriminator, answer, target=target, kind=kind)

    def record_exam(self, exam_id: str, result: str) -> None:
        self.turn_count += 1
        if exam_id in self.rejected_exams:
            self.rejected_exams.remove(exam_id)
        if exam_id not in self.completed_examinations:
            self.completed_examinations.append(exam_id)
        spec = EXAM_CATALOG.get(exam_id)
        content = spec["name_en"] if spec else exam_id
        turn = ConversationTurn(turn=self.turn_count, action_type="EXAM", content=content, result=result, key=exam_id)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)
        self.physical_examinations[exam_id] = result
        unknown = bool(_EXAM_RESULT_UNKNOWN.search(result or "")) or not (result or "").strip()
        self.action_outcomes.append(ActionOutcome(action_type="EXAM", key=exam_id, status="UNKNOWN" if unknown else "OBSERVED",
                                                  raw=result or ""))
        if exam_id == "vital_signs":
            parsed = parse_vital_signs(result)
            if parsed is not None:
                self.vital_signs.append(parsed)
                for finding in describe_vital_sign_abnormalities(parsed, self.demographics.age):
                    if finding not in self.vital_sign_findings:
                        self.vital_sign_findings.append(finding)
        # Round U follow-up: an examination that OBSERVES a feature earlier denied only by a bare "No" turns that
        # denial into a recorded conflict (the observation is kept), exactly as a later patient statement does.
        self._retract_contradicted_bare_denials()

    def record_initial_vitals(self, text: str) -> None:
        """Vital signs handed over WITH the first patient statement (preliminary-round rules): real
        objective evidence, but obtained by no action, so no turn is consumed. Recorded under the
        same keys an EXAM would use so every downstream consumer treats it identically."""
        if not text:
            return
        if "vital_signs" not in self.completed_examinations:
            self.completed_examinations.append("vital_signs")
        self.physical_examinations["vital_signs"] = text
        parsed = parse_vital_signs(text)
        if parsed is not None:
            self.vital_signs.append(parsed)
            for finding in describe_vital_sign_abnormalities(parsed, self.demographics.age):
                if finding not in self.vital_sign_findings:
                    self.vital_sign_findings.append(finding)
        self.initial_vitals_text = text

    def record_exam_rejected(self, exam_id: str) -> None:
        """The environment rejected an examination request (not on its list). Per the preliminary
        rules a rejected request costs NO turn; it is marked done so it is never re-sent, and it
        contributes no evidence (never recorded as a normal finding)."""
        if exam_id not in self.completed_examinations:
            self.completed_examinations.append(exam_id)
        self.rejected_exams.append(exam_id)
        self.action_outcomes.append(ActionOutcome(action_type="EXAM", key=exam_id, status="REJECTED"))

    def record_say(self, content: str, reply: str = "", key: str = "") -> None:
        """A conversational turn (explanation/empathy) that gathers no new history: costs one turn,
        and the patient's reply is NOT absorbed as clinical evidence."""
        self.turn_count += 1
        turn = ConversationTurn(turn=self.turn_count, action_type="SAY", content=content, result=reply, key=key)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)

    def record_test(self, test_id: str, result: str) -> None:
        self.turn_count += 1
        if test_id not in self.completed_tests:
            self.completed_tests.append(test_id)
        spec = TEST_CATALOG.get(test_id)
        content = spec["name_en"] if spec else test_id
        turn = ConversationTurn(turn=self.turn_count, action_type="TEST", content=content, result=result, key=test_id)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)
        if spec and spec["kind"] == "imaging":
            self.imaging[test_id] = result
        else:
            self.laboratory_tests[test_id] = result

    def record_diagnose(self, diagnosis: str, rationale: str = "") -> None:
        self.turn_count += 1
        self.final_diagnosis = diagnosis
        self.final_diagnosis_rationale = rationale
        # Consume whatever orchestrator.DoctorAgent.decide() staged in `pending_diagnosis_quality`
        # (see this class's own field docstrings) -- defaults to all-False only when decide() never
        # ran first (e.g. a test constructing state directly), never silently left as None once an
        # actual DIAGNOSE is recorded.
        quality = self.pending_diagnosis_quality or {}
        self.final_diagnosis_forced_due_to_turn_limit = quality.get("forced_due_to_turn_limit", False)
        self.final_diagnosis_zero_evidence_at_diagnosis = quality.get("zero_evidence_at_diagnosis", False)
        self.final_diagnosis_fallback_candidate_selected = quality.get("fallback_candidate_selected", False)
        self.pending_diagnosis_quality = None
        turn = ConversationTurn(turn=self.turn_count, action_type="DIAGNOSE", content=diagnosis, result=rationale)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)

    def _absorb_answer(self, discriminator: str, answer: str, target: Optional[str] = None,
                       kind: Optional[str] = None) -> None:
        """Very small deterministic extraction: route a free-text answer into the right
        PatientState bucket based on which question category was asked. Kept intentionally simple
        (no NLP) -- the structured discriminator already tells us what was asked, so we do not need
        to re-derive intent from the answer text, only classify it as a fresh symptom / positive /
        negative.

        A single answer often mixes affirmed and denied findings in one sentence (e.g. "diaphoresis
        and nausea; denies calf swelling, denies hemoptysis" or "No fever or chills but has severe
        chest pressure") -- treating the whole string as one positive-or-negative unit would
        silently lose (or invert) half of it, so the answer is first split into clause-level
        segments and each segment is classified independently.
        """
        category = discriminator.split(":", 1)[0]
        if kind is not None:
            # Round Q: a bare yes / no / don't-know. Grounded to the ONE feature the question really asked about;
            # otherwise it is no finding at all ("No" is not a symptom, "I don't know" is not a drug name).
            if target and kind == "yes":
                if re.search(r"\bor\b|또는|혹은", target, re.I) and target not in self.ambiguous_findings:
                    # Preserve the literal response for SOAP, but neither branch is observed.
                    self.ambiguous_findings.append(target)
                if target not in self.pertinent_positives:
                    self.pertinent_positives.append(target)
                if category == "associated_symptoms" and target not in self.associated_symptoms:
                    self.associated_symptoms.append(target)
            elif target and kind == "no":
                if re.search(r"\band\b|그리고", target, re.I):
                    # No to "A AND B?" does not establish that BOTH are absent.
                    # Keep the answer, but neither generate individual negatives
                    # nor mark this compound discriminator observed.
                    if target not in self.ambiguous_findings:
                        self.ambiguous_findings.append(target)
                    if target not in self.unknown_findings:
                        self.unknown_findings.append(target)
                elif self._already_reported(target):
                    # A bare "No" that contradicts what the patient already described is not a clean denial: keep
                    # the earlier observation and record the conflict instead of erasing either.
                    label = f"conflicting answer: {target}"
                    if label not in self.unknown_findings:
                        self.unknown_findings.append(label)
                else:
                    denial = f"no {target}"
                    if denial not in self.pertinent_negatives:
                        self.pertinent_negatives.append(denial)
                    if target not in self.bare_denials:
                        self.bare_denials.append(target)
            elif kind == "unknown":
                label = target or category
                if label not in self.unknown_findings:
                    self.unknown_findings.append(label)
            if category in ("onset", "duration", "severity") and kind != "unknown":
                setattr(self, {"onset": "symptom_onset", "duration": "duration", "severity": "severity"}[category],
                        answer)
            if answer and answer not in self.raw_history_facts:
                self.raw_history_facts.append(f"[{category}] {answer}")
            if category == "medication" and answer and answer not in self.medication_text:
                self.medication_text.append(answer)
            if category == "allergy" and answer and answer not in self.allergy_text:
                self.allergy_text.append(answer)
            self._retract_contradicted_bare_denials()
            return
        from nova_agent.evidence_scope import evidence_clauses, patient_evidence_text
        # Preserve relatives' statements even when volunteered to a symptom
        # question. Project before splitting: list continuations share subject.
        for clause in evidence_clauses(answer, source=category):
            if clause.experiencer == "FAMILY" and clause.text.strip() not in self.family_history:
                self.family_history.append(clause.text.strip())
        patient_answer = patient_evidence_text(answer)
        segments = _split_answer_segments(answer if category == "family_history" else patient_answer)
        unknown_segments = [s for s in segments if answer_kind(s) == "unknown"]
        for segment in unknown_segments:
            if segment not in self.unknown_findings:
                self.unknown_findings.append(segment)
        positive_segments = [s for s in segments if s not in unknown_segments and not _segment_is_negated(s)]
        negative_segments = [s for s in segments if s not in unknown_segments and _segment_is_negated(s)]
        combined_positive = "; ".join(positive_segments)

        if category == "onset":
            self.symptom_onset = combined_positive or answer
        elif category == "duration":
            self.duration = combined_positive or answer
        elif category == "severity":
            self.severity = combined_positive or answer
        elif category == "past_medical_history":
            if combined_positive and combined_positive not in self.past_medical_history:
                self.past_medical_history.append(combined_positive)
        elif category == "family_history":
            if combined_positive and combined_positive not in self.family_history:
                self.family_history.append(combined_positive)
        elif category == "social_history":
            if combined_positive and combined_positive not in self.social_history:
                self.social_history.append(combined_positive)
        elif category == "medication":
            # Raw fact is ALWAYS kept (spec section 4/24C) even when a clean drug name can't be
            # parsed out; a best-effort Medication record is also added so structured consumers
            # (safety.py's medication-risk checks) have something to match against.
            if answer and answer not in self.medication_text:
                self.medication_text.append(answer)
            for seg in positive_segments:
                if _ANSWER_UNKNOWN.search(seg):
                    # "I cannot remember their names": the raw text is kept above; no drug of that name exists.
                    if "medication names" not in self.unknown_findings:
                        self.unknown_findings.append("medication names")
                    continue
                self.add_medication(Medication(name=seg, status="active", note=answer))
        elif category == "allergy":
            if answer and answer not in self.allergy_text:
                self.allergy_text.append(answer)
            for seg in positive_segments:
                self.add_allergy(Allergy(substance=seg, category="unknown", severity="UNKNOWN", reaction=answer))
        else:
            for seg in positive_segments:
                if seg not in self.pertinent_positives:
                    self.pertinent_positives.append(seg)
                contextual = _contextualise_modifier(category, seg)
                if contextual and contextual not in self.pertinent_positives:
                    # Round O: the question gives the answer its meaning ("twisting" asked as an aggravating factor
                    # means "worse with twisting"); the bare answer is kept too.
                    self.pertinent_positives.append(contextual)
                if category == "associated_symptoms" and seg not in self.associated_symptoms:
                    self.associated_symptoms.append(seg)
            for seg in negative_segments:
                if seg not in self.pertinent_negatives:
                    self.pertinent_negatives.append(seg)

        if answer and answer not in self.raw_history_facts:
            self.raw_history_facts.append(f"[{category}] {answer}")
        self._retract_contradicted_bare_denials()

    def _retract_contradicted_bare_denials(self) -> None:
        """A feature denied only by an earlier bare "No" and now reported in the patient's own words is a conflict,
        not a denial: the denial is withdrawn and the conflict recorded (an explicit denial is never withdrawn)."""
        for target in list(self.bare_denials):
            if self._already_reported(target, include_last=True):
                self.bare_denials.remove(target)
                denial = f"no {target}"
                if denial in self.pertinent_negatives:
                    self.pertinent_negatives.remove(denial)
                label = f"conflicting answer: {target}"
                if label not in self.unknown_findings:
                    self.unknown_findings.append(label)

    def _already_reported(self, feature: str, include_last: bool = False) -> bool:
        """The feature (or its canonical concept) is in what the patient has already said positively."""
        from nova_agent.matching import feature_present_with_aliases
        history = self.conversation_history if include_last else self.conversation_history[:-1]
        said = [self.chief_complaint, *self.symptoms, *self.associated_symptoms, *self.pertinent_positives,
                *self.objective_findings_text(),
                *[t.result for t in history if t.action_type == "ASK" and t.result and answer_kind(t.result) is None]]
        from nova_agent.documented_diagnosis import diagnosis_evidence_text
        said = _with_canonical_concepts([diagnosis_evidence_text(t, allow_historical=False) for t in said if t])
        # A bare No to an OR question conflicts when either branch is already
        # observed (including measured fever). Do not erase an objective finding.
        branches = [part.strip() for part in re.split(r"\bor\b|또는|혹은", feature) if part.strip()]
        from nova_agent.config import get_config
        if get_config().denial_v2_enabled:
            # Round V: a bare No to a qualified form of a symptom the patient already reported ("worsening shortness of
            # breath" after "I get breathless walking") is ambiguous -- it may deny only the qualifier -- so it is a
            # conflict, not a denial of the symptom. Only leading temporal/severity qualifiers are removed.
            from nova_agent.differential import _QUALIFIER_PREFIX
            branches += [core for core in (_QUALIFIER_PREFIX.sub("", b.lower()) for b in branches) if core not in branches]
        return any(feature_present_with_aliases(part, said, scrub_negated_spans=True) for part in branches)

    def add_medication(self, medication: Medication) -> None:
        self.medications.append(medication)

    def add_allergy(self, allergy: Allergy) -> None:
        self.allergies.append(allergy)

    def add_symptom(self, symptom: str) -> None:
        if symptom not in self.symptoms:
            self.symptoms.append(symptom)

    def latest_vital_signs(self) -> Optional[VitalSigns]:
        return self.vital_signs[-1] if self.vital_signs else None

    def all_findings_text(self, include_context: bool = True, include_family: bool = True) -> List[str]:
        """Flat bag of every free-text clinical finding gathered so far, used by keyword-matching
        modules (differential.py, safety.py) as the evidence corpus."""
        out = list(self.symptoms) + list(self.associated_symptoms) + list(self.pertinent_positives)
        if include_context:
            out += list(self.past_medical_history) + list(self.social_history)
        out += [self.chief_complaint, self.symptom_onset or "", self.severity or "", self.duration or ""]
        out += list(self.physical_examinations.values()) + list(self.imaging.values())
        out += list(self.vital_sign_findings)
        out += list(self.laboratory_tests.values())
        from nova_agent.clinical_concepts import procedure_context_findings
        out += [f for key, value in self.imaging.items() for f in procedure_context_findings(key, value)]
        if include_context:
            out += list(self.medication_text) + list(self.allergy_text)
            out += [m.name for m in self.medications] + [a.substance for a in self.allergies]
        from nova_agent.documented_diagnosis import diagnosis_evidence_text
        objective = set(self.physical_examinations.values()) | set(self.imaging.values()) | set(self.laboratory_tests.values())
        out = [diagnosis_evidence_text(t, allow_historical=include_context,
                                      source="patient_observation" if t in objective else "narrative") for t in out
               if t and t not in self.ambiguous_findings and answer_kind(t) != "unknown"]
        # Localized (ko/ja) symptom phrases also count as their canonical English wording, so
        # scoring (which matches English KB features) treats them like the English patient.
        from nova_agent.multilingual_concepts import english_evidence_for
        for t in list(out):
            out += [e for e in english_evidence_for(t) if e not in out]
        out = _with_canonical_concepts(out)
        # Public context view preserves family history; diagnostic/severity consumers
        # explicitly exclude it. Never canonicalise a relative's illness as a patient symptom.
        if include_context and include_family:
            out += list(self.family_history)
        return out

    def objective_findings_text(self) -> List[str]:
        """Narrower than all_findings_text(): only text that came from an EXAM/TEST actually
        performed (physical_examinations, imaging, laboratory_tests, vital_sign_findings) --
        excludes patient-reported symptoms, chief complaint, and (critically) past_medical_history/
        social_history/family_history. A knowledge-base `confirmatory_findings` phrase (e.g.
        cardiac_arrhythmia's "atrial fibrillation on ecg") represents a specific objective test/exam
        result, not a patient history fact -- scoring it against the full findings bag let a patient
        merely REPORTING a past diagnosis of atrial fibrillation (in past_medical_history, with no
        ECG ever performed) spuriously satisfy an ECG-specific confirmatory finding via plain
        word-overlap. Confirmatory findings must only ever be earned by evidence an EXAM/TEST action
        actually produced this encounter."""
        out = list(self.physical_examinations.values()) + list(self.imaging.values())
        out += list(self.vital_sign_findings)
        out += list(self.laboratory_tests.values())
        from nova_agent.clinical_concepts import procedure_context_findings
        out += [f for key, value in self.imaging.items() for f in procedure_context_findings(key, value)]
        from nova_agent.documented_diagnosis import diagnosis_evidence_text
        out = [diagnosis_evidence_text(t, allow_historical=False, source="patient_observation") for t in out if t]
        return _with_canonical_concepts(out)
