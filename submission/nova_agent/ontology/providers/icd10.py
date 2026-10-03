"""ICD-10 / ICD-10-CM provider (LOCAL snapshot only).

The operator supplies snapshots/icd10.json. Absent that, this provider yields nothing. (ICD-10-CM
is public-domain in the US, but we still do not bundle a snapshot to keep the repo terminology-free
and let the operator control versioning/provenance.)
"""

from __future__ import annotations

from nova_agent.ontology.providers.base import TerminologyProvider


class Icd10Provider(TerminologyProvider):
    system = "ICD10"
    snapshot_filename = "icd10.json"
    concept_id_prefix = "onto"
