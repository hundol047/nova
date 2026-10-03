"""Prebuilt disease-embedding index (built once, cached; no per-request rebuild).

Encodes every disease concept ONCE at build time and stores (concept_id, vector, metadata). Query
time is a single patient encode + a linear cosine scan over the cached matrix — O(N*dim), fast
enough for 5,000+ concepts and fully dependency-free. (A production deployment can swap in an ANN
index; the interface is unchanged.)

The index is built from the DiseaseCatalog once and reused; get_default_index() memoizes it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from learning.retrieval.disease_encoder import DiseaseEncoder, _concept_to_features
from learning.retrieval.embedding import EMBED_DIM, EMBEDDING_VERSION, cosine


@dataclass
class IndexedDisease:
    concept_id: str
    name: str
    tier: str
    category: str
    vector: List[float]


@dataclass
class DiseaseIndex:
    dim: int = EMBED_DIM
    version: str = EMBEDDING_VERSION
    _items: List[IndexedDisease] = field(default_factory=list)
    _by_id: Dict[str, int] = field(default_factory=dict)
    build_seconds: float = 0.0

    def build(self, concepts: Sequence[object]) -> "DiseaseIndex":
        """Encode every concept ONCE. Idempotent rebuild (clears prior state)."""
        t0 = time.perf_counter()
        enc = DiseaseEncoder(dim=self.dim)
        self._items = []
        self._by_id = {}
        for c in concepts:
            feats = _concept_to_features(c)
            vec = enc.encode(feats)
            tier = getattr(getattr(c, "tier", None), "value", "") or ""
            self._by_id[feats.concept_id] = len(self._items)
            self._items.append(IndexedDisease(
                concept_id=feats.concept_id, name=feats.canonical_name,
                tier=tier, category=feats.category, vector=vec,
            ))
        self.build_seconds = time.perf_counter() - t0
        return self

    def __len__(self) -> int:
        return len(self._items)

    def search(self, query_vec: Sequence[float], top_k: int = 200) -> List[Tuple[IndexedDisease, float]]:
        """Return the top_k (IndexedDisease, cosine) by similarity. Single linear scan."""
        scored = [(it, cosine(query_vec, it.vector)) for it in self._items]
        scored.sort(key=lambda t: -t[1])
        return scored[:top_k]

    def get(self, concept_id: str) -> Optional[IndexedDisease]:
        i = self._by_id.get(concept_id)
        return self._items[i] if i is not None else None

    def all_ids(self) -> List[str]:
        return [it.concept_id for it in self._items]


_DEFAULT_INDEX: Optional[DiseaseIndex] = None


def get_default_index(catalog=None) -> DiseaseIndex:
    """Memoized index built from the DiseaseCatalog (built ONCE per process). Pass a catalog to
    build explicitly; otherwise the default catalog is used (imports nova_agent lazily)."""
    global _DEFAULT_INDEX
    if _DEFAULT_INDEX is not None:
        return _DEFAULT_INDEX
    if catalog is None:
        from nova_agent.ontology.registry import get_default_catalog
        catalog = get_default_catalog()
    _DEFAULT_INDEX = DiseaseIndex().build(catalog.all_concepts())
    return _DEFAULT_INDEX
