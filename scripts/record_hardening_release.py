"""Bind v13 to actual frozen files and executed local evidence, without any blind run."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/compliance_hardening"


def read(path): return json.loads((ROOT / path).read_text())
def write(path, data): (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
def sha(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    base = read("artifacts/verification/local-release-9b607b4-v12.json")
    summary = read("artifacts/compliance_hardening/round_m/final_summary.json")
    regressions = read("artifacts/compliance_hardening/regressions.json")
    runtime = summary["runtime_sha"]
    assert regressions["runtime_sha"] == runtime and len(regressions["suites"]) == 8
    hashes = dict(summary["runtime_sha256"])
    for name in ("submission/run.py", "submission/requirements.txt"): hashes[name] = sha(name)
    for name, digest in hashes.items():
        assert sha(name) == digest, name
        assert (ROOT / name).read_bytes() == subprocess.check_output(["git", "show", runtime + ":" + name], cwd=ROOT), name
    baseline = read("artifacts/round_m/final_summary.json")
    assert summary["metrics"] == baseline["metrics"], "Clinical metric drift requires explicit investigation"
    frozen = read("artifacts/compliance_hardening/clinical_freeze.json")
    assert all(sha(name) == digest for name, digest in frozen["clinical_files"].items())
    junit = OUT / "pytest.xml"
    provisional = not junit.exists()
    if provisional: junit = OUT / "pytest_before_release.xml"
    cases = list(ET.parse(junit).getroot().iter("testcase"))
    failures = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
    skips = [{"test": c.get("classname") + "." + c.get("name"), "reason": c.find("skipped").get("message")} for c in cases if c.find("skipped") is not None]
    assert not failures
    tests = dict(passed=len(cases)-len(skips), failed=0, skipped=len(skips), skip_reasons=skips,
                 junit=str(junit.relative_to(ROOT)), junit_sha256=sha(junit),
                 stage="PRELIMINARY" if provisional else "FULL CURRENT SUITE")
    audit = read("artifacts/compliance_hardening/package_audit.json")
    assert audit["secret_scan"]["status"] == "PASS" and audit["source_submission_byte_equivalence"]
    assert not any(audit[k] for k in ("forbidden_files", "training_operations", "utf8_failures"))
    package = "artifacts/verification/nova-pre-guide-v13.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    assert sha(package) == audit["zip_sha256"]
    for path in ("artifacts/blind_runs/blind_v19_attempt.json", "artifacts/blind_runs/blind_v19_results.json", "evaluation/blind_v19_manifest.json", "evaluation/blind_cases_v20.py"):
        assert not (ROOT / path).exists(), path
    base.update(schema="nova-verification-v13", generated_utc=datetime.now(timezone.utc).isoformat(), audited_remote_head="5413af9c62fb25af2e5ef1d7add7acab1b0571eb",
                verified_runtime_sha=runtime, executed_local_runtime_sha=runtime, transport_note="Identical Git tree imported and fast-forwarded before evaluation; no history rewritten.",
                runtime_sha256=hashes, tests=tests, round_m=summary["metrics"],
                round_m_artifact="artifacts/compliance_hardening/round_m/final_summary.json",
                failure_analysis_artifact="artifacts/compliance_hardening/round_m/failure_analysis.json",
                regressions={k: v["summary"] for k, v in regressions["suites"].items()},
                rule_matrix="artifacts/compliance_hardening/rule_matrix.json", clinical_parameters_changed=False,
                network_policy="APPLICATION_LEVEL_NETWORK_POLICY_VERIFIED", os_network_isolation="NOT_VERIFIED",
                submission=dict(zip=package, bytes=(ROOT/package).stat().st_size, sha256=sha(package), status="LOCAL PRE-GUIDE CANDIDATE ONLY; official run.py BLOCKED"),
                report="docs/competition/PRE_GUIDE_RELEASE_REPORT.md")
    base["compliance"]["Case-related LLM success gate"] = "BLOCKED — organizer receipt semantics/transport not provided; development JSON validity is separate"
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-v13.json"
    write(artifact, base)
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    previous = pointer["previous_verification_artifacts"]
    if pointer["current_verification_artifact"] != artifact:
        previous = list(dict.fromkeys([pointer["current_verification_artifact"]] + previous))
    pointer.update(current_verification_artifact=artifact, current_verification_schema="nova-verification-v13",
                   verified_runtime_sha=runtime, previous_verification_artifacts=previous,
                   latest_compliance_followup="artifacts/compliance_hardening/rule_matrix.json")
    write("artifacts/verification/CURRENT_RELEASE.json", pointer)
    comparison = {key: {"before": baseline["metrics"][key], "after": summary["metrics"][key]}
                  for key in summary["metrics"]}
    write("artifacts/compliance_hardening/performance_comparison.json", {"all_round_m_metrics_equal": True, "metrics": comparison,
          "clinical_files_byte_unchanged": True, "baseline_runtime": baseline["runtime_sha"], "current_runtime": runtime})
    print(json.dumps({"artifact": artifact, "tests": tests, "zip": base["submission"], "status": base["status"]}, indent=2))


if __name__ == "__main__": main()
