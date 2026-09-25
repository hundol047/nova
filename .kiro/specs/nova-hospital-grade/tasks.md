# N.O.V.A. Hospital-Grade CDS — Tasks

Small, ordered, checkbox tasks with acceptance conditions, grouped into the staged PRs described to
the user. Each stage is its own PR against the integration branch `claude/practical-feynman-xv8uxs`
and verified by GitHub Actions. Items that cannot be executed in the network-isolated authoring
environment are delegated to CI and reported `NOT VERIFIED` until CI runs them.

Legend: `[ ]` todo · `[x]` done · `[~]` done-in-code / NOT VERIFIED locally (CI-delegated).

---

## Stage 1 — Spec + Steering  (PR #1)

- [x] **T1 Repository audit.** Read backend/, nova_agent/, competition/, frontend/, docs/, CI,
  tests; classify each area DONE/PARTIAL/MISSING/STALE; verify branch = `claude/practical-feynman-xv8uxs`
  @ `b871d74`. _Acceptance:_ audit recorded in `requirements.md` statuses + audit table (below).
- [x] **T1a requirements.md** with R1–R16 + measurable acceptance criteria.
- [x] **T1b design.md** with the hospital architecture + backend=production / production=reference.
- [x] **T1c tasks.md** (this file) with T1–T18 + acceptance conditions.
- [x] **T1d Steering** `.kiro/steering/nova-safety.md`. _Acceptance:_ contains the CDS-not-autonomous,
  no-auto-treatment, no-blind-leakage, no-unverified-claims, locale-independent-ids, backend=hospital-path,
  competition-isolated rules.

## Stage 2 — N.O.V.A. Frontend + i18n  (PR #2)

- [ ] **T2 NOVA workspace components** under `frontend/src/components/nova/` (Workspace, CaseHeader,
  CriticalPanel, DifferentialPanel, NextActionPanel, EvidencePanel, ObservationForm, CaseTimeline,
  ReviewPanel, SystemStatus). _Acceptance:_ files exist, App.jsx adds a NOVA tab, SynexAgent UI
  untouched; `npm run build` green in CI.
- [ ] **T2a Full API workflow** wired to real `/v1/nova/*` (create → decide → observation →
  re-decide → review → close), idempotent `observation_id` reused on retry. _Acceptance:_ browser
  smoke passes in CI.
- [ ] **T2b UI areas** must-not-miss (separated), differential (id + LOW/MED/HIGH, no raw %),
  next-best-action (What/Why/Distinguishes), supporting/contradictory/missing evidence, timeline,
  clinician review (Accept/Modify/Reject + reason), system status + AI degraded states, per-panel
  loading/empty/error/degraded/retry, a11y + responsive.
- [ ] **T3 i18n** `frontend/src/i18n/{index,ko,en,ja,zh}.js`; top-bar selector
  (한국어|English|日本語|中文) persisted to localStorage (saved→browser→ko); externalize core
  strings (topbar, tabs, patient info, NOVA, buttons, errors, loading, audit, clinical safety,
  environment, system status) in all four languages; mid-case `PATCH locale` never resets case.
  _Acceptance:_ vitest for locale detection + a canonical-id-unchanged-on-locale-switch test.
- [ ] **T10a Frontend CI** `frontend` job: `npm ci` + `npm run build` + vitest + browser smoke.
  _Acceptance:_ job green on the PR.

## Stage 3 — Backend gap + Postgres + CI  (PR #3)

- [ ] **T5 FHIR temporal/provenance** structured field preservation (canonical id, raw display,
  code system, code, value, unit, status, observed/issued time, source); unmapped retained;
  deterministic recent/historical/stale + rising/falling/stable trend; DiagnosticReport/ImagingStudy
  reach reasoning. _Acceptance:_ mapper tests + a mapper→reasoning test (run in `production-backend`).
- [ ] **T7 Postgres CI** new `postgres-integration` job with `services: postgres:16`, env
  `NOVA_TEST_POSTGRES_URL` + `NOVA_CI_REQUIRE_POSTGRES=1`; tests fail (not skip) in CI when the DB
  is required. _Acceptance:_ job green with real DB; a deliberately-unreachable DB would fail.
- [ ] **T7a Migrations + state_schema_version.** Ordered SQL migration runner + `schema_migrations`
  table; `state_schema_version` column on `nova_cases`. _Acceptance:_ migration + round-trip tests
  in the Postgres job.
- [ ] **T8 Concurrency hardening.** Full matrix (obs+obs, obs+decide, decide+decide, decide+locale,
  decide+close, obs+close) lost-update=0; 20-way circuit-breaker single-probe test. _Acceptance:_
  tests green in the Postgres job.
- [ ] **T9 Observability/security/contract.** Add `nova_parse_failure`, `nova_case_conflict`,
  `nova_save_retry`, `nova_critical_blocks`; `locale` log field; `nova_llm_degraded` +
  `nova_storage_conflict` audit events; JSON error envelope `{code,message,request_id,retryable}`;
  request-id propagation; `/ready` + `/health/subsystems` report FHIR/DB/LLM(+breaker)/Auth/NOVA/KB;
  SMART patient-scope fail-closed check; repo-wide secret scan + pip/npm vuln scan in CI.
  _Acceptance:_ metrics/audit/error tests + CI security step.

## Stage 4 — Reasoning stabilization  (PR #4)

- [ ] **T6 Reasoning regressions (no blind-specific patching).** ClinicalPresentation rebuild +
  negation-non-reinjection; objective-evidence normalization across the analyte list + ambiguous-unit
  guard; multilingual clinical input + cross-language canonical equivalence; dangerous-anchoring
  generic rule; stop-policy minimum-discriminative gating; turn efficiency; semantic dedup across
  four languages. _Acceptance:_ new/expanded tests in `tests/`; `check_eval_leakage.py` passes;
  existing regression gates unchanged (R13.1). **Local run NOT VERIFIED (no Python env) → CI.**

