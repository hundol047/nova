# N.O.V.A. FINAL STABILIZATION + BLIND v17 REPORT

Branch: `offline/nova-competition-agent-optimization`  
Final reasoning SHA: `1046986c04e40d1c8b0d995adf1ab0e866724f3d`  
Blind v17 authoring / first-run SHA: `cf9970a0ba893d99b53f971a8ee6222cda29347b`  
Verification artifact introducing SHA and final remote head: recorded in `PUSH_RECEIPT.json` after publication.

## Release consistency

v16 is REFERENCE-ONLY; its four historical case/manifest/result files retain their original SHA-256 hashes. v17 is CURRENT, and CURRENT_RELEASE points to verification v8 and runtime 1046986. Runtime bytes match the manifest after the final submission rebuild. No reasoning changes followed the first blind run.

## Proven changes and candidate survival

- Corrected false UNKNOWN classification when retrieval fallback tags coexist with actual supporting findings.
- Competition action selection stops exploring already-resolved non-leading alternatives. The full ranking and safety differential remains available. No forced top-1 danger boost or fixed-turn narrowing.
- Korean denial and symptom-clause boundaries corrected in the bounded multilingual bridge; bilingual scoring deduplication verified.
- No new survival persistence was added: development traces did not prove dropout. 563 eligible critical candidate-turns were retained (100.0%); this is a development slice, not clinical recall.
- Corrected-observation drop/re-entry and resolved-alternative release controls pass. Empirical re-entry rate is not estimable: no such trajectory events occurred.

## Paired Round G synthetic development results

| Metric | Before | After |
|---|---:|---:|
| Accuracy | 91.67% | 91.67% |
| KB-critical recall | 75.00% | 75.00% |
| Average turns | 41.50 | 36.75 |
| Median turns | 44.50 | 39.00 |
| Average ASK | 11.08 | 9.58 |
| Average EXAM | 10.75 | 9.83 |
| Average TEST | 18.67 | 16.33 |

Diagnostic-delay proxy: 0 turns after first non-forced StopPolicy acceptance. This measures implementation delay, **not** whether the stop policy is clinically optimal. Unnecessary-test proxy in the trace is 0; it is distinct from the benchmark's relevance-based proxy. Definitions/denominators are in the JSON summaries.

Historical v16 competition-like: 83.1% scored accuracy, 92.9% critical recall, 7.1% critical miss, 39.8 average turns, 18.0 average TEST. Those belong to the prior runtime and a different dataset; do not treat v16/v17 differences as a controlled improvement.

## Regression

769 tests passed, 0 failed, 1 skipped. Held-out, generalization-v2, stress, Round D and Round E preserve accuracy and critical recall in both legacy and competition modes. Competition held-out average turns 34.67 -> 29.06, average TEST 15.00 -> 11.39. Retrieval and routing semantic outputs preserve the baseline; timing is machine-specific. One legacy generalization unnecessary-test proxy increases from 1.333 to 1.444 despite unchanged accuracy/recall/average turns, explicitly retained in the record.

## Blind v17: one predeclared execution

Configuration: **COMPETITION-STRUCTURE / MOCK-LLM**. AI-authored synthetic post-freeze holdout; no expert adjudication or independent patient validation.

| Metric | Result |
|---|---:|
| Cases / scored / critical | 60 / 55 / 25 |
| Scored accuracy | 48/55 = 87.27% |
| All-case accuracy | 48/60 = 80.00% |
| Critical recall | 24/25 = 96.00% |
| Critical miss | 1/25 = 4.00% |
| Average / median turns | 32.40 / 36.00 |
| Average ASK / EXAM / TEST | 9.08 / 8.48 / 13.83 |
| Duplicate / malformed per case | 0 / 0 |
| Unnecessary-test relevance proxy | 4.75 per case |

Manifest SHA-256: `a02b0fbcb489e352a484a4863aad6a3c02f7cc3412737f4325bf846920ad3129`. Run count: **1**. Seven scored failures and all five unscored outcomes remain in the failure review. The existing `unsupported_case_success_rate` means completed within the turn budget; **it does not mean successful OOD detection or safe abstention**. All five unscored cases returned a non-unknown label. No post-result tuning or rerun.

## Submission and remaining gates

Built ZIP: 250,491 bytes (<50 MB), `ab6acc17d39f64921600dbd89c6930bcb6b0ebe4c584732618ab742520ce4eb8`. Source/submission hashes match; standalone full-loop mock validation passes. Default provider is competition; retrieval/rerank/reasoning defaults are 150/25/25. Secret scan passes.

REAL GPT-OSS-20B: **NOT VERIFIED**. Model revision: **NOT VERIFIED**. Per-case successful-real-call gate preserved and mock-tested. OFFICIAL COMPETITION API: **NOT VERIFIED** (replaceable placeholder schema remains). These block an official readiness claim. No invented readiness percentages.

Main changed: NO. New Actions runs: 0; no workflow_dispatch. Only the requested branch is published.

## Next cycle, not this frozen runtime

Review the critical electrolyte/arrhythmia mismatch, other scored failures, OOD forced-output behavior, and the development urinary-source/sepsis miss with independently reviewed labels and new development cases. A post-freeze probe also exposed unsupported lipase-only candidate generation; document it instead of patching after seeing blind results. Further reasoning changes require another fresh frozen holdout. v17 is never a tuning target.
