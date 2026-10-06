"""Clinical Summary (spec section 3).

Deterministic template over PatientState + the current differential -- same design philosophy as
SynexAgent's backend/app/services/clinical_summary.py: every sentence traces back to a real,
recorded observation, nothing is invented. This structured summary (not the raw conversation
history) is what gets handed to the LLM each turn, keeping token usage bounded and hallucination
risk low regardless of how many turns have elapsed.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from nova_agent.differential import DifferentialItem
from nova_agent.safety import SafetyFinding
from nova_agent.state import PatientState


class ClinicalSummary(BaseModel):
    chief_complaint: str
    demographics: str
    important_positive_findings: List[str]
    important_negative_findings: List[str]
    exams_performed: List[str]
    tests_performed: List[str]
    top_differential: List[str]
    unresolved_missing_evidence: List[str]
    red_flags: List[str]
    turn_count: int
    remaining_turns: int
    history: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    social_history: List[str] = Field(default_factory=list)
    medication_history: List[str] = Field(default_factory=list)
    allergy_history: List[str] = Field(default_factory=list)
    symptom_course: List[str] = Field(default_factory=list)
    completed_action_keys: dict = Field(default_factory=dict)
    previous_hypotheses: List[str] = Field(default_factory=list)

    def to_text(self) -> str:
        def section(title: str, items: List[str]) -> str:
            body = "\n".join(f"- {i}" for i in items) if items else "- (none recorded)"
            return f"{title}:\n{body}"

        return "\n\n".join([
            f"Chief complaint: {self.chief_complaint}",
            f"Demographics: {self.demographics}",
            section("Important positive findings", self.important_positive_findings),
            section("Important negative findings", self.important_negative_findings),
            section("Past medical history (not current symptoms)", self.history),
            section("Family history (not the patient's symptoms)", self.family_history),
            section("Social history", self.social_history),
            section("Medication history (reported; preserve timing/status)", self.medication_history),
            section("Allergy history (reported)", self.allergy_history),
            section("Symptom timing and course (reported)", self.symptom_course),
            section("Exams performed", self.exams_performed),
            section("Tests performed", self.tests_performed),
            section("Top differential", self.top_differential),
            section("Previous-turn hypotheses (not observed facts; revise against new evidence)", self.previous_hypotheses),
            section("Unresolved discriminating evidence", self.unresolved_missing_evidence),
            section("Red flags", self.red_flags),
            f"Turn {self.turn_count} / remaining {self.remaining_turns}",
        ])


def build_clinical_summary(state: PatientState, differential: List[DifferentialItem],
                            safety_findings: List[SafetyFinding]) -> ClinicalSummary:
    demo = state.demographics
    demo_text = ", ".join(filter(None, [
        f"{demo.age}y" if demo.age is not None else None,
        demo.sex,
        "pregnant" if demo.pregnant is True else "not pregnant" if demo.pregnant is False else None,
    ])) or "unknown"

    def _differential_line(d: DifferentialItem) -> str:
        # Concise per-candidate provenance (spec: tier + candidate source alongside the existing
        # confidence/urgency/dangerous fields) -- never a full evidence dump for every item, which
        # would blow up prompt size once the differential can hold up to reasoning_top_k (~25)
        # candidates in competition mode; supporting/contradictory/missing evidence detail stays in
        # the separate, already-bounded "unresolved discriminating evidence" section below.
        tier = "ontology" if d.diagnosis_id.startswith("onto::") else "kb"
        source = d.candidate_sources[0] if d.candidate_sources else "llm"
        danger = "DANGEROUS" if d.dangerous_if_missed else "routine"
        return f"{d.rank}. {d.diagnosis} [{tier}/{source}] ({d.confidence_band}, {d.urgency}, {danger})"

    top_differential_text = [_differential_line(d) for d in differential]
    unresolved = []
    for d in differential[:3]:
        for missing in d.missing_discriminative_evidence[:2]:
            entry = f"{d.diagnosis}: {missing}"
            if entry not in unresolved:
                unresolved.append(entry)

    exams = [f"{k}: {v}" for k, v in state.physical_examinations.items()]
    tests = [f"{k}: {v}" for k, v in {**state.laboratory_tests, **state.imaging}.items()]
    red_flags = [f"{f.condition} - {f.reason}" for f in safety_findings]

    return ClinicalSummary(
        chief_complaint=state.chief_complaint or "(not yet stated)",
        demographics=demo_text,
        important_positive_findings=list(dict.fromkeys([
            *state.pertinent_positives, *state.symptoms, *state.associated_symptoms,
            *state.vital_sign_findings])),
        important_negative_findings=list(state.pertinent_negatives),
        exams_performed=exams,
        tests_performed=tests,
        top_differential=top_differential_text,
        unresolved_missing_evidence=unresolved,
        red_flags=red_flags,
        turn_count=state.turn_count,
        remaining_turns=state.remaining_turns,
        history=list(state.past_medical_history),
        family_history=list(state.family_history),
        social_history=list(state.social_history),
        medication_history=list(dict.fromkeys([
            *state.medication_text,
            *(f"{m.name}; status={m.status}; note={m.note}" for m in state.medications)])),
        allergy_history=list(dict.fromkeys([
            *state.allergy_text,
            *(f"{a.substance}; reaction={a.reaction}" for a in state.allergies)])),
        symptom_course=[f"{label}: {value}" for label, value in (
            ('onset', state.symptom_onset), ('duration', state.duration),
            ('severity', state.severity)) if value],
        completed_action_keys={'ASK': list(state.asked_questions),
                               'EXAM': list(state.completed_examinations),
                               'TEST': list(state.completed_tests)},
        previous_hypotheses=[d.diagnosis for d in state.current_differential],
    )
