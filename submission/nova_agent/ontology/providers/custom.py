"""Custom / hospital local code-map provider (LOCAL snapshot only).

Lets a hospital load its own internal problem-list / code vocabulary as Tier-3 searchable concepts
via scripts/import_terminology.py --source custom -> snapshots/custom.json. Operator-supplied and
local-only; never fetched from an external API. Absent the file, this provider yields nothing.
"""

from __future__ import annotations

from nova_agent.ontology.providers.base import TerminologyProvider


class CustomProvider(TerminologyProvider):
    system = "CUSTOM"
    snapshot_filename = "custom.json"
    concept_id_prefix = "onto"
