"""High-recall retriever: patient query -> Top-K disease candidates from the 5,000+ universe.

Combines the embedding index (semantic similarity) with the catalog's lexical/code/hierarchy search
so recall stays high even when the embedding is weak (rare/sparse Tier-3 concepts). The output is a
broad candidate pool (default Top-200) for the downstream router / safety-recall / reranker — NOT a
final diagnosis. Latency is measured per stage.

Dependency-free by default. Safety-recall + reranking + LLM live in later stages; this module only
retrieves.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from learning.retrieval.index import DiseaseIndex
from learning.retrieval.patient_encoder import PatientEncoder, PatientQuery


@dataclass
class RetrievedItem:
    concept_id: str
    name: str
    tier: str
    category: str
    score: float
    sources: List[str] = field(default_factory=list)  # 'embedding' | 'lexical' | 'code' | 'hierarchy'


@dataclass
class RetrievalResult:
    items: List[RetrievedItem]
    latencies_ms: Dict[str, float]

    def concept_ids(self) -> List[str]:
        return [it.concept_id for it in self.items]


class Retriever:
    """Fuses embedding-index search with optional catalog lexical/code search for high recall."""

    def __init__(self, index: DiseaseIndex, catalog=None, dim: Optional[int] = None) -> None:
        self._index = index
        self._catalog = catalog  # optional nova_agent DiseaseCatalog for lexical/code/hierarchy fusion
        self._encoder = PatientEncoder(dim=dim or index.dim)

    def retrieve(self, query: PatientQuery, top_k: int = 200,
                 lexical_terms: Optional[Sequence[str]] = None) -> RetrievalResult:
        lat: Dict[str, float] = {}

        t0 = time.perf_counter()
        qvec = self._encoder.encode(query)
        lat["patient_encode"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        emb_hits = self._index.search(qvec, top_k=top_k)
        lat["embedding_retrieval"] = (time.perf_counter() - t0) * 1000

        best: Dict[str, RetrievedItem] = {}
        for it, score in emb_hits:
            best[it.concept_id] = RetrievedItem(it.concept_id, it.name, it.tier, it.category,
                                                float(score), ["embedding"])

        # Lexical / code / hierarchy fusion from the catalog (boosts recall of exact-name & rare hits).
        t0 = time.perf_counter()
        if self._catalog is not None:
            terms = list(lexical_terms or [])
            if query.chief_complaint:
                terms.append(query.chief_complaint)
            terms.extend(str(s) for s in query.symptoms)
            for term in terms:
                if not term or len(str(term).strip()) < 3:
                    continue
                for m in self._catalog.search_conditions(str(term), limit=max(20, top_k // 4)):
                    cid = m.concept.concept_id
                    cur = best.get(cid)
                    # normalize lexical match score into a comparable band and fuse
                    lex_score = 0.4 + 0.5 * float(m.score)
                    if cur is None:
                        best[cid] = RetrievedItem(cid, m.concept.canonical_name,
                                                  m.concept.tier.value, m.concept.category or "",
                                                  lex_score, ["lexical"])
                    else:
                        if "lexical" not in cur.sources:
                            cur.sources.append("lexical")
                        cur.score = max(cur.score, lex_score)
            # external code exact match (strong signal)
            for sysid, code in query.external_codes:
                for concept in self._catalog.map_external_code(str(sysid), str(code)):
                    cid = concept.concept_id
                    cur = best.get(cid)
                    if cur is None:
                        best[cid] = RetrievedItem(cid, concept.canonical_name, concept.tier.value,
                                                  concept.category or "", 0.98, ["code"])
                    else:
                        if "code" not in cur.sources:
                            cur.sources.append("code")
                        cur.score = max(cur.score, 0.98)
        lat["lexical_fusion"] = (time.perf_counter() - t0) * 1000

        items = sorted(best.values(), key=lambda it: -it.score)[:top_k]
        lat["total"] = sum(lat.values())
        return RetrievalResult(items=items, latencies_ms=lat)
