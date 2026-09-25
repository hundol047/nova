# N.O.V.A. Hospital-Grade Clinical Decision Support — Requirements

> Spec status: **living document**. This is the authoritative requirements source for turning the
> N.O.V.A. 2026 Doctor Agent into a hospital PoC-ready, production-grade Clinical Decision Support
> (CDS) platform *and* a competition submission artifact.
>
> **Scope boundary (non-negotiable).** N.O.V.A. is **decision support + clinician review**, never
> autonomous diagnosis and never autonomous treatment. No requirement in this document authorizes
> automatic writing of diagnoses, medication/lab orders, or treatment start/stop to any EMR/FHIR
> system. `clinician_review_required` is always `true`.
>
> **Verification honesty (non-negotiable).** A requirement is only "met" when proven by real
> code + real test + real CI evidence. Anything not actually executed is labelled `NOT VERIFIED`.
> The following are **out of software scope** and stay `NOT VERIFIED` until externally proven:
> clinical validation, regulatory approval, hospital institutional security approval, real SNUBH
> integration, and any real LLM / real FHIR / real OIDC / real SMART endpoint verification for
> which no credentials/environment exist.

## Legend

Each requirement carries a current status against the repository audit (see `tasks.md` T1):

- **DONE** — implemented and (where an executable env exists) test-covered.
- **PARTIAL** — partially implemented; specific gap named.
- **MISSING** — not implemented.
- **STALE** — implemented but inconsistent with current code/docs.

---

## R1 Clinical Reasoning

**R1.1** The system shall run an ASK / EXAM / TEST / DIAGNOSE loop that reaches a final DIAGNOSE
within a hard turn limit (default 60), for every case, regardless of LLM availability.
- Acceptance: `decide()` never raises; a forced DIAGNOSE is produced at/under the turn limit;
  covered by `tests/` orchestrator + stop-policy tests. **Status: DONE.**

**R1.2** The deterministic differential/safety prior shall always be computed before the LLM step,
and the LLM may re-rank, add evidence, or introduce a diagnosis outside the knowledge base.
- Acceptance: `tests/test_hybrid_and_robustness.py` proves the LLM can change the differential and
  select a valid non-deterministic candidate. **Status: DONE.**

**R1.3** The `ClinicalPresentation` fed to reasoning shall be rebuilt from the full latest
`PatientState` every turn, and negative/denied findings shall never be re-injected as positive
candidates.
- Acceptance: `tests/test_clinical_presentation.py` covers initial complaint, ASK positive, ASK
  negative, EXAM, TEST, history, medication, imaging, lab; a negation regression asserts denied
  findings are not positive candidates. **Status: PARTIAL** — presentation exists; explicit
  negation-non-reinjection regression to be strengthened (see R1.3 tasks).

**R1.4** Objective evidence (glucose, lactate, troponin, D-dimer, K, Na, creatinine, WBC, Hgb,
platelet, pH, bicarbonate, ketone, CRP, beta-hCG) shall be normalized deterministically, and when
units are ambiguous the system shall not assert a clinical interpretation from the bare number.
- Acceptance: `nova_agent/glucose_evidence.py` + objective-evidence tests cover threshold logic and
  an ambiguous-unit case that yields no interpretation. **Status: PARTIAL** — glucose done; full
  analyte coverage + ambiguous-unit guard to be verified across the list.

---

## R2 Patient Safety

**R2.1** The system shall maintain a Must-Not-Miss (dangerous-if-missed) set separately from the
ranked differential, and shall not silently drop an active dangerous finding.
- Acceptance: safety-layer + safety-regression tests prove an active dangerous finding survives
  even if the LLM output dropped it. **Status: DONE.**

**R2.2** Diagnostic likelihood, physiologic severity, and safety priority shall be three separate
axes; a diagnosis's score shall not increase merely because it is dangerous.
- Acceptance: `tests/test_severity_evidence.py` asserts `diagnostic_score` is disease-specific and
  `severity_score` is a separate axis consumed only by the stop policy. **Status: DONE.**

**R2.3** N.O.V.A. shall never auto-execute a diagnosis/prescription/order/treatment, and every
decide response shall carry `clinician_review_required = true`.
- Acceptance: `NovaDecideResponse.clinician_review_required` is `Literal[True]`; no NOVA endpoint
  calls an order/write repository; backend RBAC/FHIR-write test asserts no write path.
  **Status: DONE (code) / NOT VERIFIED (executed here — see env constraint).**

**R2.4** A premature DIAGNOSE shall be blocked while an unresolved critical alternative remains,
but the stop policy shall not force every possible test (minimum discriminative evidence only).
- Acceptance: `tests/test_stop_policy_anchoring.py` covers block-on-unresolved-critical and
  not-over-testing. **Status: DONE.**

