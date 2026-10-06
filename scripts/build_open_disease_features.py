#!/usr/bin/env python3
"""Builds nova_agent/knowledge/tier2_open_features.json from the Human Disease Ontology (CC0).

SOURCE: Disease Ontology (DO), https://github.com/DiseaseOntology/HumanDiseaseOntology, file
src/ontology/doid.obo. The file itself states: "The Disease Ontology content is available via the
Creative Commons Public Domain Dedication CC0 1.0 Universal license" (remark line) and
``terms:license https://creativecommons.org/publicdomain/zero/1.0/``. Those two lines are copied
verbatim into the sidecar's provenance block and into research/open_sources/disease_ontology/.

WHAT IS TAKEN, AND NOTHING ELSE
  * ``has_symptom <phrase>`` clauses from a term's text definition (DO writes them as structured
    clauses, e.g. "... has_symptom fever, has_symptom arthralgia, and has_symptom maculopapular rash")
  * EXACT synonyms of the term
for each DO term that can be matched to a Tier-2 catalog concept BY EXACT NAME/ALIAS OR BY AN EXACT
ICD-10 CODE. No clinical statement is generated or paraphrased. A matched concept that already has
typical_features (from the catalog or from tier2_enrichment.json) is left untouched.

QUALITY GUARDS (documented so a reviewer can audit them): bare generic words ("lesions", "swelling",
"pain"...) are dropped, over-long descriptive clauses (> 8 words) are dropped, at most 8 features per
concept are kept, and a synonym is kept only if it collides with NO other concept name/alias in the
catalog. The output is explicitly NOT clinician-reviewed.

Usage (the OBO file is downloaded separately; it is ~7 MB and is not stored in the repository):
    curl -L -o doid.obo https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.obo
    python scripts/build_open_disease_features.py --obo doid.obo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "nova_agent/knowledge/tier2_catalog.json"
ENRICHMENT = ROOT / "nova_agent/knowledge/tier2_enrichment.json"
OUTPUT = ROOT / "nova_agent/knowledge/tier2_open_features.json"
TERMS_DIR = ROOT / "research/open_sources/disease_ontology"

SOURCE_URL = "https://raw.githubusercontent.com/DiseaseOntology/HumanDiseaseOntology/main/src/ontology/doid.obo"
MAX_FEATURES = 8
MAX_FEATURE_WORDS = 8
MAX_SYNONYMS = 5
MIN_FEATURES = 2
# One-word findings that match almost any text; they carry no diagnostic information on their own.
# Ambiguous everyday words/phrases that DO lists as a disease synonym; adopting them as aliases would let
# ordinary patient wording ("I have a cold") pull in an unrelated disease.
AMBIGUOUS_SYNONYMS = {"cold", "chest cold", "chest infection", "stress ulcer", "heart defect", "fever"}
GENERIC_FEATURES = {"fever", "mild fevers", "headache", "rash", "nausea", "vomiting", "chills", "sweat",
                    "lesion", "lesions", "swelling", "pain", "symptoms", "inflammation", "infection", "irritability",
                    "fissures", "scaling", "maceration", "itching", "redness", "weakness", "fatigue", "malaise"}

_SYMPTOM = re.compile(r"has_symptom ([^,.;]+?)(?=,| and has_symptom|\.|;| which|$)")


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def parse_obo(path: Path) -> list:
    terms, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw == "[Term]":
            cur = {"syn": [], "xref": [], "obsolete": False}
            terms.append(cur)
            continue
        if raw.startswith("["):
            cur = None
            continue
        if cur is None or ": " not in raw:
            continue
        key, value = raw.split(": ", 1)
        if key == "id":
            cur["id"] = value
        elif key == "name":
            cur["name"] = value
        elif key == "def":
            cur["def"] = value
        elif key == "synonym":
            m = re.match(r'"(.*?)" EXACT', value)
            if m:
                cur["syn"].append(m.group(1))
        elif key == "xref":
            cur["xref"].append(value)
        elif key == "is_obsolete":
            cur["obsolete"] = True
    for t in terms:
        t["symptoms"] = [s.strip() for s in _SYMPTOM.findall(t.get("def", ""))]
    return [t for t in terms if t.get("id") and t.get("name") and not t["obsolete"]]


def clean_features(raw: list) -> list:
    out = []
    for phrase in raw:
        phrase = re.sub(r"\s+", " ", phrase.strip().lower().strip("()"))
        words = phrase.split()
        if not phrase or len(words) > MAX_FEATURE_WORDS or phrase in GENERIC_FEATURES:
            continue
        if len(words) == 1 and words[0] in GENERIC_FEATURES:
            continue
        if "_" in phrase:  # DO relation tokens leaking into prose ("results_in_formation_of ...")
            continue
        if phrase not in out:
            out.append(phrase)
    return out[:MAX_FEATURES]


def usable_features(raw: list) -> list:
    """A single surviving finding is too weak to be a profile: keep features only when >= MIN_FEATURES remain."""
    cleaned = clean_features(raw)
    return cleaned if len(cleaned) >= MIN_FEATURES else []


def usable_synonym(syn: str) -> bool:
    key = norm(syn)
    words = syn.split()
    return bool(key) and key.isascii() and key not in AMBIGUOUS_SYNONYMS and len(words) <= 4 \
        and " - " not in syn and "and/or" not in syn and not re.search(r"\d", syn)


def build(obo: Path) -> dict:
    terms = parse_obo(obo)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["conditions"]
    enriched = {e["id"] for e in json.loads(ENRICHMENT.read_text(encoding="utf-8"))["entries"]}
    by_name, by_icd = {}, {}
    for t in terms:
        for name in [t["name"]] + t["syn"]:
            by_name.setdefault(norm(name), []).append(t)
        for x in t["xref"]:
            if x.startswith("ICD10CM:"):
                by_icd.setdefault(x[len("ICD10CM:"):], []).append(t)
    taken = {}
    for c in catalog:
        for name in [c["name"]] + list(c.get("aliases", [])):
            taken.setdefault(norm(name), set()).add(c["id"])

    entries = []
    for c in catalog:
        hits, how = [], ""
        for name in [c["name"]] + list(c.get("aliases", [])):
            found = by_name.get(norm(name), [])
            if found:
                hits, how = found, "exact name/alias"
                break
        if not hits:
            for code in c.get("external_codes", []):
                if str(code.get("system", "")).upper().startswith("ICD10"):
                    found = by_icd.get(str(code.get("code")), [])
                    if found:
                        hits, how = found, f"exact ICD-10 code {code['code']}"
                        break
        hits = list({h["id"]: h for h in hits}.values())
        if len(hits) != 1:  # ambiguous or absent: never guess
            continue
        term = hits[0]
        has_features = bool(c.get("typical_features")) or c["id"] in enriched
        features = [] if has_features else usable_features(term["symptoms"])
        synonyms = []
        for syn in term["syn"]:
            key = norm(syn)
            if usable_synonym(syn) and key != norm(c["name"]) and taken.get(key, set()) <= {c["id"]} \
                    and syn not in c.get("aliases", []) and syn not in synonyms:
                synonyms.append(syn)
        synonyms = synonyms[:MAX_SYNONYMS]
        if features or synonyms:
            entries.append({"id": c["id"], "doid": term["id"], "do_name": term["name"], "matched_by": how,
                            "typical_features": features, "synonyms": synonyms})
    data = obo.read_bytes()
    remark = next((l for l in data.decode("utf-8").splitlines() if l.startswith("remark: The Disease Ontology content")), "")
    license_line = next((l for l in data.decode("utf-8").splitlines() if l.startswith("property_value: terms:license")), "")
    version = next((l for l in data.decode("utf-8").splitlines() if l.startswith("data-version:")), "")
    return {
        "schema": "nova-open-disease-features-v1",
        "provenance": {
            "source": "Human Disease Ontology (Disease Ontology), DiseaseOntology/HumanDiseaseOntology",
            "source_url": SOURCE_URL, "source_file_sha256": hashlib.sha256(data).hexdigest(),
            "source_data_version": version.replace("data-version: ", ""),
            "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "license": "CC0 1.0 Universal (public domain dedication), stated inside the source file",
            "license_evidence": [remark, license_line],
            "attribution": "Source: Human Disease Ontology (https://disease-ontology.org), CC0 1.0. Schriml LM et al.",
            "extraction": "has_symptom clauses and EXACT synonyms copied from DO term definitions for terms matched to a "
                          "catalog concept by exact name/alias or exact ICD-10 code; quality guards in "
                          "scripts/build_open_disease_features.py; nothing generated or paraphrased",
            "clinician_reviewed": False,
            "use": "Low-weight typical_features / aliases for Tier-2 concepts that had none; never patient evidence",
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
        "Disease Ontology licence evidence (copied verbatim from the downloaded doid.obo header)\n"
        f"{prov['source_data_version']}\nsha256 {prov['source_file_sha256']}\n" + "\n".join(prov["license_evidence"]) + "\n",
        encoding="utf-8")
    n_feat = sum(bool(e["typical_features"]) for e in result["entries"])
    n_syn = sum(bool(e["synonyms"]) for e in result["entries"])
    print(f"entries={len(result['entries'])} with_features={n_feat} with_synonyms={n_syn}")


if __name__ == "__main__":
    main()
