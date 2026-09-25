"""Concept hierarchy traversal (parents/children/ancestors) over an in-memory concept map.

Dependency-free. Guards against cycles and missing nodes. Hierarchy edges come only from provider
snapshots; if none are present, all traversals return empty -- there is no invented taxonomy.
"""

from __future__ import annotations

from typing import Dict, List, Set

from nova_agent.ontology.models import ClinicalConcept


def parents(concepts: Dict[str, ClinicalConcept], concept_id: str) -> List[str]:
    c = concepts.get(concept_id)
    return [p for p in (c.parents if c else ()) if p in concepts]


def children(concepts: Dict[str, ClinicalConcept], concept_id: str) -> List[str]:
    c = concepts.get(concept_id)
    return [ch for ch in (c.children if c else ()) if ch in concepts]


def ancestors(concepts: Dict[str, ClinicalConcept], concept_id: str, max_depth: int = 12) -> List[str]:
    seen: Set[str] = set()
    frontier = list(parents(concepts, concept_id))
    depth = 0
    out: List[str] = []
    while frontier and depth < max_depth:
        nxt: List[str] = []
        for pid in frontier:
            if pid in seen:
                continue
            seen.add(pid)
            out.append(pid)
            nxt.extend(parents(concepts, pid))
        frontier = nxt
        depth += 1
    return out


def descendants(concepts: Dict[str, ClinicalConcept], concept_id: str, max_depth: int = 12) -> List[str]:
    seen: Set[str] = set()
    frontier = list(children(concepts, concept_id))
    depth = 0
    out: List[str] = []
    while frontier and depth < max_depth:
        nxt: List[str] = []
        for cid in frontier:
            if cid in seen:
                continue
            seen.add(cid)
            out.append(cid)
            nxt.extend(children(concepts, cid))
        frontier = nxt
        depth += 1
    return out
