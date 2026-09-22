"""Patient State Manager (spec section 2).

Holds everything the Doctor Agent has learned about the current case, accumulated turn by turn.
Uses nova_agent's own standalone Medication/Allergy/VitalSigns models (nova_agent/models.py) --
no dependency on the vendored SynexAgent backend (spec section 17).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from nova_agent.models import Allergy, Medication, VitalSigns
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG
from nova_agent.vitals_parser import describe_vital_sign_abnormalities, parse_vital_signs

ActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]


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
    r";|(?<=\w)\s+but\s+|(?<=\w)\s+however\s+|(?<=\w)\s+although\s+|(?<=\w)\s+except\s+(?:that\s+)?",
    re.IGNORECASE,
)

_NEGATION_MARKERS = [
    "denies", "denied", "no ", "none", "negative for", "not present", "without",
    "don't have", "doesn't have", "do not have", "does not have",
    "didn't have", "did not have", "never had", "not experiencing", "not having",
    "아니", "없습니다", "없음",
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
        if re.search(r"\bdenies\b", part, re.IGNORECASE):
            pieces = re.split(r",\s*(?=denies\b)", part, flags=re.IGNORECASE)
            segments.extend(p.strip() for p in pieces if p.strip())
        else:
            segments.append(part)
    return segments


def _segment_is_negated(segment: str) -> bool:
    lowered = segment.lower()
    return any(marker in lowered for marker in _NEGATION_MARKERS)


class Demographics(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = None
    pregnant: Optional[bool] = None


class ConversationTurn(BaseModel):
    turn: int
    action_type: ActionType
    content: str
    result: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DifferentialSnapshot(BaseModel):
    """Lightweight mirror of a differential.DifferentialItem stored on PatientState so the
    clinical summary and logging layers don't need to import differential.py's ranking engine."""

    diagnosis: str
    rank: int
    confidence_band: str
    urgency: str
    dangerous_if_missed: bool


class RedFlag(BaseModel):
    condition: str
    reason: str
    severity: str


class PatientState(BaseModel):
    """Everything accumulated about the current case (spec section 2)."""

    case_id: str = "case"
    demographics: Demographics = Field(default_factory=Demographics)

    chief_complaint: str = ""
    symptoms: List[str] = Field(default_factory=list)
    symptom_onset: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    pertinent_positives: List[str] = Field(default_factory=list)
    pertinent_negatives: List[str] = Field(default_factory=list)

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

    performed_actions: List[ConversationTurn] = Field(default_factory=list)
    asked_questions: List[str] = Field(default_factory=list)
    completed_examinations: List[str] = Field(default_factory=list)
    completed_tests: List[str] = Field(default_factory=list)
    conversation_history: List[ConversationTurn] = Field(default_factory=list)

    current_differential: List[DifferentialSnapshot] = Field(default_factory=list)
    red_flags: List[RedFlag] = Field(default_factory=list)

    turn_count: int = 0
    max_turns: int = 60
    final_diagnosis: Optional[str] = None
    final_diagnosis_rationale: Optional[str] = None

    @property
    def remaining_turns(self) -> int:
        return max(0, self.max_turns - self.turn_count)

    # --- duplicate-detection helpers -----------------------------------------------------------

    def question_asked(self, discriminator: str) -> bool:
        return f"ask:{discriminator}" in self.asked_questions

    def exam_done(self, exam_id: str) -> bool:
        return exam_id in self.completed_examinations

    def test_done(self, test_id: str) -> bool:
        return test_id in self.completed_tests

    def is_duplicate(self, action_type: ActionType, key: str) -> bool:
        if action_type == "ASK":
            return self.question_asked(key)
        if action_type == "EXAM":
            return self.exam_done(key)
        if action_type == "TEST":
            return self.test_done(key)
        return False

    # --- record-keeping --------------------------------------------------------------------------

    def record_ask(self, discriminator: str, question_text: str, answer: str) -> None:
        self.turn_count += 1
        key = f"ask:{discriminator}"
        if key not in self.asked_questions:
            self.asked_questions.append(key)
        turn = ConversationTurn(turn=self.turn_count, action_type="ASK", content=question_text, result=answer)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)
        self._absorb_answer(discriminator, answer)

    def record_exam(self, exam_id: str, result: str) -> None:
        self.turn_count += 1
        if exam_id not in self.completed_examinations:
            self.completed_examinations.append(exam_id)
        spec = EXAM_CATALOG.get(exam_id)
        content = spec["name_en"] if spec else exam_id
        turn = ConversationTurn(turn=self.turn_count, action_type="EXAM", content=content, result=result)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)
        self.physical_examinations[exam_id] = result
        if exam_id == "vital_signs":
            parsed = parse_vital_signs(result)
            if parsed is not None:
                self.vital_signs.append(parsed)
                for finding in describe_vital_sign_abnormalities(parsed):
                    if finding not in self.vital_sign_findings:
                        self.vital_sign_findings.append(finding)

    def record_test(self, test_id: str, result: str) -> None:
        self.turn_count += 1
        if test_id not in self.completed_tests:
            self.completed_tests.append(test_id)
        spec = TEST_CATALOG.get(test_id)
        content = spec["name_en"] if spec else test_id
        turn = ConversationTurn(turn=self.turn_count, action_type="TEST", content=content, result=result)
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
        turn = ConversationTurn(turn=self.turn_count, action_type="DIAGNOSE", content=diagnosis, result=rationale)
        self.performed_actions.append(turn)
        self.conversation_history.append(turn)

    def _absorb_answer(self, discriminator: str, answer: str) -> None:
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
        segments = _split_answer_segments(answer)
        positive_segments = [s for s in segments if not _segment_is_negated(s)]
        negative_segments = [s for s in segments if _segment_is_negated(s)]
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
                if category == "associated_symptoms" and seg not in self.associated_symptoms:
                    self.associated_symptoms.append(seg)
            for seg in negative_segments:
                if seg not in self.pertinent_negatives:
                    self.pertinent_negatives.append(seg)

        if answer and answer not in self.raw_history_facts:
            self.raw_history_facts.append(f"[{category}] {answer}")

    def add_medication(self, medication: Medication) -> None:
        self.medications.append(medication)

    def add_allergy(self, allergy: Allergy) -> None:
        self.allergies.append(allergy)

    def add_symptom(self, symptom: str) -> None:
        if symptom not in self.symptoms:
            self.symptoms.append(symptom)

    def latest_vital_signs(self) -> Optional[VitalSigns]:
        return self.vital_signs[-1] if self.vital_signs else None

    def all_findings_text(self) -> List[str]:
        """Flat bag of every free-text clinical finding gathered so far, used by keyword-matching
        modules (differential.py, safety.py) as the evidence corpus."""
        out = list(self.symptoms) + list(self.associated_symptoms) + list(self.pertinent_positives)
        out += list(self.past_medical_history) + list(self.social_history) + list(self.family_history)
        out += [self.chief_complaint, self.symptom_onset or "", self.severity or "", self.duration or ""]
        out += list(self.physical_examinations.values()) + list(self.imaging.values())
        out += list(self.vital_sign_findings)
        out += list(self.laboratory_tests.values())
        out += list(self.medication_text) + list(self.allergy_text)
        out += [m.name for m in self.medications] + [a.substance for a in self.allergies]
        return [t for t in out if t]
