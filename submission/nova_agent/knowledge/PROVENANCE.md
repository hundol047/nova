# Knowledge base provenance

Honest statement of where `nova_agent/knowledge/`'s content comes from (spec section 11), written
because the alternative -- inventing citations that were never actually checked -- would be worse
than no citation at all.

## What this is

The original entries in `diseases/*.json` (excluding the source-informed `expanded_v1.json`),
`red_flags/*.json`, `diagnostic_tests/notes.json`, and
`guidelines/chief_complaint_guidelines.json` is an **internally authored clinical heuristic**,
written by the implementer from general medical knowledge (standard differential-diagnosis
teaching: typical presenting features, common risk factors, first-line discriminating workup for
each condition). None of it was copied or algorithmically derived from a specific named guideline
document, textbook, or clinical decision-support database, and none of it has been reviewed by a
licensed clinician as part of this implementation.

**This is explicitly the same status SynexAgent (the vendored medical decision-support backend
this repo also contains) already gives its own rule tables** -- see
`backend/app/services/rule_engine.py`'s `EVIDENCE_LEVEL = 'PROTOTYPE RULE — NOT CLINICALLY
VALIDATED'` and its accompanying comment that its interaction rules are "SynexAgent internal
prototype policy... not an official drug database, formulary, or clinical guideline." The Doctor
Agent's knowledge base carries the identical caveat for the identical reason: it is a working
prototype's clinical judgment encoded as data, not a certified source.

## What this is not

- The original base catalog was not sourced from UpToDate, DynaMed, a specific national/society clinical practice guideline, a
  peer-reviewed diagnostic-accuracy study, or any other citable external reference. Later source-informed additions are listed separately below; their references do not certify the software.
- Not clinically validated against real patient outcomes or reviewed by a licensed physician.
- Not exhaustive: 68 diagnostic entries across the existing chief-complaint categories is a deliberately small,
  can't-miss-condition-weighted set (spec section 12's KB = high-frequency + can't-miss diseases /
  LLM = long-tail differential generation design), not a claim of comprehensive coverage.

## Per-entry fields

Each disease entry's `typical_features`, `risk_factors`, `discriminating_questions/exams/tests`,
`confirmatory_findings`, `minimum_workup`, and `red_flag_keywords` are the implementer's summary of
standard teaching for that condition, structured for keyword-based matching (see
`nova_agent/matching.py`) -- not a verbatim quotation of any single source. `urgency` and
`dangerous` follow conventional triage judgment (e.g. the 14 time-critical "can't-miss" diagnoses
named in the original task spec) rather than a formal acuity scoring system.

## If official guidance becomes available

If the N.O.V.A. 2026 competition rules specify a required knowledge source, an approved reference
set, or a licensing constraint, that takes precedence over everything in this file and in
`knowledge/*.json` -- update the affected entries (and this file) to cite it accurately rather than
leaving this internally-authored-heuristic framing in place once a real source is confirmed.

## Accuracy follow-up references (2026-10-01)

The new appendix imaging and lipase evidence features were checked against these primary
references. They remain implementer-authored text-matching heuristics, not implementations
of complete diagnostic criteria or clinician-reviewed rules. Lipase elevation alone is not
a specific diagnosis; numerical multiples of the upper limit of normal are not inferred.

- WSES 2020 appendicitis guidelines: https://doi.org/10.1186/s13017-020-00306-3
  (clinical assessment and imaging in diagnosis).
- NICE NG104 recommendations: https://www.nice.org.uk/guidance/ng104/chapter/Recommendations
  (raised lipase supports pancreatitis but also occurs in other conditions).

Nonspecific white blood cell/CRP evidence is weighted below disease-specific findings.
The exact scoring weights are uncalibrated implementation choices, not guideline values.

## Evidence parsing revision (2026-10-02 Asia/Seoul)

Case-insensitive KB labels, clause-linked temporal migration and resolved nasal symptoms
are language-processing fixes, not new diagnostic criteria. The combination of an
infection-compatible urine/blood result, recorded SBP below 90 and observed mental-status
change supplies bounded sepsis support. The weight 2.5 is uncalibrated. It is not a SOFA
calculation, proof of causation, a confirmed sepsis/shock diagnosis or a rule-out criterion.
Pending/possible/contaminated results and shock without infection evidence do not qualify.

Reference checked for the distinction between infection and organ dysfunction:
Sepsis-3 consensus, https://doi.org/10.1001/jama.2016.0287 . The implementation is
a limited internal heuristic and does not reproduce the complete consensus definition.


## Expanded catalog (2026-10-02 Asia/Seoul)

`diseases/expanded_v1.json` adds 34 internally authored, source-informed definitions.
Merck Manual Professional topic pages and the O-RADS US v2022 consensus inform the bounded
features. Per-entry URLs, limitations and `clinical_review_verified: false` are supplied.
See `docs/CATALOG_EXPANSION.md` for the complete list and validation limits. Literal phrase
matching, scoring weights, all-rule evidence gates and urgency labels are implementation
choices; they do not reproduce complete clinical guidelines or constitute clinical review.


## MedlinePlus reference-only library (2026-10-02 Asia/Seoul)

Source: MedlinePlus, National Library of Medicine. `reference_candidates/` contains 204
public-domain health-topic summaries and metadata from the dated official XML export.
It is separate from the 68 scored disease rules. NLM source authority is not clinical
validation of this agent. See `docs/CATALOG_272_READINESS.md` and the bundled manifest
for attribution, reuse terms, immutable hashes, the selected title list and validation limits.
No A.D.A.M. encyclopedia content, third-party images or drug monographs are imported.


## Additional Genetics condition references (2026-10-02 Asia/Seoul)

Source: MedlinePlus, National Library of Medicine. `genetics_candidates/` contains 408
public-domain Genetics condition descriptions and synonyms from the official summaries XML.
Only health-condition-summary descriptions are used, excluding gene/chromosome pages and
external database text. Together with the unchanged 204 health-topic references and 68
rules, the inventory contains 680 entries. All 612 references remain non-autonomous and
clinically unvalidated. See `docs/CATALOG_680_READINESS.md` and both bundle manifests for
selection, source hashes, attribution, source review dates and limitations. Rare/genetic
conditions are emphasized; this is not clinically prioritized or complete disease coverage.


## 1,020-entry revision (2026-10-02 Asia/Seoul)

Added 340 further condition summaries from the same frozen official Genetics XML source,
retaining the previous 408 entries. The Genetics bundle now contains 748 references; together
with 204 health-topic references and 68 rules the inventory contains 1,020 entries. No new
clinical validation or autonomous reference diagnoses are enabled. See
`docs/CATALOG_1020_AND_LEARNING.md` for selection and archival limitations.


## 1,451-entry revision (2026-10-02 Asia/Seoul)

Added the remaining 431 non-overlapping Genetics condition references from the same retained
source XML. There are now 1,179 Genetics references, 204 health-topic references and 68 rules.
Prior entries and reference-only eligibility are preserved. The source's excluded entries
collided under normalized names/aliases, not a clinical equivalence review. See
`docs/CATALOG_1451_AND_MODEL.md` for scope and model integration limitations.
