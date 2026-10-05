# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT

REMOTE HEAD audited: `3ede61c1079dc4597597a29ded1fd6668ae85402`
CURRENT RUNTIME SHA: `c37d0c4b28565c90422c4df2d3bac099791ef97e`

STATUS: **NOT READY**. LOCAL_PRE_GUIDE_VERIFIED / EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.
This release adds attributed offline reference context. No clinical scoring, features,
thresholds, stop policy, action utilities or retrieval ranking were changed.

## Reference integration

637 references: 372 MedlinePlus health-topic summaries, five medical-test articles,
260 Orphanet active disorder definitions. Reproducible publisher-field extraction;
original selected markup, source/version/hash, attribution and reuse terms retained.
Each turn receives at most two references, 1,600 text characters each, plus source metadata.
References are explicitly background, not observed patient evidence or diagnostic criteria.
Existing knowledge coverage is retained. No legacy provenance gap was cleared by citation.
Actual fixed-model accuracy, latency and prompt-token cost are NOT VERIFIED.

## ROUND M — synthetic development / mock LLM

Cases: 128; Scored: 123; Critical: 43; OOD: 5 unscored.
Top1: 95.93%; Top3: 98.37%; Top5: 99.19%; Top10: 99.19%.
MRR: 0.973577; median finite true rank: 1.0; missing rank: 1.
Critical Top1/Top3/Top5: 100% / 100% / 100%; recall: 100.00%; miss: 0.00%.
Critical denominator is the 43 existing marked cases; no urgent-looking case was relabelled.
Retrieval @150: 84.55%; rerank @25: 72.36%; active truth: 99.19%.
Retrieval and rerank remain BELOW the 92% and 85% development stretch goals.
Long-tail n=26: retrieval 100%; rerank 96.15%; active 100%; Top1 92.31%; Top5/Top10 100%.
EN: 108/113 (95.58%); KO: 1/1; JA: 2/2; Mixed: 7/7. Tiny KO/JA samples are not broad multilingual validation.
Avg ASK: 9.90625; EXAM: 6; TEST: 8.99219; turns: 25.89844; median turns: 20.5.
Redundant tests: 0; diagnostic-delay proxy: 0 (not clinical certification).
Avg unresolved dangerous alternatives: 11.39062 (heuristic candidate count).
Five wrong scored cases remain: four FINAL_RANKING_ERROR and one RERANK_MISS; see failure_analysis.json.
OOD controls still take 36–44 turns and force final DIAGNOSE; no supported-diagnosis claim.
All recorded before/after metrics AND per-case decisions are equal. No accuracy improvement claimed.

## REGRESSION

Tests passed: 1024; failed: 0; skipped: 1. FULL CURRENT SUITE.
tests/ executed in two disjoint groups: runtime tests and 3 release consistency tests.
Skip reasons: [{"test": "tests.test_learning_training.test_torch_training_and_checkpoint_roundtrip", "reason": "torch not installed (IMPLEMENTED_BUT_NOT_EXECUTED)"}]
First attempt: 2 new-test import errors under suite isolation, fixed by importing the actual orchestrator module; no clinical change.
Held-out / generalization-v2 / stress / Round D / Round E / Round G: 100% scored accuracy.
Round I: 94.74%; Round J: 92.31%. All eight full summaries and case outputs equal baseline.
Source/submission byte equivalence PASS. Standalone offline mock full-loop PASS.

## BLIND STATUS

v18: REFERENCE-ONLY.
v19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY.
Fresh final blind: NOT YET AUTHORED. No blind execution or tuning in this pass.

## COMPLIANCE

- Fixed model configured: PASS
- Fixed revision configured: PASS
- Fine-tuning absent: PASS
- 60-turn hard cap: PASS
- Official 4 actions only: PASS
- Case-related LLM success gate: BLOCKED — organizer receipt semantics/transport not provided; development JSON validity is separate
- Competition provider lock: PASS
- No online private-case learning: PASS
- Case isolation: PASS
- Static retrieval: PASS
- Secret scan: PASS
- Source documentation: BLOCKED — new reference sources verified; legacy clinical origins unresolved
- License documentation: BLOCKED — new reference terms documented; legacy rights unresolved
- LLM-generation log: FAIL — log exists, historical exact model/prompt records unresolved

Network claim: APPLICATION_LEVEL_NETWORK_POLICY_VERIFIED; OS isolation NOT VERIFIED.

## OFFICIAL INTERFACE

Participant guide: not available in inspected public material.
Official API: NOT VERIFIED. Official schema: PLACEHOLDER. Real organizer gpt-oss call: NOT VERIFIED.
Official entrypoint remains fail-closed for all providers, including mock.

## VERIFICATION

Version: nova-verification-v14.
Runtime SHA: `c37d0c4b28565c90422c4df2d3bac099791ef97e`.
Submission ZIP: `artifacts/verification/nova-pre-guide-v14.zip`; Bytes: 669068; SHA256: `63997e4cd3ac8ac06450b9abb7c3401309e9184c65eb131732930d186ae96e2f`.
UTF-8 Python; run.py and requirements.txt present; <50 MB; no evaluation/blind data, labels, tests, training artifacts or weights in ZIP.
Secret-pattern scan PASS (heuristic scope; no claim of mathematically proven secret absence).
The staged evaluated runtime was bound byte-for-byte to the imported commit; execution_checkout_head is retained separately.
Source HTML snapshots retain publisher whitespace/line endings intentionally; code whitespace check excludes those snapshots.

BLOCKERS:
1. Official participant guide, schema and approved transport/environment.
2. Real fixed-model case-call and performance/latency verification.
3. Remaining legacy medical-source, rights, generation-history and clinician-review gaps.

Evidence: artifacts/licensed_references/{before,after,performance_comparison.json,pytest.xml,package_audit.json}.
No final official submission readiness is claimed.
