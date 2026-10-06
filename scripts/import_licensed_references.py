"""Reproducible reference extraction, never clinical feature/label generation.

acquire: downloads publisher files during DEVELOPMENT only, checks pinned ZIP hashes,
and retains only permitted source fields matching the existing catalog vocabulary.
build: offline transformation of the retained source snapshot into the bundled catalog.
Neither mode reads evaluation cases, changes diagnostic rules, or calls an LLM.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research/licensed_references"
OUTPUT = ROOT / "nova_agent/knowledge/licensed_references.json"
NLM_TERMS = "https://medlineplus.gov/about/using/usingcontent/"
CC_TERMS = "https://creativecommons.org/licenses/by/4.0/"
SOURCES = {
    "medlineplus": {
        "url": "https://medlineplus.gov/xml/mplus_topics_compressed_2026-10-03.zip",
        "filename": "medlineplus_topics_2026-10-03.zip",
        "sha256": "f399013d388b3929b96bd7d826704eaeffba99d0c3b94be9b47d5c4ce8b2a604",
        "version": "2026-10-03",
        "terms_url": NLM_TERMS,
        "license": "Public-domain health-topic summaries; NLM scope-specific reuse terms",
        "attribution": "Source: MedlinePlus, National Library of Medicine.",
    },
    "orphanet": {
        "url": "https://www.orphacode.org/data/packs/Orphanet_Nomenclature_Pack_EN.zip",
        "filename": "orphanet_nomenclature_2026.zip",
        "sha256": "c05745e148d6cdb61f0261257550f5b752662b2fdb8a0903767a25b5baa84e6e",
        "version": "July 2026; XML extraction 2026-06-23 07:28:38",
        "terms_url": CC_TERMS,
        "license": "CC-BY-4.0",
        "attribution": "Orphanet (c) 2026; Orphanet Nomenclature Pack, July 2026. CC BY 4.0.",
    },
}
# Identity links to five existing test actions, checked against the publisher's test index.
# These are not test indications or interpretations; no diagnostic utility is inferred.
TESTS = {
    "ecg": ("electrocardiogram", "Electrocardiogram"),
    "troponin": ("troponin-test", "Troponin Test"),
    "d_dimer": ("d-dimer-test", "D-Dimer Test"),
    "lactate": ("lactate-test", "Lactate Test"),
    "lipase": ("lipase-tests", "Lipase Tests"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def normalize(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold().replace("_", " ")))


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.blocked = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.blocked += 1
        elif tag in {"p", "li", "br", "h2"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.blocked = max(0, self.blocked - 1)
        elif tag in {"p", "li", "h2"}:
            self.parts.append("\n")

    def handle_data(self, value):
        if not self.blocked:
            self.parts.append(value)


def plain(value):
    parser = PlainText()
    parser.feed(value)
    return "\n".join(line for raw in "".join(parser.parts).splitlines() if (line := " ".join(raw.split())))


def read_xml(data):
    if len(data) > 64_000_000 or b"<!ENTITY" in data.upper():
        raise ValueError("Oversized XML or entity declaration")
    return ET.fromstring(data)


def vocabulary():
    files = sorted((ROOT / "nova_agent/knowledge/diseases").glob("*.json"))
    files.append(ROOT / "nova_agent/knowledge/tier2_catalog.json")
    words = set()
    for path in files:
        obj = json.loads(path.read_text())
        for row in obj if isinstance(obj, list) else obj["conditions"]:
            words.update(normalize(s) for s in [row["name"], row["id"], *row.get("aliases", [])])
    return words, {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in files}


def download(url, path):
    if not path.exists():
        # Development acquisition only; deliberately absent from the submission dependency graph.
        with urllib.request.urlopen(url, timeout=45) as response:
            if response.url != url:
                raise ValueError("Unexpected source redirect")
            data = response.read(64_000_001)
        if len(data) > 64_000_000:
            raise ValueError("Oversized source")
        path.write_bytes(data)
    return path.read_bytes()


def acquire():
    raw = RESEARCH / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    words, selection_hashes = vocabulary()
    records, manifests = [], {}
    for source, info in SOURCES.items():
        data = download(info["url"], raw / info["filename"])
        if digest(data) != info["sha256"]:
            raise ValueError("Publisher archive changed; explicit version/rights review required")
        with zipfile.ZipFile(raw / info["filename"]) as archive:
            name = "mplus_topics_2026-10-03.xml" if source == "medlineplus" else next(
                n for n in archive.namelist() if n.endswith("/ORPHAnomenclature_en_2026.xml"))
            if archive.getinfo(name).file_size > 64_000_000:
                raise ValueError("Oversized XML member")
            xml = archive.read(name)
        tree = read_xml(xml)
        manifests[source] = dict(info, xml_member=name, xml_sha256=digest(xml))
        for element in tree.findall("health-topic" if source == "medlineplus" else "./DisorderList/Disorder"):
            if source == "medlineplus":
                if element.get("language") != "English":
                    continue
                title = element.get("title", "")
                aliases = [e.text or "" for tag in ("also-called", "see-reference") for e in element.findall(tag)]
                body = element.findtext("full-summary", "")
                identifier, url = element.get("id"), element.get("url")
                if not re.fullmatch(r"https://medlineplus\.gov/[a-z0-9]+\.html", url or ""):
                    continue
            else:
                if element.findtext("Totalstatus") != "Active" or element.findtext("ClassificationLevel/Name") != "Disorder":
                    continue
                title = element.findtext("Name", "")
                aliases = [e.text or "" for e in element.findall("SynonymList/Synonym")]
                definitions = [e.findtext("Contents", "") for e in element.findall(".//TextSection")
                               if e.findtext("TextSectionType/Name") == "Definition" and e.get("lang") == "en"]
                body = "\n".join(definitions)
                identifier, url = element.findtext("OrphaCode"), element.findtext("ExpertLink")
            if not body or not words.intersection(normalize(s) for s in [title, *aliases]):
                continue
            records.append(dict(reference_id=f"{source}:{identifier}", source=source, title=title,
                                aliases=aliases, source_url=url, original_markup=body,
                                kind="disease_reference"))
    manifests["medlineplus_tests"] = dict(
        version="Retrieved 2026-10-05; per-page byte hashes retained",
        terms_url=NLM_TERMS, license="Public-domain medical test information; NLM reuse terms",
        attribution=SOURCES["medlineplus"]["attribution"],
        index_url="https://medlineplus.gov/lab-tests/", pages={})
    for key, (slug, title) in TESTS.items():
        url = f"https://medlineplus.gov/lab-tests/{slug}/"
        data = download(url, raw / (slug + ".html"))
        html = data.decode("utf-8")
        if f"<h1>{title}</h1>" not in html:
            raise ValueError("Unexpected medical-test page")
        # Publisher article blocks ONLY, excluding mp-refs, sidebar, logos, references and images.
        blocks = re.findall(r'<div class="mp-content">(.*?)</div>\s*</section>', html, re.S)
        if not blocks:
            raise ValueError("Medical-test article structure changed")
        manifests["medlineplus_tests"]["pages"][key] = {"url": url, "sha256": digest(data)}
        records.append(dict(reference_id="medlineplus_tests:" + key, source="medlineplus_tests",
                            title=title, aliases=[], source_url=url, original_markup="\n".join(blocks),
                            kind="test_reference", test_id=key))
    snapshot = dict(schema="nova-reference-source-snapshot-v1", acquired_date="2026-10-05",
                    selection="Exact normalized match to existing core/Tier-2 titles, IDs or aliases; no evaluation data",
                    selection_input_sha256=selection_hashes, sources=manifests,
                    records=sorted(records, key=lambda r: r["reference_id"]))
    (RESEARCH / "source_snapshot.json").write_bytes(encode(snapshot))
    build()


def build(output=OUTPUT):
    path = RESEARCH / "source_snapshot.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for original in snapshot["records"]:
        row = {key: value for key, value in original.items() if key != "original_markup"}
        row["text"] = plain(original["original_markup"])
        row["original_markup_sha256"] = digest(original["original_markup"].encode("utf-8"))
        records.append(row)
    catalog = dict(schema="nova-licensed-references-v1", source_snapshot_sha256=digest(path.read_bytes()),
                   sources=snapshot["sources"], records=records,
                   transformation="Deterministic selection; HTML tags removed; whitespace normalized. No translation, LLM facts or diagnostic labels generated.",
                   clinical_review="NOT CLINICIAN REVIEWED; source identity does not validate NOVA decision rules",
                   use="Supplemental background only; not observed patient evidence or support for pre-existing heuristic provenance")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encode(catalog))
    print(json.dumps({"records": len(records), "by_source": {s: sum(r["source"] == s for r in records) for s in snapshot["sources"]},
                      "output": str(output.relative_to(ROOT)), "sha256": digest(output.read_bytes())}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["acquire", "build"])
    args = parser.parse_args()
    acquire() if args.mode == "acquire" else build()
