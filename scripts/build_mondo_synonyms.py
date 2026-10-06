#!/usr/bin/env python3
"""Builds nova_agent/knowledge/tier2_mondo_synonyms.json from the Mondo Disease Ontology (CC BY 4.0).

SOURCE: Mondo, https://github.com/monarch-initiative/mondo, file src/ontology/mondo-edit.obo. The file
states ``property_value: http://purl.org/dc/terms/license http://creativecommons.org/licenses/by/4.0/`` and
the repository LICENSE is the CC BY 4.0 legal text. Attribution is required and given in
docs/compliance/SOURCES_AND_LICENSES.md; the content is not endorsed by the Mondo/Monarch Initiative.

WHAT IS TAKEN: only EXACT synonyms of a Mondo term whose name or EXACT synonym equals (after
normalisation) the name/alias of exactly one Tier-2 catalog concept, and only when that Mondo term is
the single such match. No features, definitions or hierarchy are used. Guards are shared with
scripts/build_open_disease_features.py (usable_synonym; no collision with ANY other catalog name/alias).
Not clinician reviewed. The ~46 MB source file is downloaded separately and not stored in the repository:
    curl -L -o mondo-edit.obo https://raw.githubusercontent.com/monarch-initiative/mondo/master/src/ontology/mondo-edit.obo
    python scripts/build_mondo_synonyms.py --obo mondo-edit.obo
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.build_open_disease_features import CATALOG, MAX_SYNONYMS, norm, parse_obo, usable_synonym

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "nova_agent/knowledge/tier2_mondo_synonyms.json"
TERMS_DIR = ROOT / "research/open_sources/mondo"
SOURCE_URL = "https://raw.githubusercontent.com/monarch-initiative/mondo/master/src/ontology/mondo-edit.obo"


def build(obo: Path) -> dict:
    terms = parse_obo(obo)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["conditions"]
    by_name = {}
    for t in terms:
        for name in [t["name"]] + t["syn"]:
            by_name.setdefault(norm(name), {})[t["id"]] = t
    taken = {}
    for c in catalog:
        for name in [c["name"]] + list(c.get("aliases", [])):
            taken.setdefault(norm(name), set()).add(c["id"])
    entries = []
    for c in catalog:
        matches = {}
        for name in [c["name"]] + list(c.get("aliases", [])):
            matches.update(by_name.get(norm(name), {}))
        if len(matches) != 1:  # ambiguous or absent: never guess
            continue
        term = next(iter(matches.values()))
        synonyms = []
        for syn in term["syn"]:
            key = norm(syn)
            if usable_synonym(syn) and "(" not in syn and "," not in syn and key != norm(c["name"]) \
                    and taken.get(key, set()) <= {c["id"]} and syn not in c.get("aliases", []) and syn not in synonyms:
                synonyms.append(syn)
        if synonyms[:MAX_SYNONYMS]:
            entries.append({"id": c["id"], "mondo": term["id"], "mondo_name": term["name"],
                            "synonyms": synonyms[:MAX_SYNONYMS]})
    data = obo.read_bytes()
    lines = data.decode("utf-8").splitlines()
    license_line = next((l for l in lines if "purl.org/dc/terms/license" in l), "")
    version = next((l for l in lines if l.startswith("data-version:")), "")
    return {
        "schema": "nova-open-mondo-synonyms-v1",
        "provenance": {
            "source": "Mondo Disease Ontology, monarch-initiative/mondo", "source_url": SOURCE_URL,
            "source_file_sha256": hashlib.sha256(data).hexdigest(),
            "source_data_version": version.replace("data-version: ", ""),
            "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "license": "CC BY 4.0, stated inside the source file and in the repository LICENSE",
            "license_evidence": [license_line],
            "attribution": "Mondo Disease Ontology (https://mondo.monarchinitiative.org), Monarch Initiative, CC BY 4.0. "
                           "Only EXACT synonyms were extracted and filtered; no endorsement by the Monarch Initiative is implied.",
            "extraction": "EXACT synonyms of the single Mondo term whose name/synonym equals a catalog concept name/alias; "
                          "guards in scripts/build_mondo_synonyms.py and scripts/build_open_disease_features.py; nothing generated",
            "clinician_reviewed": False,
            "use": "Aliases for Tier-2 concepts only; never patient evidence",
        },
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--obo", required=True, type=Path)
    args = parser.parse_args()
    result = build(args.obo)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    TERMS_DIR.mkdir(parents=True, exist_ok=True)
    prov = result["provenance"]
    (TERMS_DIR / "terms.txt").write_text(
        "Mondo licence evidence (copied verbatim from the downloaded mondo-edit.obo header)\n"
        f"{prov['source_data_version']}\nsha256 {prov['source_file_sha256']}\n" + "\n".join(prov["license_evidence"]) + "\n"
        "Repository LICENSE: https://raw.githubusercontent.com/monarch-initiative/mondo/master/LICENSE (Creative Commons Attribution 4.0 International)\n",
        encoding="utf-8")
    print(f"entries={len(result['entries'])} synonyms={sum(len(e['synonyms']) for e in result['entries'])}")


if __name__ == "__main__":
    main()
