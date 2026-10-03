"""External-code system normalization helpers (dependency-free).

Different EMRs/LLMs refer to the same terminology with different labels (e.g. 'SNOMED',
'SNOMED-CT', 'http://snomed.info/sct'). This module folds those to the stable short ids the
catalog indexes on. Unknown systems are returned upper-cased and untouched -- we never guess a
mapping we do not have.
"""

from __future__ import annotations

from typing import Dict

_SYSTEM_ALIASES: Dict[str, str] = {
    "SNOMED": "SNOMEDCT",
    "SNOMEDCT": "SNOMEDCT",
    "SNOMED-CT": "SNOMEDCT",
    "SNOMED CT": "SNOMEDCT",
    "HTTP://SNOMED.INFO/SCT": "SNOMEDCT",
    "ICD11": "ICD11",
    "ICD-11": "ICD11",
    "ICD 11": "ICD11",
    "HTTP://ID.WHO.INT/ICD/RELEASE/11/MMS": "ICD11",
    "ICD10": "ICD10",
    "ICD-10": "ICD10",
    "ICD-10-CM": "ICD10",
    "ICD10CM": "ICD10",
    "HTTP://HL7.ORG/FHIR/SID/ICD-10": "ICD10",
    "HTTP://HL7.ORG/FHIR/SID/ICD-10-CM": "ICD10",
}


def canonical_system(system: str) -> str:
    if not system:
        return "UNKNOWN"
    key = system.strip().upper()
    return _SYSTEM_ALIASES.get(key, key)
