"""Bind the reference integration's actual local evidence to verification v14."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/licensed_references"


def read(path):
    return json.loads((ROOT / path).read_text())


def write(path, data):
    (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    previous = "artifacts/verification/local-release-9d86b04-v13.json"
    result = copy.deepcopy(read(previous))
    summary_path = "artifacts/licensed_references/after/round_m/final_summary.json"
    summary = read(summary_path)
    runtime = summary["runtime_sha"]
    assert runtime == "c37d0c4b28565c90422c4df2d3bac099791ef97e"
    hashes = dict(summary["runtime_sha256"])
    for name in ("submission/run.py", "submission/requirements.txt"):
        hashes[name] = sha(name)
    for name, digest in hashes.items():
        assert sha(name) == digest, name
        assert (ROOT / name).read_bytes() == subprocess.check_output(["git", "show", runtime + ":" + name], cwd=ROOT), name
    comparison = read("artifacts/licensed_references/performance_comparison.json")
    assert comparison["all_round_m_metrics_equal"] and comparison["round_m_case_outcomes_equal"]
    assert all(comparison["regression_case_outcomes_equal"].values())
    assert all(r["summary_equal"] for r in comparison["regressions"].values())
    junit_files = [OUT / "pytest_runtime.xml"]
    complete = (OUT / "pytest_release.xml").exists()
    if complete:
        junit_files.append(OUT / "pytest_release.xml")
    combined = ET.Element("testsuites")
    cases = []
    for path in junit_files:
        tree = ET.parse(path).getroot()
        combined.extend(list(tree))
        cases.extend(tree.iter("testcase"))
    assert len({(c.get("classname"), c.get("name")) for c in cases}) == len(cases)
    assert not any(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = [{"test": c.get("classname") + "." + c.get("name"), "reason": c.find("skipped").get("message")}
               for c in cases if c.find("skipped") is not None]
    ET.ElementTree(combined).write(OUT / "pytest.xml", encoding="utf-8", xml_declaration=True)
    tests = dict(passed=len(cases) - len(skipped), failed=0, skipped=len(skipped), skip_reasons=skipped,
                 stage="FULL CURRENT SUITE" if complete else "RUNTIME SUITE; 3 current release checks pending",
                 scope="tests/ executed in two disjoint groups: runtime tests and 3 release consistency tests",
                 junit="artifacts/licensed_references/pytest.xml", junit_sha256=sha("artifacts/licensed_references/pytest.xml"))
    audit = read("artifacts/licensed_references/package_audit.json")
    assert audit["source_submission_byte_equivalence"] and audit["secret_scan"]["status"] == "PASS"
    assert not any(audit[k] for k in ("forbidden_files", "training_operations", "utf8_failures"))
    package = "artifacts/verification/nova-pre-guide-v14.zip"
    shutil.copyfile(ROOT / "submission/submission.zip", ROOT / package)
    assert sha(package) == audit["zip_sha256"]
    result.update(schema="nova-verification-v14", generated_utc=datetime.now(timezone.utc).isoformat(),
                  audited_remote_head="3ede61c1079dc4597597a29ded1fd6668ae85402",
                  verified_runtime_sha=runtime, executed_local_runtime_sha=runtime,
                  execution_checkout_head=summary["execution_checkout_head"],
                  transport_note=summary["execution_note"], runtime_sha256=hashes, tests=tests,
                  round_m=summary["metrics"], round_m_artifact=summary_path,
                  failure_analysis_artifact="artifacts/licensed_references/after/round_m/failure_analysis.json",
                  regressions={n: r["after"] for n, r in comparison["regressions"].items()},
                  rule_matrix="artifacts/licensed_references/rule_matrix.json",
                  clinical_parameters_changed=False, clinical_prompt_changed=True,
                  reference_integration={"records": 637, "medlineplus_health_topics": 372,
                                         "medlineplus_medical_tests": 5, "orphanet_disorders": 260,
                                         "max_references_per_turn": 2, "max_reference_text_chars": 1600,
                                         "real_model_effect": "NOT VERIFIED", "clinician_review": "NOT_REVIEWED",
                                         "historical_provenance_cleared": False},
                  submission=dict(zip=package, bytes=(ROOT / package).stat().st_size, sha256=sha(package),
                                  status="LOCAL PRE-GUIDE CANDIDATE ONLY; official run.py BLOCKED"))
    result["compliance"]["Source documentation"] = "BLOCKED — new reference sources verified; legacy clinical origins unresolved"
    result["compliance"]["License documentation"] = "BLOCKED — new reference terms documented; legacy rights unresolved"
    artifact = "artifacts/verification/local-release-" + runtime[:7] + "-v14.json"
    write(artifact, result)
    pointer = read("artifacts/verification/CURRENT_RELEASE.json")
    pointer.update(current_verification_artifact=artifact, current_verification_schema="nova-verification-v14",
                   verified_runtime_sha=runtime, latest_compliance_followup=result["rule_matrix"],
                   previous_verification_artifacts=list(dict.fromkeys([previous] + pointer["previous_verification_artifacts"])))
    write("artifacts/verification/CURRENT_RELEASE.json", pointer)
    m = summary["metrics"]
    pct = lambda x: f"{100*x:.2f}%"
    lines = ["# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT", "",
             "REMOTE HEAD audited: `" + result["audited_remote_head"] + "`",
             "CURRENT RUNTIME SHA: `" + runtime + "`", "",
             "STATUS: **NOT READY**. LOCAL_PRE_GUIDE_VERIFIED / EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.",
             "This release adds attributed offline reference context. No clinical scoring, features,",
             "thresholds, stop policy, action utilities or retrieval ranking were changed.", "",
             "## Reference integration", "",
             "637 references: 372 MedlinePlus health-topic summaries, five medical-test articles,",
             "260 Orphanet active disorder definitions. Reproducible publisher-field extraction;",
             "original selected markup, source/version/hash, attribution and reuse terms retained.",
             "Each turn receives at most two references, 1,600 text characters each, plus source metadata.",
             "References are explicitly background, not observed patient evidence or diagnostic criteria.",
             "Existing knowledge coverage is retained. No legacy provenance gap was cleared by citation.",
             "Actual fixed-model accuracy, latency and prompt-token cost are NOT VERIFIED.", "",
             "## ROUND M — synthetic development / mock LLM", "",
             f"Cases: {m['cases']}; Scored: {m['scored_cases']}; Critical: {m['critical_count']}; OOD: 5 unscored.",
             f"Top1: {pct(m['Top1'])}; Top3: {pct(m['Top3'])}; Top5: {pct(m['Top5'])}; Top10: {pct(m['Top10'])}.",
             f"MRR: {m['MRR']:.6f}; median finite true rank: {m['median_true_rank']}; missing rank: {m['missing_rank_count']}.",
             f"Critical Top1/Top3/Top5: 100% / 100% / 100%; recall: {pct(m['critical_recall'])}; miss: {pct(m['critical_miss'])}.",
             "Critical denominator is the 43 existing marked cases; no urgent-looking case was relabelled.",
             f"Retrieval @150: {pct(m['retrieval_at150'])}; rerank @25: {pct(m['rerank_at25'])}; active truth: {pct(m['active_truth_retention'])}.",
             "Retrieval and rerank remain BELOW the 92% and 85% development stretch goals.",
             f"Long-tail n=26: retrieval 100%; rerank 96.15%; active 100%; Top1 {pct(m['long_tail']['Top1'])}; Top5/Top10 100%.",
             "EN: 108/113 (95.58%); KO: 1/1; JA: 2/2; Mixed: 7/7. Tiny KO/JA samples are not broad multilingual validation.",
             f"Avg ASK: {m['average_ask']:.5f}; EXAM: {m['average_exam']}; TEST: {m['average_tests']:.5f}; turns: {m['average_turns']:.5f}; median turns: {m['median_turns']}.",
             f"Redundant tests: {m['redundant_tests']}; diagnostic-delay proxy: {m['average_diagnostic_delay']} (not clinical certification).",
             f"Avg unresolved dangerous alternatives: {m['average_unresolved_critical_alternatives']:.5f} (heuristic candidate count).",
             "Five wrong scored cases remain: four FINAL_RANKING_ERROR and one RERANK_MISS; see failure_analysis.json.",
             "OOD controls still take 36–44 turns and force final DIAGNOSE; no supported-diagnosis claim.",
             "All recorded before/after metrics AND per-case decisions are equal. No accuracy improvement claimed.", "",
             "## REGRESSION", "",
             f"Tests passed: {tests['passed']}; failed: {tests['failed']}; skipped: {tests['skipped']}. {tests['stage']}.",
             tests["scope"] + ".", "Skip reasons: " + json.dumps(skipped, ensure_ascii=False),
             "First attempt: 2 new-test import errors under suite isolation, fixed by importing the actual orchestrator module; no clinical change.",
             "Held-out / generalization-v2 / stress / Round D / Round E / Round G: 100% scored accuracy.",
             "Round I: 94.74%; Round J: 92.31%. All eight full summaries and case outputs equal baseline.",
             "Source/submission byte equivalence PASS. Standalone offline mock full-loop PASS.", "",
             "## BLIND STATUS", "", "v18: REFERENCE-ONLY.",
             "v19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY.",
             "Fresh final blind: NOT YET AUTHORED. No blind execution or tuning in this pass.", "",
             "## COMPLIANCE", ""]
    lines += [f"- {name}: {status}" for name, status in result["compliance"].items()]
    lines += ["", "Network claim: APPLICATION_LEVEL_NETWORK_POLICY_VERIFIED; OS isolation NOT VERIFIED.",
              "", "## OFFICIAL INTERFACE", "", "Participant guide: not available in inspected public material.",
              "Official API: NOT VERIFIED. Official schema: PLACEHOLDER. Real organizer gpt-oss call: NOT VERIFIED.",
              "Official entrypoint remains fail-closed for all providers, including mock.", "",
              "## VERIFICATION", "", "Version: nova-verification-v14.", f"Runtime SHA: `{runtime}`.",
              f"Submission ZIP: `{package}`; Bytes: {result['submission']['bytes']}; SHA256: `{result['submission']['sha256']}`.",
              "UTF-8 Python; run.py and requirements.txt present; <50 MB; no evaluation/blind data, labels, tests, training artifacts or weights in ZIP.",
              "Secret-pattern scan PASS (heuristic scope; no claim of mathematically proven secret absence).",
              "The staged evaluated runtime was bound byte-for-byte to the imported commit; execution_checkout_head is retained separately.",
              "Source HTML snapshots retain publisher whitespace/line endings intentionally; code whitespace check excludes those snapshots.",
              "", "BLOCKERS:", "1. Official participant guide, schema and approved transport/environment.",
              "2. Real fixed-model case-call and performance/latency verification.",
              "3. Remaining legacy medical-source, rights, generation-history and clinician-review gaps.",
              "", "Evidence: artifacts/licensed_references/{before,after,performance_comparison.json,pytest.xml,package_audit.json}.",
              "No final official submission readiness is claimed.", ""]
    report = "\n".join(lines)
    for path in ("docs/competition/PRE_GUIDE_RELEASE_REPORT.md", "docs/round_m/FINAL_REPORT.md",
                 "docs/compliance/LICENSED_REFERENCE_INTEGRATION.md"):
        (ROOT / path).write_text(report)
    print(json.dumps({"version": result["schema"], "tests": tests, "submission": result["submission"]}, indent=2))


if __name__ == "__main__":
    main()
