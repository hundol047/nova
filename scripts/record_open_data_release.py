"""Binds the current runtime (preliminary-round rules + open DO synonyms) to a verification record (v16).

Local evidence only: re-uses the v15 record's honest status/blocker/compliance fields, replaces the
runtime hashes, test counts, Round M metrics and regression summaries with the freshly executed ones, and
refuses to write unless every executed hash matches the committed bytes of --runtime."""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "artifacts/preliminary_open_data/"


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    runtime = args.runtime
    reg = read(BASE + "regressions.json")
    assert reg["runtime_unchanged_during_execution"]
    hashes = dict(reg["runtime_sha256"], **{p: sha(p) for p in ("submission/run.py", "submission/requirements.txt")})
    for name, digest in hashes.items():
        assert sha(name) == digest, name
        assert (ROOT / name).read_bytes() == subprocess.check_output(["git", "show", runtime + ":" + name], cwd=ROOT), name
    subprocess.run(["python", str(ROOT / "scripts/sanitize_pytest_evidence.py"), str(ROOT / BASE / "pytest_runtime.xml")], check=True)
    cases = list(ET.parse(ROOT / BASE / "pytest_runtime.xml").getroot().iter("testcase"))
    assert not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = [{"test": c.get("classname") + "." + c.get("name"), "reason": c.find("skipped").get("message")}
               for c in cases if c.find("skipped") is not None]
    tests = {"passed": len(cases) - len(skipped), "failed": 0, "skipped": len(skipped), "skip_reasons": skipped,
             "stage": "Runtime suite complete; the release-consistency test that reads this record is checked separately",
             "scope": "tests/ minus tests/test_current_pre_guide_release.py::test_current_runtime_exact_archive_and_commit",
             "junit": BASE + "pytest_runtime.xml", "junit_sha256": sha(BASE + "pytest_runtime.xml")}
    summary = read("artifacts/round_m/final_summary.json")
    package = "artifacts/verification/nova-pre-guide-v16.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    previous = read("artifacts/verification/CURRENT_RELEASE.json")["current_verification_artifact"]
    result = copy.deepcopy(read(previous))
    result.update(schema="nova-verification-v16", generated_utc=datetime.now(timezone.utc).isoformat(),
                  verified_runtime_sha=runtime, executed_local_runtime_sha=runtime, runtime_sha256=hashes, tests=tests,
                  round_m=summary["metrics"], round_m_artifact="artifacts/round_m/final_summary.json",
                  failure_analysis_artifact="artifacts/round_m/failure_analysis.json",
                  regressions={n: r["summary"] for n, r in reg["suites"].items()},
                  transport_note="Executed bytes recorded by hash; every file matched against the runtime commit.",
                  scope_of_change="Preliminary-round rules (SAY/EXAM/no TEST/SOAP/50 turns, bounded model calls) as state-flag "
                                  "behaviour, plus CC0 Disease Ontology EXACT synonyms as Tier-2 aliases. No disease facts, score "
                                  "weights or labels edited; dev accuracy unchanged (Round M Top1 0.9593).",
                  submission={"zip": package, "bytes": (ROOT / package).stat().st_size, "sha256": sha(package),
                              "status": "LOCAL PRE-GUIDE CANDIDATE ONLY; official transport BLOCKED"})
    for stale in ("rule_matrix", "clinical_review_pass", "clinical_prompt_changed", "clinical_parameters_changed", "clinical_parameter_scope"):
        result.pop(stale, None)
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-v16.json"
    (ROOT / artifact).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    pointer.update(current_verification_artifact=artifact, current_verification_schema=result["schema"], verified_runtime_sha=runtime,
                   previous_verification_artifacts=list(dict.fromkeys([previous] + pointer["previous_verification_artifacts"])))
    (ROOT / "artifacts/verification/CURRENT_RELEASE.json").write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n")
    print(artifact, tests["passed"], "passed", tests["skipped"], "skipped")


if __name__ == "__main__":
    main()
