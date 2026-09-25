"""Base terminology provider + shared local-snapshot loader.

A provider reads a JSON snapshot the operator supplies and yields ClinicalConcept objects. The
snapshot schema is intentionally minimal and provider-agnostic:

    {
      "system": "SNOMEDCT",
      "concepts": [
        {"code": "9826008", "display": "Appendicitis",
         "aliases": ["appendicitis"], "parents": ["18526009"], "semantic_type": "DISEASE"},
        ...
      ]
    }

Absence of the file is normal and license-safe: yield nothing, never fabricate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, List, Optional

from nova_agent.ontology.models import (
    ClinicalConcept,
    ExternalCode,
    SemanticType,
    Tier,
)

SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "snapshots"


class TerminologyProvider:
    """Reads one local snapshot for a given terminology system."""

    system: str = "UNKNOWN"
    snapshot_filename: str = ""
    concept_id_prefix: str = "onto"

    def __init__(self, snapshot_root: Optional[Path] = None) -> None:
        self._root = snapshot_root or SNAPSHOT_ROOT

    def snapshot_path(self) -> Path:
        return self._root / self.snapshot_filename

    def available(self) -> bool:
        return self.snapshot_filename != "" and self.snapshot_path().is_file()

    def _semantic_type(self, raw: Optional[str]) -> SemanticType:
        if not raw:
            return SemanticType.DISEASE
        try:
            return SemanticType(raw.strip().upper())
        except ValueError:
            return SemanticType.UNKNOWN

    def iter_concepts(self) -> Iterator[ClinicalConcept]:
        if not self.available():
            return iter(())  # license-safe: no snapshot -> no concepts
        return self._parse(self.snapshot_path())

    def _parse(self, path: Path) -> Iterator[ClinicalConcept]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        system = data.get("system", self.system)
        for entry in data.get("concepts", []):
            code = str(entry.get("code", "")).strip()
            display = (entry.get("display") or "").strip()
            if not code or not display:
                continue
            aliases = tuple(a for a in entry.get("aliases", []) if a)
            parents = tuple(str(p) for p in entry.get("parents", []) if str(p).strip())
            children = tuple(str(c) for c in entry.get("children", []) if str(c).strip())
            concept_id = f"{self.concept_id_prefix}:{system}:{code}"
            yield ClinicalConcept(
                concept_id=concept_id,
                canonical_name=display,
                semantic_type=self._semantic_type(entry.get("semantic_type")),
                tier=Tier.TIER3_ONTOLOGY,
                aliases=aliases,
                category=entry.get("category"),
                external_codes=(ExternalCode(system=system, code=code, display=display),),
                parents=tuple(f"{self.concept_id_prefix}:{system}:{p}" for p in parents),
                children=tuple(f"{self.concept_id_prefix}:{system}:{c}" for c in children),
                source=f"{system.lower()}_snapshot",
                curation_status="NOT_CURATED",
            )

    def load(self) -> List[ClinicalConcept]:
        return list(self.iter_concepts())
