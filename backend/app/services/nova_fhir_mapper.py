"""Bridges backend/app's existing Patient/ClinicalEncounter/VitalSigns/Medication/Allergy/Lab
objects (populated from either DemoAdapter or a real FHIRAdapter -- see emr_adapter.py) into
nova_agent's own PatientState fields.

Read-only, one direction only: EMR/FHIR data -> nova_agent input. Nothing here writes back to
`app.state.adapter` or any FHIR server -- see nova_service.py's module docstring for why (spec:
N.O.V.A. recommendations are never auto-committed to a real hospital record).

Deliberately does NOT construct nova_agent.models.Medication/Allergy objects with a forced,
possibly-wrong structured mapping for every field. Medication class/indication context that
nova_agent's risk-factor matching depends on (e.g. "anticoagulant", "ACE inhibitor") is not
reliably recoverable from this backend's drug catalog id alone in every case, so every EMR fact
is ALSO always appended to the corresponding `_text` list verbatim (medication_text/allergy_text) --
the same "raw-fact preservation" principle nova_agent/state.py's own docstring already documents
for exactly this reason: downstream reasoning must never lose a clinical fact just because it
didn't fit the structured model perfectly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# Same sys.path bootstrap as nova_service.py (see its own comment for the full rationale) -- this
# module can be imported directly (e.g. by a unit test that never imports nova_service.py first),
# so it needs its own copy rather than relying on import order.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from nova_agent.models import Allergy as NovaAllergy
from nova_agent.models import Medication as NovaMedication
from nova_agent.models import VitalSigns as NovaVitalSigns
from nova_agent.state import PatientState
from nova_agent.vitals_parser import describe_vital_sign_abnormalities

from ..schemas import ClinicalEncounter, Patient, VitalSigns
from .rule_engine import DRUGS


def _map_sex(sex: str) -> Optional[str]:
    lowered = (sex or "").strip().lower()
    if lowered in ("male", "m", "man"):
        return "male"
    if lowered in ("female", "f", "woman"):
        return "female"
    return None


def demographics_for(patient: Patient) -> dict:
    return {"age": patient.age, "sex": _map_sex(patient.sex)}


def _drug_display(drug_id: str) -> str:
    entry = DRUGS.get(drug_id)
    return f"{drug_id} ({entry['name_ko']})" if entry else drug_id


def _format_vitals(v: VitalSigns) -> str:
    parts = []
    if v.sbp is not None and v.dbp is not None:
        parts.append(f"BP {v.sbp}/{v.dbp}")
    if v.heart_rate is not None:
        parts.append(f"HR {v.heart_rate}")
    if v.respiratory_rate is not None:
        parts.append(f"RR {v.respiratory_rate}")
    if v.temperature_c is not None:
        parts.append(f"Temp {v.temperature_c}")
    if v.spo2 is not None:
        parts.append(f"SpO2 {v.spo2}%")
    return ", ".join(parts)


def apply_patient_context(state: PatientState, patient: Patient, encounter: Optional[ClinicalEncounter] = None) -> None:
    """Populates PatientState with everything already known about this patient/encounter in the
    EMR at case-creation time -- called once, right after DoctorAgent.new_case(), before the first
    decide(). Never called again mid-case (later facts arrive through the normal ASK/EXAM/TEST
    observation flow, exactly like any other N.O.V.A. case)."""
    for condition in patient.conditions:
        if condition and condition not in state.past_medical_history:
            state.past_medical_history.append(condition)

    for m in patient.medications:
        if m.status != "active":
            continue
        display = _drug_display(m.drug_id)
        state.medications.append(NovaMedication(name=m.drug_id, status="active", note=m.note))
        text = f"{display}{' -- ' + m.note if m.note else ''}"
        if text not in state.medication_text:
            state.medication_text.append(text)

    for a in patient.allergies:
        state.allergies.append(NovaAllergy(substance=a.substance, category=a.category,
                                            severity=a.severity, reaction=a.reaction))
        text = f"{a.substance} ({a.category}, {a.severity})" + (f": {a.reaction}" if a.reaction else "")
        if text not in state.allergy_text:
            state.allergy_text.append(text)

    for lab in patient.labs:
        range_note = ""
        if lab.low is not None or lab.high is not None:
            range_note = f" (ref {lab.low if lab.low is not None else '?'}-{lab.high if lab.high is not None else '?'})"
        state.laboratory_tests[lab.name] = f"{lab.value} {lab.unit}{range_note}"

    vitals_list = encounter.vital_signs if encounter else []
    if vitals_list:
        latest = vitals_list[-1]
        raw_text = _format_vitals(latest)
        nova_vitals = NovaVitalSigns(sbp=latest.sbp, dbp=latest.dbp, heart_rate=latest.heart_rate,
                                      respiratory_rate=latest.respiratory_rate,
                                      temperature_c=latest.temperature_c, spo2=latest.spo2,
                                      raw_text=raw_text)
        state.vital_signs.append(nova_vitals)
        state.physical_examinations["vital_signs"] = raw_text
        for finding in describe_vital_sign_abnormalities(nova_vitals):
            if finding not in state.vital_sign_findings:
                state.vital_sign_findings.append(finding)
