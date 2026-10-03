"""LOINC (falling back to display text) -> nova_agent canonical clinical-concept ID mapping (spec:
FHIR Observation LOINC/display/code.text -> canonical ID, never silently discarding an unmapped
code).

Distinct from terminology_mapper.py: that module maps an internal id/name -> a DISPLAY code
(RxNorm/ATC/LOINC/ICD-10/SNOMED) for the `/patients/{pid}/terminology` transparency endpoint --
outward-facing, for a clinician to read. This module maps the OTHER direction, inward: a real
FHIR Observation's LOINC code (or, lacking one, its display text) into the exact raw-text key
nova_agent/objective_evidence.py's `LAB_SPECS` registry already reads from
`PatientState.laboratory_tests` (e.g. "potassium", "troponin", "wbc") -- so a real hospital's
numeric lab value reaches nova_agent's own numeric interpretation layer keyed correctly, not just
as an unrecognized display-name string it can only pattern-match against loosely.

Every code below is a real, standard LOINC identifier (never fabricated) for the specific lab
nova_agent/objective_evidence.py's `LAB_SPECS` registry already understands -- this table's
coverage is intentionally exactly that set, not a general-purpose LOINC database. A lab whose
LOINC code (or display text) isn't in either table below is NEVER silently dropped: `map_lab()`
still returns it with `canonical_id=None`, and the caller (nova_fhir_mapper.py) still preserves
the raw code/display for `unmapped_clinical_codes` visibility (spec: an unmapped code is surfaced,
not discarded).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# LOINC code -> (nova_agent canonical id, PatientState.laboratory_tests raw key nova_agent's own
# objective_evidence.LAB_SPECS registry expects for that lab). Kept in sync BY HAND with that
# registry's `raw_keys`/canonical ids (nova_agent/objective_evidence.py) -- there is no shared
# import between the two repos-within-a-repo (backend/ deliberately does not import nova_agent
# internals beyond PatientState itself, see nova_fhir_mapper.py's own module docstring), so a
# newly-added lab there needs one new row here too.
LOINC_TO_NOVA_LAB: Dict[str, Tuple[str, str]] = {
    '2823-3': ('lab.potassium', 'potassium'),
    '2951-2': ('lab.sodium', 'sodium'),
    '2160-0': ('lab.creatinine', 'creatinine'),
    '6690-2': ('lab.wbc', 'wbc'),
    '718-7': ('lab.hemoglobin', 'hemoglobin'),
    '777-3': ('lab.platelet', 'platelet'),
    '2744-1': ('lab.ph', 'ph'),
    '1963-8': ('lab.bicarbonate', 'bicarbonate'),
    '10839-9': ('lab.troponin', 'troponin'),
    '48065-7': ('lab.d_dimer', 'd_dimer'),
    '1988-5': ('lab.crp', 'crp'),
    '2514-8': ('lab.ketones', 'ketones'),
    '20416-4': ('lab.beta_hcg', 'beta_hcg'),
    '2345-7': ('lab.glucose', 'glucose_point_of_care'),
    '2524-7': ('lab.lactate', 'lactate'),
}

# Fallback when the Observation carries no loinc.org coding at all (a DemoAdapter-sourced lab, or
# a real FHIR server that only populated `code.text`) -- keyed on lower-cased display text.
DISPLAY_TEXT_TO_NOVA_LAB: Dict[str, Tuple[str, str]] = {
    'potassium': ('lab.potassium', 'potassium'),
    'sodium': ('lab.sodium', 'sodium'),
    'creatinine': ('lab.creatinine', 'creatinine'),
    'wbc': ('lab.wbc', 'wbc'),
    'white blood cell count': ('lab.wbc', 'wbc'),
    'white blood cells': ('lab.wbc', 'wbc'),
    'hemoglobin': ('lab.hemoglobin', 'hemoglobin'),
    'platelet': ('lab.platelet', 'platelet'),
    'platelets': ('lab.platelet', 'platelet'),
    'ph': ('lab.ph', 'ph'),
    'bicarbonate': ('lab.bicarbonate', 'bicarbonate'),
    'hco3': ('lab.bicarbonate', 'bicarbonate'),
    'troponin': ('lab.troponin', 'troponin'),
    'd-dimer': ('lab.d_dimer', 'd_dimer'),
    'd dimer': ('lab.d_dimer', 'd_dimer'),
    'crp': ('lab.crp', 'crp'),
    'c-reactive protein': ('lab.crp', 'crp'),
    'ketones': ('lab.ketones', 'ketones'),
    'beta-hcg': ('lab.beta_hcg', 'beta_hcg'),
    'beta hcg': ('lab.beta_hcg', 'beta_hcg'),
    'hcg': ('lab.beta_hcg', 'beta_hcg'),
    'glucose': ('lab.glucose', 'glucose_point_of_care'),
    'lactate': ('lab.lactate', 'lactate'),
}


@dataclass
class MappedClinicalCode:
    canonical_id: Optional[str]  # nova_agent canonical id (e.g. "lab.potassium"), None if unmapped
    nova_state_key: Optional[str]  # PatientState.laboratory_tests key to write under, None if unmapped
    raw_code: Optional[str]  # the LOINC code as given, if any
    raw_display: str  # the display text as given, always preserved
    normalized_by: str  # 'LOINC' | 'display-text' | 'unmapped'


def map_lab(display_text: str, loinc: Optional[str] = None) -> MappedClinicalCode:
    """Never returns a fabricated canonical id: LOINC match first (most reliable), display-text
    match second, otherwise explicitly `canonical_id=None` with the raw code/display preserved."""
    if loinc:
        row = LOINC_TO_NOVA_LAB.get(loinc.strip())
        if row is not None:
            return MappedClinicalCode(row[0], row[1], loinc, display_text, 'LOINC')
    row = DISPLAY_TEXT_TO_NOVA_LAB.get((display_text or '').strip().lower())
    if row is not None:
        return MappedClinicalCode(row[0], row[1], loinc, display_text, 'display-text')
    return MappedClinicalCode(None, None, loinc, display_text, 'unmapped')
