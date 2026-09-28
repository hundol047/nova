"""Structural integrity checks for the frozen Blind v13 set -- mirrors the same checks every prior
blind set's own test coverage has relied on (hash-freeze guard, ground-truth id validity, no
accidental duplicate case ids). Never asserts on Blind v13's actual diagnostic RESULTS (those are
recorded once, honestly, in the verification artifact -- never re-tuned against here)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.blind_cases_v13 import BLIND_CASES_V13
from evaluation.current_blind import ALL_BLIND_VERSIONS, CURRENT_BLIND_VERSION
from nova_agent.knowledge.retrieval import disease_by_id
from nova_agent.ontology.registry import get_default_catalog

_ROOT = Path(__file__).resolve().parents[1]


def test_v13_is_now_reference_only():
    # Blind v14 (Round D) superseded v13 as CURRENT_BLIND_VERSION -- v13 remains a known, frozen,
    # still-scanned set (its own file/hash/content below are all still checked), but is no longer
    # the untouched measure of the current code. Mirrors how v12 became reference-only when v13
    # itself was frozen.
    assert CURRENT_BLIND_VERSION != "v13"
    assert "v13" in ALL_BLIND_VERSIONS
    assert "v12" in ALL_BLIND_VERSIONS  # reference-only, still known


def test_blind_v13_file_matches_its_frozen_manifest_hash():
    case_file = _ROOT / "evaluation" / "blind_cases_v13.py"
    manifest = json.loads((_ROOT / "evaluation" / "blind_v13_manifest.json").read_text())
    actual = hashlib.sha256(case_file.read_bytes()).hexdigest()
    assert actual == manifest["file_sha256"], (
        "blind_cases_v13.py was edited after its freeze -- this must never happen post-freeze"
    )
    assert manifest["case_count"] == len(BLIND_CASES_V13)


def test_blind_v13_case_ids_are_unique():
    ids = [c.case_id for c in BLIND_CASES_V13]
    assert len(ids) == len(set(ids))


def test_blind_v13_ground_truth_ids_are_all_real():
    catalog = get_default_catalog()
    for case in BLIND_CASES_V13:
        gt = case.ground_truth_diagnosis
        if gt == "unknown":
            continue
        if gt.startswith("tier2:"):
            assert catalog.get_condition(gt) is not None, f"{case.case_id}: {gt!r} not in the real ontology catalog"
        else:
            assert disease_by_id(gt) is not None, f"{case.case_id}: {gt!r} not a real Tier-1 KB id"


def test_blind_v13_has_at_least_the_target_case_count():
    assert len(BLIND_CASES_V13) >= 50


def test_blind_v13_covers_a_broad_category_spread():
    categories = {c.category for c in BLIND_CASES_V13}
    required = {"common", "critical", "dangerous_mimic", "benign_mimic", "long_tail", "unknown_ood",
                "over_testing_trap", "premature_diagnosis_trap"}
    assert required.issubset(categories)
