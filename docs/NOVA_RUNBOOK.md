# N.O.V.A. Runbook (Backend-Integrated)

## LLM endpoint down / unreachable

**Symptom**: `nova_llm_calls_total` increments but `nova_llm_success_total` does not (`GET
/v1/nova/metrics`); repeated `decide()` responses carry `llm_degraded: true`.

**Effect on cases**: `NovaService`'s circuit breaker (`_LLMCircuitBreaker`) opens after
`NOVA_CB_FAILURE_THRESHOLD` (default 5) consecutive real-provider failures and, while open,
constructs `DoctorAgent` with a forced `MockLLMClient` instead of attempting another real call --
cases keep moving on the deterministic safety-guard reasoning path, never blocked. This is always
disclosed in the response (`llm_degraded: true` + a limitations entry), never silent.

**Action**: confirm the provider's own status page. No manual reset action is normally needed --
the breaker moves to half-open after `NOVA_CB_COOLDOWN_SECONDS` (default 30s) and retries on its
own; a success there closes it again automatically.

## High LLM fallback rate

**Symptom**: `GET /v1/nova/metrics`'s `derived.nova_llm_fallback_rate` is elevated but not near 1.0.

**Action**: check provider-side rate limiting or latency degradation first. The deterministic
fallback path is safe to run on indefinitely from a correctness standpoint, but sustained fallback
means cases aren't getting the LLM's re-ranking contribution -- treat a sustained elevated rate as
a provider incident, not a code bug here, unless the provider is confirmed healthy and failures
persist.

## Latency spike (`nova_latency_ms.p95` rising)

**Action**: check whether it correlates with `nova_llm_calls_total` rate (a real-LLM call is almost
always the dominant per-request cost) versus overall request volume (compare against
`scripts/load_smoke_backend.py`'s locally-measured throughput ceiling). If it correlates with LLM
calls, this is a provider-latency issue (see above). If it correlates with request volume alone,
this is a capacity issue -- scale out replicas. Note: `NovaCaseRepository` is currently in-memory
per-process, so a multi-replica deployment today would NOT share case state across replicas (see
`docs/NOVA_DEPLOYMENT.md`'s Persistence section) -- resolve that before scaling out for real.

## Database/EMR unavailable

**Symptom**: `GET /ready`'s `emr_adapter_ready` check fails, or a request returns
`{"error": {"code": "EMR_unavailable"}}` (503).

**Action**: this reflects the active `FHIRAdapter`'s connectivity to the real hospital FHIR server
(under `EMR_MODE=fhir`) -- an infrastructure incident outside this backend's own control. `/ready`
recovers automatically once the FHIR server is reachable again; no application restart needed
(`app.state.adapter` is checked live on every `/ready` call, not cached as a permanent-down state).

## Bad deployment (a new version is unhealthy)

**Action**: `/ready` failing on the new version's containers is the signal to halt rollout. Every
SHA-tagged image the `production-backend` CI job builds is retained; rollback means routing traffic
back to the previous known-good SHA-tagged image. No database migration is expected to need
reverting as long as schema changes stayed additive (see `docs/NOVA_DEPLOYMENT.md`'s Rollback
section).

## Secret rotation

**Action**: `OIDC_ISSUER`/`OIDC_AUDIENCE`/`FHIR_CLIENT_SECRET`/the LLM provider API key are all
read from the process environment at request time or at `get_llm_client()`/adapter-construction
time -- rotating any of them today requires a redeploy with the new value, same as this backend's
pre-existing secret-handling pattern (no live-rotation endpoint exists for any of them, N.O.V.A.-
specific or not).

## Circuit breaker stuck open

**Symptom**: `nova_llm_fallback_rate` stays near 1.0 well past `NOVA_CB_COOLDOWN_SECONDS` after the
provider is confirmed healthy again.

**Action**: the breaker only re-attempts a real call once per cooldown window (half-open trial) --
if that trial itself fails (e.g. a transient error right at the retry moment), it reopens for
another full cooldown. This is expected behavior, not a bug, but if it persists unexpectedly longer
than a few cooldown cycles after the provider is confirmed healthy, restart the backend process
(there is no live breaker-reset endpoint; `NovaService.__init__` constructs a fresh, closed breaker).
