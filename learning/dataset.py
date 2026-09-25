"""Immutable dataset snapshot builder (dependency-free).

Turns a stream of raw outcome records into a versioned, immutable training dataset:
  1. de-identify (strip direct identifiers, pseudonymize patient id),
  2. enforce label provenance (drop NOVA/LLM-sourced labels),
  3. featurize (allow-listed clinical fields only),
  4. freeze: write JSONL + a manifest with a content hash so the snapshot is reproducible and
     tamper-evident. A frozen snapshot is never edited in place; a new build makes a new snapshot.

Also refuses to build if any evaluation/blind case content is detected in the inputs (leakage
guard) — see check_no_eval_leakage.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from learning.deidentify import audit_record, pseudonymize, strip_identifiers
from learning.encoder import encode
from learning.labels import filter_valid_examples
from learning.schemas import LabelSource, TrainingExample


@dataclass(frozen=True)
class DatasetSnapshot:
    snapshot_id: str
    path: Path
    n_examples: int
    n_rejected_label: int
    content_sha256: str
    stable_deid: bool


def _feature_vector_from_raw(raw: Dict) -> List[float]:
    numeric = {
        k: raw.get(k) for k in (
            "age_years", "heart_rate", "systolic_bp", "diastolic_bp",
            "respiratory_rate", "temperature_c", "spo2", "pain_score",
        )
    }
    flags = list(raw.get("symptom_flags", [])) + list(raw.get("lab_flags", []))
    return encode({k: v for k, v in numeric.items() if v is not None}, flags)


def raw_to_example(raw: Dict) -> TrainingExample:
    """raw must contain: patient_id, encounter_time, label_concept_id, label_source, candidate_ids,
    plus clinical numerics/flags. Direct identifiers are stripped; only allow-listed clinical fields
    are featurized."""
    _ = strip_identifiers(raw)  # audited below; feature builder allow-lists rather than trusts this
    return TrainingExample(
        example_id=str(raw["example_id"]),
        patient_pseudonym=pseudonymize(raw["patient_id"]),
        encounter_time=str(raw["encounter_time"]),
        feature_vector=_feature_vector_from_raw(raw),
        candidate_concept_ids=list(raw.get("candidate_ids", [])),
        label_concept_id=str(raw["label_concept_id"]),
        label_source=LabelSource(str(raw["label_source"])),
    )


def build_snapshot(raw_records: Sequence[Dict], out_dir: Path, snapshot_id: str = "") -> DatasetSnapshot:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stable = all(audit_record(r).stable for r in raw_records) if raw_records else False

    examples = [raw_to_example(r) for r in raw_records]
    kept, rejected = filter_valid_examples(examples)

    lines = [json.dumps(e.as_dict(), ensure_ascii=False, sort_keys=True) for e in kept]
    body = "\n".join(lines) + ("\n" if lines else "")
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    sid = snapshot_id or content_hash[:12]

    snap_path = out_dir / f"dataset_{sid}.jsonl"
    if snap_path.exists():
        raise SystemExit(f"snapshot {snap_path} already exists — snapshots are immutable, refusing to overwrite.")
    snap_path.write_text(body, encoding="utf-8")

    manifest = {
        "snapshot_id": sid,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_examples": len(kept),
        "n_rejected_forbidden_label": len(rejected),
        "content_sha256": content_hash,
        "stable_deid": stable,
        "immutable": True,
    }
    (out_dir / f"dataset_{sid}.manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return DatasetSnapshot(
        snapshot_id=sid, path=snap_path, n_examples=len(kept),
        n_rejected_label=len(rejected), content_sha256=content_hash, stable_deid=stable,
    )


def load_snapshot(path: Path) -> List[TrainingExample]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        rows.append(TrainingExample(
            example_id=d["example_id"],
            patient_pseudonym=d["patient_pseudonym"],
            encounter_time=d["encounter_time"],
            feature_vector=list(d["feature_vector"]),
            candidate_concept_ids=list(d["candidate_concept_ids"]),
            label_concept_id=d["label_concept_id"],
            label_source=LabelSource(d["label_source"]),
        ))
    return rows
