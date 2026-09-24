# N.O.V.A. Clinical Safety (Backend-Integrated)

## Decision support, not autonomous diagnosis

Every response from `POST /v1/nova/cases/{id}/decide` and `GET /v1/nova/cases/{id}` carries:

- `clinician_review_required: true` -- a fixed `Literal[True]` in `backend/app/nova_schemas.py`,
  not a runtime toggle; no configuration turns it off.
- `safety_banner`: "Decision Support / Not Autonomous Medical Diagnosis / Clinician Review
  Required. This is a structured suggestion for a licensed clinician to evaluate, not a final
  diagnosis or treatment directive. N.O.V.A. never places, modifies, or cancels a medication or
  lab order, and never auto-confirms a clinical order." (`nova_service.CLINICAL_SAFETY_BANNER`)

No `/v1/nova/*` endpoint calls `app.state.medication_order_repo` or `app.state.lab_order_repo` --
grep confirms this; N.O.V.A. cannot place, modify, or cancel a real clinical order through any code
path in this backend. `backend/tests/test_nova_lifecycle.py::test_never_touches_medication_or_lab_orders`
verifies this by comparing a patient's medication-order list before and after a full N.O.V.A. case
lifecycle.

## What a decision response contains

- `differential`: ranked diagnoses with `supporting_evidence`, `contradictory_evidence`,
  `missing_discriminative_evidence`, `confidence_band`, `urgency`, `dangerous_if_missed`, and
  `candidate_sources` (symptom/risk/objective/safety-net provenance).
- `recommended_next_action`: the next ASK/EXAM/TEST/DIAGNOSE, with a `rationale`.
- `red_flags`: diagnoses the deterministic safety layer flags as dangerous-if-missed for this
  specific case.
- `limitations`: standing disclaimers (no institutional clinical validation performed) plus,
  when applicable, missing discriminative evidence for the leading diagnosis and an explicit note
  when the turn ran in LLM-degraded mode (`llm_degraded: true` -- see below).
- `versions`: `agent_version`/`schema_version`/`prompt_version`/`kb_version`/`model_version` --
  every output is traceable to the exact code/prompt/knowledge/model combination that produced it.

No field carries a raw LLM chain-of-thought transcript.

## Graceful degradation is disclosed, never silent

When `NovaService`'s LLM circuit breaker is open (repeated real-provider failures), `decide()`
forces the deterministic fallback path for that turn instead of attempting another real call. This
is never invisible: the response sets `llm_degraded: true` and appends an explicit limitation
("The real AI model is currently degraded/unavailable; this turn used the deterministic
safety-guard reasoning path only, not AI-augmented re-ranking."). The deterministic path itself is
the same safety-guard reasoning `nova_agent`'s `mock` provider always uses -- degrading to it is
never a silent drop in safety, only in AI-augmented re-ranking.

## Clinician acknowledgement, never auto-applied

`POST /v1/nova/cases/{id}/close` requires an explicit `disposition` (`accept`/`modify`/`reject`)
and optional `reason`, recorded to the audit log (`nova_case_closed` event) as a review-queue
entry. Nothing in this backend feeds a clinician's disposition back into `nova_agent`'s reasoning,
retrains anything, or adjusts any rule automatically -- it is offline review data only.

## Syndrome/localized-disease coexistence, safety-priority separation

Unchanged from `nova_agent`'s own architecture (shared by both production paths): `diagnostic_score`,
`patient_severity_score`, and `safety_priority` remain three separate axes, never remerged into one
ranking number. A localized infection and its systemic syndrome (e.g. pyelonephritis + sepsis) can
and do coexist in the same differential -- see `nova_agent/syndrome_relationships.py`; there is no
hardcoded disease-pair escalation rule anywhere.

## What is explicitly NOT verified

Per this project's own closing principle: production-grade integration code is not clinical
deployment approval. None of the following have been performed here, and none should be inferred:

- **Clinical validation** -- no prospective/retrospective accuracy study against real patient
  outcomes, with real or synthetic EMR data routed through this backend.
- **Regulatory review** -- no FDA/CE/equivalent submission or clearance.
- **Institutional security review** -- no third-party penetration test or hospital IT sign-off of
  `/v1/nova/*` specifically.
- **Real hospital FHIR/OIDC/SMART integration** -- this backend's existing FHIR/OIDC/SMART code has
  never been exercised against a real hospital IdP or FHIR server (see `docs/NOVA_SECURITY.md`);
  N.O.V.A.'s FHIR bridge inherits this same unverified status, not a new one.
- **Production load at hospital scale** -- see `docs/NOVA_OPERATIONS.md`'s load-testing note.

Do not describe this integration as "clinically validated," "safe for patient care," "regulatory
compliant," or "hospital-ready" until each of the above has actually been completed by the
appropriate party.
