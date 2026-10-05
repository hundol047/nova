"""Bounded, offline reference lookup. No patient cache or diagnostic scoring.

Only immutable publisher text/index survives between cases. References are background
reading, never observations, confirmatory findings or provenance for legacy heuristics.
"""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from types import MappingProxyType
import unicodedata

CATALOG = Path(__file__).with_name("licensed_references.json")
MAX_REFERENCES = 2
MAX_TEXT_CHARS = 1600


def _normalize(value):
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold().replace("_", " ")))


@dataclass(frozen=True)
class Reference:
    reference_id: str
    title: str
    text: str
    source_url: str
    source_version: str
    attribution: str
    license: str
    terms_url: str


@lru_cache(maxsize=1)
def _index():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if catalog.get("schema") != "nova-licensed-references-v1":
        raise ValueError("Unsupported licensed reference schema")
    terms, tests = {}, {}
    for row in catalog["records"]:
        source = catalog["sources"][row["source"]]
        ref = Reference(row["reference_id"], row["title"], row["text"], row["source_url"],
                        source["version"], source["attribution"], source["license"], source["terms_url"])
        if row["kind"] == "test_reference":
            tests[row["test_id"]] = (ref,)
        else:
            for word in {_normalize(s) for s in [row["title"], *row["aliases"]]} - {""}:
                terms.setdefault(word, {}).setdefault(row["source"], []).append(ref)
    # Ambiguous aliases in a source cannot silently choose a disease. Cross-source
    # duplicates are separately attributed, not merged into a synthetic clinical profile.
    resolved = {word: tuple(refs[0] for refs in sources.values() if len(refs) == 1)
                for word, sources in terms.items()}
    return MappingProxyType(resolved), MappingProxyType(tests)


def _excerpt(text):
    if len(text) <= MAX_TEXT_CHARS:
        return text
    # Preserve complete paragraphs; if the first paragraph is too long, omit the
    # reference instead of cutting a clinical qualifier or inventing a summary.
    paragraphs, size = [], 0
    for paragraph in text.splitlines():
        if size + len(paragraph) + bool(paragraphs) > MAX_TEXT_CHARS:
            break
        paragraphs.append(paragraph)
        size += len(paragraph) + (len(paragraphs) > 1)
    return "\n".join(paragraphs)


def retrieve_licensed_references(diagnosis_names, candidate_test_ids):
    """At most one diagnosis and one test reference (or two diagnoses if no test).

    Only current proposed diagnoses/action IDs are looked up; no fuzzy matching,
    free-text symptom lookup, online calls, downloads or patient-derived persistence.
    """
    terms, tests = _index()
    disease_refs = [ref for name in diagnosis_names[:3] for ref in terms.get(_normalize(name), ())]
    test_refs = [ref for key in candidate_test_ids for ref in tests.get(key, ())]
    ordered = disease_refs[:1] + test_refs[:1] + disease_refs[1:] + test_refs[1:]
    result, seen = [], set()
    for ref in ordered:
        text = _excerpt(ref.text)
        if ref.reference_id in seen or not text:
            continue
        seen.add(ref.reference_id)
        result.append(dict(reference_id=ref.reference_id, title=ref.title, text=text,
                           source_url=ref.source_url, source_version=ref.source_version,
                           attribution=ref.attribution, license=ref.license, terms_url=ref.terms_url,
                           excerpt=text != ref.text, evidence_level="PUBLISHER_BACKGROUND_NOT_PATIENT_EVIDENCE",
                           clinician_review="NOT_REVIEWED"))
        if len(result) == MAX_REFERENCES:
            break
    return result
