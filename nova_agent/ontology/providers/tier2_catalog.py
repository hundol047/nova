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

_ENRICHMENT_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "tier2_enrichment.json"

_OPEN_FEATURES_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "tier2_open_features.json"

_MONDO_SYNONYMS_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "tier2_mondo_synonyms.json"

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

    def _load_enrichment(self) -> dict:
        """id -> typical_features from knowledge/tier2_enrichment.json (an engineering-agent authored,
        NOT clinician-reviewed sidecar; its provenance block documents scope and limits)."""
        if self._path != _CATALOG_PATH or not _ENRICHMENT_PATH.is_file():
            return {}
        try:
            data = json.loads(_ENRICHMENT_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {e["id"]: {"typical_features": list(e.get("typical_features", [])),
                          "confirmatory_findings": list(e.get("confirmatory_findings", []))}
                for e in data.get("entries", []) if e.get("id")}

    def _load_open_features(self) -> dict:
        """id -> {typical_features, synonyms} from knowledge/tier2_open_features.json, built from the CC0
        Human Disease Ontology (has_symptom clauses + EXACT synonyms; see scripts/build_open_disease_features.py).
        Lowest precedence: catalog features > unreviewed enrichment > these. NOT clinician reviewed."""
        if self._path != _CATALOG_PATH or not _OPEN_FEATURES_PATH.is_file():
            return {}
        try:
            data = json.loads(_OPEN_FEATURES_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {e["id"]: {"typical_features": list(e.get("typical_features", [])),
                          "synonyms": list(e.get("synonyms", []))}
                for e in data.get("entries", []) if e.get("id")}

    def _load_mondo_synonyms(self) -> dict:
        """id -> EXACT synonyms from knowledge/tier2_mondo_synonyms.json (Mondo, CC BY 4.0; attribution in
        docs/compliance/SOURCES_AND_LICENSES.md). Aliases only, lowest precedence, NOT clinician reviewed."""
        from nova_agent.config import get_config
        if self._path != _CATALOG_PATH or not _MONDO_SYNONYMS_PATH.is_file() or not get_config().mondo_synonyms_enabled:
            return {}
        try:
            data = json.loads(_MONDO_SYNONYMS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return {e["id"]: list(e.get("synonyms", [])) for e in data.get("entries", []) if e.get("id")}

    @staticmethod
    def _claim(claimed: dict, cid: str, synonyms: list) -> tuple:
        """Synonyms that no other concept owns; registers them for this concept (first come, first served)."""
        out = []
        for text in synonyms:
            owners = claimed.setdefault(text.lower(), set())
            if owners <= {cid} and text.lower() not in {o.lower() for o in out} and cid not in owners:
                owners.add(cid)
                out.append(text)
        return tuple(out)

    def iter_concepts(self) -> Iterator[ClinicalConcept]:
        if not self.available():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        conditions = data.get("conditions", data if isinstance(data, list) else [])
        enrichment = self._load_enrichment()
        open_features = self._load_open_features()
        mondo_synonyms = self._load_mondo_synonyms()
        # A sidecar synonym is adopted only if no OTHER concept already uses it (catalog names/aliases or a
        # synonym adopted earlier): two sidecars may list the same term for different concepts.
        claimed = {}
        for entry in conditions:
            for text in [entry.get("name")] + list(entry.get("aliases", [])):
                if text:
                    claimed.setdefault(text.lower(), set()).add(entry.get("id"))
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
            features = tuple(entry.get("typical_features", []))
            source = "tier2_catalog"
            extra = enrichment.get(cid)
            confirmatory = tuple(entry.get("confirmatory_findings", []))
            if extra and not features:
                # Provenance stays visible on the concept itself: the features came from the
                # unreviewed enrichment sidecar, not from the original catalog.
                features = tuple(extra["typical_features"])
                confirmatory = confirmatory or tuple(extra["confirmatory_findings"])
                source = "tier2_catalog+tier2_enrichment_unreviewed"
            aliases = tuple(a for a in entry.get("aliases", []) if a)
            open_extra = open_features.get(cid)
            if open_extra:
                if open_extra["typical_features"] and not features:
                    features = tuple(open_extra["typical_features"])
                    source = "tier2_catalog+open_disease_ontology_cc0_unreviewed"
                added = self._claim(claimed, cid, open_extra["synonyms"])
                if added:
                    aliases = aliases + added
                    if source == "tier2_catalog":
                        source = "tier2_catalog+open_disease_ontology_cc0_synonyms"
            mondo_extra = mondo_synonyms.get(cid)
            if mondo_extra:
                added = self._claim(claimed, cid, mondo_extra)
                if added:
                    aliases = aliases + added
                    source += "+mondo_cc_by_synonyms"
            yield ClinicalConcept(
                concept_id=f"tier2:{cid}",
                canonical_name=name,
                semantic_type=self._semantic_type(entry.get("semantic_type")),
                tier=Tier.TIER2_STRUCTURED,
                aliases=aliases,
                category=entry.get("category"),
                external_codes=codes,
                source=source,
                curation_status="STRUCTURED" if curated else "NOT_CURATED",
                urgency=entry.get("urgency"),
                dangerous=entry.get("dangerous"),
                chief_complaint_tags=tuple(entry.get("chief_complaint_tags", [])),
                typical_features=features,
                confirmatory_findings=confirmatory,
            )

    def load(self) -> List[ClinicalConcept]:
        return list(self.iter_concepts())
