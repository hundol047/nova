"""Tier-2 structured catalog provider.

Loads nova_agent/knowledge/tier2_catalog.json -- a broad, curated list of conditions spanning many
specialties with MINIMAL structured fields (name, aliases, category, urgency hint, a few typical
features, optional external codes). These are searchable + rankable candidates but carry no deep
reasoning artifacts. Anything not curated is marked NOT_CURATED and its clinical fields are treated
as ABSENT -- we never fabricate detail to inflate coverage numbers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List

from nova_agent.ontology.models import (
    ClinicalConcept,
    ExternalCode,
    SemanticType,
    Tier,
)

_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent.parent / "knowledge" / "tier2_catalog.json"
)


class Tier2CatalogProvider:
    system = "NOVA_TIER2"

    def __init__(self, catalog_path: Path = _CATALOG_PATH) -> None:
        self._path = catalog_path

    def available(self) -> bool:
        return self._path.is_file()

    def _semantic_type(self, raw) -> SemanticType:
        if not raw:
            return SemanticType.DISEASE
        try:
            return SemanticType(str(raw).strip().upper())
        except ValueError:
            return SemanticType.UNKNOWN

    def iter_concepts(self) -> Iterator[ClinicalConcept]:
        if not self.available():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        conditions = data.get("conditions", data if isinstance(data, list) else [])
        for entry in conditions:
            cid = entry.get("id")
            name = entry.get("name")
            if not cid or not name:
                continue
            codes = tuple(
                ExternalCode(system=c["system"], code=str(c["code"]), display=c.get("display"))
                for c in entry.get("external_codes", [])
                if c.get("system") and c.get("code") is not None
            )
            curated = bool(entry.get("curated", True))
            yield ClinicalConcept(
                concept_id=f"tier2:{cid}",
                canonical_name=name,
                semantic_type=self._semantic_type(entry.get("semantic_type")),
                tier=Tier.TIER2_STRUCTURED,
                aliases=tuple(a for a in entry.get("aliases", []) if a),
                category=entry.get("category"),
                external_codes=codes,
                source="tier2_catalog",
                curation_status="STRUCTURED" if curated else "NOT_CURATED",
                urgency=entry.get("urgency"),
                dangerous=entry.get("dangerous"),
                chief_complaint_tags=tuple(entry.get("chief_complaint_tags", [])),
                typical_features=tuple(entry.get("typical_features", [])),
            )

    def load(self) -> List[ClinicalConcept]:
        return list(self.iter_concepts())
