"""Core KB provider: exposes the 34 hand-authored deep profiles as Tier-1 ClinicalConcepts.

This is the bridge that keeps the existing knowledge base authoritative. It reads
nova_agent/knowledge/diseases/*.json (the SAME files differential.py/safety consume) and wraps each
entry as a TIER1_DEEP concept, preserving its id as `kb_id` so the reasoning engine can pull the
full deep profile when this concept wins. It never mutates the KB.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List

from nova_agent.ontology.models import ClinicalConcept, SemanticType, Tier

_DISEASE_ROOT = Path(__file__).resolve().parent.parent.parent / "knowledge" / "diseases"


class CoreKbProvider:
    """Not a TerminologyProvider subclass (no external system); shares the iter/load contract."""

    system = "NOVA_CORE_KB"

    def __init__(self, disease_root: Path = _DISEASE_ROOT) -> None:
        self._root = disease_root

    def available(self) -> bool:
        return self._root.is_dir()

    def iter_concepts(self) -> Iterator[ClinicalConcept]:
        if not self.available():
            return
        for path in sorted(self._root.glob("*.json")):
            try:
                entries = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for entry in entries:
                kb_id = entry.get("id")
                name = entry.get("name")
                if not kb_id or not name:
                    continue
                yield ClinicalConcept(
                    concept_id=f"core:{kb_id}",
                    canonical_name=name,
                    semantic_type=SemanticType.DISEASE,
                    tier=Tier.TIER1_DEEP,
                    aliases=tuple(a for a in entry.get("aliases", []) if a),
                    category=entry.get("category"),
                    source="core_kb",
                    curation_status="DEEP",
                    urgency=entry.get("urgency"),
                    dangerous=entry.get("dangerous"),
                    chief_complaint_tags=tuple(entry.get("chief_complaint_tags", [])),
                    typical_features=tuple(entry.get("typical_features", [])),
                    kb_id=kb_id,
                )

    def load(self) -> List[ClinicalConcept]:
        return list(self.iter_concepts())
