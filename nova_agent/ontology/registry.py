"""DiseaseCatalog: the single abstraction the reasoning engine depends on.

Composes providers (core KB Tier-1, Tier-2 structured catalog, and any local terminology
snapshots) into one searchable universe. Provider precedence on concept-id collision favors deeper
curation: core_kb > tier2 > ontology snapshots. External codes are indexed so an LLM/EMR code can
be resolved to a canonical concept.

The engine calls: search_conditions / get_condition / get_children / get_parents / get_synonyms /
map_external_code. It never imports a specific provider.

Import-light: stdlib only. Building the default catalog reads bundled JSON (core KB always present;
tier2 if the data file exists; terminology snapshots only if the operator supplied them).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from nova_agent.ontology import hierarchy
from nova_agent.ontology.mappings import canonical_system
from nova_agent.ontology.models import ClinicalConcept, ConceptMatch, Tier
from nova_agent.ontology.providers.core_kb import CoreKbProvider
from nova_agent.ontology.providers.icd10 import Icd10Provider
from nova_agent.ontology.providers.icd11 import Icd11Provider
from nova_agent.ontology.providers.snomed import SnomedProvider
from nova_agent.ontology.providers.tier2_catalog import Tier2CatalogProvider
from nova_agent.ontology.search import ConceptSearchIndex

# Provider precedence: earlier = higher curation authority on id collision.
_TIER_RANK = {Tier.TIER1_DEEP: 0, Tier.TIER2_STRUCTURED: 1, Tier.TIER3_ONTOLOGY: 2}


class DiseaseCatalog:
    def __init__(self, concepts: Optional[List[ClinicalConcept]] = None) -> None:
        self._concepts: Dict[str, ClinicalConcept] = {}
        self._index = ConceptSearchIndex()
        self._code_index: Dict[str, List[str]] = {}  # "SYSTEM|CODE" -> concept_ids
        if concepts:
            self.add_all(concepts)

    # ---- construction ---------------------------------------------------
    def add(self, concept: ClinicalConcept) -> None:
        existing = self._concepts.get(concept.concept_id)
        if existing is not None and _TIER_RANK[existing.tier] <= _TIER_RANK[concept.tier]:
            return  # keep the more-curated existing concept
        self._concepts[concept.concept_id] = concept
        self._index.add(concept)
        for code in concept.external_codes:
            key = f"{canonical_system(code.system)}|{code.code.strip().upper()}"
            bucket = self._code_index.setdefault(key, [])
            if concept.concept_id not in bucket:
                bucket.append(concept.concept_id)

    def add_all(self, concepts: List[ClinicalConcept]) -> None:
        for c in concepts:
            self.add(c)

    # ---- engine-facing API ---------------------------------------------
    def search_conditions(self, query: str, limit: int = 20, fuzzy: bool = True) -> List[ConceptMatch]:
        """Ranked lexical matches. Scores are match confidence, NOT diagnostic probability."""
        return self._index.search(query, limit=limit, fuzzy=fuzzy)

    def get_condition(self, concept_id: str) -> Optional[ClinicalConcept]:
        return self._concepts.get(concept_id)

    def get_children(self, concept_id: str) -> List[ClinicalConcept]:
        return [self._concepts[c] for c in hierarchy.children(self._concepts, concept_id)]

    def get_parents(self, concept_id: str) -> List[ClinicalConcept]:
        return [self._concepts[p] for p in hierarchy.parents(self._concepts, concept_id)]

    def get_synonyms(self, concept_id: str) -> List[str]:
        c = self._concepts.get(concept_id)
        return list(c.aliases) if c else []

    def map_external_code(self, system: str, code: str) -> List[ClinicalConcept]:
        key = f"{canonical_system(system)}|{code.strip().upper()}"
        return [self._concepts[cid] for cid in self._code_index.get(key, []) if cid in self._concepts]

    # ---- introspection (coverage reporting) ----------------------------
    def all_concepts(self) -> List[ClinicalConcept]:
        return list(self._concepts.values())

    def counts_by_tier(self) -> Dict[str, int]:
        out: Dict[str, int] = {t.value: 0 for t in Tier}
        for c in self._concepts.values():
            out[c.tier.value] += 1
        return out

    def counts_by_curation(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for c in self._concepts.values():
            out[c.curation_status] = out.get(c.curation_status, 0) + 1
        return out

    def __len__(self) -> int:
        return len(self._concepts)


_DEFAULT_CATALOG: Optional[DiseaseCatalog] = None


def build_catalog(include_ontology_snapshots: bool = True) -> DiseaseCatalog:
    """Assemble a fresh catalog from all available providers (order = precedence)."""
    catalog = DiseaseCatalog()
    catalog.add_all(CoreKbProvider().load())          # Tier-1 (always present)
    catalog.add_all(Tier2CatalogProvider().load())    # Tier-2 (if data file present)
    if include_ontology_snapshots:
        for provider in (SnomedProvider(), Icd11Provider(), Icd10Provider()):
            if provider.available():
                catalog.add_all(provider.load())      # Tier-3 (only if snapshot supplied)
    return catalog


def get_default_catalog() -> DiseaseCatalog:
    """Process-wide singleton catalog (lazy)."""
    global _DEFAULT_CATALOG
    if _DEFAULT_CATALOG is None:
        _DEFAULT_CATALOG = build_catalog()
    return _DEFAULT_CATALOG
