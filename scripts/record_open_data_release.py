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
BASE = "artifacts/integration/"  # overridden by --base


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def conditions() -> dict:
    """The four result classes are reported SEPARATELY and never merged into one accuracy claim."""
    out = {"mock_regression_all_tests_allowed": "see regressions/round_m in this record (synthetic cases, deterministic mock model, tests allowed, 60 turns)",
           "preliminary_rules_50_turns_no_test": None,
           "real_fixed_model_gpt_oss_20b": "NOT VERIFIED -- no organizer endpoint/credentials/guide available; nothing was run",
           "independent_evaluation": "NOT AVAILABLE -- every case set used here is author-written development/regression data; no untouched independent set exists (blind v19 was invalidated, v20 not authored)"}
    path = ROOT / (BASE + "preliminary_rules_eval.json")
    if path.exists():
        data = json.loads(path.read_text())
        out["preliminary_rules_50_turns_no_test"] = {"result": data.get("preliminary_rules"),
                                                   "unrestricted_development_rules_same_cases": data.get("unrestricted_development_rules"),
                                                   "limitation": data.get("limitation")}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--base", default="artifacts/integration/", help="directory holding regressions.json, pytest_runtime.xml, ...")
    parser.add_argument("--schema", default="nova-verification-v17")
    args = parser.parse_args()
    runtime = args.runtime
    global BASE
    BASE = args.base.rstrip("/") + "/"
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
             "scope": "tests/ minus the three tests that read this record or the freshly refreshed inventory (they are run AFTER the record is written): "
                      "tests/test_current_pre_guide_release.py::test_current_runtime_exact_archive_and_commit, "
                      "tests/test_current_pre_guide_release.py::test_complete_round_m_denominators_and_failure_coverage, "
                      "tests/test_provenance_evidence.py::test_current_inventory_has_complete_hash_coverage_but_no_fake_clearance",
             "junit": BASE + "pytest_runtime.xml", "junit_sha256": sha(BASE + "pytest_runtime.xml")}
    summary = read("artifacts/round_m/final_summary.json")
    package = "artifacts/verification/nova-pre-guide-" + args.schema.rsplit("-", 1)[-1] + ".zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    previous = read("artifacts/verification/CURRENT_RELEASE.json")["current_verification_artifact"]
    result = copy.deepcopy(read(previous))
    result.update(schema=args.schema, generated_utc=datetime.now(timezone.utc).isoformat(),
                  verified_runtime_sha=runtime, executed_local_runtime_sha=runtime, runtime_sha256=hashes, tests=tests,
                  round_m=summary["metrics"], round_m_artifact="artifacts/round_m/final_summary.json",
                  failure_analysis_artifact="artifacts/round_m/failure_analysis.json",
                  regressions={n: r["summary"] for n, r in reg["suites"].items()},
                  transport_note="Executed bytes recorded by hash; every file matched against the runtime commit.",
                  scope_of_change="Integration of PR #15 (clause-level matching, aliases, audit guards) into the preliminary-round line "
                                  "(SAY/EXAM/no TEST/SOAP/50 turns, bounded model calls incl. retries, fixed-LLM wiring, reproducible ZIP). "
                                  "No labels or answers edited; scanner and evaluation data unchanged. Round M numbers are in round_m.",
                  evaluation_conditions=conditions(),
                  submission={"zip": package, "bytes": (ROOT / package).stat().st_size, "sha256": sha(package),
                              "status": "LOCAL PRE-GUIDE CANDIDATE ONLY; official transport BLOCKED"})
    for stale in ("rule_matrix", "clinical_review_pass", "clinical_prompt_changed", "clinical_parameters_changed", "clinical_parameter_scope"):
        result.pop(stale, None)
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-" + args.schema.rsplit("-", 1)[-1] + ".json"
    (ROOT / artifact).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    pointer.update(current_verification_artifact=artifact, current_verification_schema=result["schema"], verified_runtime_sha=runtime,
                   previous_verification_artifacts=list(dict.fromkeys([previous] + pointer["previous_verification_artifacts"])))
    (ROOT / "artifacts/verification/CURRENT_RELEASE.json").write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n")
    print(artifact, tests["passed"], "passed", tests["skipped"], "skipped")


if __name__ == "__main__":
    main()
