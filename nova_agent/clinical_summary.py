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
    history_facts: List[str] = Field(default_factory=list)
    symptom_timeline: List[str] = Field(default_factory=list)
    medications_and_allergies: List[str] = Field(default_factory=list)

    def to_text(self) -> str:
        def section(title: str, items: List[str]) -> str:
            body = "\n".join(f"- {i}" for i in items) if items else "- (none recorded)"
            return f"{title}:\n{body}"

        return "\n\n".join([
            f"Chief complaint: {self.chief_complaint}",
            f"Demographics: {self.demographics}",
            section("Symptom timeline", self.symptom_timeline),
            section("History (verbatim; may contain denials)", self.history_facts),
            section("Medications and allergies", self.medications_and_allergies),
            section("Important positive findings", self.important_positive_findings),
            section("Important negative findings", self.important_negative_findings),
            section("Exams performed", self.exams_performed),
            section("Tests performed", self.tests_performed),
            section("Top differential", self.top_differential),
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
        "pregnant" if demo.pregnant is True else ("not pregnant" if demo.pregnant is False else None),
    ])) or "unknown"

    top_differential_text = [
        f"{d.rank}. {d.diagnosis} ({d.confidence_band}, {'DANGEROUS' if d.dangerous_if_missed else 'routine'}); "
        f"support={d.supporting_evidence}; against={d.contradictory_evidence}"
        for d in differential
    ]
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
        important_positive_findings=list(dict.fromkeys(state.symptoms + state.associated_symptoms + state.pertinent_positives)),
        symptom_timeline=[f"{name}: {value}" for name,value in (("onset",state.symptom_onset),
            ("duration",state.duration),("severity",state.severity)) if value],
        history_facts=list(dict.fromkeys(state.raw_history_facts +
            ["Past history: " + t for t in state.past_medical_history] +
            ["Family history: " + t for t in state.family_history] +
            ["Social history: " + t for t in state.social_history])),
        medications_and_allergies=list(dict.fromkeys(
            ["Medication: " + t for t in state.medication_text] +
            ["Medication: " + m.name for m in state.medications] +
            ["Allergy: " + t for t in state.allergy_text] +
            ["Allergy: " + a.substance for a in state.allergies])),
        important_negative_findings=list(state.pertinent_negatives),
        exams_performed=exams,
        tests_performed=tests,
        top_differential=top_differential_text,
        unresolved_missing_evidence=unresolved,
        red_flags=red_flags,
        turn_count=state.turn_count,
        remaining_turns=state.remaining_turns,
    )
