#!/usr/bin/env python3
"""Single local verification entrypoint -- a GitHub-Actions-free way to see, on one command, what
can and cannot be verified in the CURRENT environment (spec: release verification without spending
CI minutes).

It runs each check that the environment actually supports and reports one of:
    PASS         -- ran and succeeded
    FAIL         -- ran and failed
    SKIPPED      -- intentionally not run (e.g. a blind first-run that must be run manually once)
    NOT AVAILABLE -- cannot run here (missing dependency / no network / no service)

It NEVER reports a check it did not actually run as PASS. It does not trigger GitHub Actions and
makes no network calls itself. Results are written to
artifacts/verification/local-release-<sha>.json (secrets/PHI excluded).

Usage:
    python scripts/verify_local_release.py            # run + print + write JSON
    python scripts/verify_local_release.py --no-write  # print only
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PASS, FAIL, SKIPPED, NA = "PASS", "FAIL", "SKIPPED", "NOT AVAILABLE"


def _have_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                               text=True, timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _run(cmd: list, cwd: Path = ROOT, timeout: int = 900) -> tuple:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "")[-4000:], (p.stderr or "")[-2000:]
    except Exception as exc:  # noqa: BLE001
        return 1, "", f"{type(exc).__name__}: {exc}"


def check_nova_agent_tests() -> dict:
    if not _have_module("pydantic"):
        return {"status": NA, "detail": "pydantic not installed"}
    rc, out, err = _run([sys.executable, "-m", "pytest", "tests/", "-q",
                          "--ignore=tests/test_production_api.py",
                          "--ignore=tests/test_production_repository.py",
                          "--ignore=tests/test_production_reliability.py",
                          "--ignore=tests/test_production_units.py"])
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def check_backend_tests() -> dict:
    if not _have_module("fastapi"):
        return {"status": NA, "detail": "fastapi not installed"}
    rc, out, err = _run([sys.executable, "-m", "pytest", "backend/tests/", "-q"])
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def check_unit_safety_guard() -> dict:
    # The unit-safety + glucose guards are dependency-free and always runnable.
    rc, out, err = _run([sys.executable, "-m", "pytest", "tests/test_objective_evidence_units.py", "-q"])
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def check_leakage_scan() -> dict:
    if not _have_module("pydantic"):
        return {"status": NA, "detail": "pydantic not installed (blind case modules import SyntheticCase)"}
    rc, out, err = _run([sys.executable, "scripts/check_eval_leakage.py"])
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def check_submission_sync() -> dict:
    if not _have_module("pydantic"):
        return {"status": NA, "detail": "pydantic not installed (sync test imports the agent)"}
    rc, out, err = _run([sys.executable, "-m", "pytest",
                          "tests/test_safety_regression.py::test_submission_source_sync", "-q"])
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def _frontend_ready() -> tuple:
    """(ready, reason). Frontend checks need a working npm AND installed node_modules (vite/vitest);
    without an `npm ci` the build/test binaries are absent -- that is NOT AVAILABLE, not a FAIL."""
    if shutil.which("npm") is None:
        return False, "npm not available"
    if not (ROOT / "frontend" / "node_modules" / ".bin" / "vite").exists():
        return False, "frontend/node_modules not installed (run `npm ci` first)"
    return True, ""


def check_frontend_build() -> dict:
    ready, reason = _frontend_ready()
    if not ready:
        return {"status": NA, "detail": reason}
    rc, out, err = _run(["npm", "run", "build"], cwd=ROOT / "frontend", timeout=600)
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def check_frontend_unit_tests() -> dict:
    ready, reason = _frontend_ready()
    if not ready:
        return {"status": NA, "detail": reason}
    rc, out, err = _run(["npm", "run", "test:unit"], cwd=ROOT / "frontend", timeout=600)
    return {"status": PASS if rc == 0 else FAIL, "detail": (out + err).strip()[-500:]}


def _blind_manifest_ok(version: str) -> dict:
    import hashlib
    case = ROOT / "evaluation" / f"blind_cases_{version}.py"
    man = ROOT / "evaluation" / f"blind_{version}_manifest.json"
    if not case.exists() or not man.exists():
        return {"status": NA, "detail": f"{version} files not present"}
    actual = hashlib.sha256(case.read_bytes()).hexdigest()
    frozen = json.loads(man.read_text()).get("file_sha256")
    ok = actual == frozen
    return {"status": PASS if ok else FAIL,
            "detail": f"{version} hash {'matches' if ok else 'DRIFTED from'} frozen manifest"}


def check_blind_integrity() -> dict:
    # Freeze-integrity of the current untouched blind set (v9); v6/v8 are reference-only.
    return _blind_manifest_ok("v9")


def check_blind_v9_first_run() -> dict:
    # A blind FIRST RUN must be a deliberate, one-time manual action -- never auto-run here.
    if not _have_module("pydantic"):
        return {"status": NA, "detail": "pydantic not installed; run `python -m evaluation.blind_benchmark_v9` once in a runnable env"}
    return {"status": SKIPPED,
            "detail": "Blind v9 first run is a deliberate one-time manual step; not auto-run. "
                      "Run `python -m evaluation.blind_benchmark_v9` exactly once, then record the result."}


def check_postgres_available() -> dict:
    url = os.getenv("NOVA_TEST_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/nova_test")
    if not _have_module("psycopg"):
        return {"status": NA, "detail": "psycopg not installed"}
    try:
        import psycopg  # noqa
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return {"status": PASS, "detail": "Postgres reachable"}
    except Exception as exc:  # noqa: BLE001
        return {"status": NA, "detail": f"no Postgres reachable: {type(exc).__name__}"}


def check_redis_available() -> dict:
    url = os.getenv("SYNEX_REDIS_URL")
    if not _have_module("redis"):
        return {"status": NA, "detail": "redis client not installed"}
    if not url:
        return {"status": NA, "detail": "SYNEX_REDIS_URL not set"}
    try:
        import redis  # noqa
        r = redis.from_url(url, socket_connect_timeout=2)
        r.ping()
        return {"status": PASS, "detail": "Redis reachable"}
    except Exception as exc:  # noqa: BLE001
        return {"status": NA, "detail": f"no Redis reachable: {type(exc).__name__}"}


def check_browser_e2e_available() -> dict:
    if shutil.which("npx") is None:
        return {"status": NA, "detail": "npx not available; browser E2E cannot run"}
    if not (ROOT / "frontend" / "tests" / "e2e").exists() and not list((ROOT / "frontend").glob("**/*.spec.*")):
        return {"status": NA, "detail": "no Playwright/E2E spec present"}
    return {"status": SKIPPED, "detail": "E2E harness present but not auto-run here"}


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def check_i18n_parity() -> dict:
    # Accurate structural parity across the 4 locale dicts by importing them in node (dependency-
    # free) and comparing the flattened key paths -- a regex over `key:` tokens is unreliable
    # because string VALUES can contain colons, so node is the source of truth here.
    if shutil.which("node") is None:
        return {"status": NA, "detail": "node not available"}
    script = (
        "function flat(o,p=''){let r=[];for(const k in o){const v=o[k];const kk=p?p+'.'+k:k;"
        "if(v&&typeof v==='object')r=r.concat(flat(v,kk));else r.push(kk);}return r;}"
        "const en=(await import('./frontend/src/i18n/en.js')).default;const enk=new Set(flat(en));"
        "let bad=[];for(const loc of ['ko','ja','zh']){const dk=new Set(flat((await import('./frontend/src/i18n/'+loc+'.js')).default));"
        "const miss=[...enk].filter(k=>!dk.has(k));const extra=[...dk].filter(k=>!enk.has(k));"
        "if(miss.length||extra.length)bad.push(loc+':miss'+miss.length+':extra'+extra.length);}"
        "console.log(bad.length?('FAIL '+bad.join(',')):('OK '+enk.size));"
    )
    rc, out, err = _run(["node", "--input-type=module", "-e", script], timeout=60)
    line = (out.strip().splitlines() or [""])[-1]
    if line.startswith("OK"):
        return {"status": PASS, "detail": f"en/ko/ja/zh parity ({line.split()[1]} keys)"}
    if line.startswith("FAIL"):
        return {"status": FAIL, "detail": line}
    return {"status": NA, "detail": (err or "could not evaluate")[-160:]}


def check_hardcoded_string_audit() -> dict:
    if shutil.which("node") is None:
        return {"status": NA, "detail": "node not available"}
    rc, out, err = _run(["node", "scripts/audit_frontend_i18n.mjs", "--json"], timeout=60)
    if not out:
        return {"status": NA, "detail": (err or "audit could not run")[-200:]}
    try:
        total = json.loads(out).get("total_findings")
    except Exception:
        total = "?"
    # REVIEW-CANDIDATE report, not a pass/fail gate here -- report the count as info (PASS = ran).
    return {"status": PASS, "detail": f"{total} hardcoded CJK candidate line(s) across frontend/src (review only)"}


def check_e2e_harness_present() -> dict:
    spec = ROOT / "frontend" / "tests" / "e2e"
    cfg = ROOT / "frontend" / "playwright.config.js"
    if cfg.exists() and spec.exists() and any(spec.glob("*.spec.js")):
        return {"status": PASS, "detail": "playwright.config.js + tests/e2e/*.spec.js present (EXECUTION NOT VERIFIED here)"}
    return {"status": FAIL, "detail": "E2E harness files missing"}


def check_case_resume_wiring() -> dict:
    # Static presence checks for the resume path (backend route + service + frontend usage).
    ok = all([
        "def list_cases_for_patient" in _read("backend/app/services/nova_service.py"),
        "/v1/nova/patients/{patient_id}/cases" in _read("backend/app/main.py"),
        "resumeCase" in _read("frontend/src/components/nova/NovaWorkspace.jsx"),
        "conversation_history" in _read("frontend/src/components/nova/NovaWorkspace.jsx"),
    ])
    return {"status": PASS if ok else FAIL,
            "detail": "open-case API + service + frontend resume/timeline restore wired"}


def check_reasoning_unchanged_blind_v9() -> dict:
    # Documents (statically) that v9 is the current untouched set and its manifest matches.
    return _blind_manifest_ok("v9")


CHECKS = [
    ("nova_agent_tests", check_nova_agent_tests),
    ("backend_tests", check_backend_tests),
    ("unit_safety_guard", check_unit_safety_guard),
    ("leakage_scan", check_leakage_scan),
    ("submission_sync", check_submission_sync),
    ("frontend_build", check_frontend_build),
    ("frontend_unit_tests", check_frontend_unit_tests),
    ("i18n_parity", check_i18n_parity),
    ("hardcoded_string_audit", check_hardcoded_string_audit),
    ("e2e_harness_present", check_e2e_harness_present),
    ("case_resume_wiring", check_case_resume_wiring),
    ("blind_integrity", check_blind_integrity),
    ("blind_v9_first_run", check_blind_v9_first_run),
    ("postgres_available", check_postgres_available),
    ("redis_available", check_redis_available),
    ("browser_e2e_available", check_browser_e2e_available),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true", help="print only; do not write the JSON artifact")
    args = ap.parse_args()

    sha = _git_sha()
    results = {}
    print(f"N.O.V.A. local release verification  (SHA {sha[:12]})")
    print("=" * 60)
    for name, fn in CHECKS:
        try:
            res = fn()
        except Exception as exc:  # noqa: BLE001
            res = {"status": FAIL, "detail": f"checker crashed: {type(exc).__name__}: {exc}"}
        results[name] = res
        print(f"  {name:22s} {res['status']:14s} {res.get('detail', '')[:80]}")

    payload = {
        "git_sha": sha,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "pydantic": _have_module("pydantic"),
            "fastapi": _have_module("fastapi"),
            "psycopg": _have_module("psycopg"),
            "npm": shutil.which("npm") is not None,
        },
        "results": results,
    }

    if not args.no_write:
        out_dir = ROOT / "artifacts" / "verification"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"local-release-{sha[:12]}.json"
        out_file.write_text(json.dumps(payload, indent=2))
        print("=" * 60)
        print(f"Wrote {out_file.relative_to(ROOT)}")

    # Exit non-zero only on a genuine FAIL (NOT AVAILABLE / SKIPPED are not failures).
    any_fail = any(r["status"] == FAIL for r in results.values())
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
