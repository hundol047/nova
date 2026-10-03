"""Lexical search index over ClinicalConcepts (dependency-free, in-memory).

Builds an inverted index (exact-name, alias, token, external-code) once and answers ranked
`ConceptMatch` queries. Scores are lexical match confidences in [0,1] -- NOT diagnostic
probabilities. A tiny bounded edit-distance is used for near-miss ('fuzzy') matches without any
third-party fuzzy library.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from nova_agent.ontology.models import ClinicalConcept, ConceptMatch
from nova_agent.ontology.normalizer import normalize, tokens


def _bounded_levenshtein(a: str, b: str, max_dist: int) -> int:
    """Edit distance capped at max_dist+1 (returns max_dist+1 if it exceeds the cap)."""
    if abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        best = cur[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            cur.append(v)
            best = min(best, v)
        if best > max_dist:
            return max_dist + 1
        prev = cur
    return prev[-1]


class ConceptSearchIndex:
    def __init__(self) -> None:
        self._by_exact: Dict[str, List[str]] = {}      # normalized full term -> concept_ids
        self._by_token: Dict[str, List[str]] = {}      # token -> concept_ids
        self._by_code: Dict[str, List[str]] = {}       # code -> concept_ids
        self._term_source: Dict[Tuple[str, str], Tuple[str, str]] = {}
        # (concept_id, normalized_term) -> (original_term, kind 'name'|'alias')
        self._concepts: Dict[str, ClinicalConcept] = {}
        self._all_norm_terms: List[Tuple[str, str]] = []  # (norm_term, concept_id) for fuzzy pass

    def add(self, concept: ClinicalConcept) -> None:
        self._concepts[concept.concept_id] = concept
        name_norm = normalize(concept.canonical_name)
        if name_norm:
            self._by_exact.setdefault(name_norm, []).append(concept.concept_id)
            self._term_source[(concept.concept_id, name_norm)] = (concept.canonical_name, "name")
            self._all_norm_terms.append((name_norm, concept.concept_id))
        for alias in concept.aliases:
            a_norm = normalize(alias)
            if not a_norm:
                continue
            self._by_exact.setdefault(a_norm, []).append(concept.concept_id)
            self._term_source[(concept.concept_id, a_norm)] = (alias, "alias")
            self._all_norm_terms.append((a_norm, concept.concept_id))
        for term in concept.all_search_terms():
            for tok in tokens(term):
                bucket = self._by_token.setdefault(tok, [])
                if concept.concept_id not in bucket:
                    bucket.append(concept.concept_id)
        for code in concept.external_codes:
            self._by_code.setdefault(code.code.strip().upper(), []).append(concept.concept_id)

    def bulk_add(self, concepts: Iterable[ClinicalConcept]) -> None:
        for c in concepts:
            self.add(c)

    def get(self, concept_id: str) -> Optional[ClinicalConcept]:
        return self._concepts.get(concept_id)

    def __len__(self) -> int:
        return len(self._concepts)

    def search(self, query: str, limit: int = 20, fuzzy: bool = True) -> List[ConceptMatch]:
        q_norm = normalize(query)
        if not q_norm:
            return []
        best: Dict[str, ConceptMatch] = {}

        def offer(cid: str, score: float, matched_term: str, kind: str) -> None:
            existing = best.get(cid)
            if existing is None or score > existing.score:
                concept = self._concepts.get(cid)
                if concept is not None:
                    best[cid] = ConceptMatch(concept, score, matched_term, kind)

        # 1) exact full-term match (name/alias)
        for cid in self._by_exact.get(q_norm, []):
            orig, kind = self._term_source.get((cid, q_norm), (query, "name"))
            offer(cid, 1.0 if kind == "name" else 0.95, orig, "exact" if kind == "name" else "alias")

        # 2) external code match
        for cid in self._by_code.get(query.strip().upper(), []):
            offer(cid, 0.97, query.strip().upper(), "code")

        # 3) token overlap (Jaccard-ish over query tokens)
        q_tokens = tokens(query)
        if q_tokens:
            candidate_counts: Dict[str, int] = {}
            for tok in q_tokens:
                for cid in self._by_token.get(tok, []):
                    candidate_counts[cid] = candidate_counts.get(cid, 0) + 1
            for cid, hits in candidate_counts.items():
                score = 0.5 + 0.4 * (hits / len(q_tokens))  # 0.5..0.9
                concept = self._concepts.get(cid)
                mt = concept.canonical_name if concept else query
                offer(cid, min(score, 0.9), mt, "token")

        # 4) bounded fuzzy pass over exact terms (only if we have few strong hits)
        if fuzzy and len([m for m in best.values() if m.score >= 0.9]) < limit:
            max_dist = 1 if len(q_norm) <= 6 else 2
            for norm_term, cid in self._all_norm_terms:
                if abs(len(norm_term) - len(q_norm)) > max_dist:
                    continue
                d = _bounded_levenshtein(q_norm, norm_term, max_dist)
                if d <= max_dist:
                    score = 0.85 - 0.1 * d
                    orig, kind = self._term_source.get((cid, norm_term), (norm_term, "name"))
                    offer(cid, score, orig, "fuzzy")

        ranked = sorted(best.values(), key=lambda m: (-m.score, m.concept.canonical_name))
        return ranked[:limit]
