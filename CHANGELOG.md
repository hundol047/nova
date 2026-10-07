# Changelog

## Preliminary pre-guide candidate / verification v17 (runtime `fd238d7`)

- **Fix SOAP data loss:** `classify_answer` marks an answer "denied" only when every clause is a clear denial; mixed, positive and uncertain answers keep the patient's words (EN/KO/JA/ZH, `but/however/except/and`, `; , .`, Korean connectives). 85 regression tests.
- SOAP: Assessment separates supporting / contradictory / missing evidence; "Patient education" reports only what was actually said (else "Planned"); new `evaluation/soap_provenance.py` traceability checker with adversarial fabrication tests.
- Diagnosis SAY (<= 30 chars) uses a short alias when the formal name does not fit (was "I will explain next.").
- Korean colloquial symptom/history evidence bridge (negation-aware) + routing aliases; English suites bit-identical; Round M dev Top1 0.9593 / critical 1.0 unchanged.
- `competition/official_transport.py`: isolated fail-closed transport boundary, evidence ladder, `TransportLLMClient`; stubs never count as official.
- Preliminary-only benchmark (`scripts/evaluate_preliminary_benchmark.py`, LOCAL DEVELOPMENT / PRELIMINARY SIMULATION) + 20 new synthetic Korean cases; isolation, tripwire, failure-mode, call-policy, Korean and documentation-honesty tests.
- The 8-call cap is labelled an INTERNAL ENGINEERING BUDGET. Provenance inventory re-hashed (statuses untouched; Mondo synonyms recorded VERIFIED from embedded provenance); 75 assets remain UNRESOLVED (submission clearance BLOCKED).
- CI: Python 3.11 + 3.12, preliminary tests/benchmark gates, provenance coverage, fresh-directory package smoke, package audit; `offline/**` branches trigger CI. README/status rewritten: `docs/CURRENT_STATUS.md`.
- Still NOT VERIFIED: real `openai/gpt-oss-20b` behaviour, the organizer interface, clinical review, asset licences. Status: PRE-GUIDE CANDIDATE, NOT OFFICIALLY READY.

## Round J / structural deficiency repair / verification v11

- Freeze reasoning at `f315fbf`; final full suite 849 passed, 1 skipped. Publish verified source/mirror/package hashes.

- Preserve observed symptom wording through candidate generation and retain deep KB profiles for core retrieval hits.
- Recognize objective absence; apply negative penalties after positive evidence saturation.
- Keep pending results and soft reassurance from silently closing critical alternatives; retain unresolved confirmatory actions.
- Add top-competitor separation, critical-resolution and specificity utility components; protect minimum workup at stop time.
- Add 54 fresh synthetic development cases, complete compressed per-turn traces, primary failure attribution and a clinical-depth audit.
- Round J: 47/52 → 48/52; critical 20/20 unchanged; mean turns 29.59 → 26.19, tests 12.06 → 10.81. No clinical or real-model performance claim.
- v18 becomes REFERENCE-ONLY; case/manifest/result bytes and original archive retained. No v18 rerun or v19.

## Round I / verification v10

- Published reasoning freeze `d6e2b84` before authoring 64 new synthetic v18 cases; published case/runner/runtime hashes before the single declared mock run.
- v18: 41/58 scored correct, 22/25 critical correct, three critical misses, mean 33.578125 turns and 14.125 tests. No runtime tuning after execution.
- Final full suite: 833 passed, 1 skipped (optional torch missing). Archived 257390-byte submission, exact source/mirror/runtime hashes and updated CURRENT_RELEASE to v10.
- Preserve all historical verification archives and v17 cases/results. Update historical-version test assertions for v18 without changing their preserved hashes.
- Report remaining ranking/coverage errors and unavailable official endpoint/schema; no clinical or real-model accuracy claim.

## Round I / integration readiness

- Distinguish absent endpoint, unreachable transport, failed auth/model/revision, invalid structure and verified transport; official schema readiness remains separately blocked.
- Preserve per-case parsed real-call gating, reject credential-bearing URLs/redirects, repair syntax without changing strings, and record optional token/latency facts.
- Fix positive focal findings incorrectly counted as an explicit reassuring denial; preserve retrieval, safety and stop policies.
- Evaluate fresh request-scope OOD controls and 20 diagnostic development cases; preserve every error trajectory.
- Public rules confirm the fixed model revision; no undocumented revision request parameter is sent.

## Current-issues fix / verification v9

- Separate deterministic evidence support, insufficient information and bounded nonmedical OOD detection from protocol-forced diagnosis labels.
- Preserve ranking and safety workup for sparse clinical presentations; expose evidence signals without calibrated probability claims.
- Block final competition answers when real-call success is false OR unattempted; startup now exits NOT READY on failed structured model preflight.
- Require the configured model target and response identity, structured output, bounded timeouts and retries. Server identity does not prove weights.
- Keep official schema PLACEHOLDER and block official-readiness claims; local stubs test wiring only.
- Add synthetic development uncertainty cases and isolated mock/unreachable/stub runtime tests.
- Mark v17 REFERENCE-ONLY without editing or rerunning its cases; preserve historical archive hashes.


## Round G / verification v8

- Fixed false zero-evidence fallback status after real findings arrive.
- Focused competition action generation away from resolved alternatives without narrowing safety/ranking.
- Corrected bounded Korean negation and cross-symptom negation scope.
- Added candidate/action development traces, multilingual and re-entry controls.
- Preserved v16 as reference-only; froze and ran synthetic v17 once after reasoning freeze.
- Rebuilt standalone submission; published measured results and unresolved limitations in docs/round_g/FINAL_REPORT.md.
- No main merge, external LLM substitution, new disease catalog or Actions dispatch.
