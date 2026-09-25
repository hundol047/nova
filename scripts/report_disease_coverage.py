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


def collect(catalog) -> dict:
    by_category: dict = {}
    coded = 0
    dup_ids: dict = {}
    for c in catalog.all_concepts():
        by_category[c.category or "uncategorized"] = by_category.get(c.category or "uncategorized", 0) + 1
        if c.external_codes:
            coded += 1
        dup_ids[c.concept_id] = dup_ids.get(c.concept_id, 0) + 1
    duplicates = {k: v for k, v in dup_ids.items() if v > 1}
    snapshots_dir = _ROOT / "nova_agent" / "ontology" / "snapshots"
    snapshot_files = sorted(p.name for p in snapshots_dir.glob("*.json")) if snapshots_dir.is_dir() else []
    return {
        "total_concepts": len(catalog),
        "by_tier": catalog.counts_by_tier(),
        "by_curation": catalog.counts_by_curation(),
        "by_category": dict(sorted(by_category.items())),
        "with_external_code": coded,
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
    print("=" * 40)
    print(f"Total concepts in catalog : {report['total_concepts']}")
    print()
    print("By tier:")
    for tier, n in report["by_tier"].items():
        print(f"  {tier:18s} {n}")
    print()
    print("By curation status:")
    for status, n in sorted(report["by_curation"].items()):
        print(f"  {status:18s} {n}")
    print()
    print("By category:")
    for cat, n in report["by_category"].items():
        print(f"  {cat:26s} {n}")
    print()
    print(f"Concepts with an external code : {report['with_external_code']}")
    snaps = report["terminology_snapshots_present"]
    print(f"Terminology snapshots present  : {snaps if snaps else 'NONE (Tier-3 empty; license-safe)'}")
    if report["duplicate_concept_ids"]:
        print()
        print("WARNING duplicate concept ids:")
        for cid, n in report["duplicate_concept_ids"].items():
            print(f"  {cid} x{n}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
