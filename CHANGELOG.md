# Changelog

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
