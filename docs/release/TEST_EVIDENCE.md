# N.O.V.A. Test Evidence

> Only **actually-executed** evidence is recorded here. Anything not run is marked **NOT VERIFIED**.
> CI runs are GitHub Actions runs on the `hundol047/nova` repository. Because the authoring
> environment is network-isolated (no pip/npm/docker/Postgres), all Python/JS/container/DB
> verification was executed by GitHub Actions, not locally.

## CI jobs (workflow `.github/workflows/nova-ci.yml`)

| Job | What it verifies | How it can fail loudly |
|---|---|---|
| `nova-agent` | pytest (nova_agent + competition + safety regression + new unit-safety tests), benchmark (tuning/held-out/generalization/stress) regression gates, generalization benchmark, ablation, adversarial, stability, README-number check, **evaluation leakage scan**, build submission + **submission source-sync** | any test/gate failure; a leaked blind phrase; submission drift |
| `frontend` | `npm ci` + `npm run build` (vite) + bridge-free vitest unit tests (i18n + N.O.V.A. components) | build error; unit-test failure |
| `production` | standalone package unit/reliability/repository/API tests + load smoke + Docker build + container `/health`+`/ready` smoke | test/build/smoke failure |
| `production-backend` | backend + N.O.V.A. integration tests (lifecycle, RBAC, concurrency, idempotency, FHIR mapper, reliability) + load smoke + Docker build + container smoke | test/build/smoke failure |
| `postgres-integration` | Postgres repository + concurrency + audit + migration tests vs a real `postgres:16` service; `NOVA_CI_REQUIRE_POSTGRES=1` turns a would-be skip into a **failure** | any test failure; a silent skip becomes a failure |
| `competition-readiness` | (gated on real LLM secrets) preflight + real-LLM smoke | real-LLM problem, when secrets exist |

## Per-stage CI evidence (workflow_dispatch on the stacked branch)

Each stage's top-of-stack branch contains all prior stages, so the run for a stage reflects the
cumulative state at that point.

| Stage | Run id | Result |
|---|---|---|
| Stage 2 (frontend + i18n) | 36089006008 | `frontend` PASS, `nova-agent` PASS, `production-backend` PASS; `production` failing on a pre-existing container-DB smoke later fixed in Stage 3 |
| Stage 3 (Postgres CI + migrations + observability) | 36090285952 | ALL green; `postgres-integration` = **27 tests passed vs real postgres:16, 0 skipped** |
| Stage 4 (glucose unit-safety + tests) | 36090924482 | ALL green; `nova-agent` regression gates + submission source-sync PASS (reasoning fix non-regressive) |
| Stage 5 (docs + Blind v8 authored) | 36092278237 | ALL green; leakage scan (incl. v8 import) + full regression PASS |
| Stage 6 (release readiness + leakage-in-CI) | see the final HEAD run | to be recorded at merge time |

> Run ids are transcribed from the GitHub Actions run history. To re-verify: `gh api
> repos/hundol047/nova/actions/runs/<id>/jobs`.

## Locally-executed evidence (authoring environment)

Only pieces with no network/pydantic dependency could run locally:

- `nova_agent/glucose_evidence.py` unit-safety guard: verified directly (module is dependency-free)
  — `glucose 90 mmol/L` → `None` (previously `90.0`); mg/dL, mixed, unreadable-HI cases correct.
- `tests/test_objective_evidence_units.py`: the glucose-guard class ran locally (5 passed); the
  pydantic-dependent objective_evidence/presentation classes skipped locally and run in CI.
- `py_compile` clean on every changed Python file.
- Blind v9 (current untouched set; v6 + v8 are now REFERENCE-ONLY after this round's unit-safety
  reasoning change): 44 cases, all ground-truth ids validated against the 34-diagnosis KB; manifest
  SHA-256 matches the frozen case file (`scripts/verify_local_release.py` blind_integrity: PASS);
  freeze-integrity check in the runner. Blind v9 FIRST RUN: NOT VERIFIED (needs pydantic).
- Unit-safety guard (nova_agent/unit_safety.py): 9 dedicated tests PASS locally
  (tests/test_objective_evidence_units.py, dependency-free direct import).
- Workflow YAML structure validated (7 jobs, services block).

## NOT VERIFIED (could not be executed anywhere in this workstream)

- Real LLM turn generation (no GPU/API/secret).
- Real FHIR / OIDC / SMART endpoint exchange (no hospital endpoint/credentials).
- **Blind v8 first run** (needs a runnable Python env; must run exactly once, then transcribed).
- Load/performance at 100/250/500 concurrent cases beyond the CI load-smoke defaults.
- Backup/restore and rollback drills against a real database.
- Clinical validation, institutional security review, regulatory review, real SNUBH integration.
