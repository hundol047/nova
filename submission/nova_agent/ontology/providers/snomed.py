"""SNOMED CT provider (LOCAL snapshot only).

SNOMED CT is license-restricted; we ship NO SNOMED content. An operator with a valid affiliate
license places a snapshot at snapshots/snomed.json. Absent that, this provider yields nothing.
"""

from __future__ import annotations

from nova_agent.ontology.providers.base import TerminologyProvider


class SnomedProvider(TerminologyProvider):
    system = "SNOMEDCT"
    snapshot_filename = "snomed.json"
    concept_id_prefix = "onto"
