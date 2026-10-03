# N.O.V.A. Security (Backend-Integrated)

Covers `/v1/nova/*` specifically. This backend's broader security posture (OIDC verification, SMART
SSRF protection, CORS credentialed-origin rule, idempotency) is documented in the existing
`docs/SECURITY.md` and unchanged by this work -- see "Existing security controls reused unchanged"
below for exactly what N.O.V.A. inherits without modification.

## Authentication and authorization

Every `/v1/nova/*` endpoint requires `Depends(require('nova:...'))`, using this backend's existing
`get_current_user()` (AUTH_MODE=demo fixed identity, or AUTH_MODE=oidc real bearer-token/session
verification -- see `backend/app/services/auth.py`, unchanged). Three new least-privilege
permissions:

| Role | nova:read | nova:invoke | nova:review |
|---|---|---|---|
| clinician_readonly | yes | no | no |
| clinician | yes | yes | yes |
| pharmacist | yes | no | no |
| admin | yes | yes | yes |

`nova:invoke` covers case creation, observation submission, and `decide()` -- the actual diagnostic
reasoning actions, same bucket as `note:write`/`order:write`. `nova:review` covers closing a case
with a clinician's accept/modify/reject disposition. `pharmacist` gets read-only access (to see an
existing differential relevant to a medication decision) but not `invoke`, matching this role's
existing "no note access" pattern elsewhere in this backend.

`GET /v1/nova/metrics` requires `user:admin` (not a clinician permission) -- observability data is
an operations concern, not a clinical one.

## Input validation / prompt-injection framing

`backend/app/nova_schemas.py`'s `NovaCaseCreateRequest`/`NovaObservationRequest`:
- `chief_complaint`/`result` free text: max 4000 characters, control characters (C0/C1 except
  `\t\n\r`) rejected via a `field_validator`.
- Every request model is a `StrictModel` (`extra='forbid'`) -- an unexpected field is a 422, not
  silently dropped.
- `action_type` is a closed `Literal["ASK","EXAM","TEST","DIAGNOSE"]`.

Patient-authored free text is never treated as instructions anywhere in the pipeline: the
deterministic reasoning layers only ever pattern-match clinical concepts out of it
(`nova_agent/clinical_presentation.py`, `nova_agent/matching.py`), and the one place free text
reaches a real LLM (`nova_agent/llm_client.py`'s `build_reasoning_prompt()`) explicitly frames the
patient summary as **untrusted clinical data**, instructing the model that any text resembling a
command inside it is itself a symptom to evaluate, never something to obey (see that module's own
"Security note" paragraph -- shared code, so this applies to both the standalone `production/` path
and this backend-integrated one).

## Structured error model

`backend/app/main.py`'s `nova_call()` translates every `NovaServiceError` subclass into
`{"error": {"code", "message", "retryable"}}` (never a bare `HTTPException(detail=str(e))`):
`validation_error` (422), `case_not_found`/`patient_not_found` (404), `case_conflict` (409),
`EMR_unavailable` (503, also returned when the adapter itself raises `NotImplementedError`, mapped
to 501), `storage_error` (503, reserved for a future database-backed repository), `internal_error`
(500, the base class default). Authentication/authorization failures keep this app's existing
plain-string 401/403 shape (unchanged everywhere else in this backend) rather than getting a
NOVA-specific envelope -- a deliberate scope boundary, not an oversight.

## Secrets

No secret is baked into `docker/Dockerfile`'s image. `NOVA_LLM_PROVIDER`'s API key,
`OIDC_ISSUER`/`OIDC_AUDIENCE`, `FHIR_CLIENT_ID`/`FHIR_CLIENT_SECRET`, and `SYNEX_REDIS_URL` (if
used) are all runtime environment variables only, matching this backend's existing convention.
`docker-compose.production.yml` deliberately leaves `POSTGRES_PASSWORD` unset, documented as "pass
via `--env-file` or a secret manager."

## Existing security controls reused unchanged

- OIDC JWT verification (issuer/audience/signature/expiry via JWKS) -- `verify_oidc_token()`.
- SMART App Launch SSRF protection (issuer allowlist/private-address rejection) -- `smart_launch.py`.
- CORS credentialed-origin rule (`resolve_cors_config()` refuses `*` origin with credentials).
- HttpOnly session cookies for both clinician auth (`synex_auth_session`) and SMART patient context
  (`synex_session`) -- never a raw bearer token reaching the browser.
- `IdempotencyStore`'s SQL-uniqueness-constraint-based concurrency-safe claim/complete/fail protocol
  (available to a future `/v1/nova/*` HTTP-level `Idempotency-Key` use, though the current design
  achieves per-observation idempotency at the domain level via `observation_id` instead -- see
  `docs/NOVA_PRODUCTION_ARCHITECTURE.md`).

## Known NOT VERIFIED items

- No institutional/third-party security review of `/v1/nova/*` specifically.
- No dependency vulnerability scan / SBOM generation wired into CI for this backend.
- AUTH_MODE=oidc has been unit-tested against a locally-generated JWT/fake JWKS endpoint
  (`backend/tests/test_auth.py`), never against a real hospital IdP (Keycloak, Azure AD, Okta) --
  this was already true before this round's work and remains true.
- `FHIR_AUTH_MODE=smart`'s SMART Launch -> session -> FHIR request chain has never been exercised
  against a real EMR's authorization server (see `smart_launch.py`'s own docstring) -- unchanged by
  this round.