---

## R3 FHIR / EMR Integration

**R3.1** FHIR → N.O.V.A. mapping shall be read-only (never write back) and shall preserve:
canonical id, raw display, code system, code, value, unit, status, observed time, issued time,
source; unmapped codes shall be retained (counted), never silently dropped.
- Acceptance: `backend/tests/test_nova_fhir_mapper.py` asserts field preservation and that an
  unmapped code appears in `unmapped_clinical_codes` and increments the metric.
  **Status: PARTIAL** — ingestion + unmapped retention DONE; structured code-system/code +
  issued-vs-observed time + per-observation source to be elevated from free-text to structured
  fields.

**R3.2** DiagnosticReport.conclusion and ImagingStudy.description (CXR/CT/MRI, ECG-derived findings
where represented) shall actually reach candidate generation / scoring.
- Acceptance: a mapper→reasoning test proves a DiagnosticReport conclusion changes the differential.
  **Status: PARTIAL** — resources are ingested into `state.imaging`; reasoning-consumption test to
  be added.

**R3.3** Temporal evidence shall support recent / historical / stale distinctions and, where two
timestamped values exist, a deterministic trend (e.g. troponin rising, Hgb falling).
- Acceptance: a deterministic trend-extraction unit test over timestamped labs. **Status: MISSING.**

**R3.4** LOINC/clinical code mapping shall use only real standard codes; no fabricated codes.
- Acceptance: `backend/tests/test_clinical_code_mapper.py` covers the LOINC table; codes are real.
  **Status: DONE.**

---

## R4 Authentication / RBAC

**R4.1** The system shall enforce role-based access with least privilege across roles
`clinician_readonly`, `clinician`, `pharmacist`, `admin` and scopes `nova:read`, `nova:invoke`,
`nova:review`, plus `metrics` and `audit` access.
- Acceptance: `backend/tests/test_nova_auth.py` asserts each role's allowed/denied NOVA actions.
  **Status: DONE (code) / NOT VERIFIED here.**

**R4.2** OIDC bearer/session verification shall validate signature/issuer/audience/expiry, and an
unrecognized role claim shall fall back to least privilege.
- Acceptance: auth unit tests. Real IdP verification is **NOT VERIFIED** (no IdP).
  **Status: PARTIAL (unit DONE, real IdP NOT VERIFIED).**

**R4.3** RBAC/OIDC/SMART safety shall never be bypassable by request shape.
- Acceptance: negative auth tests (missing/invalid token → 401/403). **Status: DONE (code).**

---

## R5 Persistence

**R5.1** N.O.V.A. case state and audit shall be durable in Postgres in production; production shall
not silently fall back to in-memory persistence.
- Acceptance: `production_guard.py` blocks production start without Postgres; Postgres repo tests
  run in CI against a real DB. **Status: PARTIAL** — repo + guard DONE; **real Postgres CI
  enforcement MISSING** (tests currently skip when no DB).

**R5.2** Case records shall carry a `state_schema_version` for forward compatibility.
- Acceptance: column present in the `nova_cases` schema + a read/write round-trip test.
  **Status: MISSING** (a `SCHEMA_VERSION` constant exists in the decide `versions` dict, but no
  persisted column).

**R5.3** Long-lived schema shall be managed by a versioned migration system (not only
`CREATE TABLE IF NOT EXISTS`), with migration version + upgrade path + schema history.
- Acceptance: migration files + a CI step that applies them to the real Postgres service.
  **Status: MISSING.**

---

## R6 Concurrency

**R6.1** Concurrent writers to one case shall use optimistic concurrency with retry + jittered
backoff; silent lost updates shall be zero.
- Acceptance: `backend/tests/test_nova_postgres_concurrency.py` covers observation+observation,
  observation+decide, decide+decide, decide+locale, decide+close, observation+close with a
  lost-update assertion of 0. **Status: PARTIAL** — optimistic concurrency + retry DONE; full
  matrix + **real-DB CI execution MISSING**.

**R6.2** The LLM circuit breaker shall guarantee a single half-open probe under concurrency.
- Acceptance: a test firing ~20 concurrent requests asserts exactly one recovery probe.
  **Status: PARTIAL** — single-probe guarantee implemented (commit b871d74); explicit 20-way
  concurrency test to be verified.

---

## R7 Multilingual

