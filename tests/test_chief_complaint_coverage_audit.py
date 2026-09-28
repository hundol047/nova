"""Pytest wrapper around scripts/audit_chief_complaint_coverage.py's systematic Tier-1
typical_features audit (Round D). Keeps the coverage-gap regression check inside the normal test
suite (not only reachable via a standalone script invocation) so `pytest` alone catches a routing
regression -- e.g. an alias accidentally deleted -- without a separate manual script run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_chief_complaint_coverage import KNOWN_GENUINE_GAPS_NOW_FIXED, audit


def test_all_previously_identified_genuine_coverage_gaps_remain_routed():
    gaps_now = set(audit())
    # A previously-fixed gap has REGRESSED if it is a current gap again (present in `gaps_now`) --
    # not merely "absent from the known-fixed list", which every genuinely-still-fixed gap already
    # satisfies trivially.
    regressed = [g for g in KNOWN_GENUINE_GAPS_NOW_FIXED if g in gaps_now]
    assert not regressed, f"previously-fixed coverage gap(s) regressed: {regressed}"


def test_known_genuine_gaps_list_is_non_trivial():
    # Sanity: the regression list itself must not have silently become empty (which would make
    # the test above vacuously pass forever).
    assert len(KNOWN_GENUINE_GAPS_NOW_FIXED) >= 10
