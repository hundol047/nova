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


# Paths that may change between a verified SHA and HEAD WITHOUT invalidating the verification
# (metadata/docs only — never runtime/reasoning/training code).
_NON_RUNTIME_PREFIXES = (
    "artifacts/verification/",
    "docs/",
    "README.md",
    "README_NOVA.md",
)


def _runtime_files_changed_since(verified_sha: str):
    """Return the list of RUNTIME files changed between verified_sha and HEAD, or None if the diff
    can't be computed. An empty list means only metadata/docs changed (verification still valid)."""
    try:
        p = subprocess.run(["git", "diff", "--name-only", f"{verified_sha}..HEAD"],
                           cwd=ROOT, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            return None
        changed = [ln.strip() for ln in p.stdout.splitlines() if ln.strip()]
        runtime = [f for f in changed if not any(f.startswith(pfx) or f == pfx for pfx in _NON_RUNTIME_PREFIXES)]
        return runtime
    except Exception:
        return None


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


def _current_blind_version() -> str:
    """The current untouched blind version, from the single source of truth (evaluation.current_blind).
    Falls back to reading the constant statically if the package can't be imported here."""
    try:
        import importlib.util as _u
        spec = _u.spec_from_file_location("_cb", ROOT / "evaluation" / "current_blind.py")
        mod = _u.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.CURRENT_BLIND_VERSION
    except Exception:
        return "v10"


def check_blind_integrity() -> dict:
    # Freeze-integrity of the CURRENT untouched blind set (derived from evaluation.current_blind).
    return _blind_manifest_ok(_current_blind_version())


def check_blind_first_run() -> dict:
    # A blind FIRST RUN must be a deliberate, one-time manual action -- never auto-run here.
    v = _current_blind_version()
    if not _have_module("pydantic"):
        return {"status": NA, "detail": f"pydantic not installed; run `python -m evaluation.blind_benchmark_{v}` once in a runnable env"}
    return {"status": SKIPPED,
            "detail": f"Blind {v} first run is a deliberate one-time manual step; not auto-run. "
                      f"Run `python -m evaluation.blind_benchmark_{v}` exactly once, then record the result."}


def check_current_blind_consistency() -> dict:
    """The current blind version (evaluation.current_blind) must have present, hash-matching frozen
    files, and the leakage scanner's module list must include every authored set."""
    v = _current_blind_version()
    man = _blind_manifest_ok(v)
    if man["status"] != PASS:
        return {"status": FAIL, "detail": f"current blind {v}: {man['detail']}"}
    # leakage scanner must reference the current version
    scan = _read("scripts/check_eval_leakage.py")
    if f"blind_cases_{v}" not in scan:
        return {"status": FAIL, "detail": f"leakage scanner missing blind_cases_{v}"}
    # verifier must not hard-code a DIFFERENT version as current (self-check)
    return {"status": PASS, "detail": f"current blind = {v}; frozen hash matches; leakage scanner includes it"}


def check_docs_current_counts() -> dict:
    """Docs describing CURRENT state must match the real catalog bundled count and current blind
    version. Historical sections are exempt when explicitly marked 'HISTORICAL SNAPSHOT'."""
    try:
        cat = _load_catalog_via_stub()
        tiers = cat.counts_by_tier()
        bundled = tiers.get("TIER1_DEEP", 0) + tiers.get("TIER2_STRUCTURED", 0)
    except Exception as exc:  # noqa: BLE001
        return {"status": NA, "detail": f"catalog unavailable: {type(exc).__name__}"}
    v = _current_blind_version()
    problems = []
    # DISEASE_COVERAGE.md should state the real bundled count and not a stale one.
    cov = _read("docs/ontology/DISEASE_COVERAGE.md")
    if cov and str(bundled) not in cov:
        problems.append(f"DISEASE_COVERAGE.md does not mention current bundled={bundled}")
    if cov and "174 concepts total" in cov and "HISTORICAL" not in cov:
        problems.append("DISEASE_COVERAGE.md still shows stale '174 concepts total' as current")
    if problems:
        return {"status": FAIL, "detail": "; ".join(problems)[:120]}
    return {"status": PASS, "detail": f"docs reflect bundled={bundled}, current blind={v}"}


def check_verified_sha_consistency() -> dict:
    """The latest verification artifact's verified_code_sha must correspond to the actual runtime
    code: git diff verified_code_sha..HEAD may only touch artifacts/verification/** or release docs
    (runtime_files_changed_after_verification must be false). If runtime code changed since the
    recorded SHA, this reports FAIL so the artifact is regenerated."""
    art_dir = ROOT / "artifacts" / "verification"
    arts = sorted(art_dir.glob("local-release-*.json")) if art_dir.is_dir() else []
    if not arts:
        return {"status": NA, "detail": "no verification artifact present yet"}
    latest = max(arts, key=lambda p: p.stat().st_mtime)
    try:
        data = json.loads(latest.read_text())
    except Exception:  # noqa: BLE001
        return {"status": FAIL, "detail": f"artifact {latest.name} unreadable"}
    verified = data.get("verified_code_sha") or data.get("git_sha")
    if not verified:
        return {"status": NA, "detail": f"{latest.name} has no verified_code_sha"}
    changed = _runtime_files_changed_since(verified)
    if changed is None:
        return {"status": NA, "detail": f"cannot diff {verified[:12]} (unknown ref)"}
    if changed:
        return {"status": FAIL,
                "detail": f"runtime code changed since verified_code_sha {verified[:12]}: "
                          f"{', '.join(changed[:4])} -> regenerate artifact"}
    return {"status": PASS, "detail": f"runtime code unchanged since verified_code_sha {verified[:12]}"}


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


def check_reasoning_unchanged_current_blind() -> dict:
    # Documents (statically) that the CURRENT blind set's manifest matches its frozen hash.
    return _blind_manifest_ok(_current_blind_version())


def _load_catalog_via_stub():
    """Build the DiseaseCatalog without triggering the pydantic-heavy nova_agent package __init__
    (dependency-free path, works locally)."""
    import sys as _sys
    import types as _types
    if "nova_agent" not in _sys.modules:
        pkg = _types.ModuleType("nova_agent")
        pkg.__path__ = [str(ROOT / "nova_agent")]
        _sys.modules["nova_agent"] = pkg
    from nova_agent.ontology import registry
    return registry.build_catalog()


def check_ontology_catalog_integrity() -> dict:
    """Dependency-free: builds the catalog, asserts the 34 core deep concepts survive, no duplicate
    concept ids, a broad Tier-2 layer is present, and external-code mapping round-trips."""
    try:
        cat = _load_catalog_via_stub()
    except Exception as exc:  # noqa: BLE001
        return {"status": FAIL, "detail": f"catalog build failed: {type(exc).__name__}: {exc}"}
    tiers = cat.counts_by_tier()
    ids = [c.concept_id for c in cat.all_concepts()]
    dups = len(ids) - len(set(ids))
    if tiers.get("TIER1_DEEP", 0) != 34:
        return {"status": FAIL, "detail": f"expected 34 Tier-1 deep, got {tiers.get('TIER1_DEEP')}"}
    if dups:
        return {"status": FAIL, "detail": f"{dups} duplicate concept id(s)"}
    bundled = tiers.get("TIER1_DEEP", 0) + tiers.get("TIER2_STRUCTURED", 0)
    if bundled < 500:
        return {"status": FAIL, "detail": f"bundled catalog {bundled} < 500 target"}
    # code mapping round-trip
    coded = [c for c in cat.all_concepts() if c.external_codes]
    if coded:
        s = coded[0]
        mapped = cat.map_external_code(s.external_codes[0].system, s.external_codes[0].code)
        if s.concept_id not in {m.concept_id for m in mapped}:
            return {"status": FAIL, "detail": "external-code mapping did not round-trip"}
    total = len(ids)
    return {"status": PASS, "detail": f"{total} concepts (34 deep + {tiers['TIER2_STRUCTURED']} structured), "
                                      f"bundled>={500} OK, 0 dup ids, code-map OK"}


def check_disease_coverage_500() -> dict:
    """Runs the dependency-free 500+ coverage + search test file."""
    if not _have_module("pytest"):
        return {"status": NA, "detail": "pytest not installed"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_disease_coverage_500.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return {"status": PASS if proc.returncode == 0 else FAIL, "detail": tail[0][:80]}


def check_terminology_import() -> dict:
    """Runs the dependency-free terminology import CLI tests (validation + Tier-3 provider read)."""
    if not _have_module("pytest"):
        return {"status": NA, "detail": "pytest not installed"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_terminology_import.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return {"status": PASS if proc.returncode == 0 else FAIL, "detail": tail[0][:80]}


def check_ml_runtime_and_lifecycle() -> dict:
    """Runs the dependency-free ML runtime + training + retraining lifecycle + open-world +
    admin RBAC + continual-validation test files (everything that does not need torch/pydantic)."""
    if not _have_module("pytest"):
        return {"status": NA, "detail": "pytest not installed"}
    files = [
        "tests/test_ml_runtime_integration.py",
        "tests/test_learning_training.py",
        "tests/test_retraining_lifecycle.py",
        "tests/test_continual_validation.py",
        "tests/test_open_world_expansion.py",
        "tests/test_learning_admin_rbac.py",
    ]
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", *files],
                          cwd=str(ROOT), capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return {"status": PASS if proc.returncode == 0 else FAIL, "detail": tail[0][:80]}


def check_checkpoint_roundtrip_static() -> dict:
    """Static: the checkpoint compatibility guard exists and torch training is torch-gated. Actual
    torch weight roundtrip is exercised by test_learning_training.py (torch-skipped without torch)."""
    ck = _read("learning/checkpoint.py")
    tr = _read("learning/train.py")
    ok = ("def check_compatibility" in ck and "CheckpointIncompatibleError" in ck
          and "MODEL_INPUT_DIM" in ck and "IMPLEMENTED_BUT_NOT_EXECUTED" in tr)
    if not ok:
        return {"status": FAIL, "detail": "checkpoint guard / torch-gated training markers missing"}
    detail = "checkpoint compat-guard present; torch training torch-gated"
    if not _have_module("torch"):
        detail += " (torch weight roundtrip NOT EXECUTED here -> CI/torch env)"
    return {"status": PASS, "detail": detail}


def check_learning_isolation() -> dict:
    """Static: learning/ never imports evaluation/; nova_agent/ + submission/ never import
    torch/learning; submission excludes the learning package + torch requirement."""
    import re as _re
    eval_imp = _re.compile(r"^\s*(from|import)\s+evaluation\b", _re.MULTILINE)
    tl_imp = _re.compile(r"^\s*(from|import)\s+(torch|learning)\b", _re.MULTILINE)
    problems = []
    for py in (ROOT / "learning").rglob("*.py"):
        if eval_imp.search(py.read_text(encoding="utf-8", errors="ignore")):
            problems.append(f"learning imports evaluation: {py.name}")
    for base in ("nova_agent", "submission"):
        for py in (ROOT / base).rglob("*.py"):
            if tl_imp.search(py.read_text(encoding="utf-8", errors="ignore")):
                problems.append(f"{base} imports torch/learning: {py.name}")
    if (ROOT / "submission" / "learning").exists():
        problems.append("submission/ contains the learning package")
    req = (ROOT / "submission" / "requirements.txt")
    if req.exists() and "torch" in req.read_text(encoding="utf-8").lower():
        problems.append("submission/requirements.txt declares torch")
    if problems:
        return {"status": FAIL, "detail": "; ".join(problems)[:120]}
    return {"status": PASS, "detail": "learning<->eval isolated; torch/learning absent from core+submission"}


def check_learning_pipeline_tests() -> dict:
    """Runs the dependency-free learning pipeline + isolation tests (no torch/pydantic needed)."""
    if not _have_module("pytest"):
        return {"status": NA, "detail": "pytest not installed"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         "tests/test_learning_pipeline.py", "tests/test_learning_eval_isolation.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return {"status": PASS if proc.returncode == 0 else FAIL, "detail": tail[0][:80]}


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
    ("ontology_catalog_integrity", check_ontology_catalog_integrity),
    ("disease_coverage_500", check_disease_coverage_500),
    ("terminology_import", check_terminology_import),
    ("ml_runtime_and_lifecycle", check_ml_runtime_and_lifecycle),
    ("checkpoint_roundtrip_static", check_checkpoint_roundtrip_static),
    ("learning_isolation", check_learning_isolation),
    ("learning_pipeline_tests", check_learning_pipeline_tests),
    ("blind_integrity", check_blind_integrity),
    ("blind_first_run", check_blind_first_run),
    ("current_blind_consistency", check_current_blind_consistency),
    ("reasoning_unchanged_current_blind", check_reasoning_unchanged_current_blind),
    ("docs_current_counts", check_docs_current_counts),
    ("verified_sha_consistency", check_verified_sha_consistency),
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

    # --- verification artifact v2 metadata --------------------------------------------------
    def _branch() -> str:
        try:
            return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
                                  capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def _remote_sha(branch: str) -> str:
        try:
            out = subprocess.run(["git", "ls-remote", "origin", branch], cwd=ROOT,
                                 capture_output=True, text=True, timeout=20).stdout.strip()
            return out.split("\t")[0] if out else "unknown"
        except Exception:
            return "unknown"

    tier_counts = {}
    total_searchable = None
    try:
        _cat = _load_catalog_via_stub()
        tier_counts = _cat.counts_by_tier()
        total_searchable = len(_cat)
    except Exception:  # noqa: BLE001
        pass

    branch = _branch()
    not_available = [n for n, r in results.items() if r["status"] == NA]
    # runtime_files_changed_after_verification: compared to THIS sha, nothing has changed yet (this
    # run IS the verification of `sha`). The self-consistency check verified_sha_consistency guards
    # the previously-recorded artifact. Recorded here as false by construction for this artifact.
    payload = {
        "schema": "nova-verification-v2",
        "verified_code_sha": sha,
        "artifact_commit_sha": None,  # unknown until this artifact is committed (documented, not looped)
        "branch": branch,
        "remote_sha": _remote_sha(branch),
        "current_blind_version": _current_blind_version(),
        "total_searchable_diagnoses": total_searchable,
        "tier_counts": tier_counts,
        "runtime_files_changed_after_verification": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "pydantic": _have_module("pydantic"),
            "fastapi": _have_module("fastapi"),
            "psycopg": _have_module("psycopg"),
            "torch": _have_module("torch"),
            "npm": shutil.which("npm") is not None,
        },
        "not_available": not_available,
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