**R7.1** The system shall support ko / en / ja / zh-CN.
- Acceptance:
  - same canonical `diagnosis_id` across all locales;
  - locale changes affect display language only;
  - switching locale does not reset the case (turn count, observations, differential, patient
    state preserved);
  - mixed-language clinical input is supported.
  **Status: PARTIAL** — backend locale + canonical-id invariance DONE; **frontend i18n MISSING**.

**R7.2** Mid-case locale switching shall be via `PATCH /v1/nova/cases/{id}/locale` and shall never
reinitialize the case.
- Acceptance: `backend/tests/test_nova_locale.py` / `test_locale_switching.py` assert turn count +
  observations + differential survive the switch. **Status: DONE (backend).**

**R7.3** Multilingual clinical input shall be handled for ko/en/ja/zh and mixed (ko/en, ja/en,
zh/en) across clinical categories: chest pain, dyspnea, focal weakness, aphasia, GI bleeding,
syncope, fever, allergic symptoms, abdominal pain, trauma, pelvic symptoms, metabolic symptoms.
- Acceptance: `tests/test_multilingual_clinical_input.py` covers each category + mixed input and
  asserts the same canonical routing/diagnosis id. **Status: PARTIAL** — expand coverage to the
  full category + language matrix.

**R7.4** Negation / temporality / severity shall be recognized in all four languages
(ko: 없음/부인함/갑자기/며칠 전부터/심한/악화됨; en: denies/sudden/for 3 days/severe/worsening;
ja: ない/否定/突然/数日前から/激しい/悪化; zh: 没有/否认/突然/几天前开始/严重/加重).
- Acceptance: parser tests per language. **Status: PARTIAL — verify coverage across all four.**

---

## R8 Frontend Clinical UX

**R8.1** There shall be a dedicated N.O.V.A. clinical workspace (separate from the SynexAgent UI,
not breaking it), composed of small components under `frontend/src/components/nova/`.
- Acceptance: `NovaWorkspace` and sub-panels exist as separate files; SynexAgent UI still builds
  and renders. **Status: MISSING.**

**R8.2** The workspace shall drive the full real-API workflow: patient selection → create case →
chief complaint → decide → must-not-miss → differential → next best action → ASK/EXAM/TEST → enter
result → POST observation → re-decide → updated differential → final recommendation → accept /
modify / reject → audit → close. It shall use the real `/v1/nova/*` API (no mock-only frontend).
- Acceptance: browser smoke exercises the path against a running backend. **Status: MISSING.**

**R8.3** The UI shall present, as distinct areas: MUST-NOT-MISS (separated from differential),
DIFFERENTIAL, NEXT BEST ACTION, SUPPORTING EVIDENCE, CONTRADICTORY EVIDENCE, MISSING INFORMATION,
CASE TIMELINE, CLINICIAN REVIEW, SYSTEM STATUS.
- Acceptance: each area rendered from decide-response fields. **Status: MISSING.**

**R8.4** Each differential item shall show: display diagnosis, canonical `diagnosis_id`, confidence
band (LOW/MEDIUM/HIGH — never a `%` unless calibrated), urgency, `dangerous_if_missed`, supporting
evidence, contradictory evidence, missing discriminative evidence, candidate sources.
- Acceptance: component test asserts no raw `%` for uncalibrated confidence. **Status: MISSING.**

**R8.5** Next Best Action shall show the action type (ASK/EXAM/TEST/DIAGNOSE) plus What / Why /
What-it-distinguishes. **Status: MISSING.**

**R8.6** Observation submission shall carry a stable `observation_id` reused across network retries
so a retry never creates a double turn. **Status: MISSING (frontend); backend idempotency DONE.**

**R8.7** Clinician review shall support Accept / Modify / Reject with a reason, and shall never
trigger an automatic order. The audit record shall include case_id, patient_id, clinician, role,
disposition, reason, locale, agent_version, model_version, kb_version, timestamp.
- Acceptance: review flow posts to `/close`; audit fields asserted in backend tests.
  **Status: PARTIAL** — backend audit fields DONE; **frontend review UI MISSING**.

**R8.8** A top-bar language selector (한국어 | English | 日本語 | 中文) shall persist to
localStorage with priority: saved preference → browser language → Korean. **Status: MISSING.**

**R8.9** Every panel shall have loading / empty / error / degraded / retry states. **Status: MISSING.**

**R8.10** The UI shall meet basic accessibility (keyboard nav, focus management, ARIA, critical
state not conveyed by color alone, accessible button names) and be responsive at 1920 / 1440 /
tablet-landscape. **Status: MISSING.**

**R8.11** Frontend strings shall be externalized to `frontend/src/i18n/{index,ko,en,ja,zh}.js`
covering at least: topbar, tabs, patient information, NOVA, buttons, errors, loading, audit,
clinical safety, environment, system status — in all four languages. **Status: MISSING.**

