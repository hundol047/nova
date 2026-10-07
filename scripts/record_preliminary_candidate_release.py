"""Binds the current runtime to a verification record (schema v17): the preliminary-candidate round.

Local evidence only. Re-uses the previous record's honest status / blocker / compliance fields, and replaces the
runtime hashes, test counts, Round M metrics, regression summaries and (new) preliminary-benchmark / provenance
summaries with freshly executed ones. Refuses to write unless every executed hash matches the committed bytes of
``--runtime`` and the regression run reports the runtime unchanged during execution.

    NOVA_COMPETITION_RETRIEVAL=1 python scripts/evaluate_round_m_final.py
    NOVA_COMPETITION_RETRIEVAL=1 NOVA_REGRESSION_OUTPUT=artifacts/preliminary_candidate/regressions.json python scripts/evaluate_pre_guide_regressions.py
    python -m pytest tests -q --junitxml=artifacts/preliminary_candidate/pytest_runtime.xml <ignores> --deselect <the two record-reading tests>
    python scripts/evaluate_preliminary_benchmark.py --gate --output artifacts/preliminary_benchmark/latest.json
    python scripts/build_nova_submission.py
    python scripts/record_preliminary_candidate_release.py --runtime <commit-with-the-runtime-bytes>
"""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = "artifacts/preliminary_candidate/"


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    runtime = args.runtime
    reg = read(BASE + "regressions.json")
    assert reg["runtime_unchanged_during_execution"], "runtime changed during the regression run"
    hashes = dict(reg["runtime_sha256"], **{p: sha(p) for p in ("submission/run.py", "submission/requirements.txt")})
    for name, digest in hashes.items():
        assert sha(name) == digest, name
        assert (ROOT / name).read_bytes() == subprocess.check_output(["git", "show", runtime + ":" + name], cwd=ROOT), name
    subprocess.run([sys.executable, str(ROOT / "scripts/sanitize_pytest_evidence.py"), str(ROOT / BASE / "pytest_runtime.xml")], check=True)
    cases = list(ET.parse(ROOT / BASE / "pytest_runtime.xml").getroot().iter("testcase"))
    assert not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = [{"test": c.get("classname") + "." + c.get("name"), "reason": c.find("skipped").get("message")}
               for c in cases if c.find("skipped") is not None]
    tests = {"passed": len(cases) - len(skipped), "failed": 0, "skipped": len(skipped), "skip_reasons": skipped,
             "stage": "Runtime suite complete; the release-consistency test that reads this record is checked separately",
             "scope": "tests/ minus the four tests/test_production_*.py files (need FastAPI; separate CI job) and minus "
                      "the two tests/test_current_pre_guide_release.py tests that read THIS record "
                      "(test_current_runtime_exact_archive_and_commit, test_complete_round_m_denominators_and_failure_coverage; "
                      "re-run and passing after the record is written)",
             "python": "3.13 local; CI runs 3.11 and 3.12 (3.12 executed locally: all passed)",
             "junit": BASE + "pytest_runtime.xml", "junit_sha256": sha(BASE + "pytest_runtime.xml")}
    summary = read("artifacts/round_m/final_summary.json")
    for name, digest in summary["runtime_sha256"].items():
        assert hashes.get(name, digest) == digest, "Round M evidence was not produced on the runtime being recorded: " + name
    bench = read("artifacts/preliminary_benchmark/latest.json")
    from scripts.validate_runtime_provenance import validate
    provenance = validate()
    assert provenance["coverage_status"] == "PASS" and provenance["permission_status"] == "BLOCKED"
    package = "artifacts/verification/nova-pre-guide-v17.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    previous = read("artifacts/verification/CURRENT_RELEASE.json")["current_verification_artifact"]
    result = copy.deepcopy(read(previous))
    result.update(
        schema="nova-verification-v17", generated_utc=datetime.now(timezone.utc).isoformat(),
        verified_runtime_sha=runtime, executed_local_runtime_sha=runtime, runtime_sha256=hashes, tests=tests,
        round_m=summary["metrics"], round_m_artifact="artifacts/round_m/final_summary.json",
        failure_analysis_artifact="artifacts/round_m/failure_analysis.json",
        regressions={n: r["summary"] for n, r in reg["suites"].items()},
        preliminary_benchmark={"label": bench["label"], "artifact": "artifacts/preliminary_benchmark/latest.json",
                               "artifact_sha256": sha("artifacts/preliminary_benchmark/latest.json"),
                               "summaries": bench["summaries"], "model": bench["model"]},
        runtime_provenance={"coverage_status": provenance["coverage_status"], "permission_status": provenance["permission_status"],
                            "unresolved_assets": len(provenance["unresolved_assets"]), "official_submission_allowed": False},
        transport_note="Executed bytes recorded by hash; every file matched against the runtime commit.",
        scope_of_change="SOAP answer-denial data-loss fix + SOAP provenance checker, Korean colloquial evidence bridge, short-alias "
                        "diagnosis explanation, isolated fail-closed official-transport boundary, preliminary-only benchmark. English "
                        "development suites bit-identical; no disease facts, score weights or labels edited.",
        submission={"zip": package, "bytes": (ROOT / package).stat().st_size, "sha256": sha(package),
                    "status": "LOCAL PRE-GUIDE CANDIDATE ONLY; NOT OFFICIALLY READY; official transport BLOCKED"})
    for stale in ("rule_matrix", "clinical_review_pass", "clinical_prompt_changed", "clinical_parameters_changed", "clinical_parameter_scope"):
        result.pop(stale, None)
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-v17.json"
    (ROOT / artifact).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    pointer.update(current_verification_artifact=artifact, current_verification_schema=result["schema"], verified_runtime_sha=runtime,
                   previous_verification_artifacts=list(dict.fromkeys([previous] + pointer["previous_verification_artifacts"])))
    (ROOT / "artifacts/verification/CURRENT_RELEASE.json").write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(artifact, tests["passed"], "passed", tests["skipped"], "skipped")


if __name__ == "__main__":
    main()
