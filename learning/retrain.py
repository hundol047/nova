"""End-to-end offline retraining lifecycle CLI (torch-optional).

Subcommands:
  train     snapshot -> split -> real training loop (learning.train) -> held-out eval -> register
            the result as SHADOW in the model registry (NEVER auto-promoted).
  promote   promote a SHADOW model to PRODUCTION — requires an explicit --approved-by AND clearing
            the safety gate (critical-recall floor + no regression vs current production).
  rollback  restore the previous production model.
  status    print the registry (versions, states, production pointer).

This orchestrates the GOVERNED lifecycle:
    encounter outcome -> frozen dataset snapshot -> offline training -> evaluation -> SHADOW
    -> (human, gated) approval -> PRODUCTION -> (on failure) rollback.

torch absent: training is IMPLEMENTED_BUT_NOT_EXECUTED (data prep + split integrity still run);
registry/promote/rollback are dependency-free and fully functional. Real clinical performance is
never claimed from synthetic runs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from learning._torch import torch_available
from learning.checkpoint import CheckpointMeta, load_meta, training_code_sha
from learning.registry import ModelRegistry


def _run_training(snapshot: str, output_dir: str, model_version: str, split: str,
                  cutoff: str, epochs: int) -> int:
    cmd = [sys.executable, "-m", "learning.train", "--snapshot", snapshot,
           "--output-dir", output_dir, "--model-version", model_version,
           "--split", split, "--epochs", str(epochs)]
    if split == "temporal" and cutoff:
        cmd += ["--cutoff", cutoff]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _metrics_from_checkpoint(output_dir: str, model_version: str) -> Optional[Dict[str, float]]:
    weights = Path(output_dir) / f"{model_version}.pt"
    meta_json = weights.with_suffix(".json")
    if not meta_json.is_file():
        return None
    meta = load_meta(weights)
    return meta.metrics


def cmd_train(args) -> int:
    reg = ModelRegistry(Path(args.registry_dir))
    model_version = args.model_version or f"ranker-{Path(args.snapshot).stem}"

    rc = _run_training(args.snapshot, args.output_dir, model_version, args.split, args.cutoff, args.epochs)
    if rc != 0:
        print("training failed; nothing registered.", file=sys.stderr)
        return rc

    metrics = _metrics_from_checkpoint(args.output_dir, model_version)
    if metrics is None:
        # torch absent -> no checkpoint produced. This is the IMPLEMENTED_BUT_NOT_EXECUTED path.
        print("STATUS: training did not produce a checkpoint (torch absent). "
              "No SHADOW model registered. Run in a torch environment to complete the cycle.")
        return 0

    # Regression comparison vs current production baseline (informational at register time; the
    # binding gate is enforced at promote()).
    prod = reg.production_version()
    baseline_metrics = reg.get(prod).metrics if prod else None
    if baseline_metrics:
        delta = {k: round(metrics.get(k, 0.0) - baseline_metrics.get(k, 0.0), 4)
                 for k in ("top_1_recall", "top_3_recall", "critical_recall") if k in metrics}
        print(f"regression-vs-baseline({prod}): {delta}")

    entry = reg.register(model_version, dataset_snapshot_id=Path(args.snapshot).stem,
                         metrics=metrics, code_sha=training_code_sha(),
                         dataset_version=args.dataset_version or Path(args.snapshot).stem,
                         notes="registered as SHADOW by retrain.py")
    print(f"REGISTERED SHADOW: {entry.version} state={entry.state.value} "
          f"critical_recall={metrics.get('critical_recall')} (NOT auto-promoted).")
    return 0


def cmd_promote(args) -> int:
    reg = ModelRegistry(Path(args.registry_dir))
    try:
        entry = reg.promote(args.version, approved_by=args.approved_by)
    except (PermissionError, ValueError) as exc:
        print(f"PROMOTION BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"PROMOTED: {entry.version} -> PRODUCTION by {entry.approved_by} at {entry.approved_at}")
    return 0


def cmd_rollback(args) -> int:
    reg = ModelRegistry(Path(args.registry_dir))
    restored = reg.rollback()
    if restored is None:
        print("no previous production version to roll back to.", file=sys.stderr)
        return 1
    print(f"ROLLED BACK: production restored to {restored.version}")
    return 0


def cmd_status(args) -> int:
    reg = ModelRegistry(Path(args.registry_dir))
    print(json.dumps({
        "production": reg.production_version(),
        "torch_available": torch_available(),
        "entries": [e.as_dict() for e in reg.list_versions()],
    }, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Governed offline retraining lifecycle.")
    ap.add_argument("--registry-dir", default="artifacts/models/registry")
    sub = ap.add_subparsers(dest="command", required=True)

    t = sub.add_parser("train")
    t.add_argument("--snapshot", required=True)
    t.add_argument("--output-dir", default="artifacts/models/ranker")
    t.add_argument("--model-version", default="")
    t.add_argument("--dataset-version", default="")
    t.add_argument("--split", choices=["patient", "temporal"], default="patient")
    t.add_argument("--cutoff", default="")
    t.add_argument("--epochs", type=int, default=20)
    t.set_defaults(func=cmd_train)

    p = sub.add_parser("promote")
    p.add_argument("--version", required=True)
    p.add_argument("--approved-by", required=True, help="explicit human approver (audited)")
    p.set_defaults(func=cmd_promote)

    r = sub.add_parser("rollback")
    r.set_defaults(func=cmd_rollback)

    s = sub.add_parser("status")
    s.set_defaults(func=cmd_status)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
