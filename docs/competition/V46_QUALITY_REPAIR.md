# v46: information, reasoning, follow-up, safety and communication

## Goal and evidence boundary

The owner reported 57.41/100: information 10.44/25, reasoning 7.36/15,
tests/follow-up 3.67/10, safety 10/15, communication 5.94/15 and efficiency 20/20.
The requested tradeoff is more complete clinical work even at some efficiency cost.
These are owner-reported v45 scores, not an evaluation of v46.

The supplied v45 archive differs from the repository v45. This change combines
its adaptive interview/plan work with the repository's guardian attribution,
spoken quantities, diagnosis fallback and plain-language Doctor explanation.
The available session/result files do not contain the scored conversation, so
the exact cause of each lost point cannot be established from those files.

## Resulting behavior

| Area | Change |
| --- | --- |
| Information | Ask the patient's main concern early; clarify positive medication/allergy/history screens; track attempted-but-unknown separately from answered; ask relevant chronic-presentation danger questions early. Reserve time for targeted Doctor follow-up instead of exhausting a static history list. |
| Reasoning | Up to four bounded follow-up planning rounds, at most four planned questions per round plus needed clarification. New answers and remaining gaps can trigger review even when the optional model flag is absent. Keep grounded quotations, a concise interpretation, supporting/opposing evidence and remaining uncertainty. |
| Tests/follow-up | Connect the final structured test plan to supported catalog/profile tests. Record purpose, observed indication and conditional next steps. All proposed tests remain unperformed. Preserve concrete result review, medication reconciliation and interval growth review. |
| Safety | Fix a swallowed type error: lightweight differential snapshots lacked the score fields needed for disposition, which could hide measured danger. Resolve scored items and retain independent vital/glucose checks if candidate processing fails. Urgent plans state immediate evaluation and safe transport. |
| Communication | Speak disposition, precautions, uncertainty, test purpose, follow-up and treatment; answer the concern and invite questions. Check understanding and correct a wrong return interval. The spoken and written plan share the same source. |

The official 50-turn maximum is retained, with 12 turns reserved for closing.
Urgent cases bypass routine extra interviewing. When fewer than 75 seconds
remain at closing, prioritize the working diagnosis, disposition and precautions,
then submit rather than attempt the full routine conversation. No unused-turn
quota is imposed. Empty plans and exhausted information stop reassessment.

The added reasoning text is explicitly clinical interpretation in A, never a
new S/O observation. Quotes must pass the existing evidence check. Proposed test
branches cannot introduce drug doses or explicitly cancel urgent review. The
existing deterministic safety/diagnostic thresholds have not been recalibrated.

## Validation

The final selected regression run passed **1,077 tests**. The prior five failures
were an unwanted engine-to-transport import and obsolete expectations for
short-deadline closing and untimed model follow-up. The evidence validator is
now passed as a callback; the deadline and timed-plan expectations are explicit.
Three packaging tests also passed.

Final checks and exact archive hash are recorded in
`artifacts/releases/nova-v46-publication.json`.
Tests exercise actual root sources: the SDK test fixture now loads only the
vendored SDK by path, avoiding an old `sys.path` insertion that could silently
test stale copies under `submission/`.

The regression selection covers the official adapter, question-bound evidence,
clinical interviewing, safety, SOAP, spoken quantities, guardian scope, deadlines,
case isolation and evaluation separation. It is not a run of every historical,
web, training or release-integrity suite. Blind v18 was not rerun or tuned.
No official scored evaluation or live designated-model encounter was performed.
Synthetic HTTP checks prove local SDK transport and packaging behavior only.

To reproduce the candidate archive from the same base commit and runtime files:

```bash
python scripts/package_quality_candidate.py --version v46
python scripts/audit_official_package.py artifacts/releases/nova-v46-submission.zip
python scripts/validate_submission_zip.py artifacts/releases/nova-v46-submission.zip
python scripts/smoke_official_http.py artifacts/releases/nova-v46-submission.zip
```

The runtime source, staging mirror and archive are compared byte-for-byte.
The manifest labels this an unscored candidate and hashes every runtime file.
No organizer reference corpus, test cases, credentials, model weights or private
conversation transcripts are shipped. The historical CURRENT_RELEASE record is
left as historical evidence, not relabeled as a v46 evaluation.

## References checked 2026-10-13

- [Official rules](https://nova.snubhai.org/rules/): action/turn limits and designated Doctor requirement. The runtime uses the server's default model rather than hardcoding the former model name.
- [Official interface](https://nova.snubhai.org/docs/) and [evaluation](https://nova.snubhai.org/evaluation/): actions, record and observed communication.
- [NICE NG197](https://www.nice.org.uk/guidance/ng197/chapter/recommendations): explain choices, uncertainty and understanding.
- [NICE CG95](https://www.nice.org.uk/guidance/cg95/chapter/recommendations): acute chest-pain referral and limits of a normal initial ECG. No new diagnostic thresholds were introduced.

Improved coverage is an implementation result. A higher official score remains
unmeasured and must not be inferred from unit-test counts or synthetic cases.
