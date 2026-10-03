#!/usr/bin/env python3
"""Operator-side terminology import CLI (vNext PART B, dependency-free).

Turns an operator-provided, LICENSED terminology export (SNOMED CT / ICD-11 / ICD-10) into the
minimal, provider-compatible snapshot the ontology Tier-3 layer reads
(nova_agent/ontology/snapshots/<system>.json). The repository ships NO terminology content; this
tool only transforms an export the operator already holds under their own licence.

Supported input formats (--format, or inferred from extension):
  - json : {"concepts":[{"code","display","aliases","parents","children","active","semantic_type"}]}
           (or a bare list of such objects)
  - csv  : header row; columns code,display[,aliases,parents,children,active,semantic_type]
  - tsv  : same as csv but tab-delimited
  - rf2  : a NORMALIZED RF2-derived export (NOT raw RF2 release files) with the same columns as csv;
           multi-value cells (aliases/parents/children) use '|' as the separator. We deliberately do
           not parse the full raw SNOMED RF2 release format here — the operator normalizes it first
           (documented in docs/ontology/TERMINOLOGY_PROVENANCE.md), keeping this tool small and the
           repo free of any SNOMED-specific parsing assumptions.

Validation (reported; invalid rows are dropped, not silently kept):
  duplicate concept id, missing preferred name, inactive concept, invalid hierarchy reference
  (parent/child id not in the file), unknown code system, malformed synonym, cyclic hierarchy.

Usage:
  python scripts/import_terminology.py --source snomed --input EXPORT --output nova_agent/ontology/snapshots/snomed.json
  python scripts/import_terminology.py --source icd10 --input EXPORT.csv --format csv
  python scripts/import_terminology.py --source icd11 --input EXPORT.json --dry-run --report report.json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# source -> (canonical system id, default snapshot filename). This is the ONLY place code systems
# are recognized; anything else is an "unknown code system".
SOURCE_TO_SYSTEM: Dict[str, Tuple[str, str]] = {
    "snomed": ("SNOMEDCT", "snomed.json"),
    "snomedct": ("SNOMEDCT", "snomed.json"),
    "icd11": ("ICD11", "icd11.json"),
    "icd10": ("ICD10", "icd10.json"),
    "icd10cm": ("ICD10", "icd10.json"),
    # A hospital's own local code map (e.g. an internal problem-list vocabulary mapped to canonical
    # concepts). Local-only, operator-supplied; never fetched from an external API.
    "custom": ("CUSTOM", "custom.json"),
    "hospital": ("CUSTOM", "custom.json"),
}

_SNAPSHOT_ROOT = Path(__file__).resolve().parent.parent / "nova_agent" / "ontology" / "snapshots"
_MULTI_SEP = "|"


class ImportError_(Exception):
    pass


def _split_multi(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(_MULTI_SEP) if p.strip()]


def _truthy_active(value) -> bool:
    """Default active=True when the field is absent; explicit 0/false/inactive => inactive."""
    if value is None or value == "":
        return True
    s = str(value).strip().lower()
    return s not in ("0", "false", "no", "inactive", "n")


def _read_rows(input_path: Path, fmt: str) -> List[dict]:
    text = input_path.read_text(encoding="utf-8")
    if fmt == "json":
        data = json.loads(text)
        rows = data.get("concepts", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ImportError_("json input must be a list of concepts or {'concepts': [...]}")
        return [dict(r) for r in rows]
    delimiter = "\t" if fmt in ("tsv", "rf2") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if reader.fieldnames is None or "code" not in reader.fieldnames or "display" not in reader.fieldnames:
        raise ImportError_(f"{fmt} input must have a header with at least 'code' and 'display' columns")
    return [dict(r) for r in reader]


def normalize_rows(rows: List[dict]) -> List[dict]:
    """Coerce heterogeneous input rows into the common concept shape."""
    out = []
    for r in rows:
        out.append({
            "code": str(r.get("code", "")).strip(),
            "display": str(r.get("display") or r.get("preferred_name") or r.get("name") or "").strip(),
            "aliases": _split_multi(r.get("aliases") or r.get("synonyms")),
            "parents": _split_multi(r.get("parents") or r.get("parent")),
            "children": _split_multi(r.get("children") or r.get("child")),
            "active": _truthy_active(r.get("active")),
            "semantic_type": (str(r.get("semantic_type") or "DISEASE").strip().upper() or "DISEASE"),
        })
    return out


def validate(concepts: List[dict], system: str) -> Tuple[List[dict], List[dict]]:
    """Return (valid_concepts, findings). Invalid rows are excluded from valid_concepts.

    Findings each carry {code, issue}. Detected: unknown code system, duplicate id, missing name,
    inactive, malformed synonym, invalid hierarchy reference, cyclic hierarchy."""
    findings: List[dict] = []
    if system not in {v[0] for v in SOURCE_TO_SYSTEM.values()}:
        findings.append({"code": "*", "issue": f"unknown code system: {system}"})

    seen: set = set()
    by_code: Dict[str, dict] = {}
    kept: List[dict] = []
    for c in concepts:
        code = c["code"]
        if not code:
            findings.append({"code": "(empty)", "issue": "missing concept code"})
            continue
        if not c["display"]:
            findings.append({"code": code, "issue": "missing preferred name"})
            continue
        if code in seen:
            findings.append({"code": code, "issue": "duplicate concept id"})
            continue
        if not c["active"]:
            findings.append({"code": code, "issue": "inactive concept (dropped)"})
            continue
        malformed = [a for a in c["aliases"] if not isinstance(a, str) or not a.strip()]
        if malformed:
            findings.append({"code": code, "issue": "malformed synonym"})
            c["aliases"] = [a for a in c["aliases"] if isinstance(a, str) and a.strip()]
        seen.add(code)
        by_code[code] = c
        kept.append(c)

    # Hierarchy validation over the kept set: parent/child references must exist, no self-loop.
    valid_ids = set(by_code)
    for c in kept:
        for pid in list(c["parents"]):
            if pid == c["code"]:
                findings.append({"code": c["code"], "issue": "self-referential parent (dropped)"})
                c["parents"].remove(pid)
            elif pid not in valid_ids:
                findings.append({"code": c["code"], "issue": f"invalid hierarchy reference (parent {pid})"})
                c["parents"].remove(pid)
        for cid in list(c["children"]):
            if cid == c["code"]:
                findings.append({"code": c["code"], "issue": "self-referential child (dropped)"})
                c["children"].remove(cid)
            elif cid not in valid_ids:
                findings.append({"code": c["code"], "issue": f"invalid hierarchy reference (child {cid})"})
                c["children"].remove(cid)

    # Cycle detection over the parent graph (after cleaning invalid refs).
    parent_map = {c["code"]: list(c["parents"]) for c in kept}
    cyclic = _find_cyclic_nodes(parent_map)
    if cyclic:
        for code in sorted(cyclic):
            findings.append({"code": code, "issue": "cyclic hierarchy (parents pruned)"})
            by_code[code]["parents"] = []

    return kept, findings


def _find_cyclic_nodes(parent_map: Dict[str, List[str]]) -> set:
    """Return the set of nodes involved in any parent-graph cycle (DFS with coloring)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in parent_map}
    cyclic: set = set()

    def dfs(node: str, stack: List[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for parent in parent_map.get(node, []):
            if parent not in color:
                continue
            if color[parent] == GRAY:
                # cycle: mark every node from the recurrence point onward
                if parent in stack:
                    cyclic.update(stack[stack.index(parent):])
            elif color[parent] == WHITE:
                dfs(parent, stack)
        stack.pop()
        color[node] = BLACK

    for n in parent_map:
        if color[n] == WHITE:
            dfs(n, [])
    return cyclic


def to_snapshot(concepts: List[dict], system: str) -> dict:
    return {
        "system": system,
        "provenance": ("Operator-provided terminology export imported via "
                       "scripts/import_terminology.py. The repository ships no terminology content."),
        "count": len(concepts),
        "concepts": [
            {
                "code": c["code"],
                "display": c["display"],
                "aliases": c["aliases"],
                "parents": c["parents"],
                "children": c["children"],
                "semantic_type": c["semantic_type"],
            }
            for c in concepts
        ],
    }


def run_import(source: str, input_path: Path, fmt: Optional[str],
               output_path: Optional[Path], dry_run: bool) -> dict:
    src_key = source.strip().lower()
    if src_key not in SOURCE_TO_SYSTEM:
        raise ImportError_(f"unknown --source '{source}'. Known: {sorted(SOURCE_TO_SYSTEM)}")
    system, default_name = SOURCE_TO_SYSTEM[src_key]

    if fmt is None:
        ext = input_path.suffix.lower().lstrip(".")
        fmt = {"json": "json", "csv": "csv", "tsv": "tsv", "txt": "tsv", "rf2": "rf2"}.get(ext, "json")
    fmt = fmt.lower()
    if fmt not in ("json", "csv", "tsv", "rf2"):
        raise ImportError_(f"unsupported --format '{fmt}'")

    rows = _read_rows(input_path, fmt)
    concepts = normalize_rows(rows)
    valid, findings = validate(concepts, system)
    snapshot = to_snapshot(valid, system)

    out = output_path or (_SNAPSHOT_ROOT / default_name)
    if not dry_run:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "source": src_key,
        "system": system,
        "format": fmt,
        "input_rows": len(rows),
        "valid_concepts": len(valid),
        "rejected": len(rows) - len(valid),
        "findings": findings,
        "output": None if dry_run else str(out),
        "dry_run": dry_run,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Import a licensed terminology export into a Tier-3 snapshot.")
    ap.add_argument("--source", required=True, help="snomed | icd11 | icd10")
    ap.add_argument("--input", required=True, help="path to the operator's export")
    ap.add_argument("--format", default=None, help="json | csv | tsv | rf2 (inferred from extension if omitted)")
    ap.add_argument("--output", default=None, help="snapshot output path (default: snapshots/<system>.json)")
    ap.add_argument("--report", default=None, help="write the import report JSON here")
    ap.add_argument("--dry-run", action="store_true", help="validate + report without writing the snapshot")
    args = ap.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ERROR: input not found: {input_path}", file=sys.stderr)
        return 2
    try:
        report = run_import(args.source, input_path,
                            args.format, Path(args.output) if args.output else None, args.dry_run)
    except (ImportError_, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"terminology import [{report['system']}] format={report['format']}")
    print(f"  input rows      : {report['input_rows']}")
    print(f"  valid concepts  : {report['valid_concepts']}")
    print(f"  rejected        : {report['rejected']}")
    if report["findings"]:
        print(f"  findings ({len(report['findings'])}):")
        for f in report["findings"][:50]:
            print(f"    - {f['code']}: {f['issue']}")
        if len(report["findings"]) > 50:
            print(f"    ... and {len(report['findings']) - 50} more")
    print(f"  output          : {report['output'] or '(dry-run, not written)'}")

    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
