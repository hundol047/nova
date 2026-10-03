# N.O.V.A. Demo / Judge Flow (≈5 minutes)

> A short, honest walkthrough for the N.O.V.A. 2026 competition / a SNUBH demo. **Only shows
> features that actually exist and are CI-verified.** No feature is implied that is NOT VERIFIED.

## Happy-path flow (≈5 min)

1. **Language** — pick 한국어 / English / 日本語 / 中文 in the top-bar selector (persists; canonical
   diagnosis ids stay identical across languages — only display changes).
2. **Patient context** — select a (synthetic/test) patient in the workspace.
3. **Start a N.O.V.A. case** — enter a chief complaint (e.g. "sudden chest pressure with sweating").
4. **Decide** — the workspace calls the real `/v1/nova/decide` and shows:
   - **MUST-NOT-MISS** panel (separated from the differential),
   - **Differential** with canonical id + LOW/MEDIUM/HIGH confidence (never a fake %),
   - **Next Best Action** (ASK/EXAM/TEST/DIAGNOSE) with What / Why,
   - **Supporting / Contradictory / Missing** evidence for the selected item.
5. **Enter a result** — submit an ASK/EXAM/TEST result (stable `observation_id`, retry-safe) →
   re-decide → the differential updates.
6. **Final recommendation** — when the agent reaches DIAGNOSE, the recommendation is shown with the
   standing "clinician review required" banner.
7. **Clinician review** — Accept / Modify / Reject with a reason. **No order is executed
   automatically.**
8. **Audit + close** — the disposition, reason, locale, and versions are recorded to the audit
   trail; close the case.
9. **Mid-case language switch (optional)** — switch language mid-case; the case is preserved (turn
   count, observations, differential) — only the display language changes.
10. **System status** — the SYSTEM STATUS panel shows FHIR / DB / LLM / Auth / N.O.V.A. and, if the
    model is degraded, an explicit "AI Degraded / Safety Fallback Active" state (never hidden).

## What to say about status (honesty on stage)

- "This is decision support with clinician review — not autonomous diagnosis or treatment."
- "Persistence, concurrency, RBAC, FHIR mapping, and the frontend are verified in CI (including a
  real Postgres integration job)."
- "Real hospital LLM/FHIR/OIDC/SMART integration, clinical validation, security review, and
  regulatory approval are **NOT VERIFIED** — this is a PoC-ready software platform, not a
  hospital-cleared product."

## Failure fallback (if something breaks during the demo)

Do **not** pretend a failure didn't happen. The system is designed to fail visibly:

- **LLM down** → the decide response shows `llm_degraded` and the UI shows "AI Degraded / Safety
  Fallback Active"; explain that the deterministic safety-guard reasoning still produces a safe,
  reviewable recommendation and never fabricates a confident answer.
- **FHIR unavailable** → patient context can't load; explain the read-only, fail-closed design and
  fall back to a manual chief-complaint entry for the synthetic case.
- **Network / backend hiccup** → each panel has loading/error/retry states; hit retry, or switch to
  a pre-created case; explain the idempotent observation design (a retry never double-advances a
  turn).
