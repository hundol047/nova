# N.O.V.A. Final Independent Re-Audit

> An independent, from-scratch audit that does NOT trust prior "DONE/READY" claims. Each row was
> checked against the actual code. Verdicts:
> **VERIFIED** (checked + a real local test ran) · **IMPLEMENTED_BUT_NOT_VERIFIED** (code inspected
> and correct, but the executable proof could not run in this network-isolated env) · **PARTIAL** ·
> **BROKEN** · **MISSING** · **STALE** · **N/A**.
>
> Environment: network-isolated. No pip/npm install; `pydantic`/`fastapi`/`psycopg` absent;
> node/npm broken; docker daemon up but registry pulls Forbidden (no Postgres/Redis image). So
> Python/JS/DB/container/real-integration checks are delegated to a runnable env / CI and reported
> IMPLEMENTED_BUT_NOT_VERIFIED here. **GitHub Actions used this round: 0 minutes.**
>
> Local verification entrypoint: `python scripts/verify_local_release.py` (artifact under
> `artifacts/verification/`).

## Audit matrix

| # | Area | Status | Evidence | Missing | Action taken | Residual risk |
|---|---|---|---|---|---|---|
| A | Clinical reasoning (ASK/EXAM/TEST/DIAGNOSE hybrid) | IMPLEMENTED_BUT_NOT_VERIFIED | nova_agent/orchestrator.py decide() never raises; forced-diagnose within turn limit | full pytest needs pydantic | none (unchanged) | live behavior not re-run locally |
| B | Must-not-miss safety | IMPLEMENTED_BUT_NOT_VERIFIED | safety.py + safety_validator override; separated in UI (NovaCriticalPanel) | pytest env | none | not re-run locally |
| C | Stop policy | IMPLEMENTED_BUT_NOT_VERIFIED | stop_policy.py unresolved-danger gate + minimum_workup | pytest env | none | not re-run locally |
| D | Candidate generation | IMPLEMENTED_BUT_NOT_VERIFIED | candidate_generator + action_selector | pytest env | none | not re-run locally |
| E | Objective evidence | VERIFIED (unit guard) / IMPLEMENTED_BUT_NOT_VERIFIED (full) | unit_safety.py guard has 9 local tests PASS; registry gained lipase + urinalysis | full normalize needs pydantic | **generalized unit safety + added lipase/urinalysis** | ranking impact not re-run locally |
| F | Multilingual clinical parsing | IMPLEMENTED_BUT_NOT_VERIFIED | chief_complaint CONCEPT_ALIASES ko/en/ja/zh; cross-language equivalence test exists | pytest env | none | not re-run locally |
| G | FHIR normalization | IMPLEMENTED_BUT_NOT_VERIFIED | nova_fhir_mapper.py read-only, unmapped retained | backend pytest env | none | real FHIR NOT VERIFIED |
| H | FHIR temporality | IMPLEMENTED_BUT_NOT_VERIFIED | summarize_lab_temporality() recency+trend | backend pytest env | none | not re-run locally |
| I | Imaging/DiagnosticReport | IMPLEMENTED_BUT_NOT_VERIFIED | mapper ingests into state.imaging | backend pytest env | none | not re-run locally |
| J | Frontend N.O.V.A. workspace | IMPLEMENTED_BUT_NOT_VERIFIED | 11 components imported+rendered+real /v1/nova/* calls; 0 hardcoded KO in components | npm build | **case isolation/race/dup guards rewritten** | build not run locally |
| K | Full frontend i18n | PARTIAL | NOVA workspace fully i18n; SynexAgent workspace (App.jsx) still has hardcoded KO strings | App.jsx tab/sidebar/env strings | env label + review hints localized; App.jsx full sweep NOT done | non-NOVA workspace strings still KO |
| L | Clinician review | IMPLEMENTED_BUT_NOT_VERIFIED | Accept/Modify/Reject + required reason; close audit now has locale+versions; Modify hint added | backend pytest env | **added locale/agent/kb to close audit + Modify hint** | not re-run locally |
| M | Case resume | PARTIAL | server now returns conversation_history (GET case); no resume-entry UI yet | resume UI | **exposed conversation_history for restore** | resume path not wired in UI |
| N | Timeline persistence | PARTIAL | durable server-side (conversation_history); UI timeline still session-scoped | UI restore call | server data now available | refresh loses in-session timeline until resume UI added |
| O | Patient context isolation | VERIFIED (code) | NovaWorkspace useEffect[patientId] hard-reset + epoch guard | JS bracket-parse OK | **fixed real defect (was absent)** | build not run locally |
| P | Postgres persistence | IMPLEMENTED_BUT_NOT_VERIFIED | PostgresNovaCaseRepository + audit; historical CI PASS (prior SHA) | no local Postgres image | none | current SHA not re-run in CI |
| Q | Migrations | IMPLEMENTED_BUT_NOT_VERIFIED | nova_migrations ordered runner + state_schema_version | no local Postgres | none | not re-run at current SHA |
| R | Concurrency | IMPLEMENTED_BUT_NOT_VERIFIED | optimistic version + retry; historical CI PASS | no local Postgres | none | not re-run at current SHA |
| S | Idempotency | IMPLEMENTED_BUT_NOT_VERIFIED | observation PK; frontend reuses observation_id + double-submit guard | no local DB | frontend double-submit guard added | not re-run locally |
| T | Redis/SMART session | IMPLEMENTED_BUT_NOT_VERIFIED | code present; no Redis image (registry Forbidden) | Redis service | none | REDIS INTEGRATION: NOT VERIFIED |
| U | OIDC/RBAC | IMPLEMENTED_BUT_NOT_VERIFIED | roles/scopes + JWKS verify; historical CI PASS | real IdP | none | real IdP NOT VERIFIED |
| V | Audit | IMPLEMENTED_BUT_NOT_VERIFIED | events incl close (now locale+versions); no private reasoning stored | backend pytest env | close audit fields added | not re-run locally |
| W | Observability | IMPLEMENTED_BUT_NOT_VERIFIED | metrics incl parse_failure/case_conflict/save_retry/critical_blocks | pytest env | none | not re-run locally |
| X | Error contracts | IMPLEMENTED_BUT_NOT_VERIFIED | JSON envelope {code,message,request_id,retryable}; FE uses errText | pytest env | none | not re-run locally |
| Y | LLM degradation | VERIFIED (FE) / IMPLEMENTED_BUT_NOT_VERIFIED (BE) | decision.llm_degraded → prominent red banner (NovaWorkspace) + status headline | build | **added degraded banner** | build not run locally |
| Z | Prompt-injection safety | IMPLEMENTED_BUT_NOT_VERIFIED | UNTRUSTED CLINICAL DATA boundary in llm_client | pytest env | none | not re-run locally |
| AA | Docker/deployment | IMPLEMENTED_BUT_NOT_VERIFIED | backend + production Dockerfiles; historical CI container smoke PASS | no registry access | none | not re-run at current SHA |
| AB | Backup/recovery prep | PARTIAL/MISSING | documented in DEPLOYMENT; no automated drill | drill | none | NOT VERIFIED |
| AC | Browser E2E | MISSING | no Playwright/E2E spec present (verify_local_release reports NOT AVAILABLE) | E2E harness | documented as gap | no automated E2E |
| AD | Competition artifact | IMPLEMENTED_BUT_NOT_VERIFIED | submission/ pydantic-only; source-sync test; mirror re-synced incl unit_safety | build_submission needs pydantic | mirror re-synced | sync test not re-run locally |
| AE | Official competition adapter | N/A (correctly placeholder) | competition/schema.py PLACEHOLDER | official API doc | none | Official contract NOT VERIFIED |
| AF | Blind evaluation | PARTIAL | v6/v8 REFERENCE-ONLY; v9 authored+frozen (sha 39b1847d, integrity PASS) | v9 first run needs pydantic | **authored+froze Blind v9** | BLIND V9 FIRST RUN: NOT VERIFIED |
| AG | Documentation consistency | VERIFIED | overclaim scan: no unverified production-ready/validated/100% claims | — | v8→reference-only noted; TEST_EVIDENCE updated | — |
| AH | Security/privacy | VERIFIED (static) | secret scan 0 hits; no PHI params in log_event | — | none | institutional review NOT VERIFIED |
| AI | Performance | IMPLEMENTED_BUT_NOT_VERIFIED | historical CI load-smoke PASS | no local load env | none | not re-run at current SHA |
| AJ | Accessibility | IMPLEMENTED_BUT_NOT_VERIFIED | ARIA roles, focus, non-color-only state in NOVA components | manual/axe run | none | not audited with a tool this round |

## Reasoning-code-change note (blind discipline)

This round changed reasoning code (`nova_agent/unit_safety.py` [new], `objective_evidence.py`,
`severity_evidence.py`). Per the blind-set discipline: **Blind v6 and Blind v8 are now
REFERENCE-ONLY**, and a fresh **Blind v9** (44 cases, frozen `blind_v9_manifest.json`) was authored
as the untouched check for the current code. Its **first run is NOT VERIFIED** (needs pydantic) and
must be run exactly once, then transcribed and never re-tuned against.

## Local verification (this environment)

`python scripts/verify_local_release.py` →
`unit_safety_guard: PASS`, `blind_integrity: PASS (v9)`, everything else `NOT AVAILABLE`
(pydantic/fastapi/psycopg/npm/Postgres/Redis absent). No FAIL. Artifact:
`artifacts/verification/local-release-<sha>.json`.
