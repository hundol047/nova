"""Reproducible publisher excerpts for review, deliberately not runtime promotion.

An introductory paragraph cannot replace a diagnostic interpretation safely.
This script records that gap instead of laundering a citation into approval.
"""
import hashlib
import json
from pathlib import Path
import re

from scripts.import_licensed_references import plain

ROOT = Path(__file__).resolve().parents[1]


def main():
    snapshot_path = ROOT / "research/licensed_references/source_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    catalog = json.loads((ROOT / "nova_agent/knowledge/licensed_references.json").read_text())
    notes_path = ROOT / "nova_agent/knowledge/diagnostic_tests/notes.json"
    old = {r["test_id"]: r["note"] for r in json.loads(notes_path.read_text())}
    rows = []
    for source in snapshot["records"]:
        if source["kind"] != "test_reference":
            continue
        paragraph = re.search(r"<p\b[^>]*>.*?</p>", source["original_markup"], re.S | re.I)
        assert paragraph, source["test_id"]
        rows.append({
            "test_id": source["test_id"], "original_note": old[source["test_id"]],
            "original_provenance": "UNRESOLVED",
            "candidate_background_note": plain(paragraph.group(0)),
            "source_url": source["source_url"],
            "source_metadata": catalog["sources"][source["source"]],
            "source_markup_sha256": hashlib.sha256(source["original_markup"].encode()).hexdigest(),
            "transformation": "First complete p element; HTML removed with retained plain() function. No paraphrase or AI clinical generation.",
            "generation_code": "scripts/prepare_test_note_replacements.py",
            "generation_date": "2026-10-05",
            "clinical_generation_model": "NOT_APPLICABLE_DETERMINISTIC_EXTRACTION",
            "source_rights_scope": "NLM medical-test prose only; excludes third-party content and images",
            "manual_clinical_review": "PENDING", "clinician_review": "PENDING",
            "promotion": "BLOCKED_PENDING_SCOPE_AND_SAFETY_REVIEW",
            "reason": "Test-purpose background is not equivalent to the original indications, exclusions, thresholds or safety caveats. Do not silently remove those clinical distinctions.",
            "submission_included_as_replacement": False,
        })
    out = ROOT / "docs/clinical_review/TEST_NOTE_REPLACEMENT_CANDIDATES.json"
    out.write_text(json.dumps({
        "source_snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "original_notes_sha256": hashlib.sha256(notes_path.read_bytes()).hexdigest(),
        "runtime_modified": False, "candidates": rows,
    }, ensure_ascii=False, indent=2) + "\n")
    print(f"Prepared {len(rows)} candidates; zero promoted without clinical review")


if __name__ == "__main__":
    main()
