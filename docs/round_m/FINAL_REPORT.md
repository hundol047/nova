# N.O.V.A. 2026 PRE-GUIDE RELEASE REPORT — v13

REMOTE HEAD (inspected): `5413af9c62fb25af2e5ef1d7add7acab1b0571eb`

CURRENT RUNTIME SHA: `9d86b047fcc9c501491ee9ec4c104fd64628001f`

Status: **NOT READY**. Local engineering validation completed; official interface and rights
clearance remain blocked. This is synthetic development/mock evidence, not an official score,
real gpt-oss verification or clinical validation.

## Changes actually applied

- Official `submission/run.py` fails closed for every provider, including mock, before patient
  input or model client construction. Environment/CLI/base URL/proxy overrides cannot unlock it.
- Explicit local development harness: `python -m competition.local_runner`. It only permits
  mock. Its JSON-lines protocol is PLACEHOLDER and does not constitute organizer integration.
- Adapter cleans active state, pending actions and emitted-action counters on completion,
  errors and reused-ID initial observations. Continuation of a closed case fails explicitly.
- Emitted interaction count is capped independently of internal model retries. Local parsing
  errors terminate rather than emitting an unbudgeted ASK. No fifth wire action was introduced.
- Development structured-output validity and official call receipt are separately recorded.
  Official receipt/count remains NOT_VERIFIED/unknown; real model identity cannot be established
  by internal JSON parsing or a development stub. Existing real-LLM success gate is preserved.
- Full provenance inventory: 72 existing assets + 3 absent optional snapshots, all required
  authorship/rights/generation/review fields, SHA256 and genuine Git-history evidence.
  Coverage validator passes, permission clearance remains BLOCKED. No fake authorship, license,
  model/prompt receipt, generation date or clinician review was added.
- Recovered historical MedlinePlus/Orphanet records belong to different catalogs; no backfilling
  of current origins. Controlled per-asset recovery/replacement plan and scope-limited publisher
  terms recorded. No new clinical material promoted and no disease coverage removed.

Current Round M evidence: `artifacts/compliance_hardening/round_m/final_summary.json`.
The earlier `artifacts/round_m/final_summary.json` remains the immutable v12 comparison baseline.

## ROUND M — all metrics unchanged

Cases: 128; Scored: 123; Critical: 43; OOD/unscored: 5.

| Metric | Current |
|---|---:|
| Top1 | 95.93% |
| Top3 | 98.37% |
| Top5 | 99.19% |
| Top10 | 99.19% |
| MRR | 0.973577 |
| Median true rank (finite only) | 1.0 |
| Missing true rank count | 1 |
| Critical Top1 / Top3 / Top5 | 100.00% / 100.00% / 100.00% |
| Critical recall / miss | 100.00% / 0.00% |
| Retrieval @150 | 84.55% |
| Rerank @25 | 72.36% |
| Active truth | 99.19% |
| Long-tail retrieval / rerank / active | 100.00% / 96.15% / 100.00% |
| Long-tail Top1 / Top5 / Top10 | 92.31% / 100.00% / 100.00% |
| Average ASK / EXAM / TEST | 9.90625 / 6.00000 / 8.99219 |
| Average / median turns | 25.89844 / 20.5 |
| Redundant TEST | 0 |
| Policy-relative diagnostic delay | 0 |
| Average unresolved active dangerous candidates | 11.39062 |

Languages (chief-complaint partition only, follow-ups often English):
- EN: 108/113 = 95.58%
- KO: 1/1 = 100.00%
- JA: 2/2 = 100.00%
- Mixed: 7/7 = 100.00%

Pure KO/JA samples are too small to establish multilingual ability. Critical recall is measured
on the unchanged 43-case critical subset; it does not mean every urgent illness was correct.
All five existing scored errors remain, including ovarian torsion. Earliest-failure attribution:
1 RERANK_MISS, 4 FINAL_RANKING_ERROR. Retrieval/rerank stretch targets remain unmet.
OOD full-loop controls still take 36–44 turns; no unsafe arbitrary early-stop patch was applied.
The separately rerun 32-case OOD snapshot evaluation is `artifacts/compliance_hardening/ood.json`.

## REGRESSION

Tests: **1016 passed / 0 failed / 1 skipped**.

Skipped: optional hospital-learning torch checkpoint roundtrip because torch is not installed;
that learning package is excluded from the competition ZIP. Current full suite was executed,
including verification consistency tests. Test-only pytest/FastAPI/httpx dependencies were
installed when absent; none were added to submission requirements.

