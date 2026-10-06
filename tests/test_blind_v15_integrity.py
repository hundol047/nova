"""Structural integrity checks for the frozen Blind v15 set -- mirrors the same checks every prior
blind set's own test coverage has relied on (hash-freeze guard, ground-truth id validity, no
accidental duplicate case ids). Never asserts on Blind v15's actual diagnostic RESULTS (those are
recorded once, honestly, in the verification artifact -- never re-tuned against here)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.blind_cases_v15 import BLIND_CASES_V15
from evaluation.current_blind import ALL_BLIND_VERSIONS, CURRENT_BLIND_VERSION
from nova_agent.knowledge.retrieval import all_diseases, disease_by_id
from nova_agent.ontology.registry import get_default_catalog

_ROOT = Path(__file__).resolve().parents[1]


def test_v15_is_now_reference_only():
    # Blind v16 (Round F) superseded v15 as CURRENT_BLIND_VERSION -- v15 stays a known, frozen,
    # still-scanned set (hash/content checks below still run) but is no longer the untouched measure.
    assert CURRENT_BLIND_VERSION != "v15"
    assert "v15" in ALL_BLIND_VERSIONS
    assert "v14" in ALL_BLIND_VERSIONS  # reference-only, still known


def test_blind_v15_file_matches_its_frozen_manifest_hash():
    case_file = _ROOT / "evaluation" / "blind_cases_v15.py"
    manifest = json.loads((_ROOT / "evaluation" / "blind_v15_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    assert actual == manifest["file_sha256"], (
        "blind_cases_v15.py was edited after its freeze -- this must never happen post-freeze"
    )
    assert manifest["case_count"] == len(BLIND_CASES_V15)


def test_blind_v15_case_ids_are_unique():
    ids = [c.case_id for c in BLIND_CASES_V15]
    assert len(ids) == len(set(ids))


def test_blind_v15_ground_truth_ids_are_all_real():
    catalog = get_default_catalog()
    for case in BLIND_CASES_V15:
        gt = case.ground_truth_diagnosis
        if gt == "unknown":
            continue
        if gt.startswith("tier2:"):
            assert catalog.get_condition(gt) is not None, f"{case.case_id}: {gt!r} not in the real ontology catalog"
        else:
            assert disease_by_id(gt) is not None, f"{case.case_id}: {gt!r} not a real Tier-1 KB id"


def test_blind_v15_has_at_least_the_target_case_count():
    assert len(BLIND_CASES_V15) >= 60


def test_blind_v15_covers_a_broad_category_spread():
    categories = {c.category for c in BLIND_CASES_V15}
    required = {"common", "critical", "dangerous_mimic", "benign_mimic", "long_tail", "unknown_ood",
                "over_testing_trap", "premature_diagnosis_trap",
                "specific_vs_generic_severity_conflict", "fuzzy_phrase_collision_trap",
                "reproductive_age_emergency", "multilingual_korean", "multilingual_japanese",
                "mixed_language", "routing_trap", "late_diagnosis_trap"}
    assert required.issubset(categories)


def test_blind_v15_covers_every_tier1_diagnosis():
    # Every one of the 34 Tier-1 knowledge/diseases ids is touched at least once (not merely a
    # representative subset) -- same coverage discipline v14 established.
    used = {c.ground_truth_diagnosis for c in BLIND_CASES_V15
            if not c.ground_truth_diagnosis.startswith("tier2:") and c.ground_truth_diagnosis != "unknown"}
    assert used == set(all_diseases().keys())


def test_blind_v15_no_reasoning_files_changed_since_its_freeze_commit():
    # The manifest records the exact commit v15 was frozen against (FINAL_REASONING_SHA) -- this
    # doesn't re-check git history (out of scope for a unit test), but does assert the manifest's
    # own self-reported freeze commit is present and well-formed, so a future edit can't silently
    # blank it out.
    manifest = json.loads((_ROOT / "evaluation" / "blind_v15_manifest.json").read_text())
    created_commit = manifest["created_commit"]
    assert len(created_commit) == 40
    assert all(ch in "0123456789abcdef" for ch in created_commit)