---

## R9 Observability

**R9.1** The system shall emit metrics: `nova_requests_total`, `nova_errors_total`, `nova_latency`,
`nova_llm_calls`, `nova_llm_success`, `nova_llm_fallback`, `nova_parse_failure`,
`nova_case_conflict`, `nova_save_retry`, `nova_unmapped_clinical_codes`, `nova_critical_blocks`,
`nova_turn_count`.
- Acceptance: a metrics test asserts each named counter/histogram exists and moves.
  **Status: PARTIAL** — requests/errors/latency/llm_*/turn_count/unmapped DONE; **parse_failure,
  case_conflict, save_retry, critical_blocks MISSING under those names** (`nova_safety_blocks`
  exists as the closest to critical_blocks).

**R9.2** Structured logs shall carry: timestamp, request_id, case_id, component, event, latency_ms,
provider, model, locale, error_code; raw PHI text shall be minimized.
- Acceptance: log-event test asserts fields present and no chief_complaint/result payload.
  **Status: PARTIAL** — most fields DONE; add `locale`; verify no PHI.

**R9.3** Audit shall record at least: `nova_case_created`, `nova_observation_added`, `nova_decide`,
`nova_locale_changed`, `nova_case_reviewed`, `nova_case_closed`, `nova_llm_degraded`,
`nova_storage_conflict`. Private chain-of-thought shall never be stored.
- Acceptance: audit tests assert events + absence of raw reasoning. **Status: PARTIAL** — most
  events DONE; `nova_llm_degraded` + `nova_storage_conflict` to be verified as explicit events.

**R9.4** A single correlation/request id shall be traceable across frontend → API → service →
audit → logs. **Status: PARTIAL** — request_id generated server-side; end-to-end propagation
(incl. client-supplied header) to be verified.

---

## R10 Reliability

**R10.1** A per-turn LLM failure shall degrade to the deterministic fallback without crashing the
case, and the degraded state shall be visible (never disguised as a healthy LLM response).
- Acceptance: reliability tests + decide response `llm_degraded`. **Status: DONE (code).**

**R10.2** The frontend shall display AI Available / AI Degraded / LLM Unavailable / Safety Fallback
Active. **Status: MISSING.**

**R10.3** A `/ready` readiness check shall verify Postgres, audit, shared state, auth config, FHIR
config, LLM provider, NOVA service, knowledge base.
- Acceptance: `/ready` returns 503 when a required subsystem is down in production mode.
  **Status: PARTIAL** — `/ready` exists; add explicit Postgres/audit/circuit-breaker subsystem
  reporting.

**R10.4** A system-status surface (FHIR, Database, LLM, Auth, NOVA) shall be exposed without
leaking secrets. **Status: PARTIAL** — `/health/subsystems` exists; circuit-breaker + DB status to
be surfaced; frontend SYSTEM STATUS panel MISSING.

---

## R11 Security / Privacy

**R11.1** Patient free-text shall be treated as untrusted clinical data at the LLM boundary
(explicit "UNTRUSTED CLINICAL DATA" delimiter; injection attempts treated as symptom text, never
instructions). **Status: DONE.**

**R11.2** SMART launch patient context shall fail closed: a request for a different patient than the
SMART session's patient shall be refused. **Status: PARTIAL** — FHIR fetch layer is fail-closed;
NOVA endpoint-level patient-scope cross-check to be verified/added.

**R11.3** No secret / API key / password shall be committed; a CI secret scan shall run.
- Acceptance: `build_nova_submission.py` secret scan + a repo-wide secret-scan CI step.
  **Status: PARTIAL** — submission secret scan DONE; repo-wide CI secret scan to be added.

**R11.4** Dependency vulnerability scanning (pip + npm) shall run and report critical/high findings;
no blind force-upgrades. **Status: MISSING.**

**R11.5** Private chain-of-thought shall never be persisted to API responses, audit, or logs.
**Status: DONE (only differential + selected action consumed).**

---

## R12 Competition Runtime

**R12.1** The competition I/O schema/adapter shall remain a disclosed placeholder until an official
N.O.V.A. 2026 API document is provided; nothing competition-protocol-shaped shall leak into the
reasoning engine. Absent the official spec, status shall read `Official competition API:
NOT VERIFIED`. **Status: DONE.**

**R12.2** Competition mode shall never silently complete a case on the deterministic fallback alone;
a zero-real-LLM-success DIAGNOSE shall raise rather than return a disguised success.
**Status: DONE (code) / real-LLM path NOT VERIFIED.**

