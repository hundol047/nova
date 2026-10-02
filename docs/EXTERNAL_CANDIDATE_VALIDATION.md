# External candidate validation: currently blocked

The inventory remains 680 entries. This change adds **no clinically validated diagnoses**
and enables no reference-only diagnosis. Existing 68 rules remain operational; the new report's
`enable_autonomous_diagnosis: false` means this audit grants no new activation authorization.

The available environment has no configured NOVA model provider or API credentials. The only
external-case bundle present is `evaluation/examples/external_cases.json`, explicitly a synthetic
plumbing example authored by the repository implementer. It is not independent validation.
`evaluation/candidate_validation_readiness.json` therefore reports zero reviewed passes and all
680 conditions awaiting external evidence. No live model calls were made.

## Implemented comparison

`evaluation.candidate_validation` compares baseline and candidate reports from
`evaluation.real_llm_benchmark --require-real` on the exact same frozen case bundle. It rejects
mock reports, incomplete/subset runs, duplicate cases, changed labels/manifests, missing code or
catalog fingerprints, different model/provider, fallback, malformed and timed-out decisions.
It recomputes correctness from frozen labels and final diagnoses instead of trusting a report's
`correct` field. Unknown or ambiguous gold labels are rejected; unresolved predictions are errors.

Each of 680 conditions gets positive/negative case counts, true positives/negatives and separate
95% Wilson intervals for sensitivity and specificity. Any new error on a case that the baseline
answered correctly, or any candidate critical miss, blocks every numerical screen. Conditions
without sufficient cases fail individually, even if aggregate accuracy is high.

The initial **engineering screening policy**, not a clinical standard, requires 40 positive and
40 negative cases per condition and both Wilson lower bounds at least 0.90. Forty perfect cases
have a lower bound above 0.90; forty cases with errors may require additional data. This is not
a sample-size recommendation for a clinical study. Broad unrelated negatives are insufficient
for clinical review: hard near-neighbor controls, atypical presentations, demographic subgroups,
coexisting conditions, and representative deployment settings must be planned externally.
Intervals are descriptive, not simultaneous across 680 conditions, and do not account for
patient clustering, repeated evaluation, case selection, or model stochasticity. No statistical
claim of non-inferiority or real-world accuracy is made by this screen.

Reports carry `clinical_approval: false` even if numerical screening passes. Hashes establish
unchanged bytes, not reviewer identity, independence, representativeness, or diagnosis validity.
The existing frozen manifest's independence/review flags remain false. Independent clinical
adjudication and implementation review are still required; this command cannot edit runtime
rules or promote a reference candidate. Candidate work must occur on a separate research branch
before evaluation, keeping production reference guards intact.

## Run when independent cases and a provider are available

Retain the two code revisions and use the same model settings, complete frozen case set and
predeclared protocol. Change only the proposed implementation. Do not tune against test labels.
Use institutionally approved, de-identified case data; do not commit patient records or keys.
The following commands are templates, not completed evaluations:

```bash
# Freeze the adjudicated bundle once, before either run.
python -m evaluation.sealed_cases --cases-json /secure/cases.json --manifest /secure/cases.manifest.json

# Run once in each isolated revision; provider settings must already be configured.
python -m evaluation.real_llm_benchmark --require-real --cases-json /secure/cases.json --case-manifest /secure/cases.manifest.json --save-json /secure/baseline.json
# Repeat the command in the candidate revision, using /secure/candidate.json as output.

python -m evaluation.candidate_validation --baseline /secure/baseline.json --candidate /secure/candidate.json --cases-json /secure/cases.json --case-manifest /secure/cases.manifest.json --save-json /secure/comparison.json
```

No `--max-cases` is used: partial coverage cannot pass. Diagnostic rules and source context may
change between revisions, with both fingerprints retained in the output. Runtime configuration
hashes are recorded but not interpreted; reviewers must verify only intended settings changed.
Exit zero means at least one condition passed engineering screening, **never clinical approval**.
Exit one means no condition passed, or missing external evidence in readiness mode. Malformed
inputs fail with an error. To regenerate the explicitly blocked readiness report:

```bash
python -m evaluation.candidate_validation --save-json evaluation/candidate_validation_readiness.json
# Expected exit status: 1 (no evidence supplied).
```

Tests use invented plumbing records only and are not clinical evidence.
