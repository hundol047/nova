"""Terminology providers.

Each provider translates a LOCAL, license-respecting snapshot into ClinicalConcept objects. No
provider ever calls an external terminology API at runtime. If its snapshot file is absent, a
provider yields NOTHING (it must never fabricate concepts to fill a number).

Snapshot location convention: nova_agent/ontology/snapshots/<provider>.json  (operator-supplied,
git-ignored by default). See docs/ontology/TERMINOLOGY_PROVENANCE.md.
"""

from nova_agent.ontology.providers.base import TerminologyProvider

__all__ = ["TerminologyProvider"]
