# Changelog

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
