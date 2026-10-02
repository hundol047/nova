# Expansion audit corrections — 2026-10-02

Expansion remains blocked. Software tests are not clinical validation.

## Changes

- Named Tier-2 benchmark ground truths are included even when historical fixtures set scoring_expected=False. Frozen case files are unchanged; v11 is now a reference regression set, not a new independent validation.
- Critical-case accounting includes Tier-2 urgency/danger metadata conservatively. Unknown handling succeeds only when the outcome is actually unknown, not merely when a run terminates.
- Exact names/aliases and stable IDs normalize; ambiguous aliases and substring guesses do not. Potential duplicate concepts remain separate, unverified records pending review rather than being silently merged.
- The 1,246 additional records are marked NOT_VERIFIED. Their unreviewed code anchors cannot perform authoritative runtime mapping. Sixteen known-problem mappings are quarantined with reasons, including fourteen absent from the FY2027 ICD-10-CM file and two specificity/name mismatches. No substitute clinical codes were invented.
- Production catalog loading rejects synthetic/NOVASYNTH snapshots. Synthetic fixtures remain available for scale tests only.
- Actual DoctorAgent turns supply a bounded retrieval/router/rerank candidate bundle to the LLM prompt. Each candidate includes a verification warning. Retrieval scores do not become diagnostic evidence. Submission includes only the runtime dependency subset; training and evaluation data stay excluded.
- Unsupported final diagnoses and error fallbacks abstain as unknown; dangerous alternatives remain visible in the differential. This is not proof that all uncertain cases are detected.
- Broken summary calls are corrected; expansion gate fails closed pending independent clinical review. The catalog generator rejects new IDs while that gate is closed.

## External reference

CDC FY2027 ICD-10-CM code descriptions:
https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip

Code existence is separate from correct clinical mapping. The original catalog labels codes ICD10 with no version; FY2027-CM mismatch does not itself prove that a disease does not exist. Sources, clinician adjudication, independently labeled cases, and real-provider evaluation are still required. No new diseases were added.

## Executed validation

- Core suite: 371 passed, 1 skipped (production API separately: 17 passed).
- New audit-defect regressions: eight tests included in that suite.
- Standalone submission build/import smoke test passed.
- v11 reference under mock provider: 22 labeled cases, 11 correct (50%); 24 total, 11 correct; critical recall 7/15. The changed denominator includes previously hidden Tier-2 failures, so this is not directly comparable with the old 12/15 headline.
- Unknown handling is still unsuccessful on the two v11 unknown cases. The guard now catches absent evidence/internal errors, but generic matched evidence can still produce a wrong named diagnosis. Do not claim this solves clinical uncertainty detection.
- All 1,246 additional clinical reviews remain outstanding; expansion gate returns BLOCKED. No real-provider or clinical validation was performed.