## Stage 5 — Documentation + Blind v7  (PR #5)

- [ ] **T11 Docs cleanup.** Reconcile `docs/NOVA_*.md` vs `docs/nova/*.md` to one authoritative
  source; fix stale README claims; label `backend/` authoritative and `production/` reference;
  enforce `NOT VERIFIED` on all external-validation claims. _Acceptance:_ no conflicting duplicate
  docs; README matches code.
- [ ] **T12 Existing regression confirmation** (held-out/generalization/stress/critical-miss/
  duplicate/failed-diagnosis) via CI. **NOT VERIFIED locally → CI.**
- [ ] **T13 Code freeze.** All reasoning changes merged + regression green before authoring v7.
- [ ] **T14 Blind v7 author + freeze.** `evaluation/blind_cases_v7.py` (70–80 cases across the
  required clinical + language axes, not translated reuse) + `blind_benchmark_v7.py` +
  `evaluation/blind_v7_manifest.json` (case_count, sha256, base_commit, created_at, language +
  category distribution). _Acceptance:_ manifest hash matches the case file.
- [ ] **T15 Blind v7 FIRST RUN — exactly once.** Report accuracy/all-case/critical recall/critical
  miss/avg+median turns/action mix/duplicate rate/failed diagnosis/LLM fallback/per-language +
  sample size. No re-tuning against v7 (future v8 stays untouched). **First run NOT VERIFIED here
  (requires runnable Python env).**

## Stage 6 — Final PR / CI verification  (integration)

- [ ] **T16 Submission rebuild** `python scripts/build_nova_submission.py`; never hand-edit
  `submission/`; sync test green. **NOT VERIFIED locally → CI.**
- [ ] **T17 Full CI** on the final HEAD: nova-agent, production, production-backend, frontend,
  postgres-integration, docker build + container health/ready, submission sync, evaluation leakage,
  secret scan. _Acceptance:_ report each PASS/FAIL/SKIPPED with the run link.
- [ ] **T18 Integration + report.** Ensure each stage PR merged into the integration branch; report
  final HEAD SHA + required CI statuses in the CA format. Do not merge to `main` without the merge
  conditions (BY) met.

---

## Kiro hooks (BU)

- [ ] Hook: on `nova_agent/**` change → run relevant pytest + `scripts/check_eval_leakage.py`.
- [ ] Hook: on `backend/**` change → run targeted backend tests.
- [ ] Hook: on `frontend/**` change → `npm run build`.
- [ ] Hook: pre-commit/pre-task-complete → regression + secret scan.

(Hooks are advisory in the isolated env; they execute in a runnable env / CI.)

---

## T1 Audit table (DONE / PARTIAL / MISSING / STALE)

| Area | Status | Note |
|---|---|---|
| Clinical reasoning engine (nova_agent) | DONE | full ASK/EXAM/TEST/DIAGNOSE hybrid loop |
| Prompt-injection boundary | DONE | UNTRUSTED CLINICAL DATA delimiter |
| Patient safety / must-not-miss / score separation | DONE | severity vs diagnostic vs safety_priority |
| clinician_review_required / no FHIR write | DONE | `Literal[True]`, no order path |
| Backend /v1/nova/* API | DONE | create/observation(idempotent)/decide/get/locale/close/metrics |
| Postgres case repo + audit store | PARTIAL | version+FOR UPDATE+retry done; migrations + state_schema_version missing |
| Concurrency (optimistic + retry) | PARTIAL | matrix + 20-way breaker test + real-DB CI missing |
| Multilingual backend (locale, canonical ids) | DONE | PATCH locale, id invariance |
| Multilingual frontend | MISSING | no i18n; App.jsx Korean-hardcoded |
| NOVA frontend workspace | MISSING | no components/nova/; UI is SynexAgent-only |
| Observability metrics | PARTIAL | parse_failure/case_conflict/save_retry/critical_blocks missing by name |
| FHIR temporal/trend + structured provenance | MISSING/PARTIAL | ingestion done; trend + structured fields missing |
| LOINC code mapping | DONE | real codes, no fabrication |
| Auth/RBAC/OIDC (unit) | DONE(code)/NOT VERIFIED | real IdP not verified |
| SMART fail-closed | PARTIAL | fetch-layer done; endpoint patient-scope check to add |
| /ready + system status | PARTIAL | exists; DB + circuit-breaker surfacing to add |
| Error contract + request-id propagation | PARTIAL | request_id server-side; envelope + e2e to add |
| Reliability / degraded mode (backend) | DONE(code) | decide llm_degraded |
| Circuit breaker single-probe | DONE(code) | commit b871d74; 20-way test to add |
| Competition adapter/schema | DONE(placeholder) | official API NOT VERIFIED |
| Submission sync | DONE | build script + sync test |
| Evaluation regression gates | PARTIAL/NOT VERIFIED | exist; not runnable here |
| Blind sets | v6 present | v7 to author |
| Eval leakage scan | DONE | mechanism present |
| CI jobs | PARTIAL | frontend + postgres-integration missing; triggers only main |
| Docker builds + container smoke | DONE(CI)/NOT VERIFIED | not runnable here |
| Docs | STALE | NOVA_*.md vs nova/*.md duplicates; stale claims |
| External validation claims | PARTIAL | enforce NOT VERIFIED consistently |
| clinical/regulatory/institutional/SNUBH/real-LLM-FHIR-OIDC-SMART | NOT VERIFIED | out of software scope |
