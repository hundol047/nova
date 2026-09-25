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
- Neither `SYNEX_AUDIT_PATH`, `SYNEX_REDIS_URL`, nor `NOVA_POSTGRES_URL` set -- the audit log would
  default to an in-container SQLite path that does not survive a container replacement.
- `NOVA_POSTGRES_URL` not set -- N.O.V.A. cases would be held in the in-process
  `NovaCaseRepository`, which loses every open case on restart or redeploy.

## Configuration reference (new/N.O.V.A.-relevant variables)

| Variable | Default | Meaning |
|---|---|---|
| `NOVA_ENV` | `development` | `development` / `test` / `production` |
| `NOVA_ALLOW_DEMO_EMR` | `false` | Explicit override to run `NOVA_ENV=production` against the demo patient roster |
| `NOVA_CB_FAILURE_THRESHOLD` | `5` | LLM circuit breaker consecutive-failure threshold |
| `NOVA_CB_COOLDOWN_SECONDS` | `30` | LLM circuit breaker open-state cooldown |
| `NOVA_LLM_PROVIDER` | `mock` | `nova_agent`'s own provider setting (`nova_agent/config.py`) |
| `NOVA_POSTGRES_URL` | unset | Set to a real Postgres DSN to switch both `NovaCaseRepository` and `AuditStore` to their durable, restart-surviving Postgres-backed implementations (see Persistence below). Required in `NOVA_ENV=production`. |
| `NOVA_SAVE_RETRY_ATTEMPTS` | `6` | Bounded retry count for a `ConcurrentModificationError` on the same case (Postgres backend only; see Persistence below) |
| `NOVA_SAVE_RETRY_BASE_DELAY_SECONDS` | `0.02` | Base for the jittered exponential backoff between save-retry attempts |

Every other variable (`AUTH_MODE`, `EMR_MODE`, `OIDC_ISSUER`/`OIDC_AUDIENCE`, `FHIR_BASE_URL`/
`FHIR_CLIENT_ID`/`FHIR_CLIENT_SECRET`, `CDS_AUTH_MODE`, `SYNEX_REDIS_URL`, `SYNEX_AUDIT_PATH`) is
this backend's existing configuration, unchanged.

## Persistence

`backend/app/services/nova_repository.py`'s `NovaCaseRepository` (in-memory) is the dev/test
default -- the same limitation every other Clinical Workspace repository in this backend has by
default (`EncounterRepository`/`ClinicalNoteRepository`/... all wrap `DemoAdapter.mutate()`, itself
process memory). Setting `NOVA_POSTGRES_URL` switches both N.O.V.A. cases and the audit log to
durable, restart-surviving Postgres-backed implementations that share the exact same interface
(`PostgresNovaCaseRepository`: `create`/`get`/`save`/`try_apply_observation`/`update_locale`/
`close`/`list_for_patient`; `PostgresAuditStore`: `record`/`save_analysis`/`get_analysis`/`list`) --
`production_guard.validate_production_startup()` refuses to start in `NOVA_ENV=production` without
it, so a real deployment cannot silently fall back to the in-memory default. See
`backend/tests/test_nova_postgres_repository.py`/`test_audit_postgres.py` for tests run against a
real local Postgres server (not a mock).

**Concurrent writes to the same case**: `try_apply_observation` is fully atomic under concurrent
Postgres writers (the same `PRIMARY KEY` insert primitive `idempotency.py` uses), and
`update_locale`/`close` are single-transaction `SELECT ... FOR UPDATE` read-modify-writes, so both
are race-safe outright. The `get()` -> mutate in Python -> `save()` cycle `add_observation()`/
`decide()` drive is NOT atomic across that gap by construction (the repository interface hands the
caller a plain object between calls, not an open transaction); `PostgresNovaCaseRepository` instead
uses optimistic concurrency (a `version` column), and `NovaService` retries the whole
get-mutate-save cycle (re-reading the now-current state, so a concurrent writer's change is never
discarded) up to `NOVA_SAVE_RETRY_ATTEMPTS` times (default 6) with jittered backoff
(`NOVA_SAVE_RETRY_BASE_DELAY_SECONDS`) between attempts before giving up and surfacing
`StorageError` (HTTP 503, `retryable: true`) -- verified directly against a real Postgres server
under a 12-concurrent-writer HTTP-level test
(`backend/tests/test_nova_postgres_concurrency.py`) that mirrors `test_nova_concurrency.py`'s own
in-memory-backend scenarios and holds the identical guarantee (`turn_count == n`, no lost or
duplicated turns) for the Postgres backend too.

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
`SYNEX_REDIS_URL`) and Postgres (now consumed by `PostgresNovaCaseRepository`/`PostgresAuditStore`
via `NOVA_POSTGRES_URL` -- see Persistence above). Real secrets are never baked into either compose
file -- supply via `--env-file` or a secret manager.

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
