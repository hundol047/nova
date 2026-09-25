"""N.O.V.A. clinical ontology layer (vNext PART A).

Purpose: stop limiting the differential to the 34-entry structured knowledge base. This package
provides a broad, terminology-backed disease UNIVERSE that candidate generation can search, while
the existing 34 deep profiles remain the Tier-1 "core clinical profile layer" (unchanged).

Design constraints (deliberate):
  - Dependency-free at import time (no pydantic/torch/network). Uses stdlib dataclasses + JSON so
    it runs in any environment and inside the competition submission if ever needed.
  - NEVER calls an external SNOMED/ICD API at runtime. Providers read a LOCAL, license-respecting
    snapshot the operator supplies (see providers/). Absent a snapshot, a provider yields nothing
    rather than fabricating concepts.
  - Open-world by construction: a concept that is not in the deep KB is still a searchable
    candidate, and "no confident match" is a first-class outcome (see nova_agent/open_world.py),
    never a forced known diagnosis.

The reasoning engine depends only on the DiseaseCatalog abstraction (registry.DiseaseCatalog),
not on any specific terminology provider.
"""

from nova_agent.ontology.models import (
    ClinicalConcept,
    ConceptMatch,
    ExternalCode,
    SemanticType,
    Tier,
)
from nova_agent.ontology.registry import DiseaseCatalog, get_default_catalog

__all__ = [
    "ClinicalConcept",
    "ConceptMatch",
    "ExternalCode",
    "SemanticType",
    "Tier",
    "DiseaseCatalog",
    "get_default_catalog",
]
