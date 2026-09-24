# N.O.V.A. Doctor Agent - Architecture

This document covers the reasoning engine (`nova_agent/`) and the production service layer
(`production/`) that wraps it. It does not cover `backend/`, `frontend/`, `docker/`, or the other
top-level `docs/*.md` files in this repository, which belong to the unrelated, pre-existing
SynexAgent project vendored alongside this one (see `README_SYNEXAGENT.md`).

## Two separate consumers of `nova_agent/`

`nova_agent/` (the reasoning engine) and `competition/` (the competition protocol adapter) have
exactly one required dependency: `pydantic`. Two things build on top of it, and neither is allowed
to add a dependency the other must carry:

- **`submission/`** -- the competition submission artifact. Built by
  `scripts/build_nova_submission.py`, which copies only `nova_agent/` and `competition/`. It never
  copies `production/`, and `production/`'s dependencies (FastAPI, uvicorn) are never required to
  build or run it.
- **`production/`** -- the decision-support API described below. It imports `nova_agent/` but is
  never imported back by it, and is never copied into the submission artifact. See
  `production/__init__.py`'s docstring for the isolation rule this repo enforces.

## Reasoning pipeline (`nova_agent/`)

```
raw chief complaint text
  -> ClinicalPresentation extraction (nova_agent/clinical_presentation.py)
       multi-concept: several simultaneous symptom concepts, onset, severity, body regions
  -> candidate generation (nova_agent/candidate_generator.py)
       symptom_match / risk_match / objective_finding / safety_candidate, each provenance-tagged
       on the resulting CandidateDiagnosis; target pool ~8-15 diagnoses, never the full catalog
       except as a last-resort fallback when nothing else matched at all
  -> differential scoring (nova_agent/differential.py)
       per-diagnosis diagnostic_score from disease-specific objective evidence only
  -> severity / safety layer (nova_agent/severity_evidence.py, nova_agent/safety.py,
     nova_agent/stop_policy.py)
       patient_severity_score and safety_priority tracked SEPARATELY from diagnostic_score --
       never re-merged into one number. safety_priority drives the SafetyLayer's must-not-miss
       tracking and StopPolicy, never the differential's own ranking.
  -> action selection (nova_agent/action_selector.py)
       information-gain-based utility scoring (expected_information_gain, discrimination,
       safety_gain, management_relevance, turn/redundancy cost), with semantic duplicate detection
       (nova_agent/semantic_dedup.py) so re-phrased questions about the same concept are not
       asked twice
  -> stop policy (nova_agent/stop_policy.py)
       early DIAGNOSE only when the leading diagnosis has strong evidence, sufficient margin over
       the runner-up, and no unresolved dangerous alternative; a hard forced-diagnose ceiling
       still guarantees a DIAGNOSE within max_turns regardless of what the LLM layer does
```

`nova_agent/chief_complaint.py`'s single-best-tag `classify()`/`route()` is kept as a compatibility
layer (used by `nova_agent/safety.py` and RAG retrieval), not deleted -- `ClinicalPresentation` is
additive multi-concept extraction built on top of the same underlying `_scores()` matcher, not a
replacement matching mechanism.

Every disease pairing (e.g. pyelonephritis + sepsis) that can legitimately coexist does so through
the general evidence/safety mechanism above, not a hardcoded disease-pair rule -- see
`nova_agent/syndrome_relationships.py`.

## Production service layer (`production/`)

```
production/
  api.py            FastAPI app: POST /v1/cases, POST /v1/cases/{id}/observations,
                     POST /v1/cases/{id}/decide, GET /v1/cases/{id}, GET /health, GET /ready,
                     GET /metrics
  auth.py           API-key authentication + role-based authorization
                     (clinician / reviewer / admin / service)
  schemas.py        Strict Pydantic request/response models (extra="forbid"); every clinically-
                     facing response carries the safety banner and clinician_review_required=true
  repository.py     CaseRepository / AuditRepository abstractions + a thread-safe in-memory
                     implementation of each (per-case-id locking; see docs/nova/deployment.md for
                     what a real DB-backed implementation needs to preserve)
  validation.py     API-boundary input validation (size limits, control characters, unicode
                     category checks, identifier format)
  errors.py         Distinct exception types (validation / auth / not-found / conflict / LLM-
                     timeout / LLM-unavailable / KB / persistence / circuit-open), each with a
                     stable error_code and HTTP status
  circuit_breaker.py  Closed/open/half-open breaker for a failing external call (e.g. a real LLM
                     provider), independent of nova_agent's own per-case budget/fallback logic
  redaction.py      Regex-based free-text redaction (defense-in-depth; the primary PHI control is
                     config.log_raw_chief_complaint_text=False)
  logging_config.py  Structured JSON logging (one call site: log_event())
  metrics.py        In-process counters/latency percentiles, exposed via GET /metrics
  versions.py       AGENT_VERSION / SCHEMA_VERSION / PROMPT_VERSION / kb_fingerprint() (a content
                     hash, not a hand-maintained version string) / model_version()
  config.py         NOVA_ENV-driven settings; validate() fails fast in production only
  Dockerfile        Production container image (see docs/nova/deployment.md)
```

### Request flow (`POST /v1/cases/{id}/decide`)

1. `X-API-Key` header -> `auth.authenticate()` -> `Principal` (role) -> `auth.authorize()` against
   the `decide` permission.
2. Input validation (`validation.py`) on `case_id`.
3. `CaseRepository.get()` under that case's lock.
4. A **fresh** `nova_agent.orchestrator.DoctorAgent` is constructed for this call (not shared
   across requests -- see the concurrency-safety note in `production/api.py`'s module docstring:
   `BaseLLMClient` tracks its most recent call's outcome on plain instance attributes that
   `orchestrator.decide()` reads right after calling it, which is correct for the sequential
   evaluation harnesses this engine was built for but would race if two concurrent requests shared
   one client instance).
5. `DoctorAgent.decide()` runs the full reasoning pipeline above and never raises (its own
   documented contract); the result is mapped into `DecideResponse`.
6. `CaseRepository.save()`, an `AuditEntry` append, a structured log line, and metrics counters are
   recorded.

### Explainability without private chain-of-thought

`DecideResponse` never carries a raw LLM chain-of-thought field. What it carries is exactly what
`nova_agent`'s deterministic layers already produce: `supporting_evidence` /
`contradictory_evidence` / `missing_discriminative_evidence` per differential item,
`candidate_sources` (symptom_match/risk_match/objective_finding/safety_candidate provenance),
`red_flags`, and a `rationale` string on the selected next action.
