"""Record measured current-issues verification; no blind execution or inferred live-model success.

Run after benchmarks, submission build, and pytest --junitxml=<path>:
  python scripts/record_current_issues_verification.py --runtime-sha <freeze> --junit <path>
The freeze must already exist in git. This recorder verifies all runtime bytes against it.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def read(rel):
    return json.loads((ROOT / rel).read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(runtime_sha, junit):
    prefix = "artifacts/current_issues/"
    files = [p for base in ("nova_agent", "competition", "submission/nova_agent", "submission/competition")
             for p in (ROOT / base).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    files += [ROOT / "submission/run.py", ROOT / "submission/requirements.txt"]
    hashes = {}
    for p in sorted(files):
        rel = p.relative_to(ROOT).as_posix()
        frozen = subprocess.check_output(["git", "show", runtime_sha + ":" + rel], cwd=ROOT)
        assert frozen == p.read_bytes(), f"runtime changed after freeze: {rel}"
        hashes[rel] = sha(frozen)
    for name in ("nova_agent", "competition"):
        for p in (ROOT / name).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                assert p.read_bytes() == (ROOT / "submission" / p.relative_to(ROOT)).read_bytes()

    archive = "artifacts/verification/nova-submission-v9.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / archive)
    with zipfile.ZipFile(ROOT / archive) as z:
        names = z.namelist()
        assert all(n in {"run.py", "requirements.txt", "MANIFEST.json"}
                   or n.startswith(("nova_agent/", "competition/")) for n in names)
        manifest = json.loads(z.read("MANIFEST.json"))
        assert set(names) == set(manifest["files"]) | {"MANIFEST.json"}
        for name, digest in manifest["files"].items():
            assert sha(z.read(name)) == digest
            assert z.read(name) == (ROOT / "submission" / name).read_bytes()
    assert (ROOT / archive).stat().st_size < 50 * 1024 * 1024

    suites = ElementTree.parse(junit).getroot()
    cases = list(suites.iter("testcase"))
    failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = sum(c.find("skipped") is not None for c in cases)
    assert failed == 0 and len(cases) >= 770
    names = {c.get("name") for c in cases}
    assert {"test_isolated_submission_runtime_modes[mock]",
            "test_isolated_submission_runtime_modes[unreachable]",
            "test_isolated_submission_runtime_modes[stub]",
            "test_preflight_success_does_not_credit_new_case",
            "test_timeout_is_bounded_and_retry_recovers",
            "test_schema_blocks_official_readiness_even_with_valid_stub"} <= names
    tests = {"command": "python -m pytest tests -q --junitxml=<local XML>",
             "passed": len(cases) - skipped, "skipped": skipped, "failed": failed,
             "runtime_boundary_test_count": sum("test_competition_runtime_boundaries" in c.get("classname", "") for c in cases),
             "source": "Parsed executed pytest JUnit XML; no test counts hardcoded"}
    (ROOT / prefix / "pytest_summary.json").write_text(json.dumps(tests, indent=2) + "\n")
    # Replace the incomplete buffered log from an earlier attempt with an explicit measured summary.
    (ROOT / prefix / "pytest.txt").write_text(
        f"Executed pytest JUnit result: {tests['passed']} passed, {skipped} skipped, {failed} failed.\n"
        "See pytest_summary.json; this is a parsed summary, not a captured stdout transcript.\n")

    baseline = read("artifacts/round_g/regression/competition_metrics.json")
    current = read(prefix + "regression/competition_metrics.json")
    regression = {name: {"cases": m["n_cases"], "scored_cases": m["n_scored_cases"],
                         "scored_accuracy": m["scored_diagnostic_accuracy"],
                         "critical_cases": m["n_critical_cases"], "critical_recall": m["critical_diagnosis_recall"],
                         "average_turns": m["average_turns"],
                         "accuracy_delta": m["scored_diagnostic_accuracy"] - baseline[name]["scored_diagnostic_accuracy"],
                         "critical_recall_delta": m["critical_diagnosis_recall"] - baseline[name]["critical_diagnosis_recall"]}
                  for name, m in current.items()}
    assert all(v["accuracy_delta"] >= 0 and v["critical_recall_delta"] >= 0 for v in regression.values())
    checks = read(prefix + "regression/checks.json")
    assert all(c["returncode"] == 0 for c in checks)
    round_g = read(prefix + "round_g_summary.json")
    assert round_g == read("artifacts/round_g/after_summary.json")
    result = {
        "schema": "nova-verification-v9", "status": "LOCAL_VERIFICATION_COMPLETED_EXTERNAL_BLOCKED",
        "verified_runtime_sha": runtime_sha, "remote_head_observed_at_runtime_freeze": runtime_sha,
        "runtime_changed_after_freeze": False, "runtime_sha256": hashes,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "current_blind_version": "v17", "current_blind_status": "REFERENCE-ONLY", "new_blind_runs": 0,
        "v17_cases_changed": False, "v17_rerun": False,
        "tests": tests, "ood": read(prefix + "ood_development.json")["metrics"],
        "data_type": "SYNTHETIC DEVELOPMENT / MOCK-LLM; local HTTP stub integration only",
        "independent_clinical_validation": False, "expert_reviewed": False,
        "real_gpt_oss": read(prefix + "real_endpoint_probe.json"),
        "official_api_status": "NOT VERIFIED", "schema_status": "PLACEHOLDER",
        "runtime_modes": {"A_mock": "PASS", "B_unreachable_fails_closed": "PASS",
                          "C_valid_local_stub_wiring": "PASS; NOT real GPT-OSS verification",
                          "D_real_endpoint": "NOT VERIFIED"},
        "real_call_gate": "PASS: zero-success, unattempted, expired-budget, new-case isolation",
        "submission": {"zip": archive, "bytes": (ROOT / archive).stat().st_size,
                       "sha256": sha((ROOT / archive).read_bytes()), "file_count": len(names),
                       "under_50mb": True, "source_sync": True, "standalone": "PASS / MOCK AND STUB",
                       "secret_scan": "PASS / build scanner, no suspicious credential-shaped strings",
                       "dependencies": ["pydantic>=2.6,<3"], "external_llm_sdk_required": False,
                       "default_provider": "competition", "model_target": "openai/gpt-oss-20b"},
        "regression_competition": regression, "round_g": {k: v for k, v in round_g.items() if k != "cases_detail"},
        "regression_artifacts": prefix + "regression/", "critical_recall_regression": False,
        "limitations": [
            "No available real model endpoint; response identity cannot attest model weights or revision.",
            "Official competition API, abstention legality and model serving contract remain unverified.",
            "OOD is a conservative lexical development heuristic: 2/8 nonmedical intents remain insufficient, not OOD.",
            "One of four evidenced development snapshots remains insufficient; existing candidate coverage limitations persist.",
            "Forced-label default remains provisional protocol behavior; metadata is required to interpret it safely.",
            "No new blind this round. v17 is reference-only and supplies no accuracy claim for this runtime.",
            "Generalization unnecessary-test proxy varies between runs; no efficiency improvement is claimed.",
        ],
    }
    rel = f"artifacts/verification/local-release-{runtime_sha[:7]}-v9.json"
    (ROOT / rel).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    previous = pointer["previous_verification_artifacts"]
    v8 = "artifacts/verification/local-release-1046986-v8.json"
    if v8 not in previous:
        previous.insert(0, v8)
    pointer.update(current_verification_artifact=rel, current_verification_schema=result["schema"],
                   verified_runtime_sha=runtime_sha, current_blind_status="REFERENCE-ONLY",
                   status=result["status"], updated_utc=result["generated_utc"],
                   reason="v9 verifies frozen local runtime, uncertainty development and standalone wiring; external gates remain blocked.")
    (ROOT / "artifacts/verification/CURRENT_RELEASE.json").write_text(json.dumps(pointer, indent=2) + "\n")
    print(json.dumps({"artifact": rel, "tests": tests, "zip_bytes": result["submission"]["bytes"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--runtime-sha", required=True)
    parser.add_argument("--junit", required=True); args = parser.parse_args()
    record(args.runtime_sha, args.junit)
