# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT

REMOTE HEAD (at recovery): `677c944e5fbab602bcb8d9580358ad6a80df6cc7`

CURRENT RUNTIME SHA: `9b607b49c56e64b072645f1539d53d1ca4b92c74`

This is an offline mock-LLM synthetic development result, not an official score or clinical validation.

Transport note: Git CLI push had no credentials. Connected GitHub API created a commit with exactly the same Git tree (4eb14c58e89076c8f10a6c4df7139fefd9eac0a6). Only author/commit metadata differs; evaluation/runtime bytes are unchanged.

## ROUND M

Cases: 128
Scored: 123
Critical: 43

| Metric | Current result |
|---|---:|
| Top1 | 95.93% |
| Top3 | 98.37% |
| Top5 | 99.19% |
| Top10 | 99.19% |
| Critical Top1 | 100.00% |
| Critical Top3 | 100.00% |
| Critical Top5 | 100.00% |
| Critical recall | 100.00% |
| Critical miss | 0.00% |
| Retrieval @150 | 84.55% |
| Rerank @25 | 72.36% |
| Active truth | 99.19% |
| MRR | 0.97358 |
| Median true rank (finite only) | 1.0 |
| Missing final truth ranks | 1 |
| Long-tail retrieval_at150 (n=26) | 100.00% |
| Long-tail rerank_at25 (n=26) | 96.15% |
| Long-tail active (n=26) | 100.00% |
| Long-tail Top10 (n=26) | 100.00% |
| Long-tail Top5 (n=26) | 100.00% |
| Long-tail Top1 (n=26) | 92.31% |
| EN accuracy (n=113) | 95.58% |
| KO accuracy (n=1) | 100.00% |
| JA accuracy (n=2) | 100.00% |
| Mixed accuracy (n=7) | 100.00% |
| Avg ASK | 9.90625 |
| Avg EXAM | 6 |
| Avg TEST | 8.9921875 |
| Avg turns | 25.8984375 |
| Median turns | 20.5 |
| Redundant TEST actions | 0 |
| Avg diagnostic delay | 0 |
| Avg unresolved critical alternatives | 11.390625 |

Diagnostic delay is measured against the first policy-eligible unforced stop, not a clinically adjudicated safe stopping point. Critical recall means correct final diagnosis among the unchanged critical labels, not merely inclusion in top-k. Critical-like Tier-2 tags are not silently moved into that denominator. The missed ovarian-torsion development case is outside the inherited 43-case critical subset: 100% critical recall therefore does NOT mean every medically urgent presentation was correct. Language partition is by chief complaint; follow-up evidence often uses English.

### Development goals (not release score manipulation)

| Goal | Actual | Met |
|---|---:|---|
| Top1 ≥ 95.00% | 95.93% | True |
| Top3 ≥ 97.00% | 98.37% | True |
| Top5 ≥ 98.00% | 99.19% | True |
| retrieval_at150 ≥ 92.00% | 84.55% | False |
| rerank_at25 ≥ 85.00% | 72.36% | False |
| active_truth_retention ≥ 98.00% | 99.19% | True |
| critical_recall ≥ 98.00% | 100.00% | True |

### Failure analysis

Ordered earliest observable terminal-pipeline failure, followed by heuristic evidence/action/stop/ranking attribution. Full traces are retained; this is not clinician causal adjudication.

| Failure class | Count |
|---|---:|
| RETRIEVAL_MISS | 0 |
| RERANK_MISS | 1 |
| ACTIVE_SET_MISS | 0 |
| EVIDENCE_EXTRACTION_ERROR | 0 |
| EVIDENCE_WEIGHTING_ERROR | 0 |
| ACTION_SELECTION_ERROR | 0 |
| FINAL_RANKING_ERROR | 4 |
| STOP_POLICY_ERROR | 0 |
| PROTOCOL_OR_OOD_ERROR | 0 |

