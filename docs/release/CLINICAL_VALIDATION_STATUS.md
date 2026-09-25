# N.O.V.A. Clinical Validation Status, Evaluation Protocol Draft & FMEA

> **Clinical validation status: NOT VERIFIED.** No clinical validation study has been conducted.
> N.O.V.A. has never been evaluated against real patients or real clinician ground truth in a
> hospital setting. Nothing in this document is a validation *result*; the protocol below is a
> *plan* for a future SNUBH pilot, and the FMEA is a hazard analysis, not evidence of mitigation
> effectiveness in the field.

## 1. What has and has not been evaluated

- **Evaluated (synthetic, in CI):** accuracy / critical-recall / critical-miss / turn-count on
  hand-authored synthetic vignettes (tuning, held-out, generalization-v2, stress; reference blind
  sets v3–v6). These are synthetic, not real patients, and use a deterministic mock LLM in CI.
- **NOT evaluated:** any real patient data, real clinician agreement, live-LLM clinical quality,
  prospective outcomes, or a hospital workflow. **Blind v8's first run has not been executed yet.**

## 2. Clinical evaluation protocol (DRAFT — for a future SNUBH pilot)

This is a protocol proposal to be reviewed and approved by clinical and institutional review
bodies before any real-data evaluation. It is not a validation and produces no result here.

- **Objective:** assess whether N.O.V.A.'s differential, must-not-miss set, and next-best-action
  recommendations are safe and useful as *decision support* under clinician review.
- **Design:** retrospective, silent (shadow) evaluation first — N.O.V.A. runs on de-identified
  historical encounters with no effect on care — before any prospective step.
- **Case population:** consecutive undifferentiated ED/triage presentations across the covered
  chief-complaint categories; **inclusion:** adult presentations with a documented final diagnosis;
  **exclusion:** incomplete records, out-of-scope complaints, pediatrics (out of current KB scope).
- **Ground truth:** the documented discharge/final diagnosis, adjudicated by ≥2 clinician reviewers
  with a third for disagreements (inter-rater agreement reported).
- **Primary endpoints:** critical-miss rate (must-not-miss conditions), top-1 and top-3 diagnostic
  accuracy.
- **Secondary endpoints:** time-to-decision, unnecessary-test rate, action-sequence appropriateness,
  fallback/LLM-degraded rate, per-language performance (ko/en/ja/zh).
- **Reviewers:** attending-level clinicians; a documented adjudication and disagreement process.
- **Failure reporting:** every critical miss root-caused; no case-specific patch to the agent from
  the evaluation set (leakage discipline preserved).
- **Statistics:** sample-size justification and confidence intervals defined before data access.

See `docs/release/PILOT_CHECKLIST.md` for the environment/setup prerequisites, and
`docs/NOVA_CLINICAL_SAFETY.md` for the standing clinical-safety contract.

## 3. Human-factors evaluation plan (DRAFT)

To be run with clinicians on the N.O.V.A. workspace UI: task-completion rate, time-to-relevant-
evidence, alert comprehension, override/reject reason quality, false-alert burden, language
preference, and usability feedback. Plan only; no result.

## 4. FMEA (failure mode & effects analysis)

Hazard analysis. "Mitigation" = implemented control; "Residual risk" is what remains and is
explicitly NOT proven eliminated in the field.

| # | Hazard | Cause | Effect | Detection | Mitigation (implemented) | Residual risk |
|---|---|---|---|---|---|---|
| 1 | Critical diagnosis missed | ranking/routing gap; sparse data | delayed emergency care | must-not-miss panel; stop policy blocks premature DIAGNOSE on unresolved danger | KB is 34 dx; coverage gaps NOT VERIFIED clinically |
| 2 | Wrong patient context | SMART/session mismatch | data shown for wrong patient | SMART fail-closed fetch; patient-scoped auth | endpoint-level cross-check to strengthen; real SMART NOT VERIFIED |
| 3 | Stale evidence treated as current | old lab/imaging reused | wrong reassurance | deterministic recency/trend annotation (`summarize_lab_temporality`) | clinical thresholds are heuristic; field impact NOT VERIFIED |
| 4 | Unit misinterpretation | ambiguous lab unit | wrong numeric interpretation | glucose unit-safety guard (Stage 4); objective_evidence returns "unknown" on unparseable | only glucose/analyte-registry covered; broader units NOT VERIFIED |
| 5 | FHIR mapping error | unmapped/garbled code | evidence lost or wrong | unmapped codes retained + counted (never dropped); provenance preserved | mapping breadth limited; real FHIR NOT VERIFIED |
| 6 | Hallucinated LLM output | model error | invalid/unsafe action | deterministic safety validator overrides LLM; legal-key/turn-limit enforcement | live-LLM behavior NOT VERIFIED |
| 7 | Auth bypass | misconfig/attack | unauthorized access | RBAC + OIDC + production guard | real IdP/deployment NOT VERIFIED |
| 8 | Audit failure | store outage | lost traceability | Postgres audit store; fail-closed storage errors | DB HA/retention is deployment policy, NOT VERIFIED |
| 9 | Duplicate observation | client retry | double turn | observation idempotency PK (case_id, observation_id) | verified in CI vs real Postgres |
| 10 | DB write conflict | concurrent writers | lost update | optimistic concurrency + jittered retry; fail-closed on exhaustion | real HA NOT VERIFIED |
| 11 | LLM outage | provider down | silent degradation | circuit breaker + deterministic fallback + surfaced degraded state | real-LLM recovery NOT VERIFIED |

## 5. Standing safety invariants (must never regress)

`clinician_review_required` always true; no autonomous diagnosis; no automatic treatment/order/
FHIR write; must-not-miss separated from the ranked differential; no blind-set-specific rules;
diagnostic likelihood / physiologic severity / safety priority kept as separate axes.
