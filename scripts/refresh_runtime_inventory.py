#!/usr/bin/env python3
"""Keeps artifacts/compliance_hardening/clinical_asset_inventory.json in step with the files that are
actually shipped, WITHOUT ever raising a rights or provenance status.

What it does (and the only things it does):
  * refreshes ``sha256`` of an existing entry whose file bytes changed;
  * adds a NEW entry for a runtime file that has none, copied from a conservative template whose every
    authorship/licence/permission field is ``UNRESOLVED`` (status UNRESOLVED), unless the file has an
    explicit, source-evidenced override below;
  * marks an entry whose file no longer exists as removed (submission_included false, status
    NOT_USED_IN_SUBMISSION) instead of deleting history.
It never edits original_author/license/permission/clinician fields of an existing entry, and never
changes UNRESOLVED to anything else. Authorship, licence and permission remain separate questions from
"the hash is current"; ``--check`` exits non-zero when the inventory is stale.

Run order (see docs/release/RELEASE_ORDER.md): freeze runtime -> commit -> this script -> record
verification. The inventory is not part of the shipped archive, so refreshing it cannot change a runtime hash.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "artifacts/compliance_hardening/clinical_asset_inventory.json"
SUFFIXES = {".py", ".json", ".md"}

# Files whose source and licence are evidenced by the file itself (provenance block + retained licence
# lines). Everything else gets the all-UNRESOLVED template.
SOURCED = {
    "nova_agent/knowledge/tier2_open_features.json": dict(
        runtime_use="Alias vocabulary (EXACT synonyms) for Tier-2 concepts; opt-in (NOVA_OPEN_SYNONYMS), default off; never patient evidence",
        original_author="Human Disease Ontology consortium (Schriml LM et al.)",
        original_source="Disease Ontology doid.obo, https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.obo",
        source_reference=["research/open_sources/disease_ontology/terms.txt", "scripts/build_open_disease_features.py", "docs/compliance/SOURCES_AND_LICENSES.md"],
        license="CC0 1.0 Universal, stated inside the source file (licence lines retained verbatim in terms.txt)",
        research_publication_permission="CC0 public-domain dedication permits any use",
        redistribution_permission="CC0 public-domain dedication permits redistribution",
        modification_permission="CC0 public-domain dedication permits modification",
        generation_method="Deterministic extraction and exact-match filtering; no LLM generation",
        generation_code="scripts/build_open_disease_features.py", status="VERIFIED",
        rights_status="Source licence verified from the source file text only; mapping to NOVA concepts is unreviewed"),
    "nova_agent/knowledge/tier2_mondo_synonyms.json": dict(
        runtime_use="Alias vocabulary (EXACT synonyms) for Tier-2 concepts; opt-in (NOVA_MONDO_SYNONYMS), default off; never patient evidence",
        original_author="Monarch Initiative (Mondo Disease Ontology)",
        original_source="Mondo mondo-edit.obo, https://raw.githubusercontent.com/monarch-initiative/mondo/master/src/ontology/mondo-edit.obo",
        source_reference=["research/open_sources/mondo/terms.txt", "scripts/build_mondo_synonyms.py", "docs/compliance/SOURCES_AND_LICENSES.md"],
        license="CC BY 4.0, stated inside the source file and in the repository LICENSE; attribution in docs/compliance/SOURCES_AND_LICENSES.md",
        research_publication_permission="CC BY 4.0 permits any purpose subject to attribution",
        redistribution_permission="CC BY 4.0 permits redistribution with attribution",
        modification_permission="CC BY 4.0 permits adaptation with a change notice (EXACT synonyms extracted and filtered)",
        generation_method="Deterministic extraction and exact-match filtering; no LLM generation",
        generation_code="scripts/build_mondo_synonyms.py", status="VERIFIED",
        rights_status="Source licence verified from the source file text only; mapping to NOVA concepts is unreviewed"),
}
# Present in this repository but only the PR #15 history records where they came from.
PR15_DERIVED = {"nova_agent/pr15_feature_aliases.py": "Feature-local aliases ported from PR #15 (fix/nova-expansion-validation); see artifacts/integration/pr15_alias_provenance.json"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_files() -> list:
    return sorted(str(p.relative_to(ROOT)) for p in (ROOT / "nova_agent").rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix in SUFFIXES)


def build(check_only: bool) -> dict:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    by_path = {a["path"]: a for a in inventory["assets"]}
    current = set(runtime_files())
    template_code = next(a for a in inventory["assets"] if a["path"] == "nova_agent/state.py")
    template_data = next((a for a in inventory["assets"] if a["path"] == "nova_agent/knowledge/tier2_enrichment.json"), template_code)
    changes = {"refreshed": [], "added": [], "removed": []}
    for path in sorted(current):
        digest = sha(ROOT / path)
        if path in by_path:
            asset = by_path[path]
            if asset.get("sha256") != digest or not asset.get("submission_included", True) and asset.get("removed_from_runtime"):
                asset["sha256"] = digest
                if asset.get("removed_from_runtime"):
                    asset.pop("removed_from_runtime")
                    asset["submission_included"] = True
                changes["refreshed"].append(path)
            continue
        base = copy.deepcopy(template_data if path.startswith("nova_agent/knowledge/") else template_code)
        base.update(asset_id=path, path=path, sha256=digest, submission_included=True, status="UNRESOLVED",
                    history_evidence=[], runtime_use=("Static clinical data or clinical rules" if path.startswith("nova_agent/knowledge/")
                                                     else "Supporting runtime code/metadata; conservatively inventoried"),
                    original_source="Engineering-agent authored in this repository's history; not independently established")
        if path in PR15_DERIVED:
            base["original_source"] = PR15_DERIVED[path]
            base["source_reference"] = ["artifacts/integration/pr15_alias_provenance.json"]
        base.update(SOURCED.get(path, {}))
        inventory["assets"].append(base)
        by_path[path] = base
        changes["added"].append(path)
    for path, asset in by_path.items():
        if path.startswith("nova_agent/") and path not in current and asset.get("submission_included"):
            asset["submission_included"] = False
            asset["status"] = "NOT_USED_IN_SUBMISSION"
            asset["removed_from_runtime"] = True
            changes["removed"].append(path)
    inventory["assets"].sort(key=lambda a: a["path"])
    return {"inventory": inventory, "changes": changes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 if the inventory is stale; write nothing")
    args = parser.parse_args()
    result = build(args.check)
    changes = result["changes"]
    print(json.dumps({k: len(v) for k, v in changes.items()}))
    if args.check:
        raise SystemExit(1 if any(changes.values()) else 0)
    if any(changes.values()):
        INVENTORY.write_text(json.dumps(result["inventory"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for key, values in changes.items():
            for value in values:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
