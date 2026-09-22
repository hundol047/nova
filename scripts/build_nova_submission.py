#!/usr/bin/env python3
"""Regenerates submission/nova_agent/ and submission/competition/ from the real nova_agent/ and
competition/ packages at the repository root (the single source of truth) -- spec section 16/24I --
then validates the result before declaring it ready (spec section 23/24): requirements sanity,
an actual import/subprocess smoke test, a forbidden-file/secret scan, and a versioned
submission.zip + manifest for a reproducible artifact to actually hand in.

submission/run.py and submission/requirements.txt are hand-authored and NOT touched by this
script. Run this after any change to nova_agent/ or competition/:

    python scripts/build_nova_submission.py

Deliberately excludes everything NOT needed to run the agent (spec section 16): no frontend/, no
3D anatomy assets, no Jetson-specific scripts, no dev docs, no pytest, no large research/ assets --
only the two packages the Doctor Agent actually imports at runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")

# Same shape/spirit as scripts/preflight_competition.py's secret_scan, applied here to the exact
# files about to be shipped rather than the whole repo. Covers known credential-shaped prefixes
# (OpenAI/Anthropic API keys, AWS access keys, PEM private keys, GitHub/Slack tokens) PLUS a
# generic fallback for an api_key/secret/token/password variable assigned a real-looking (not
# placeholder/env-var-reference) string literal -- since a competition submission is exactly the
# kind of thing someone might accidentally leave a real key hardcoded in during local testing.
_SECRET_PATTERNS = [re.compile(p) for p in (
    r"sk-[A-Za-z0-9]{16,}",
    r"sk-ant-[A-Za-z0-9\-_]{16,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"AKIA[0-9A-Z]{16}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"xox[baprs]-[A-Za-z0-9\-]{10,}",
    r"(?i)\b(api_key|apikey|secret_key|access_token|password)\s*[:=]\s*[\"'][A-Za-z0-9/+_\-]{12,}[\"']",
)]
# A quoted literal that's obviously a placeholder/config-reference, not a real secret -- excluded
# from the generic fallback pattern above so this scan doesn't cry wolf on the codebase's own
# legitimate, already-safe patterns (env var names, "" defaults, os.environ.get(...) calls).
_PLACEHOLDER_HINTS = ("your_", "changeme", "example", "xxxx", "<", "${", "os.environ")


def _copy_package(name: str) -> None:
    src = ROOT / name
    dst = SUBMISSION / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=IGNORE)
    print(f"copied {src} -> {dst}")


def _check_requirements() -> None:
    text = (SUBMISSION / "requirements.txt").read_text(encoding="utf-8")
    live_lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    if not any("pydantic" in l.lower() for l in live_lines):
        raise SystemExit("submission/requirements.txt must declare pydantic (nova_agent's only hard runtime dependency).")
    if any("openai" in l.lower() for l in live_lines):
        raise SystemExit("submission/requirements.txt must not hard-depend on the openai package -- "
                          "the competition/local/openai_compatible providers use a stdlib urllib client.")
    print(f"requirements OK: {live_lines}")


def _submission_files() -> list:
    return sorted(
        p for p in SUBMISSION.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.name not in {"submission.zip", "MANIFEST.json"}
    )


def _secret_scan() -> None:
    hits = []
    for path in _submission_files():
        if path.suffix not in {".py", ".txt", ".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in _SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                line = text[line_start: line_end if line_end != -1 else None]
                if any(hint in line for hint in _PLACEHOLDER_HINTS):
                    continue
                hits.append(f"{path.relative_to(SUBMISSION)}: matches {pattern.pattern}")
    if hits:
        raise SystemExit("secret-shaped string(s) found in submission/, refusing to build:\n" + "\n".join(hits))
    print("secret scan OK: no suspicious credential-shaped strings")


def _import_smoke_test() -> None:
    """Runs the packaged run.py as a real subprocess with ONLY submission/ on sys.path and a
    minimal environment (no inherited PYTHONPATH) -- the same standalone check
    tests/test_hybrid_and_robustness.py::test_submission_run_entrypoint does, run again here at
    build time so a broken submission is never left in place even if the test suite wasn't run."""
    proc = subprocess.run(
        [sys.executable, "run.py"],
        input='{"case_id": "build_smoke", "observation_type": "initial", "chief_complaint": "chest pain", '
              '"demographics": {"age": 55, "sex": "male"}}\n',
        cwd=str(SUBMISSION), capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin"},
    )
    if proc.returncode != 0 or '"action_type"' not in proc.stdout:
        raise SystemExit(f"submission/run.py import/smoke test FAILED (exit={proc.returncode}):\n{proc.stderr}")
    print("import/subprocess smoke test OK: submission/run.py produced a valid action standalone")


def _build_zip_and_manifest() -> None:
    files = _submission_files()
    manifest = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": {
            str(p.relative_to(SUBMISSION)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        },
    }
    (SUBMISSION / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    zip_path = SUBMISSION / "submission.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, arcname=p.relative_to(SUBMISSION))
        zf.write(SUBMISSION / "MANIFEST.json", arcname="MANIFEST.json")
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"submission.zip built: {len(files)} files, {size_mb:.2f} MB -- {zip_path}")


def main() -> None:
    SUBMISSION.mkdir(exist_ok=True)
    _copy_package("nova_agent")
    _copy_package("competition")
    for required in ("run.py", "requirements.txt"):
        if not (SUBMISSION / required).exists():
            raise SystemExit(f"submission/{required} is missing -- it is hand-authored and must "
                              "exist before running this script.")
    _check_requirements()
    _secret_scan()
    _import_smoke_test()
    _build_zip_and_manifest()
    print("submission/ is ready.")


if __name__ == "__main__":
    main()
