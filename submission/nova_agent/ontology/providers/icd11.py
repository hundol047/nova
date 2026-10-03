"""ICD-11 provider (LOCAL snapshot only).

ICD-11 (WHO) has its own licensing/attribution terms. We ship NO ICD-11 content; the operator
supplies snapshots/icd11.json. Absent that, this provider yields nothing.
"""

from __future__ import annotations

from nova_agent.ontology.providers.base import TerminologyProvider


class Icd11Provider(TerminologyProvider):
    system = "ICD11"
    snapshot_filename = "icd11.json"
    concept_id_prefix = "onto"
