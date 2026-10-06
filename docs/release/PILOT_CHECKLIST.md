# N.O.V.A. Hospital Pilot Checklist

> Prerequisites a hospital/IT team must provide before a N.O.V.A. PoC/pilot. **All environment
> values are placeholders — never commit real hospital credentials, endpoints, or patient
> identifiers to this repository.** Provide them via environment variables / a secret manager at
> deploy time.

## Environment values to provide (placeholders)

| Setting | Env var | Placeholder | Notes |
|---|---|---|---|
| Runtime environment | `NOVA_ENV` | `production` | Activates the fail-fast production guard |
| FHIR base URL | `FHIR_BASE_URL` | `https://<hospital-fhir-host>/fhir` | Real SNUBH FHIR: **NOT VERIFIED** |
| FHIR client id/secret | `FHIR_CLIENT_ID` / `FHIR_CLIENT_SECRET` | `<from hospital app registration>` | Store in a secret manager |
| SMART / EMR mode | `EMR_MODE` | `fhir` | `demo` only for non-clinical testing |
| OIDC issuer / audience | `OIDC_ISSUER` / `OIDC_AUDIENCE` | `https://<hospital-idp>` / `<client-id>` | Real IdP: **NOT VERIFIED** |
| Auth mode | `AUTH_MODE` | `oidc` | `demo` is refused in production |
| Allowed scopes | (IdP config) | `nova:read nova:invoke nova:review` | Least privilege per role |
| Postgres DSN | `NOVA_POSTGRES_URL` | `postgresql://<user>:<pass>@<host>:5432/<db>` | Required in production; durable persistence |
| Redis (optional) | `SYNEX_REDIS_URL` | `redis://<host>:6379/0` | Shared idempotency/session store |
| LLM provider/endpoint | `NOVA_LLM_PROVIDER` / `NOVA_LLM_BASE_URL` / `NOVA_LLM_API_KEY` | `openai_compatible` / `https://<model-host>/v1` / `<key>` | Real LLM: **NOT VERIFIED** |
| TLS / domain | (ingress) | `https://<nova-host>` | Terminate TLS at the ingress; no plaintext |

## Pre-pilot checklist

- [ ] FHIR endpoint reachable and a **test patient** available (no real patient data in early tests).
- [ ] SMART app registered; OIDC client configured; allowed scopes limited to `nova:*` as needed.
- [ ] Postgres provisioned; migrations applied automatically at startup (verify `schema_migrations`).
- [ ] Redis provisioned if multi-instance idempotency/session sharing is needed.
- [ ] LLM endpoint reachable; run `scripts/preflight_competition.py` / a readiness check; confirm
      `competition-readiness` / real-LLM smoke passes (otherwise real LLM stays **NOT VERIFIED**).
- [ ] TLS/domain configured; secrets in a secret manager, never in the repo.
- [ ] Centralized logging configured (structured JSON; confirm PHI minimization).
- [ ] Monitoring/alerting wired to the N.O.V.A. metrics (see `docs/NOVA_OPERATIONS.md`).
- [ ] Backup/restore procedure defined and drilled against the pilot DB.
- [ ] Rollback plan for the container image defined; migrations kept additive.
- [ ] Support contact / on-call defined.
- [ ] Institutional security review scheduled (**NOT VERIFIED** until completed).
- [ ] Clinical evaluation protocol reviewed/approved (see `CLINICAL_VALIDATION_STATUS.md`) before
      any real-patient step.

## Explicitly out of scope until externally proven

Real SNUBH FHIR/OIDC/SMART integration, clinical validation, institutional security approval, and
regulatory review are **NOT VERIFIED** and must not be represented as complete on the strength of
this checklist alone.
