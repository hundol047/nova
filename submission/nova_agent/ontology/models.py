"""Core ontology value objects (vNext PART A).

Dependency-free by design: stdlib dataclasses + enums only. No pydantic, no torch, no network.
These are the *only* types the reasoning engine (candidate_generator / differential / open_world)
depends on when talking to the DiseaseCatalog abstraction. Terminology providers translate their
LOCAL snapshots into these types; the engine never sees provider-specific shapes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class Tier(str, Enum):
    """Curation depth of a clinical concept.

    TIER1_DEEP        - one of the 34 hand-authored deep profiles (discriminating questions/exams/
                        tests, confirmatory findings, red flags). Full reasoning support.
    TIER2_STRUCTURED  - broad curated conditions with minimal structured fields (name, aliases,
                        category, urgency hint, a few typical features). Searchable + rankable,
                        but reasoning falls back to generic workup guidance.
    TIER3_ONTOLOGY    - concept known ONLY from a terminology snapshot (name + codes + hierarchy).
                        Retrievable as a named possibility; carries NO curated clinical claims.
    """

    TIER1_DEEP = "TIER1_DEEP"
    TIER2_STRUCTURED = "TIER2_STRUCTURED"
    TIER3_ONTOLOGY = "TIER3_ONTOLOGY"


class SemanticType(str, Enum):
    """What kind of thing a concept is. Keeps disease/finding/organism separable so we never
    rank a symptom as if it were a diagnosis."""

    DISEASE = "DISEASE"
    SYNDROME = "SYNDROME"
    FINDING = "FINDING"
    ORGANISM = "ORGANISM"
    PROCEDURE = "PROCEDURE"
    SUBSTANCE = "SUBSTANCE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ExternalCode:
    """A code from an external terminology. `system` is a stable short id (e.g. 'SNOMEDCT',
    'ICD11', 'ICD10'). We store codes verbatim from a local snapshot; we never mint them."""

    system: str
    code: str
    display: Optional[str] = None

    def as_dict(self) -> Dict[str, Optional[str]]:
        return {"system": self.system, "code": self.code, "display": self.display}


@dataclass(frozen=True)
class ClinicalConcept:
    """A single node in the disease universe.

    A Tier-1 concept is backed by a deep KB entry (`kb_id` set); Tier-2/3 concepts may have no
    curated clinical detail at all -- in which case `curation_status == 'NOT_CURATED'` and the
    reasoning engine must treat clinical fields as ABSENT rather than empty-and-therefore-safe.
    """

    concept_id: str
    canonical_name: str
    semantic_type: SemanticType = SemanticType.DISEASE
    tier: Tier = Tier.TIER3_ONTOLOGY
    aliases: Tuple[str, ...] = ()
    category: Optional[str] = None
    external_codes: Tuple[ExternalCode, ...] = ()
    parents: Tuple[str, ...] = ()
    children: Tuple[str, ...] = ()
    # Provenance / honesty
    source: str = "unknown"            # e.g. 'core_kb', 'tier2_catalog', 'snomed_snapshot'
    curation_status: str = "NOT_CURATED"  # 'DEEP' | 'STRUCTURED' | 'NOT_CURATED'
    # Optional clinical hints (only Tier-1/2). Absence is meaningful; do not default-fill.
    urgency: Optional[str] = None       # 'CRITICAL' | 'URGENT' | 'ROUTINE'
    dangerous: Optional[bool] = None
    chief_complaint_tags: Tuple[str, ...] = ()
    typical_features: Tuple[str, ...] = ()
    kb_id: Optional[str] = None         # id into knowledge/diseases when tier==TIER1_DEEP

    def all_search_terms(self) -> List[str]:
        terms = [self.canonical_name, *self.aliases]
        return [t for t in terms if t]

    def as_dict(self) -> Dict[str, object]:
        return {
            "concept_id": self.concept_id,
            "canonical_name": self.canonical_name,
            "semantic_type": self.semantic_type.value,
            "tier": self.tier.value,
            "aliases": list(self.aliases),
            "category": self.category,
            "external_codes": [c.as_dict() for c in self.external_codes],
            "parents": list(self.parents),
            "children": list(self.children),
            "source": self.source,
            "curation_status": self.curation_status,
            "urgency": self.urgency,
            "dangerous": self.dangerous,
            "chief_complaint_tags": list(self.chief_complaint_tags),
            "typical_features": list(self.typical_features),
            "kb_id": self.kb_id,
        }


@dataclass(frozen=True)
class ConceptMatch:
    """A concept returned by a search, with a lexical match score in [0,1] and WHY it matched.

    `score` is a lexical/structural match confidence ONLY. It is NOT a diagnostic probability and
    must never be presented to a clinician as one (open-world / calibration rules). The candidate
    generator combines this with clinical evidence separately.
    """

    concept: ClinicalConcept
    score: float
    matched_term: str
    match_kind: str  # 'exact' | 'alias' | 'token' | 'code' | 'fuzzy'

    def as_dict(self) -> Dict[str, object]:
        return {
            "concept": self.concept.as_dict(),
            "score": round(self.score, 4),
            "matched_term": self.matched_term,
            "match_kind": self.match_kind,
        }
