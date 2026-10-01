# Validation and remaining dependencies

This revision improves the six identified weaknesses. It does not claim that external
clinical validation or probability calibration has been completed.

| Area | Implemented | Still required |
|---|---|---|
| Independent evaluation | External JSON importer, immutable-by-hash manifest, unknown defaults, duplicate/key validation, source/case/catalog hashes in real-run metadata | Independently authored and adjudicated cases; a hash cannot prove authorship or medical correctness |
| Live model | External-case support in real benchmark and manual GitHub workflow; mock cannot pass `--require-real` | Approved model server/runtime and connection configuration; official adapter verification |
| Scope | Validated offline catalog extensions; acceptable labels and coexisting-condition differential recall; outside-catalog quality flag | Built-in catalog is still 34 diseases; reviewed extensions and measured external/compound-case performance |
| Language | Explicit Korean phrases/negation, common English abbreviations, Korean vital labels, family/patient symptom separation; originals retained | Broad Korean, typo, dialect, temporal and multi-person validation |
| Efficiency | Existing medication text/associated symptoms suppress redundant questions | Large reductions in tests/turns remain unproven. Removing nonpositive candidates cut V5 accuracy to 42/44 and was rejected |
| Confidence | LOW cap/reasons for conflicts, close alternatives, unsupported/novel diagnoses and forced decisions; null probability; observed reliability by band and Wilson intervals | Probability calibration on separate calibration data, followed by untouched validation |

## External cases

An example is in `evaluation/examples/external_cases.json`. It is an unscored synthetic
plumbing example, not independent evaluation. JSON fields `author` and `provenance` are
required declarations. Each case follows `SyntheticCase`; unknown keys and duplicate IDs
are rejected. Omitted responses default to `Unknown / not provided.` rather than normal.
Out-of-catalog labels require explicit `critical_override`. `acceptable_diagnoses` records
adjudicated alternative primary answers; `coexisting_diagnoses` measures companion diagnoses
in the differential, not whether the final single-label answer fully represents comorbidity.

Freeze before evaluating, and never tune against the reserved external validation set:

```bash
python -m evaluation.sealed_cases --cases-json external.json --manifest external.manifest.json
python -m evaluation.real_llm_benchmark --provider competition --require-real --cases-json external.json --case-manifest external.manifest.json --timeout 180 --save-json external-real-report.json
```

The manifest creator refuses to overwrite an existing manifest. Loading rejects changed
case bytes/provenance. Reports explicitly state that independence and clinical review are
not verified by the software. `--resume` checks run metadata including the catalog hash.
With `--require-real`, every decision must have a successful real response with no fallback
or skipped-budget decisions. Passing this execution check still does not mean 90% accuracy.

## Live runtime

Configure `NOVA_COMPETITION_BASE_URL`, `NOVA_COMPETITION_MODEL`, and (when the endpoint
requires it) `NOVA_COMPETITION_API_KEY` through environment variables or GitHub Secrets.
Use the competition-approved runtime/model and retain the existing endpoint restrictions.

`External frozen case validation` is a manual GitHub Actions workflow accepting repository
paths to the cases and manifest plus a case limit. It checks the manifest before calls,
runs preflight and requires successful real-model verification. It has not been dispatched
in this workspace: no real endpoint is configured. Do not post credentials in chat or code.

## Catalog extension

Set `NOVA_KNOWLEDGE_EXTENSION` to a local JSON list of disease definitions. Definitions need
unique `id`, `name`, `evidence_level`, `sources` (HTTPS URLs), `dangerous`, `urgency`, evidence
features, and valid action keys. The loader refuses overrides of built-in diagnoses and
invented action keys. Source declarations are not automatically fetched or clinically
verified. Extensions must be bundled/mounted in the actual offline runtime as well; a path
on a developer machine alone will not extend the submitted package. Restart after changes.

No unreviewed disease definitions were added merely to increase the disease count.

## Confidence and efficiency results

`decision_quality` contains a qualitative evidence band, explicit uncertainty reasons,
catalog status, `probability: null`, and `calibrated: false`. It does not replace ranking or
relax safety. A turn-limit decision has readiness zero rather than fabricated full readiness.
The probability calibration itself remains undone. Reliability figures on reused synthetic
cases cannot establish generalization; report denominators and intervals with this limitation.

The rejected action-pruning experiment retained only rank 1/positive-score candidates (plus
existing safety flags). V5 scored 42/44 (95.5%), mean 25.95 turns. That logic was removed.
The accepted changes retain the broader search and only avoid already-provided questions.

## Input validation follow-up

External bundles reject null or coerced boolean labels, blank identifiers/complaints/diagnoses,
blank alternative or companion labels, non-object cases, whitespace-equivalent duplicate IDs,
and unknown relevant-test IDs. Authorship and provenance declarations must be nonempty text.
This prevents malformed inputs from silently changing critical-miss or accuracy denominators.

Catalog extensions reject empty evidence and alias strings, noncanonical diagnosis IDs,
and malformed HTTPS source URLs (including missing hosts, invalid ports, whitespace and
embedded credentials). URL syntax checks do not establish source authority or clinical validity.
The submitted runtime uses the same loader. Validation: 233 tests pass, including 25 new
malformed-input regressions; standalone submission build/import smoke passes.
