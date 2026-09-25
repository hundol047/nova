# N.O.V.A. Final Gap Closure (independent re-audit round)

> **HISTORICAL SNAPSHOT (independent-re-audit round).** Accurate for that round, when Blind **v9**
> was current. For CURRENT state see `docs/VNEXT_INDEPENDENT_AUDIT.md` and
> `evaluation/current_blind.py`.


What the independent re-audit found and what was actually done about it. Only real changes are
listed; nothing is claimed as verified that was not actually run locally.

## Defects fixed this round

1. **Patient-context case isolation (P0, was a real defect).** `NovaWorkspace` had NO reset on
   patient change — patient A's `caseState`/`decision`/`timeline`/`closed`/`caseId` persisted onto
   patient B's screen. Added a `useEffect([patientId])` hard reset + an `epochRef` so any in-flight
   response for an old patient/case is discarded. (Locale change does NOT reset the case.)

2. **Frontend API race (P1).** No stale-response protection. Every async op (create/decide/observe/
   review/locale) now captures an epoch and discards its result if the epoch changed, so a slow
   response cannot overwrite the current patient/case view.

3. **Duplicate / concurrent requests + double-submit (P1/P2).** Added an `inFlightRef` guard so a
   second create/decide/observe/review/locale is refused while one is running (covers double-click,
   repeated Enter, locale-effect + observation racing to re-decide). Retry button disabled while busy.

4. **Action after DIAGNOSE/close (P2).** Observation form hidden once the action is DIAGNOSE or the
   case is closed; decide/observe/review/locale all no-op when closed; error-retry hidden when closed.

5. **Custom (non-EMR) patient handling (P2).** Custom/locally-entered patients cannot be resolved by
   the backend adapter; instead of silently disabling the workspace, it now shows an explicit
   localized message (`nova.unavailableForCustomPatient`).

6. **Lab-unit safety generalized (P0 patient-safety, was glucose-only).** Independent audit found
   creatinine (SI µmol/L vs mg/dL, ~88×) and hemoglobin (g/L vs g/dL, ~10× — could HIDE a critical
   anemia) were interpreted from bare numbers regardless of unit — the same bug class as the earlier
   glucose fix. Added `nova_agent/unit_safety.py` (dependency-free, 9 local tests PASS) and
   `disallowed_units` on the at-risk `LabSpec`s; `_extract_numeric` refuses a value in a disallowed
   unit. Lactate numeric parse also now refuses an explicit mg/dL value.

7. **Objective-evidence registry gaps (P1).** The KB relied on `lipase` (pancreatitis) and urine
   dipstick `leukocyte esterase`/`nitrites` (UTI) but the registry had no entry — values were only
   keyword-matched. Added `lab.lipase` + `lab.urinalysis_infection` specs and wired both into
   `CONFIRMATORY_PHRASE_TO_LAB`.

8. **Review audit completeness (P1).** The `nova_case_closed` audit now records `locale` +
   `agent_version` + `kb_version` (disposition/reason/user_id/role were already present). "Modify"
   clarified via a UI hint: it records the clinician's amended judgement as the reason; N.O.V.A.
   never writes a diagnosis/order back to the EMR.

9. **Timeline durability (P2).** `GET /v1/nova/cases/{id}` now returns `conversation_history`
   (durable per-turn ASK/EXAM/TEST/DIAGNOSE from `PatientState`), so a future resume path can
   restore the timeline server-side. (The resume-entry UI itself is not yet wired — see below.)

10. **Degraded-LLM visibility (P2).** A prominent red degraded banner shows in the workspace when
    `decision.llm_degraded` is true, in addition to the system-status headline — the deterministic
    fallback is never hidden as a normal AI result.

11. **Additions:** `scripts/verify_local_release.py` — a single GitHub-Actions-free verification
    entrypoint that runs what the environment supports and reports PASS/FAIL/SKIPPED/NOT AVAILABLE
    (never a false PASS), writing `artifacts/verification/local-release-<sha>.json`. Leakage scan
    now covers Blind v8 + v9.

## Gaps deliberately NOT closed this round (with reason)

- **Full SynexAgent-workspace i18n (K).** The NOVA workspace is fully localized; the legacy
  SynexAgent Clinical Workspace (`App.jsx`, a very large single file) still has hardcoded Korean.
  A full sweep is a large, build-risky change that cannot be verified here (npm broken). The
  highest-visibility, safety-relevant strings (env label, review hints, custom-patient message,
  degraded banner) were localized; the rest is left as a scoped follow-up rather than shipping an
  unverifiable mass edit. **Status: PARTIAL.**
- **Case resume UI (M) / timeline restore call (N).** The server data is now available
  (`conversation_history`); wiring a "resume existing open case" entry point is a genuine new
  feature, out of scope for a defect-fix pass. **Status: PARTIAL, server-ready.**
- **Browser E2E (AC).** No Playwright/E2E harness exists and one cannot be installed/run here
  (npm broken, no network). Documented as MISSING; `verify_local_release.py` reports it NOT
  AVAILABLE. **Status: MISSING.**
- **Redis / Postgres integration at current SHA (T/P/Q/R).** Docker daemon is up but registry
  pulls are Forbidden — no image. Code inspected; historical CI verified a prior SHA. **Status:
  NOT VERIFIED at current SHA.**

## Blind evaluation

Reasoning code changed → Blind v6 + v8 are REFERENCE-ONLY; **Blind v9** authored + frozen
(`evaluation/blind_v9_manifest.json`, sha256 `39b1847d…`, integrity check PASS). **First run NOT
VERIFIED** — run `python -m evaluation.blind_benchmark_v9` exactly once in a runnable env, record
as-is, never re-tune against.
