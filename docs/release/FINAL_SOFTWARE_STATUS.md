# N.O.V.A. Final Software Status

> **HISTORICAL SNAPSHOT (gap-closure / independent-re-audit round).** Accurate for that round, when
> Blind **v9** was current. For CURRENT state see `docs/VNEXT_INDEPENDENT_AUDIT.md`,
> `docs/ontology/DISEASE_COVERAGE.md`, and `evaluation/current_blind.py`.

> Two separate scores, never conflated. **Software readiness** is backed by code + the checks that
> actually ran. **External hospital validation** is a separate axis that is entirely NOT VERIFIED.

## Software readiness

The software implements — and, where an executable check could run, verifies — the N.O.V.A.
decision-support platform: hybrid clinical reasoning with must-not-miss safety; a 4-language NOVA
clinical workspace driving the real `/v1/nova/*` API with patient-context isolation, race/duplicate
guards, and degraded-LLM visibility; read-only FHIR normalization with unit-safe objective evidence;
durable Postgres persistence + migrations + optimistic concurrency + observation idempotency;
OIDC/RBAC; audit; observability; a consistent error contract; an isolated competition artifact; and
an honest local verification entrypoint.

This round's independent re-audit found and fixed real defects (patient-context isolation, frontend
races/duplicates, generalized lab-unit safety, registry gaps, review-audit fields) — see
`FINAL_GAP_CLOSURE.md`. No known software blocker remains for a PoC.

**Known non-blockers (documented, not hidden):** full SynexAgent-workspace i18n is PARTIAL (NOVA
workspace fully localized); case-resume UI is not wired (server data is ready); no browser E2E
harness; Redis/Postgres/real-integration checks are NOT VERIFIED at the current SHA (no local
service/registry). Blind v9 first run is NOT VERIFIED (must be run once in a runnable env).

**Environment caveat:** this round ran in a network-isolated environment (no pip/npm install; no
pydantic/fastapi/psycopg; broken npm; docker registry Forbidden), so most executable verification
was delegated. **GitHub Actions was NOT used (0 minutes).** The last GitHub Actions runs verified an
EARLIER SHA (all jobs green: nova-agent, frontend, production, production-backend,
postgres-integration; competition-readiness skipped). The current SHA has NOT been re-run in CI.

### Software readiness score

**~90% (PoC-ready), with the explicit caveats above.** The deductions from 100% are: PARTIAL
full-workspace i18n, no wired case-resume UI, no browser E2E, and the fact that the current SHA's
Python/JS/DB checks were not executed at this SHA (only statically inspected + the dependency-free
guards run locally). A number is given only for the *software* axis and only because no known
software blocker exists; per policy it is not 100% while unverified critical paths remain and no
external validation has occurred.

## External hospital validation — NOT VERIFIED

| Item | Status |
|---|---|
| Real LLM | NOT VERIFIED |
| Real FHIR | NOT VERIFIED |
| Real OIDC | NOT VERIFIED |
| Real SMART | NOT VERIFIED |
| SNUBH environment integration | NOT VERIFIED |
| Clinical validation | NOT VERIFIED |
| Institutional security review | NOT VERIFIED |
| Regulatory review | NOT VERIFIED |

These are out of software scope and must remain NOT VERIFIED until externally performed, regardless
of software maturity. N.O.V.A. operates strictly as **AI decision support + clinician review** —
never autonomous diagnosis or treatment; `clinician_review_required` is always true and no path
writes orders back to any EMR/FHIR system.

## How to verify locally (no GitHub Actions)

```
python scripts/verify_local_release.py
```

Reports PASS / FAIL / SKIPPED / NOT AVAILABLE per check and writes
`artifacts/verification/local-release-<sha>.json`. In a full environment (pydantic + fastapi +
psycopg + npm-installed frontend + Postgres) this covers the Python/backend/frontend/leakage/
submission-sync/Postgres checks; the Blind v9 first run remains a deliberate one-time manual step
(`python -m evaluation.blind_benchmark_v9`).