**R12.3** After any `nova_agent/` change, `scripts/build_nova_submission.py` shall regenerate
`submission/`, and `submission/` shall never be hand-edited; a sync test shall fail CI on drift.
**Status: DONE.**

**R12.4** The competition artifact shall stay minimal and independent (no FastAPI/Postgres/frontend/
FHIR/OIDC dependencies pulled into the submission). **Status: DONE.**

---

## R13 Evaluation

**R13.1** Existing regression gates shall hold: Held-out scored = 100%, Held-out all-case ≥ 94.4%,
Development generalization = 100%, Stress = 100%, Critical miss = 0, Duplicate action = 0, Failed
diagnosis = 0. A blind-set-leakage static scan shall pass. **Status: PARTIAL (gates exist;
execution here NOT VERIFIED — no runnable Python env).**

**R13.2** Blind evaluation shall be honest: after all reasoning changes are complete and the code is
frozen, a fresh Blind v7 (70–80 cases across the required clinical + language axes, not translated
reuse) shall be authored and hash-frozen (manifest: case_count, sha256, base_commit, created_at,
language + category distribution) and run **exactly once**; its result shall not drive further
tuning of v7 (a future v8 stays untouched instead). Blind v6 becomes reference-only.
- Acceptance: `evaluation/blind_v7_manifest.json` + `blind_cases_v7.py` + `blind_benchmark_v7.py`;
  a first-run report. **Status: MISSING (v6 exists; v7 to author). First run is NOT VERIFIED in
  this env — requires a runnable Python environment.**

**R13.3** No rule/alias/case shall be hardcoded from a specific blind case's sentence or answer.
- Acceptance: `scripts/check_eval_leakage.py` passes. **Status: DONE (mechanism exists).**

---

## R14 CI/CD

**R14.1** CI shall include jobs (or equivalent): `nova-agent`, `production`, `production-backend`,
`frontend`, `postgres-integration`, `competition-readiness`.
- Acceptance: workflow file defines them and they run on PRs to the integration branch.
  **Status: PARTIAL** — nova-agent/production/production-backend/competition-readiness DONE;
  **frontend + postgres-integration MISSING**; triggers currently only target `main`.

**R14.2** Postgres integration tests shall run against a real `postgres:16` service in CI, and a
skipped Postgres integration in CI shall FAIL the build (local skip allowed only).
- Acceptance: a `postgres-integration` job with a `services: postgres` block + an env flag that
  turns skip into failure in CI. **Status: MISSING.**

**R14.3** Frontend CI shall run `npm ci` + `npm run build` (+ vitest where present), and a browser
smoke (Playwright where feasible) shall exercise page load, patient open, NOVA tab, case create,
decision visible, observation submit, locale switch, review. **Status: MISSING.**

**R14.4** Docker build + container health/ready smoke shall pass for both the backend image and the
production image. **Status: DONE (in CI) / NOT VERIFIED here.**

**R14.5** A repo-wide secret scan and dependency vulnerability scan shall run in CI.
**Status: MISSING.**

---

## R15 Deployment

**R15.1** There shall be **one** official hospital production path: the `backend/` integrated app
(FHIR/OIDC/SMART/RBAC/audit reuse). `production/` is an explicitly labelled reference/lightweight
standalone deployment. Two competing hospital production architectures shall not be maintained.
- Acceptance: docs name `backend/` as authoritative; `production/` labelled reference.
  **Status: PARTIAL** — both exist; authoritative-vs-reference labelling to be made explicit and
  consistent.

**R15.2** Docker + docker-compose (incl. a production compose with Postgres) shall build and start
to a healthy `/ready`. **Status: PARTIAL (compose exists) / NOT VERIFIED here.**

---

## R16 Documentation

**R16.1** README and all NOVA docs shall match current code; stale claims (e.g. "NOVA cases are
in-memory only", "Postgres not consumed") shall be removed/corrected. **Status: STALE.**

**R16.2** Duplicate doc trees (`docs/NOVA_*.md` vs `docs/nova/*.md`) shall be reconciled to a single
authoritative source; duplicates shall not state conflicting facts. **Status: STALE.**

**R16.3** Final documentation shall cover: Architecture, Deployment, FHIR Integration, SMART/OIDC,
Security, Clinical Safety, Operations, Runbook, Data Model, Persistence, Multilingual, Evaluation,
Competition Submission, Known Limitations. **Status: PARTIAL.**

**R16.4** External-validation claims (clinical validation, hospital security approval, regulatory
approval, real SNUBH integration, real LLM/FHIR/OIDC/SMART) shall be explicitly `NOT VERIFIED`
wherever they appear. **Status: PARTIAL — enforce consistently.**
