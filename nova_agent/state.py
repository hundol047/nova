"""Patient State Manager (spec section 2).

Holds everything the Doctor Agent has learned about the current case, accumulated turn by turn.
Reuses SynexAgent's own Pydantic models (Allergy, Medication, Lab, VitalSigns) for the sub-records
that already have a validated shape in the vendored backend, instead of redefining them.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from nova_agent._synex import Allergy, Medication, VitalSigns
from nova_agent.taxonomy import EXAM_CATALOG, TEST_CATALOG

ActionType = Literal["ASK", "EXAM", "TEST", "DIAGNOSE"]


def normalize_key(text: str) -> str:
    """Collapse whitespace/punctuation/case so trivially-different phrasings of the same free
    text hash identically. Used as a last-resort fallback when a piece of content does not match
    any catalog entry (normal path is the catalog id itself, which is already stable)."""
    lowered = text.strip().lower()
    lowered = re.sub(r"[^\w\s가-힣]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


_NEGATION_MARKERS = ["denies", "denied", "no ", "none", "negative for", "not present", "아니", "없습니다", "없음"]


def _split_answer_segments(answer: str) -> List[str]:
    """Splits a free-text answer into clause-level segments so a single sentence that both affirms
    and denies findings (e.g. "diaphoresis and nausea; denies calf swelling, denies hemoptysis")
    can be classified segment-by-segment instead of as one all-or-nothing unit."""
    if not answer:
        return []
    segments: List[str] = []
    for part in re.split(r";", answer):
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

    physical_examinations: Dict[str, str] = Field(default_factory=dict)
    vital_signs: List[VitalSigns] = Field(default_factory=list)
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
        and nausea; denies calf swelling, denies hemoptysis") -- treating the whole string as one
        positive-or-negative unit would silently lose (or invert) half of it, so the answer is first
        split into clause-level segments and each segment is classified independently.
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
            pass  # structured medication entries are added via add_medication(), not free text
        elif category == "allergy":
            pass  # structured allergy entries are added via add_allergy()
        else:
            for seg in positive_segments:
                if seg not in self.pertinent_positives:
                    self.pertinent_positives.append(seg)
                if category == "associated_symptoms" and seg not in self.associated_symptoms:
                    self.associated_symptoms.append(seg)
            for seg in negative_segments:
                if seg not in self.pertinent_negatives:
                    self.pertinent_negatives.append(seg)

    def add_medication(self, medication: "Medication") -> None:
        self.medications.append(medication)

    def add_allergy(self, allergy: "Allergy") -> None:
        self.allergies.append(allergy)

    def add_symptom(self, symptom: str) -> None:
        if symptom not in self.symptoms:
            self.symptoms.append(symptom)

    def all_findings_text(self) -> List[str]:
        """Flat bag of every free-text clinical finding gathered so far, used by keyword-matching
        modules (differential.py, safety.py) as the evidence corpus."""
        out = list(self.symptoms) + list(self.associated_symptoms) + list(self.pertinent_positives)
        out += list(self.past_medical_history) + list(self.social_history) + list(self.family_history)
        out += [self.chief_complaint, self.symptom_onset or "", self.severity or "", self.duration or ""]
        out += list(self.physical_examinations.values()) + list(self.imaging.values())
        out += list(self.laboratory_tests.values())
        return [t for t in out if t]