All wrong scored cases: `artifacts/round_m/failure_analysis.json`. No labels, difficulty, scoring flags or OOD membership changed. General correction in this pass: punctuation-bounded negative clauses no longer invert preceding positive evidence. Remaining misses are retained, not patched with case IDs/answers.

### Change comparison

Initial saved predictions were re-scored with the corrected alias matcher. This is a descriptive comparison; the initial baseline was not byte-attested. Historical raw accuracy numbers using the old embedded-acronym matcher must not be treated as directly comparable validation.

| Metric | Re-scored initial outputs | Current |
|---|---:|---:|
| diagnosis_accuracy | 0.951220 | 0.959350 |
| critical_recall | 1.000000 | 1.000000 |
| average_tests | 9.046875 | 8.992188 |
| average_turns | 26.132812 | 25.898438 |

Unresolved critical alternatives count every active danger-flagged candidate not marked resolved, including weak/unsupported ontology alternatives. It is a workload/safety review signal, not the critical diagnosis miss rate.

### OOD

Five Round M controls remain unscored. See `artifacts/round_m/round_m_ood.json` for their full-loop internal/wire outcomes; the separate broader snapshot benchmark is `artifacts/round_m/ood.json`. Internal uncertainty always remains within four wire actions.

- supported_false_ood: 0/12 (0.00%)
- ood_detection: 6/8 (75.00%)
- unsupported_uncertainty_detection: 20/20 (100.00%)
- insufficient_information: 23/32 (71.88%)
- forced_protocol_diagnosis: 29/32 (90.62%)
- unsafe_confident_diagnosis_proxy: 0/20 (0.00%)
- supported_evidenced_acceptance: 3/4 (75.00%)

Round M full-loop controls:

| Case | Internal outcome | Turns |
|---|---|---:|
| RoundM_124 | INSUFFICIENT_INFORMATION | 44 |
| RoundM_125 | INSUFFICIENT_INFORMATION | 44 |
| RoundM_126 | INSUFFICIENT_INFORMATION | 36 |
| RoundM_127 | INSUFFICIENT_INFORMATION | 40 |
| RoundM_128 | INSUFFICIENT_INFORMATION | 44 |

These controls can take many turns and do not necessarily classify as OUT_OF_DOMAIN. This remains an efficiency/uncertainty weakness, not a passed diagnostic accuracy case.

## REGRESSION

Tests passed: 962  
Tests failed: 0  
Tests skipped: 1

- `tests.test_learning_training.test_torch_training_and_checkpoint_roundtrip`: torch not installed (IMPLEMENTED_BUT_NOT_EXECUTED). Optional hospital training subsystem is excluded from competition ZIP; no training was run.

`pytest tests` covers all root Doctor Agent/production tests. Bare repository-root discovery also collects a frontend bridge script that invokes unavailable Vitest; that initial collection error was not counted as a successful suite. Frontend/backend deployment and optional GPU training are outside this Doctor Agent package.

| Suite | Cases / scored | Accuracy | Critical recall | Avg TEST | Avg turns |
|---|---:|---:|---:|---:|---:|
| held_out | 18 / 15 | 100.00% | 100.00% | 9.22 | 29.83 |
| generalization_v2 | 18 / 18 | 100.00% | 100.00% | 7.28 | 21.39 |
| stress | 8 / 8 | 100.00% | 100.00% | 9.62 | 26.12 |
| round_d | 7 / 6 | 100.00% | 100.00% | 13.43 | 34.29 |
| round_e | 7 / 6 | 100.00% | 100.00% | 11.71 | 32.29 |
| round_g | 12 / 12 | 100.00% | 100.00% | 9.17 | 23.58 |
| round_i | 20 / 19 | 94.74% | 100.00% | 6.90 | 19.20 |
| round_j | 54 / 52 | 92.31% | 100.00% | 8.07 | 24.35 |

OOD, multilingual, retrieval, routing, specificity, adversarial, invariance, competition boundaries and standalone checks are covered by the executed tests and supplemental artifacts. Retrieval/routing results are recorded separately; they are not substituted for diagnosis accuracy.

Separate 44-case retrieval probe (not Round M):