| Development suite | Accuracy | Critical recall | Mean TEST | Mean turns |
|---|---:|---:|---:|---:|
| held_out | 100.00% | 100.00% | 9.22222 | 29.83333 |
| generalization_v2 | 100.00% | 100.00% | 7.27778 | 21.38889 |
| stress | 100.00% | 100.00% | 9.62500 | 26.12500 |
| round_d | 100.00% | 100.00% | 13.42857 | 34.28571 |
| round_e | 100.00% | 100.00% | 11.71429 | 32.28571 |
| round_g | 100.00% | 100.00% | 9.16667 | 23.58333 |
| round_i | 94.74% | 100.00% | 6.90000 | 19.20000 |
| round_j | 92.31% | 100.00% | 8.07407 | 24.35185 |

All eight complete summary objects match their prior permitted baseline. All clinical source
bytes are unchanged; no disease/retrieval/stop/safety weights or thresholds changed. Round M
and all eight suites were rerun after freezing the changed adapter/entrypoint runtime.
Alone / both orders / interleaved / reused-ID / exception cleanup and bounded final-retry tests
pass. Emission limits cover None, 0, negative, 1, 40, 59, 60, 61, 100, huge integer and invalid types.
Unknown/mock/external providers, URL/proxy overrides, development ranker env settings and a
synthetic redirect credential test pass. The redirect helper is development-only, not an assumed
organizer protocol. Full-loop standalone mock, adversarial and retrieval checks pass.

## COMPLIANCE / OFFICIAL INTERFACE

Machine-readable requirements: `artifacts/compliance_hardening/rule_matrix.json`.
Statuses are PASS, FAIL, NOT_VERIFIED, BLOCKED or NOT_APPLICABLE only. PASS for a blocked
network boundary is not a claim of a functioning official inference system.

- Fixed model/revision: configured; organizer execution NOT_VERIFIED.
- Fine-tuning/weights absent, hard cap, 4 actions, independent cases and no private learning:
  locally verified for the inspected paths. Hospital learning/logger/network clients remain
  outside the official entrypoint dependency path.
- Network: APPLICATION_LEVEL_NETWORK_POLICY_VERIFIED; OS-level isolation NOT_VERIFIED.
- Source inventory coverage PASS; source/rights clearance BLOCKED. Historical external-LLM
  generation reproducibility BLOCKED. Internally authored does not automatically mean invalid.
- Participant guide unavailable in provided/public material inspected. API NOT VERIFIED,
  schema PLACEHOLDER; no endpoint/auth/route/invocation or response fields invented.
- Secret scan PASS (pattern-based with digest-pinned synthetic fixture exclusions), source/mirror
  bytes PASS, UTF-8/package contents PASS. Regex scanning is not an absolute absence proof.

## BLIND STATUS

v18: REFERENCE-ONLY. v19: NOT EXECUTED / PREEXECUTION INVALIDATED / REFERENCE-ONLY.
Fresh final blind: NOT YET AUTHORED. No v20, no new blind run, no frozen blind data/results changed.

## VERIFICATION

Version: v13. Runtime: `9d86b047fcc9c501491ee9ec4c104fd64628001f`.

ZIP: `artifacts/verification/nova-pre-guide-v13.zip`

Bytes: 285000 (<50 MB).

SHA256: `1a9e26954488f5a02dffcba53a80e1509a732081d99f2f03953cae17b836904d`

## STATUS AND BLOCKERS

LOCAL_PRE_GUIDE_VERIFIED / EXTERNAL_OFFICIAL_INTERFACE_BLOCKED / overall NOT READY.

1. Need actual organizer participant guide, approved transport/schema/environment and credentials
   to implement and test case-related fixed-model calls. The official entrypoint remains blocked.
2. Need substantiated original authorship/use rights and historical generation records, or reviewed,
   reproducible licensed replacements. Inventory completion is not permission or clinical approval.
3. Existing retrieval/rerank, long-tail errors, OOD efficiency and tiny multilingual samples remain;
   this compliance pass intentionally preserves clinical behavior.
4. Fresh blind only after post-guide integration and final reasoning freeze.

Official sources inspected 2026-10-05: https://nova.snubhai.org/rules/,
https://nova.snubhai.org/evaluation/, https://nova.snubhai.org/faq/.
Replacement-candidate terms: https://medlineplus.gov/about/using/usingcontent/ and
https://medlineplus.gov/xml.html. No candidate source has been retroactively attached as an
original source of current features. See CONTROLLED_REPLACEMENT_PLAN.md and
SUBMISSION_REACHABILITY_AUDIT.md for details.
