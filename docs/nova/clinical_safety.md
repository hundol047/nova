# Clinical Safety

## This system is decision support, not autonomous diagnosis

Every response from `POST /v1/cases/{id}/decide` and `GET /v1/cases/{id}` carries two fixed
fields, always, with no code path that omits them:

- `safety_banner`: "Decision Support / Not Autonomous Medical Diagnosis / Clinician Review
  Required. This system's output is a structured suggestion for a licensed clinician to evaluate,
  not a final diagnosis or treatment directive. It never autonomously executes a prescription or
  treatment order."
- `clinician_review_required: true` (a `Literal[True]` in `production/schemas.py` -- not a runtime
  toggle; there is no configuration that turns it off).

The system never calls out to a pharmacy, EHR order-entry system, or any other system capable of
executing a prescription or treatment order. No such integration exists in this codebase.

## What a `DecideResponse` actually contains

- `differential`: ranked diagnoses, each with `supporting_evidence`, `contradictory_evidence`,
  `missing_discriminative_evidence`, `confidence_band` (LOW/MEDIUM/HIGH), `urgency`,
  `dangerous_if_missed`, and `candidate_sources` (how this diagnosis entered the candidate pool:
  symptom match, risk-factor match, objective finding, or the cross-cutting safety net).
- `next_action`: the recommended next ASK/EXAM/TEST/DIAGNOSE, with a `rationale` string.
- `red_flags`: diagnoses the deterministic `SafetyLayer` has flagged as dangerous-if-missed for
  this specific case (not a blanket "test everything dangerous" list -- see
  `nova_agent/safety.py`'s own docstring on this point).
- `limitations`: standing disclaimers (no institutional clinical validation performed; limited
  structured evidence model) plus, when applicable, the specific missing discriminative evidence
  for the leading diagnosis.
- `versions`: `agent_version`, `schema_version`, `prompt_version`, `kb_version` (a content hash of
  the knowledge base), `model_version` -- every output is traceable to the exact code/prompt/
  knowledge/model combination that produced it.

## What it never contains

No field carries a raw LLM chain-of-thought transcript. The only reasoning artifacts a caller (or
the audit log) ever sees are the structured evidence/source/contradiction/rationale fields above,
which are produced by `nova_agent`'s deterministic layers (`safety_validator.py`,
`clinical_summary.py`) regardless of what the underlying LLM's raw output looked like.

## Safety guarantees carried over from `nova_agent/`'s own test suite

These are enforced by `tests/test_safety_regression.py` and `evaluation/benchmark.py`'s
critical-miss tracking, and the production API layer adds no new diagnostic logic that could
regress them (it only wraps `nova_agent.orchestrator.DoctorAgent`, unmodified):
- A diagnosis is never silently dropped from consideration by the trim/fallback logic in
  `candidate_generator.py` unless it has zero real symptom/risk/objective-finding evidence at all.
- `DoctorAgent.decide()` never raises -- any internal failure falls back to a safe, conservative
  next action (`_safe_fallback()`), never a crash mid-case.
- A hard forced-diagnose ceiling (`max_turns`) guarantees the case always terminates with a
  DIAGNOSE action, regardless of what the LLM layer does or doesn't produce.

## What is explicitly NOT verified

Per the project's own closing principle: production-grade code is not the same thing as clinical
deployment approval. None of the following have been performed, and none should be inferred from
anything in this repository:
- **Clinical validation** -- no prospective or retrospective clinical accuracy study against real
  patient outcomes.
- **Regulatory review** -- no FDA/CE/equivalent regulatory submission or clearance.
- **Institutional security review** -- no third-party penetration test or hospital IT security
  sign-off.
- **Legal/compliance review** -- no HIPAA/GDPR (or local equivalent) compliance audit.

Do not describe this system as "clinically validated," "safe for patient care," "regulatory
compliant," or "hospital-ready" until each of the above has actually been completed by the
appropriate party -- see `docs/nova/security.md` and the production readiness summary in this
project's final report for the current, honest status of each.
