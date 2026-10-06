# N.O.V.A. Release Readiness

> **Purpose.** A single, honest statement of what is and is not verified for the N.O.V.A. Clinical
> Decision Support platform, for a pilot/PoC conversation with Seoul National University Bundang
> Hospital (SNUBH) and for the N.O.V.A. 2026 competition submission. This is a *software*
> readiness statement backed by real CI evidence (see `TEST_EVIDENCE.md`); it is **not** a claim
> of clinical validation, regulatory approval, institutional security approval, or real hospital
> integration — all four remain **NOT VERIFIED** (see below and `CLINICAL_VALIDATION_STATUS.md`).

## Two separate readiness scores (never conflated)

| Score | Basis | Status |
|---|---|---|
| **Software readiness** | Real code + tests + CI evidence | See the dimension table below |
| **Hospital external-validation readiness** | Real institutional/clinical/regulatory sign-off | **NOT VERIFIED** (no external validation has occurred) |

A high software-readiness score does **not** imply hospital readiness. The system is intended to
operate strictly as **AI decision support + clinician review**, never autonomous diagnosis or
treatment (`clinician_review_required` is always `true`; no N.O.V.A. path writes orders to any
EMR/FHIR system).

## Software-readiness by dimension

Each row is backed by a CI job on the final integration HEAD (see `TEST_EVIDENCE.md` for run
links). "READY-IN-CI" means the behavior is implemented and verified by an automated job; it does
**not** mean it has run in a real hospital environment.

| Dimension | Status | Evidence |
|---|---|---|
| Clinical reasoning engine (ASK/EXAM/TEST/DIAGNOSE, hybrid) | READY-IN-CI | `nova-agent` job: pytest + benchmark/held-out/generalization/stress regression gates |
| Patient safety (must-not-miss, score separation, no auto-order, clinician review) | READY-IN-CI | `nova-agent` safety-regression tests; `clinician_review_required: Literal[True]` |
| Frontend N.O.V.A. workspace + 4-language i18n | READY-IN-CI | `frontend` job: `npm ci` + `npm run build` + i18n/component unit tests |
| Multilingual backend (locale switch, canonical-id invariance) | READY-IN-CI | backend locale tests; cross-language equivalence test |
| FHIR normalization (read-only, provenance, temporal trend, unmapped retained) | READY-IN-CI | `production-backend` FHIR mapper tests |
| Persistence (durable Postgres repo + audit + migrations + `state_schema_version`) | READY-IN-CI | `postgres-integration` job vs real `postgres:16` (skip == failure) |
| Concurrency (optimistic + retry, observation idempotency) | READY-IN-CI | `postgres-integration` concurrency tests |
| Auth / RBAC / OIDC (unit-level) | READY-IN-CI | `production-backend` RBAC/auth tests |
| SMART patient-scope fail-closed (design) | PARTIAL | fetch-layer fail-closed; real SMART launch NOT VERIFIED |
| Audit trail (events, no private reasoning stored) | READY-IN-CI | audit tests; `PostgresAuditStore` |
| Observability (metrics + structured logs, PHI-minimized) | READY-IN-CI | metrics/log tests |
| Docker images + `/health`+`/ready` container smoke | READY-IN-CI | `production` + `production-backend` container smoke |
| CI/CD (nova-agent, frontend, production, production-backend, postgres-integration) | READY-IN-CI | `.github/workflows/nova-ci.yml` |
| Competition artifact (isolated, submission source-sync) | READY-IN-CI | `nova-agent` build-submission + sync check |
| Real LLM path | **NOT VERIFIED** | no live model call; `competition-readiness` skipped (no secret) |
| Real FHIR / OIDC / SMART endpoint | **NOT VERIFIED** | no real hospital endpoint/credentials |
| Clinical validation | **NOT VERIFIED** | no clinical study performed (see `CLINICAL_VALIDATION_STATUS.md`) |
| Institutional security review | **NOT VERIFIED** | not performed |
| Regulatory review | **NOT VERIFIED** | not performed |
| Real SNUBH integration | **NOT VERIFIED** | not performed |

## What "done" means here

Software-ready is claimed only where implementation + test + integration + CI all agree. Anything
that could not be executed (real LLM/FHIR/OIDC/SMART, clinical/security/regulatory sign-off) is
reported **NOT VERIFIED**, not PASS. The authoring environment for this workstream is
network-isolated, so all executable verification was delegated to GitHub Actions; see
`TEST_EVIDENCE.md` for the exact runs.

## Blind evaluation status

- Blind v6 (54 cases) is now **reference-only** (a reasoning-code change was made after it).
- **Blind v8** (72 cases) is authored and hash-frozen (`evaluation/blind_v8_manifest.json`). Its
  **first run is NOT VERIFIED** — it requires a runnable Python environment and will be run exactly
  once, then reported as-is and never tuned against. Do not cite a Blind v8 accuracy number until
  that single run has occurred.

## Known limitations

See `KNOWN_LIMITATIONS.md`. The most material: limited 34-diagnosis knowledge base, keyword/entropy
matching (not embeddings), no live real-LLM/FHIR/OIDC/SMART verification, and no external clinical
or security validation.
