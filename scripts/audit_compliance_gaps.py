"""Read-only evidence coverage audit; incomplete records can never yield clearance."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(root=ROOT):
    sources = json.loads((root / "artifacts/round_m/source_inventory.json").read_text())
    generations = json.loads((root / "artifacts/round_m/generation_inventory.json").read_text())
    indexed = {row["file"]: row for row in sources}
    runtime = {str(p.relative_to(root)) for p in (root / "nova_agent").rglob("*.py")}
    runtime |= {str(p.relative_to(root)) for p in (root / "nova_agent/knowledge").rglob("*.json")}
    changed = [name for name in sorted(runtime & indexed.keys())
               if hashlib.sha256((root / name).read_bytes()).hexdigest() != indexed[name]["sha256"]]
    generated = {row["output_file"] for row in generations}
    required = {name for name in runtime if name.endswith(".json")}
    required |= {"nova_agent/lay_language.py", "nova_agent/multilingual_concepts.py"}
    unresolved = [row["file"] for row in sources
                  if row.get("research_publication_use_allowed") is not True
                  or row.get("license") in (None, "", "UNRESOLVED")
                  or "UNRESOLVED" in row.get("original_source", "UNRESOLVED")]
    return {
        "scope": "nova_agent source inventory; dependency terms documented separately",
        "status": "NOT CLEARED" if unresolved or changed or runtime - indexed.keys() or required - generated else "REQUIRES HUMAN REVIEW",
        "official_submission_allowed": False,
        "runtime_inventory_count": len(runtime),
        "missing_source_inventory": sorted(runtime - indexed.keys()),
        "stale_source_hashes": changed,
        "missing_generation_records": sorted(required - generated),
        "unresolved_source_or_license": unresolved,
        "required_resolution": [
            "Recover original authorship, source versions, license text and research-publication permission.",
            "Recover original model/version, prompts, generation code and output records; do not reconstruct fictitious receipts.",
            "Replace or remove assets that cannot be cleared, then obtain clinical review and rerun development regressions.",
            "Integrate supplied participant guide, organizer fixed-model transport and exact schema; no guessed endpoints.",
        ],
    }


if __name__ == "__main__":
    result = audit()
    target = ROOT / "artifacts/compliance_repair/provenance_gaps.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "unresolved_source_or_license"}, indent=2))
