#!/usr/bin/env python3
"""Keep artifacts/compliance_hardening/clinical_asset_inventory.json byte-accurate WITHOUT inventing provenance.

* An inventoried asset whose bytes changed gets its sha256 refreshed and a ``bytes_changed_since_review`` note;
  its status, licence, authorship and permission fields are never touched (a changed file does not become
  more or less cleared).
* A new runtime file is appended as UNRESOLVED with every provenance field UNRESOLVED -- unless it is in
  ``VERIFIED_FROM_SOURCE`` below, whose values are copied from the asset's OWN embedded provenance block and
  the repository's attribution document (checked by a test), never written from memory.

    python scripts/refresh_asset_inventory.py            # rewrites the inventory, prints what changed
    python scripts/validate_runtime_provenance.py        # coverage must then PASS (permission stays BLOCKED)
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "artifacts/compliance_hardening/clinical_asset_inventory.json"
SUFFIXES = {".py", ".json", ".md"}

VERIFIED_FROM_SOURCE = {
    "nova_agent/knowledge/tier2_mondo_synonyms.json": {
        "runtime_use": "Alias vocabulary (EXACT synonyms) for Tier-2 concepts; not patient evidence, not scored features",
        "original_author": "Mondo Disease Ontology, Monarch Initiative",
        "original_source": "mondo-edit.obo, https://raw.githubusercontent.com/monarch-initiative/mondo/master/src/ontology/mondo-edit.obo",
        "source_reference": ["scripts/build_mondo_synonyms.py", "research/open_sources/mondo/terms.txt",
                             "docs/compliance/SOURCES_AND_LICENSES.md"],
        "source_version": "retrieved 2026-10-06; file sha256 30fd1b2d50ea2a14330f1d93e7ef5e61607a05c1a36e1ce8e0f54b6aceaabf7e",
        "license": "CC BY 4.0, stated inside the source file and in the repository LICENSE (attribution required)",
        "research_publication_permission": "CC BY 4.0 permits any purpose subject to attribution",
        "redistribution_permission": "CC BY 4.0 permits redistribution with attribution",
        "modification_permission": "CC BY 4.0 permits adaptation; only EXACT synonyms were extracted and filtered",
        "generation_method": "Deterministic extraction and exact-match filtering; no LLM generation",
        "generation_code": "scripts/build_mondo_synonyms.py",
        "generation_date": "2026-10-06 (new extraction, not original authorship)",
        "manual_review": "Source licence line inspected; engineering hash/selection checks; synonym-to-concept matching is by exact name/alias only",
        "authorship_status": "Named source ontology; not FutureLabs-original",
        "rights_status": "Source licence verified from the source file text only; mapping to NOVA concepts is unreviewed",
        "status": "VERIFIED",
    },
}


def _template(path: str, digest: str) -> dict:
    unresolved = "UNRESOLVED"
    return {
        "asset_id": path, "path": path, "sha256": digest,
        "runtime_use": "Supporting runtime code/metadata; conservatively inventoried",
        "original_author": unresolved, "original_source": unresolved,
        "source_reference": ["nova_agent/knowledge/PROVENANCE.md"], "source_version": unresolved, "license": unresolved,
        "research_publication_permission": unresolved, "redistribution_permission": unresolved,
        "modification_permission": unresolved, "generation_method": unresolved, "generating_model": unresolved,
        "model_version": unresolved, "generation_prompt": unresolved, "generation_code": unresolved,
        "generation_date": unresolved,
        "manual_review": "Engineering tests do not establish original authorship or medical correctness",
        "clinician_review": "No documented clinician signoff", "submission_included": True, "status": "UNRESOLVED",
        "history_evidence": [], "history_caveat": "Commit author/time are not original clinical author/generation time",
        "authorship_status": unresolved, "medical_validation_status": "NOT independently clinically validated",
        "rights_status": unresolved,
        "replacement_plan": {"decision": "E", "status": "BLOCKED",
                             "reason": "No evidence supports safe loss of coverage; no source or permission inferred"},
    }


def refresh(root: Path = ROOT, write: bool = True) -> dict:
    inventory = json.loads((root / INVENTORY.relative_to(ROOT)).read_text(encoding="utf-8"))
    by_path = {a["path"]: a for a in inventory["assets"]}
    report = {"rehashed": [], "added": []}
    for path, asset in by_path.items():
        if not asset.get("submission_included"):
            continue
        file = root / path
        if file.is_file():
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            if digest != asset["sha256"]:
                asset["sha256"] = digest
                asset["bytes_changed_since_review"] = ("sha256 refreshed to the current bytes; status/permissions unchanged "
                                                       "and NOT re-reviewed")
                report["rehashed"].append(path)
    for file in sorted((root / "nova_agent").rglob("*")):
        rel = str(file.relative_to(root))
        if (file.is_file() and "__pycache__" not in file.parts and file.suffix in SUFFIXES and rel not in by_path):
            asset = _template(rel, hashlib.sha256(file.read_bytes()).hexdigest())
            if rel in VERIFIED_FROM_SOURCE:
                asset.update(copy.deepcopy(VERIFIED_FROM_SOURCE[rel]))
                asset.update({"generating_model": "NOT_APPLICABLE", "model_version": "NOT_APPLICABLE",
                              "generation_prompt": "NOT_APPLICABLE: no LLM-generated clinical material",
                              "clinician_review": "NOT_REVIEWED", "history_evidence": [],
                              "replacement_plan": {"decision": "C", "status": "REFERENCE_CONTEXT_ONLY",
                                                   "reason": "Added vocabulary only; no existing heuristic relabelled or replaced"}})
            inventory["assets"].append(asset)
            report["added"].append(rel)
    if write:
        (root / INVENTORY.relative_to(ROOT)).write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(refresh(), indent=2))
