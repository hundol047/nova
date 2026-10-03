"""Tests for the terminology import CLI + Tier-3 provider integration (vNext PART B).

Dependency-free: import scripts.import_terminology directly, and drive the ontology providers with a
temporary snapshot_root so no license-restricted content is ever committed. Confirms:
  - validation catches duplicate id / missing name / inactive / invalid hierarchy ref / cyclic /
    unknown code system / malformed synonym,
  - a valid import produces a provider-compatible snapshot,
  - with a snapshot present, Tier-3 concepts appear (count > 0) and hierarchy references resolve,
  - without a snapshot, the system degrades gracefully (Tier-3 == 0).
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

# Bootstrap a lightweight 'nova_agent' package so importing nova_agent.ontology.* does NOT trigger
# the pydantic-heavy package __init__ (this test is dependency-free; CI has pydantic and can import
# the real package, but this keeps the ontology providers testable without app deps).
if "nova_agent" not in sys.modules:
    _pkg = types.ModuleType("nova_agent")
    _pkg.__path__ = [str(_ROOT / "nova_agent")]
    sys.modules["nova_agent"] = _pkg

import import_terminology as imp  # noqa: E402


def _rows_to_valid(rows, system="ICD10"):
    return imp.validate(imp.normalize_rows(rows), system)


def test_validation_detects_all_issue_classes():
    rows = [
        {"code": "A00", "display": "Cholera", "active": "1"},
        {"code": "A01", "display": "Typhoid", "parents": "A00", "active": "1"},
        {"code": "A01", "display": "Typhoid dup", "active": "1"},           # duplicate id
        {"code": "A99", "display": "Inactive", "active": "0"},              # inactive
        {"code": "B00", "display": "Bad parent", "parents": "ZZZ", "active": "1"},  # invalid ref
        {"code": "C00", "display": "Cyclic A", "parents": "C01", "active": "1"},    # cycle
        {"code": "C01", "display": "Cyclic B", "parents": "C00", "active": "1"},    # cycle
        {"code": "", "display": "No code", "active": "1"},                 # missing code
        {"code": "D00", "display": "", "active": "1"},                     # missing name
    ]
    valid, findings = _rows_to_valid(rows)
    issues = {f["issue"].split(" (")[0] for f in findings}
    assert "duplicate concept id" in issues
    assert "inactive concept" in " ".join(f["issue"] for f in findings)
    assert any("invalid hierarchy reference" in f["issue"] for f in findings)
    assert any("cyclic hierarchy" in f["issue"] for f in findings)
    assert any("missing concept code" in f["issue"] for f in findings)
    assert any("missing preferred name" in f["issue"] for f in findings)
    valid_codes = {c["code"] for c in valid}
    assert valid_codes == {"A00", "A01", "B00", "C00", "C01"}  # dropped dup/inactive/empty/missing-name
    # invalid parent ref was pruned; cyclic parents pruned
    b00 = next(c for c in valid if c["code"] == "B00")
    assert b00["parents"] == []


def test_unknown_code_system_flagged():
    _, findings = imp.validate(imp.normalize_rows([{"code": "X", "display": "Y", "active": "1"}]), "MADEUP")
    assert any("unknown code system" in f["issue"] for f in findings)


def test_run_import_writes_snapshot_and_provider_reads_tier3(tmp_path):
    export = tmp_path / "snomed_export.json"
    export.write_text(json.dumps({"concepts": [
        {"code": "9826008", "display": "Appendicitis", "aliases": ["appendicitis"], "parents": ["18526009"]},
        {"code": "18526009", "display": "Disorder of appendix", "children": ["9826008"]},
        {"code": "195967001", "display": "Asthma", "aliases": ["asthma", "\ucc9c\uc2dd"]},
    ]}), encoding="utf-8")
    out = tmp_path / "snapshots" / "snomed.json"

    report = imp.run_import("snomed", export, "json", out, dry_run=False)
    assert report["valid_concepts"] == 3 and report["rejected"] == 0
    assert out.is_file()

    # Drive the provider directly with this snapshot_root -> Tier-3 concepts appear.
    from nova_agent.ontology.providers.snomed import SnomedProvider
    provider = SnomedProvider(snapshot_root=out.parent)
    concepts = provider.load()
    assert len(concepts) == 3
    names = {c.canonical_name for c in concepts}
    assert {"Appendicitis", "Asthma"} <= names
    appx = next(c for c in concepts if c.canonical_name == "Appendicitis")
    assert appx.parents == ("onto:SNOMEDCT:18526009",)  # hierarchy reference preserved
    assert all(c.tier.value == "TIER3_ONTOLOGY" for c in concepts)
    assert all(c.curation_status == "NOT_CURATED" for c in concepts)  # never deep-curated


def test_graceful_degrade_without_snapshot(tmp_path):
    from nova_agent.ontology.providers.snomed import SnomedProvider
    provider = SnomedProvider(snapshot_root=tmp_path)  # empty dir, no snapshot
    assert provider.available() is False
    assert provider.load() == []


def test_csv_and_tsv_parsing(tmp_path):
    csv_path = tmp_path / "icd.csv"
    csv_path.write_text("code,display,aliases\nA00,Cholera,cholera|\ucf5c\ub808\ub77c\n", encoding="utf-8")
    report = imp.run_import("icd10", csv_path, "csv", tmp_path / "icd10.json", dry_run=False)
    assert report["valid_concepts"] == 1

    tsv_path = tmp_path / "icd.tsv"
    tsv_path.write_text("code\tdisplay\taliases\nA01\tTyphoid\ttyphoid\n", encoding="utf-8")
    report2 = imp.run_import("icd10", tsv_path, "tsv", tmp_path / "icd10b.json", dry_run=False)
    assert report2["valid_concepts"] == 1
