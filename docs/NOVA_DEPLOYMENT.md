# N.O.V.A. Deployment (Backend-Integrated)

## Environments (`NOVA_ENV`)

`backend/app/services/production_guard.py`'s `validate_production_startup()` runs once at app
startup (`lifespan()`, before serving any request). A no-op outside `NOVA_ENV=production`. In
production, fails fast (crashes startup, never serves a single request) if any of:

- `AUTH_MODE=demo` -- every request would authenticate as the same fixed demo identity.
- `AUTH_MODE=oidc` but `OIDC_ISSUER`/`OIDC_AUDIENCE` missing.
- `NOVA_LLM_PROVIDER=mock` -- N.O.V.A. would run entirely on the deterministic fallback.
- `EMR_MODE=demo` without `NOVA_ALLOW_DEMO_EMR=true` -- every patient would be the synthetic demo
  roster. The explicit override exists for a staging/sandbox instance intentionally run under
  `NOVA_ENV=production` (e.g. infra testing) without real patient data.
- `EMR_MODE=fhir` but `FHIR_BASE_URL` missing.
- `CDS_AUTH_MODE=none` -- the CDS Hooks execution endpoint would accept unauthenticated calls.
- Neither `SYNEX_AUDIT_PATH` nor `SYNEX_REDIS_URL` set -- the audit log would default to an
  in-container SQLite path that does not survive a container replacement.

## Configuration reference (new/N.O.V.A.-relevant variables)

| Variable | Default | Meaning |
|---|---|---|
| `NOVA_ENV` | `development` | `development` / `test` / `production` |
| `NOVA_ALLOW_DEMO_EMR` | `false` | Explicit override to run `NOVA_ENV=production` against the demo patient roster |
| `NOVA_CB_FAILURE_THRESHOLD` | `5` | LLM circuit breaker consecutive-failure threshold |
| `NOVA_CB_COOLDOWN_SECONDS` | `30` | LLM circuit breaker open-state cooldown |
| `NOVA_LLM_PROVIDER` | `mock` | `nova_agent`'s own provider setting (`nova_agent/config.py`) |

Every other variable (`AUTH_MODE`, `EMR_MODE`, `OIDC_ISSUER`/`OIDC_AUDIENCE`, `FHIR_BASE_URL`/
`FHIR_CLIENT_ID`/`FHIR_CLIENT_SECRET`, `CDS_AUTH_MODE`, `SYNEX_REDIS_URL`, `SYNEX_AUDIT_PATH`) is
this backend's existing configuration, unchanged.

## Persistence

`backend/app/services/nova_repository.py`'s `NovaCaseRepository` is process-memory-only -- the
same limitation every other Clinical Workspace repository in this backend already has
(`EncounterRepository`/`ClinicalNoteRepository`/... all wrap `DemoAdapter.mutate()`, itself
process memory). **A real production deployment needs a database-backed implementation of the same
interface** (`create`/`get`/`save`/`try_apply_observation`/`close`/`list_for_patient`) before case
data survives a container restart or is shared across replicas. This is a genuine, disclosed
remaining blocker -- see Remaining blockers below and `docker-compose.production.yml`'s own note on
why Postgres is started there but not yet consumed.

## Containerization

`docker/Dockerfile` now also `COPY`s `nova_agent/` into the image (no new pip dependency --
`nova_agent`'s `pydantic>=2.6,<3` requirement is already satisfied by
`backend/requirements-core.txt`'s pinned `pydantic==2.13.5`). Non-root user, no baked-in secrets,
`HEALTHCHECK` against the real `/health` endpoint -- all pre-existing, unchanged by this addition.

```
docker build -f docker/Dockerfile -t nova-synexagent:<tag> .
docker run -d -p 8000:8000 \
  -e NOVA_ENV=production -e AUTH_MODE=oidc -e OIDC_ISSUER=... -e OIDC_AUDIENCE=... \
  -e NOVA_LLM_PROVIDER=anthropic -e ANTHROPIC_API_KEY=... \
  -e EMR_MODE=fhir -e FHIR_BASE_URL=... \
  -e CDS_AUTH_MODE=bearer -e SYNEX_AUDIT_PATH=/app/runtime/audit.sqlite3 \
  nova-synexagent:<tag>
```

**Verification status**: the merged Dockerfile was verified structurally (base-image resolution,
COPY ordering) in this repo's own development sandbox; a full image build there was blocked by the
sandbox's Docker registry rate-limiting (unrelated to this change -- confirmed by the identical
limitation this project's earlier standalone `production/Dockerfile` work hit for a different
reason, PyPI network access). The `production-backend` CI job (`.github/workflows/nova-ci.yml`)
builds the image and runs a container `/health`+`/ready` smoke test on every push/PR under GitHub
Actions' normal network access -- check that job's latest run for the actual verified state.

## `docker-compose.production.yml`

An overlay profile (`docker compose -f docker-compose.yml -f docker-compose.production.yml up`)
adding Redis (already supported by `idempotency.py`/`smart_launch.py`/`auth.py` via
`SYNEX_REDIS_URL`) and Postgres (documents the intended persistence target; not yet consumed by a
repository -- see Persistence above). Real secrets are never baked into either compose file --
supply via `--env-file` or a secret manager.

## CI/CD

`.github/workflows/nova-ci.yml` now has five jobs: `nova-agent`, `check-competition-secrets` /
`competition-readiness` (real-LLM competition-mode checks), `production` (the standalone
`production/` package's own API), and `production-backend` (this backend-integrated path: pytest,
a load smoke test, a Docker build, and a container `/health`+`/ready` smoke test). All five are
fully independent -- a failure in any one never blocks or is blocked by another.

## Rollback

No automated deploy pipeline exists in this repository (out of scope without a real target
environment). The `production-backend` CI job tags every built image with the triggering commit
SHA (`nova-synexagent:<sha>`); rollback means redeploying a previously-known-good SHA-tagged image.
As long as a future schema change to `NovaCaseRepository`/`AuditStore` stays additive, reverting the
container never requires a separate data migration rollback.
