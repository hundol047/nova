#!/usr/bin/env python3
"""Writes evaluation/blind_v19_manifest.json AFTER the runtime freeze and BEFORE the one run.

Hashes the case file, the runner, and every runtime file (nova_agent/, competition/, and the
submission/ mirror); records the effective competition configuration and the FINAL_REASONING_SHA.
Run exactly once per blind set; the runner refuses to execute if any recorded hash drifts.
"""
import hashlib, json, sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.blind_cases_v19 import BLIND_CASES_V19  # noqa: E402
from nova_agent.config import get_config  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runtime_hashes() -> dict:
    out = {}
    for base in ("nova_agent", "competition", "submission/nova_agent", "submission/competition"):
        for p in sorted((ROOT / base).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                out[str(p.relative_to(ROOT))] = sha(p)
    return out


def main(final_reasoning_sha: str) -> None:
    import os
    os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")
    cfg = get_config(reload=True)
    manifest = dict(
        version="v19", authored_after_runtime_freeze=True,
        authored_utc=datetime.now(timezone.utc).isoformat(),
        final_reasoning_sha=final_reasoning_sha,
        file_sha256=sha(ROOT / "evaluation/blind_cases_v19.py"),
        runner_sha256=sha(ROOT / "evaluation/blind_benchmark_v19.py"),
        case_count=len(BLIND_CASES_V19),
        scored_case_count=sum(c.scoring_expected for c in BLIND_CASES_V19),
        critical_case_count=sum(c.critical for c in BLIND_CASES_V19),
        data_type="POST-FREEZE SYNTHETIC HOLDOUT", expert_reviewed=False, independent_clinical_validation=False,
        independence_note="New vignettes authored after the Round M freeze without v18/Round J/Round M wording or results; same development author. Not an independent author or clinical evaluation.",
        effective_config=asdict(cfg), runtime_sha256=runtime_hashes(),
        declared_runs=[dict(provider="mock", configuration="COMPETITION-STRUCTURE / MOCK-LLM", count=1)],
        no_post_run_runtime_changes=True,
        label_validation="catalog identifiers/names and schema verified; medical ground truth not expert-adjudicated",
        unscored_policy="Five ambiguous/unsupported/nonmedical cases declared before execution; report separately, do not drop failures after execution.",
    )
    (ROOT / "evaluation/blind_v19_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("manifest written:", manifest["case_count"], "cases;", len(manifest["runtime_sha256"]), "runtime files")


if __name__ == "__main__":
    main(sys.argv[1])
