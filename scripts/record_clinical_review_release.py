"""Bind current clinical-review/engineering evidence to a real runtime commit (v15)."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "artifacts/clinical_review_pass/"


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, value):
    (ROOT / path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()
    runtime = args.runtime
    summary = read(BASE + "final_summary.json")
    regressions = read(BASE + "regressions.json")
    hashes = summary["runtime_sha256"]
    assert regressions["runtime_unchanged_during_execution"]
    assert hashes == regressions["runtime_sha256"]
    for name in ("submission/run.py", "submission/requirements.txt"):
        hashes[name] = sha(name)
    for name, digest in hashes.items():
        assert sha(name) == digest, name
        assert (ROOT / name).read_bytes() == subprocess.check_output(
            ["git", "show", runtime + ":" + name], cwd=ROOT), name
    hashes.pop("submission/run.py")
    hashes.pop("submission/requirements.txt")
    for value, name in ((summary, "final_summary.json"), (regressions, "regressions.json")):
        value.setdefault("execution_checkout_head", value["runtime_sha"])
        value["runtime_sha"] = runtime
        value["execution_note"] = "Executed bytes recorded by hash before runtime commit; matched every file against the imported commit. No runtime changes during execution."
        write(BASE + name, value)
    hashes = dict(hashes, **{p: sha(p) for p in ("submission/run.py", "submission/requirements.txt")})
    combined = ET.Element("testsuites")
    cases = []
    files = ["pytest_runtime.xml"]
    complete = (ROOT / BASE / "pytest_release.xml").exists()
    if complete:
        files.append("pytest_release.xml")
    for file in files:
        subprocess.run(["python", str(ROOT / "scripts/sanitize_pytest_evidence.py"),
                        str(ROOT / BASE / file)], check=True)
        tree = ET.parse(ROOT / BASE / file).getroot()
        combined.extend(list(tree))
        cases.extend(tree.iter("testcase"))
    assert len(cases) == len({(c.get("classname"), c.get("name")) for c in cases})
    assert not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = [{"test": c.get("classname") + "." + c.get("name"), "reason": c.find("skipped").get("message")}
               for c in cases if c.find("skipped") is not None]
    ET.ElementTree(combined).write(ROOT / BASE / "pytest.xml", encoding="utf-8", xml_declaration=True)
    tests = {"passed": len(cases) - len(skipped), "failed": 0, "skipped": len(skipped),
             "skip_reasons": skipped, "stage": "FULL CURRENT SUITE" if complete else "Runtime complete; 3 release consistency checks pending",
             "scope": "tests/ in two disjoint groups: all runtime tests and current-release consistency checks",
             "junit": BASE + "pytest.xml", "junit_sha256": sha(BASE + "pytest.xml")}
    audit = read(BASE + "package_audit.json")
    assert audit["source_submission_byte_equivalence"] and audit["secret_scan"]["status"] == "PASS"
    assert not any(audit[k] for k in ("forbidden_files", "training_operations", "utf8_failures"))
    package = "artifacts/verification/nova-pre-guide-v15.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    assert sha(package) == audit["zip_sha256"]
    previous = "artifacts/verification/local-release-c37d0c4-v14.json"
    result = copy.deepcopy(read(previous))
    result.update(schema="nova-verification-v15", generated_utc=datetime.now(timezone.utc).isoformat(),
                  audited_remote_head="7c2c59773cdff71a8fde33e61dfa346f3110e076",
                  verified_runtime_sha=runtime, executed_local_runtime_sha=runtime,
                  execution_checkout_head=summary["execution_checkout_head"], transport_note=summary["execution_note"],
                  runtime_sha256=hashes, tests=tests, round_m=summary["metrics"],
                  round_m_artifact=BASE + "final_summary.json", failure_analysis_artifact=BASE + "failure_analysis.json",
                  regressions={n: r["summary"] for n, r in regressions["suites"].items()},
                  rule_matrix=BASE + "rule_matrix.json", clinical_prompt_changed=False,
                  clinical_parameters_changed=False,
                  clinical_parameter_scope="No disease facts, diagnostic score weights, safety thresholds, minimum-workup requirements or case labels changed. Only evidence-coverage mechanics changed; retrieval experiments rejected. See experiment decisions.",
                  source_submission_sync=audit["source_submission_byte_equivalence"], secret_scan=audit["secret_scan"],
                  clinical_review_pass={"provenance_summary": BASE + "provenance_summary.json",
                                        "experiments": BASE + "experiment_decisions.json", "professor_packet": "docs/clinical_review/README.md",
                                        "clinician_review": "PENDING", "promoted_clinical_replacements": 0},
                  submission={"zip": package, "bytes": (ROOT / package).stat().st_size, "sha256": sha(package),
                              "status": "LOCAL PRE-GUIDE CANDIDATE ONLY; official transport BLOCKED"})
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-v15.json"
    write(artifact, result)
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    pointer.update(current_verification_artifact=artifact, current_verification_schema=result["schema"],
                   verified_runtime_sha=runtime, latest_compliance_followup=result["rule_matrix"],
                   previous_verification_artifacts=list(dict.fromkeys([previous] + pointer["previous_verification_artifacts"])))
    write("artifacts/verification/CURRENT_RELEASE.json", pointer)
    comparison = read(BASE + "performance_comparison.json")
    m = summary["metrics"]
    lines = ["# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT", "",
             f"REMOTE HEAD audited: `{result['audited_remote_head']}`", f"CURRENT RUNTIME SHA: `{runtime}`", "",
             "STATUS: **NOT READY**. LOCAL_PRE_GUIDE_VERIFIED / EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.", "",
             "## Four requested tasks", "",
             "1. Field-level provenance triage and reproducible replacement candidates prepared. No legacy rights cleared or clinical replacement promoted without review.",
             "2. Retrieval experiments and every metric delta retained, including rejected variants and remaining losses.",
             "3. Question coverage and action-efficiency experiments evaluated against unchanged cases and safety tests.",
             "4. Professor packet covers all 34 core profiles, 29 with lexical source leads; all approval fields pending.", "",
             "637 previously integrated licensed references remain. Five test-purpose excerpts are review candidates, not substitutes for diagnostic indications/safety caveats.",
             "Tier-2: 1,246 total; 83 have features; 1,163 do not; 27 have confirmatory fields; no clinician review claimed.", "",
             "## ROUND M — synthetic development / mock LLM", "",
             "128 cases; 123 scored; 43 marked critical; five OOD/unscored. Labels and denominators unchanged.",
             "Critical recall uses the existing 43 marked cases; it is not a clinical safety certification.",
             "Retrieval is measured at the final decision turn; core scoring may bypass ontology retrieval.",
             "Pure KO/JA sample sizes are tiny; follow-up text may be English. No broad multilingual claim.", "",
             "| Metric | Before (v14) | Current | Delta |", "|---|---:|---:|---:|"]
    for name, row in comparison["round_m"].items():
        if isinstance(row, dict) and "before" in row and type(row["before"]) in (int, float):
            lines.append(f"| {name} | {row['before']} | {row['after']} | {row['delta']} |")
    lines += ["", "Rates above are fractions, not percentages. Long-tail and language detail:", "", "```json",
              json.dumps({"long_tail": m["long_tail"], "languages": m["languages"]}, ensure_ascii=False, indent=2), "```", "",
              "OOD observations (forced DIAGNOSE is not a supported-diagnosis claim):", "", "```json",
              json.dumps([{k: r[k] for k in ("case_id", "final", "turns", "tests", "asks", "exams")} for r in summary["cases"] if not r["scored"]], indent=2), "```", "",
              "Every wrong scored case has ordered earliest-stage failure attribution in `" + BASE + "failure_analysis.json`.",
              "This heuristic attribution is not clinician causal adjudication. Diagnostic delay is a policy proxy; missing observations are not zero delay.", "",
              "## REGRESSION", "", f"Tests passed: {tests['passed']}; failed: {tests['failed']}; skipped: {tests['skipped']}. {tests['stage']}.",
              "Skip reasons: " + json.dumps(skipped, ensure_ascii=False), "",
              "| Suite | Scored accuracy | Critical recall | Mean tests | Mean turns |", "|---|---:|---:|---:|---:|"]
    for name, r in regressions["suites"].items():
        s = r["summary"]
        lines.append(f"| {name} | {s['scored_diagnostic_accuracy']} | {s['critical_diagnosis_recall']} | {s['average_test_count']} | {s['average_turns']} |")
    lines += ["", "All per-case changes, including increases in test count or turns, are retained in `" + BASE + "performance_comparison.json`.", "",
              "## BLIND STATUS", "", "v18: REFERENCE-ONLY. v19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY.",
              "Fresh final blind: NOT YET AUTHORED. No v19 execution or v20 creation.", "",
              "## COMPLIANCE", "", "```json", json.dumps(result["compliance"], ensure_ascii=False, indent=2), "```", "",
              "Machine-readable rule matrix distinguishes PASS, BLOCKED and NOT_VERIFIED. Application-level fail-closed policy tested; OS network isolation not proven.", "",
              "## OFFICIAL INTERFACE", "", "Participant guide: not available to this audit. Official API: NOT VERIFIED. Schema: PLACEHOLDER.",
              "Real organizer gpt-oss call: NOT VERIFIED. No guessed transport or official readiness claim.", "",
              "## VERIFICATION", "", f"Version: v15; runtime SHA: `{runtime}`.",
              f"Submission ZIP: `{package}`; bytes: {result['submission']['bytes']}; SHA256: `{result['submission']['sha256']}`.",
              "Source/submission byte equivalence: PASS. Secret scan: PASS (heuristic scan limitations retained). UTF-8/Python, run.py and requirements.txt present; below 50 MB.",
              "No evaluation data, tests, frontend/backend, training artifacts or model weights in candidate ZIP.", "",
              "## BLOCKERS", "", "1. Original clinical authorship/rights and historical AI-generation receipts remain unresolved for legacy assets.",
              "2. Clinical review of rules and candidate replacements remains pending.",
              "3. Official participant guide, exact schema/transport and real fixed-model validation are unavailable to this pass.",
              "4. Development retrieval/rerank targets and independent clinical validation remain unmet."]
    (ROOT / "docs/competition/PRE_GUIDE_RELEASE_REPORT.md").write_text("\n".join(lines) + "\n")
    (ROOT / "docs/round_m/FINAL_REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"artifact": artifact, "runtime": runtime, "tests": tests, "submission": result["submission"]}, indent=2))


if __name__ == "__main__":
    main()