| Input | Recall @20 | Recall @50 | Recall @150 |
|---|---:|---:|---:|
| chief_complaint_only | 50.0% | 61.4% | 61.4% |
| chief_complaint_plus_history | 50.0% | 75.0% | 90.9% |

## BLIND STATUS

v18: REFERENCE-ONLY (historical).

v19: NOT EXECUTED; PREEXECUTION INVALIDATED / REFERENCE-ONLY. No attempt/results/manifest created.

Fresh final blind: NOT YET AUTHORED. No v20.

## COMPLIANCE

| Check | Status |
|---|---|
| Fixed model configured | PASS |
| Fixed revision configured | PASS |
| Fine-tuning absent | PASS |
| 60-turn hard cap | PASS |
| Official 4 actions only | PASS |
| Case-related LLM success gate | PASS |
| Competition provider lock | PASS |
| No online private-case learning | PASS |
| Case isolation | PASS |
| Static retrieval | PASS |
| Secret scan | PASS |
| Source documentation | FAIL — inventory complete, medical sources unresolved |
| License documentation | FAIL — exact licenses/research permission unresolved |
| LLM-generation log | FAIL — log exists, historical exact model/prompt records unresolved |

PASS for the call gate/provider lock means local fail-closed behavior, not a successful organizer call. Model/revision constants are configured, but actual weights are not attested.

Tier-2 audit: tier2_total=1246, tier2_enriched=83, tier2_unenriched=1163, tier2_with_confirmatory_findings=27, tier2_with_provenance_metadata=83, tier2_with_verified_medical_provenance=0. Global authorship metadata is not verified medical provenance.

## OFFICIAL INTERFACE

Participant guide: NOT YET AVAILABLE in supplied/public materials.  
Official API: NOT VERIFIED.  
Official schema: PLACEHOLDER.  
Real organizer gpt-oss call: NOT VERIFIED.

## VERIFICATION

Version: nova-verification-v12  
Runtime SHA: `9b607b49c56e64b072645f1539d53d1ca4b92c74`  
Submission ZIP: `artifacts/verification/nova-pre-guide-v12.zip`  
Bytes: 285023  
SHA256: `2b1971c95c78f8fa2371ecdb190628cc11f4c0be785d02473925043475abd389`

Source/submission byte equivalence: PASS. ZIP has run.py/requirements.txt, UTF-8 Python, under 50 MB, no evaluation/blind/test/frontend/backend/training/weight files or detected credentials. Generic development client definitions remain in the identical source mirror but are unreachable through the locked submission entrypoint.

## STATUS

**NOT READY** for official submission.

Local engineering status: LOCAL_PRE_GUIDE_VERIFIED.  
External status: EXTERNAL_OFFICIAL_INTERFACE_BLOCKED.

BLOCKERS:
1. Official participant guide, exact transport/schema/invocation and sample environment not provided; submission network path intentionally blocked.
2. Real organizer gpt-oss call and fixed-weight revision not verified; stubs/mock do not count.
3. Clinical source provenance, research-use licenses and original generation records remain unresolved; candidate is not cleared for official submission.
4. Round M development weaknesses and small multilingual sample sizes remain; no independent clinical accuracy claim.
5. No current untouched fresh blind; v19 pre-execution invalidated, v20 not authored.

Next cycle: official guide audit → exact adapter/schema → organizer fixed-model smoke test → public sample benchmark → final accuracy/safety/efficiency tuning → full regression → final runtime freeze → fresh blind authored after freeze → hash/leakage review → one-shot blind → final verification → official ZIP.

## Compliance repair follow-up (2026-10-04 UTC)

See `docs/compliance/REPAIR_EXECUTION_REPORT.md` and
`artifacts/compliance_repair/execution_summary.json` for packaging/secret-audit fixes,
expanded license evidence, current test results and the rejected retrieval experiment.
The reasoning runtime and historical v12 ZIP remain byte-unchanged. The follow-up
ZIP has explicit pre-guide-only metadata; it is not an official submission.
