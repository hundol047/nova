# N.O.V.A. Security Status & Threat Model

> Software-level security posture backed by code + tests. **Institutional security review is
> NOT VERIFIED** — no hospital security team has assessed this system. This document is a
> self-assessment and a threat model to *support* such a review, not a substitute for it.

## Implemented & tested controls

| Control | Status | Evidence |
|---|---|---|
| RBAC least-privilege (`clinician_readonly`/`clinician`/`pharmacist`/`admin`; `nova:read`/`invoke`/`review`) | READY-IN-CI | `production-backend` RBAC matrix tests |
| OIDC bearer/session verification (signature/issuer/audience/expiry; unknown role → least privilege) | READY-IN-CI (unit) / real IdP NOT VERIFIED | auth unit tests |
| SMART launch fail-closed at the FHIR fetch layer | PARTIAL | endpoint-level patient-scope cross-check to strengthen; real SMART NOT VERIFIED |
| No FHIR write-back from any N.O.V.A. path | READY-IN-CI | no order-repository call; read-only mapper |
| Prompt-injection boundary (patient free-text = UNTRUSTED CLINICAL DATA) | READY | `nova_agent/llm_client.build_reasoning_prompt` delimiter; only differential + selected action consumed |
| No private chain-of-thought persisted to API/audit/logs | READY | only differential + action stored |
| PHI minimization in logs/metrics | READY-IN-CI | `log_event` has no chief_complaint/result params; metrics carry no PHI |
| Secret scan (submission build) | READY-IN-CI | `build_nova_submission` secret scan; `test_build_script_aborts_on_leaked_secret` |
| Production startup guard (fail-fast on unsafe prod config) | READY-IN-CI | `production_guard` tests |
| Non-root container, no baked secrets, healthcheck | READY-IN-CI | `docker/Dockerfile`, `production/Dockerfile` |

## Gaps / follow-ups (software)

- A **repo-wide** secret scan and pip/npm dependency-vulnerability scan are recommended as explicit
  CI steps (the current secret scan runs inside the submission build; a dedicated dependency-audit
  step is not yet wired). Do not blind force-upgrade — assess impact first.
- SMART patient-scope cross-check at the N.O.V.A. endpoint layer (in addition to the FHIR fetch
  layer) should be made explicit and test-covered.

## Threat model (STRIDE-flavored, abbreviated)

| Threat actor / vector | Concern | Mitigation (implemented) | Residual / NOT VERIFIED |
|---|---|---|---|
| External unauthenticated attacker | Reach clinical endpoints | OIDC/session auth required; fail-closed; production guard | Real IdP hardening NOT VERIFIED |
| Malicious authenticated user (over-privilege) | Perform actions beyond role | RBAC least-privilege per scope | Real directory/role provisioning NOT VERIFIED |
| Prompt injection via patient free-text | Change policy / exfiltrate / disable safety | Untrusted-data boundary; only structured differential/action consumed; deterministic safety validator overrides LLM | Adversarial red-team not executed (documented as design intent) |
| Token theft | Impersonation | HttpOnly opaque session cookie; no token in browser storage/URL | TLS/termination is a deployment responsibility, NOT VERIFIED here |
| FHIR overreach / cross-patient access | Read another patient's data | SMART session patient context; fail-closed fetch | Endpoint-level cross-check to strengthen; real SMART NOT VERIFIED |
| Secret exposure | Credential leak in repo/logs | Secret scan; PHI-minimized logs; no baked container secrets | Repo-history-wide scan recommended as CI step |
| Audit tampering | Repudiation | Append-only audit store (SQLite/Postgres); locale + canonical ids recorded | DB-level immutability/retention is a deployment policy, NOT VERIFIED |
| DB failure / conflict | Data loss / duplicate turns | Optimistic concurrency + retry; observation idempotency PK; fail-closed on exhausted retries | Real HA/failover NOT VERIFIED |
| LLM outage | Unsafe or hidden degradation | Circuit breaker; deterministic fallback; degraded state surfaced (never hidden) | Real-LLM behavior NOT VERIFIED |

## Data-flow summary (for a reviewer to trace)

`Hospital EMR → SMART/OIDC (auth + patient context) → backend FastAPI → read-only FHIR
normalization → PatientState → DoctorAgent (deterministic prior + LLM, untrusted-data boundary) →
safety validator → decide response (clinician_review_required=true) → clinician Accept/Modify/Reject
→ audit + Postgres`. No branch writes back to the EMR.
