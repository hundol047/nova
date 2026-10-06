"""`python scripts/audit_chief_complaint_coverage.py` -- systematic cross-reference of EVERY Tier-1
disease's own curated typical_features against nova_agent/chief_complaint.py's routing concepts, to
find common presentation vocabulary with no plausible routing entry at all.

This is a permanent, reusable audit tool (Round D's generalization-hardening mandate: "systematic
audit across all Tier-1 profiles," never inspecting only a handful of known-miss cases). Re-run it
after adding a new Tier-1 disease or changing chief_complaint.py's CONCEPT_PHRASES to catch a new
coverage gap before it becomes a routing failure in the field.

Method: for every Tier-1 disease's own `typical_features` phrase, run it through
chief_complaint.route(). A phrase that routes to NOTHING at all (match_type == "none") is flagged.
Not every flagged phrase is a real gap -- many typical_features are associated/exam findings (e.g.
"tachycardia", "rebound tenderness") that a patient would never say AS their presenting complaint,
so this script reports the full flagged list for human review rather than claiming every single one
needs a new routing tag. The `--known-gaps-only` flag filters to phrases this repo's own audit has
already judged genuine (see KNOWN_GENUINE_GAPS below, kept in sync with chief_complaint.py's own
"systematic Tier-1 typical_features audit" comment) so the script stays useful as a regression check
without re-triggering a full manual review every run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nova_agent.chief_complaint import route
from nova_agent.knowledge.retrieval import all_diseases

# Phrases this round's manual review judged to be genuine presenting-complaint vocabulary gaps
# (not exam/lab findings, not risk factors) -- each already fixed by either a new CONCEPT_PHRASES
# tag or a scoped alias extension. Kept here so a regression (e.g. an alias accidentally deleted)
# is caught automatically rather than requiring another full manual pass.
KNOWN_GENUINE_GAPS_NOW_FIXED = {
    ("viral_uri", "rhinorrhea"), ("viral_uri", "sore throat"),
    ("gastroenteritis", "diarrhea"),
    ("ischemic_stroke", "unilateral numbness"), ("ischemic_stroke", "sudden vision loss"),
    ("subarachnoid_hemorrhage", "neck stiffness"), ("meningitis", "neck stiffness"),
    ("pulmonary_embolism", "hemoptysis"),
    ("severe_electrolyte_disorder", "seizure"),
    ("asthma_copd_exacerbation", "wheeze"),
    ("anaphylaxis", "throat tightness"),
}


def audit() -> list[tuple[str, str]]:
    """Returns every (disease_id, typical_feature_phrase) pair that routes to NOTHING at all."""
    gaps = []
    for disease_id, entry in sorted(all_diseases().items()):
        for feature in entry.get("typical_features", []):
            result = route(feature)
            if result.match_type == "none":
                gaps.append((disease_id, feature))
    return gaps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--known-gaps-only", action="store_true",
                         help="Only report phrases this round's review already judged genuine (regression check).")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args()

    gaps = audit()
    if args.known_gaps_only:
        still_broken = [g for g in KNOWN_GENUINE_GAPS_NOW_FIXED if g not in set(gaps)]
        fixed_but_now_gapped = [g for g in gaps if g in KNOWN_GENUINE_GAPS_NOW_FIXED]
        if args.json:
            print(json.dumps({"regressed": fixed_but_now_gapped, "total_known_gaps": len(KNOWN_GENUINE_GAPS_NOW_FIXED)}))
        else:
            if fixed_but_now_gapped:
                print("REGRESSION: previously-fixed coverage gaps are unrouted again:")
                for did, feat in fixed_but_now_gapped:
                    print(f"  {did:30s} {feat!r}")
                raise SystemExit(1)
            print(f"OK: all {len(KNOWN_GENUINE_GAPS_NOW_FIXED)} previously-identified genuine gaps remain routed.")
        return

    diseases_total = len(all_diseases())
    if args.json:
        print(json.dumps({
            "diseases_scanned": diseases_total,
            "unrouted_phrase_count": len(gaps),
            "unrouted_phrases": [{"disease_id": d, "phrase": f} for d, f in gaps],
        }, indent=2))
    else:
        print(f"=== Chief-complaint coverage audit: {diseases_total} Tier-1 diseases ===\n")
        print(f"{len(gaps)} typical_feature phrase(s) route to NOTHING at all "
              f"(review each -- many are associated/exam findings, not presenting complaints):\n")
        for did, feat in gaps:
            already_known = " [KNOWN, reviewed]" if (did, feat) in KNOWN_GENUINE_GAPS_NOW_FIXED else ""
            print(f"  {did:30s} {feat!r}{already_known}")


if __name__ == "__main__":
    main()
