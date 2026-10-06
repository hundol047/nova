"""Validate evidence coverage/hashes; optionally fail if permission clearance is incomplete.

This cannot establish legal rights or medical correctness from a JSON status string.
No clinical content is generated, replaced, removed or promoted by this command.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = set("asset_id path sha256 runtime_use original_author original_source source_reference source_version license research_publication_permission redistribution_permission modification_permission generation_method generating_model model_version generation_prompt generation_code generation_date manual_review clinician_review submission_included status".split())
STATUSES = {"VERIFIED", "TEAM_ORIGINAL_VERIFIED", "UNRESOLVED", "REPLACEMENT_REQUIRED", "NOT_USED_IN_SUBMISSION"}


def validate(root=ROOT):
    inventory = json.loads((root / "artifacts/compliance_hardening/clinical_asset_inventory.json").read_text())
    errors, blocked, paths = [], [], set()
    for asset in inventory["assets"]:
        name = asset.get("path", "")
        if FIELDS - asset.keys(): errors.append({"path": name, "error": "missing fields"})
        if asset.get("status") not in STATUSES: errors.append({"path": name, "error": "invalid status"})
        if name in paths: errors.append({"path": name, "error": "duplicate path"})
        paths.add(name)
        if asset.get("submission_included"):
            p = root / name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != asset.get("sha256"):
                errors.append({"path": name, "error": "missing or stale bytes"})
            if asset.get("status") not in {"VERIFIED", "TEAM_ORIGINAL_VERIFIED"}:
                blocked.append(name)
            else:
                # Rights/authorship evidence must be supplied for manual assessment; a label
                # alone cannot manufacture clearance or make clinical review unnecessary.
                for key in ("original_author", "license", "research_publication_permission", "redistribution_permission", "modification_permission"):
                    if asset.get(key) in (None, "", "UNRESOLVED"):
                        errors.append({"path": name, "error": "unsubstantiated clearance: " + key})
    actual = {str(p.relative_to(root)) for p in (root / "nova_agent").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".json", ".md"}}
    for missing in sorted(actual - paths): errors.append({"path": missing, "error": "not inventoried"})
    return {"coverage_status": "FAIL" if errors else "PASS", "errors": errors,
            "permission_status": "BLOCKED" if errors or blocked else "NOT_VERIFIED",
            "unresolved_assets": blocked, "official_submission_allowed": False,
            "note": "Manual rights/authorship review required; no automatic legal or medical certification."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-cleared", action="store_true")
    args = parser.parse_args()
    result = validate()
    path = ROOT / "artifacts/compliance_hardening/provenance_validation.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "unresolved_assets"}, indent=2))
    if result["errors"] or args.require_cleared: raise SystemExit(2)
