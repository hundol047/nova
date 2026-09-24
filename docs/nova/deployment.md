# Deployment

## Environments (`NOVA_ENV`)

`production/config.py`'s `ProductionConfig` reads `NOVA_ENV` (`development` default, or
`staging`/`production`). `ProductionConfig.validate()` is a no-op outside `env=production` --
dev/test never gets blocked by production-only checks -- and is called explicitly at application
startup (`GET /ready`, and should also be called at process start in a real deployment entrypoint),
never at import time, so tests can construct a `ProductionConfig` with placeholder values freely.

In `production`, `validate()` fails fast (raises `ProductionConfigError`, refuses to start serving)
when:
- `NOVA_REQUIRE_AUTH=true` (the default) but `NOVA_API_KEYS` is empty -- no one could ever
  authenticate.
- `NOVA_DATABASE_URL` is still a local/in-memory SQLite path -- case data would not survive a
  container restart or be shared across replicas.

## Configuration reference

| Variable | Default | Meaning |
|---|---|---|
| `NOVA_ENV` | `development` | `development` / `staging` / `production` |
| `NOVA_API_KEYS` | (empty) | `key1:clinician,key2:admin,key3:service` role map |
| `NOVA_REQUIRE_AUTH` | `true` | `false` only for local dev/test |
| `NOVA_DATABASE_URL` | `sqlite:///./nova_production.db` | must be a real DB in production (see below) |
| `NOVA_AUDIT_RETENTION_DAYS` | `2555` (~7y) | audit log retention window |
| `NOVA_CLINICAL_EVENT_RETENTION_DAYS` | `2555` | clinical event retention window |
| `NOVA_DEBUG_LOG_RETENTION_DAYS` | `30` | debug log retention window |
| `NOVA_LOG_RAW_TEXT` | `false` | log raw patient free text (primary PHI control -- keep `false`) |
| `NOVA_CB_FAILURE_THRESHOLD` | `5` | circuit breaker consecutive-failure threshold |
| `NOVA_CB_COOLDOWN_SECONDS` | `30` | circuit breaker open-state cooldown |
| `NOVA_LLM_PROVIDER` | `mock` | `mock` / `anthropic` / `openai_compatible` / `competition` (nova_agent/config.py) |

## Persistence

`production/repository.py` ships one implementation: `InMemoryCaseRepository` /
`InMemoryAuditRepository`, thread-safe (per-case-id locking) but process-memory-only. **A real
production deployment must supply a database-backed implementation of the same `CaseRepository` /
`AuditRepository` interfaces** (e.g. a Postgres-backed one) before going live -- this is listed
explicitly under Remaining blockers because it has not been built or verified in this codebase. The
interface contract a replacement must preserve:
- `create()` raises `ConflictError` on a duplicate `case_id`.
- `get()` raises `NotFoundError` for an unknown `case_id`.
- `try_apply_event()` is the idempotency gate: returns `False` (no-op) for a previously-seen
  `observation_id`/`event_id` on that case, `True` (proceed) the first time.
- Every mutating operation on a given `case_id` must be serialized relative to every other
  operation on that SAME `case_id` (never a single global lock across all cases).
- A case must be readable/resumable after a process restart -- the in-memory implementation
  cannot satisfy this; a DB-backed one must.

## Containerization

`production/Dockerfile` builds a small `python:3.12-slim`-based image, runs as a non-root user
(`nova`, uid 10001), installs only `production/requirements.txt` (nova_agent's runtime deps plus
FastAPI/uvicorn -- never anything from `requirements-nova-dev.txt`), never `COPY`s a secret into
the image (`NOVA_API_KEYS`/`NOVA_DATABASE_URL`/etc are runtime environment variables), and declares
a `HEALTHCHECK` against the real `/health` endpoint using Python's stdlib `urllib` (no `curl`
package needed, which also keeps the installed package count down).

Build from the repo root (it needs both `nova_agent/` and `production/` in its context):

```
docker build -f production/Dockerfile -t nova-doctor-agent:<tag> .
docker run -d -p 8000:8000 \
  -e NOVA_ENV=production \
  -e NOVA_API_KEYS="realkey:clinician" \
  -e NOVA_DATABASE_URL="postgresql://user:pass@host/db" \
  nova-doctor-agent:<tag>
```

**Verification status**: the Dockerfile's structure (COPY paths, dependency-file resolution, build
stage ordering) was verified by building it in this repo's own development sandbox up through
`pip`'s dependency resolution step; the sandbox's network policy blocks that sandbox's Docker build
network from reaching PyPI, so the full image build and a running-container smoke test could not be
completed there. `.github/workflows/nova-ci.yml`'s `production` job builds the image and runs a
container smoke test (`/health`, `/ready`) on every push/PR under GitHub Actions' normal network
access -- that CI run, not this document, is the actual verification record; check its latest run
before treating the container as deployable.

## CI/CD

`.github/workflows/nova-ci.yml` has four jobs:
- `nova-agent` -- pytest + benchmark suites + submission build, always runs, always mock provider.
- `check-competition-secrets` / `competition-readiness` -- real-LLM competition-mode checks, only
  runs when a real provider secret is configured.
- `production` -- production dependency install, `tests/test_production_*.py`,
  `scripts/load_smoke.py`, `docker build`, and a container smoke test. Fully independent of the
  other three jobs: a production-only failure never blocks the competition submission artifact,
  and vice versa.

## Rollback

There is no automated deploy pipeline in this repository (out of scope without a real target
environment to deploy to) -- rollback here means: every image the `production` CI job builds is
tagged with the triggering commit SHA (`nova-doctor-agent:<sha>`); reverting to a previous stable
version means redeploying the previously-known-good SHA-tagged image, and reverting the API
container to a prior version never requires a database migration to also roll back as long as the
new schema is additive (the `CaseRepository`/`AuditRepository` interfaces here have no versioned
schema migration mechanism yet -- see Remaining blockers). Keep the last several SHA-tagged images
available specifically so this rollback path stays a `docker run` of an older tag, not a rebuild
from an older commit under time pressure.
