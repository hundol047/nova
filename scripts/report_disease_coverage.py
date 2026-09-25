#!/usr/bin/env python3
"""Report N.O.V.A. disease-universe coverage across tiers (dependency-free).

Prints an honest breakdown of the DiseaseCatalog: counts by tier, by curation status, by category,
number of concepts carrying an external code, and whether any terminology snapshots are present.
This is the number we cite in docs/ontology/DISEASE_COVERAGE.md — we report what is ACTUALLY in the
catalog, never an aspirational figure.

Usage:
  python scripts/report_disease_coverage.py           # human-readable
  python scripts/report_disease_coverage.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
import types
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _load_catalog():
    # Bypass the pydantic-heavy nova_agent package __init__ so this runs without app deps.
    if "nova_agent" not in sys.modules:
        pkg = types.ModuleType("nova_agent")
        pkg.__path__ = [str(_ROOT / "nova_agent")]
        sys.modules["nova_agent"] = pkg
    from nova_agent.ontology import registry
    return registry.build_catalog()


# Bundled coverage target (Tier-1 + Tier-2). Tier-3 (operator terminology snapshot) is additive
# and not required to meet this.
COVERAGE_TARGET = 500              # bundled (Tier-1 + Tier-2) minimum
SEARCHABLE_TARGET = 5000           # total searchable (all tiers, incl. Tier-3 snapshot)


def collect(catalog) -> dict:
    by_category: dict = {}
    coded = 0
    dangerous = 0
    not_curated = 0
    rare = 0
    dup_ids: dict = {}
    bundled = 0  # Tier-1 + Tier-2 (excludes Tier-3 ontology-only)
    for c in catalog.all_concepts():
        by_category[c.category or "uncategorized"] = by_category.get(c.category or "uncategorized", 0) + 1
        if c.external_codes:
            coded += 1
        if c.dangerous:
            dangerous += 1
        if c.curation_status == "NOT_CURATED":
            not_curated += 1
        if c.tier.value in ("TIER1_DEEP", "TIER2_STRUCTURED"):
            bundled += 1
        # "rare" heuristic: Tier-3 ontology-only concepts are the long tail; also count any concept
        # explicitly categorized rare. Reported honestly as a heuristic, not a curated rarity flag.
        if c.tier.value == "TIER3_ONTOLOGY" or (c.category or "") == "rare":
            rare += 1
        dup_ids[c.concept_id] = dup_ids.get(c.concept_id, 0) + 1
    duplicates = {k: v for k, v in dup_ids.items() if v > 1}
    total = len(catalog)
    by_tier = catalog.counts_by_tier()
    snapshots_dir = _ROOT / "nova_agent" / "ontology" / "snapshots"
    snapshot_files = sorted(p.name for p in snapshots_dir.glob("*.json")) if snapshots_dir.is_dir() else []
    return {
        "tier1_count": by_tier.get("TIER1_DEEP", 0),
        "tier2_count": by_tier.get("TIER2_STRUCTURED", 0),
        "tier3_count": by_tier.get("TIER3_ONTOLOGY", 0),
        "total_concepts": total,
        "total_searchable": total,          # every concept in the catalog is searchable
        "bundled_concepts": bundled,        # Tier-1 + Tier-2 (ships without a snapshot)
        "coverage_target": COVERAGE_TARGET,
        "coverage_target_met": bundled >= COVERAGE_TARGET,
        "searchable_target": SEARCHABLE_TARGET,
        "searchable_target_met": total >= SEARCHABLE_TARGET,
        "by_tier": by_tier,
        "by_curation": catalog.counts_by_curation(),
        "by_category": dict(sorted(by_category.items())),
        "category_count": len(by_category),
        "dangerous_concepts": dangerous,
        "rare_count": rare,
        "mapped_count": coded,
        "unmapped_count": total - coded,
        "with_external_code": coded,
        "without_external_code": total - coded,
        "not_curated_concepts": not_curated,
        "duplicate_count": len(duplicates),
        "duplicate_concept_ids": duplicates,
        "terminology_snapshots_present": snapshot_files,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    catalog = _load_catalog()
    report = collect(catalog)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("N.O.V.A. Disease Coverage Report")
    print("=" * 44)
    print(f"Total searchable concepts : {report['total_searchable']}")
    print(f"  Tier-1 deep             : {report['tier1_count']}")
    print(f"  Tier-2 structured       : {report['tier2_count']}")
    print(f"  Tier-3 ontology-only    : {report['tier3_count']}")
    print(f"Bundled (Tier-1 + Tier-2) : {report['bundled_concepts']}")
    met = "YES" if report["coverage_target_met"] else "NO"
    smet = "YES" if report["searchable_target_met"] else "NO"
    print(f"Bundled target (>= {report['coverage_target']})   : {met} "
          f"(coverage_target_met={str(report['coverage_target_met']).lower()})")
    print(f"Searchable target (>= {report['searchable_target']}): {smet} "
          f"(searchable_target_met={str(report['searchable_target_met']).lower()})")
    print()
    print("By tier:")
    for tier, n in report["by_tier"].items():
        print(f"  {tier:18s} {n}")
    print()
    print("By curation status:")
    for status, n in sorted(report["by_curation"].items()):
        print(f"  {status:18s} {n}")
    print()
    print(f"Categories                     : {report['category_count']}")
    for cat, n in report["by_category"].items():
        print(f"  {cat:26s} {n}")
    print()
    print(f"Dangerous concepts             : {report['dangerous_concepts']}")
    print(f"Rare / long-tail (heuristic)   : {report['rare_count']}")
    print(f"Mapped (has external code)     : {report['mapped_count']}")
    print(f"Unmapped (no external code)    : {report['unmapped_count']}")
    print(f"NOT_CURATED concepts           : {report['not_curated_concepts']}")
    print(f"Duplicate concept ids          : {report['duplicate_count']}")
    snaps = report["terminology_snapshots_present"]
    print(f"Terminology snapshots present  : {snaps if snaps else 'NONE (Tier-3 empty; license-safe)'}")
    if report["duplicate_concept_ids"]:
        print()
        print("WARNING duplicate concept ids:")
        for cid, n in report["duplicate_concept_ids"].items():
            print(f"  {cid} x{n}")
        return 1
    if not report["coverage_target_met"]:
        print()
        print(f"WARNING coverage_target_met=false (bundled {report['bundled_concepts']} < {report['coverage_target']})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
