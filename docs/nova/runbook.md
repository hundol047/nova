# Runbook

## LLM endpoint down / unreachable

**Symptom**: `llm_calls_total` increments but `llm_success_total` does not; `/ready` still reports
`ready: true` (LLM reachability is not currently one of its checks -- see Remaining blockers).

**Effect on cases**: `nova_agent.orchestrator.DoctorAgent.decide()` never raises regardless -- a
failed real-LLM call falls back to the deterministic differential/action-selection path
transparently (spec section 20's documented degradation). Cases keep moving; the visible symptom is
a rising `llm_fallback_rate` in `GET /metrics`, not a user-facing error.

**Action**: confirm the provider's own status page. If a `CircuitBreaker`
(`production/circuit_breaker.py`) is wired around the specific provider call site, check its
`snapshot().state` -- `open` means it is already short-circuiting to fail fast rather than adding
latency per request; it will move to `half_open` after `cooldown_seconds` and retry on its own. No
manual reset action is normally needed; `CircuitBreaker.reset()` exists for an operator to force it
closed early if the provider is confirmed recovered.

## High LLM fallback rate

**Symptom**: `GET /metrics`'s `derived.llm_fallback_rate` is elevated but not near 1.0 (intermittent
failures, not a total outage).

**Action**: check provider-side rate limiting or latency degradation first (this is the most common
cause). The deterministic fallback path is safe to keep running on indefinitely from a correctness
standpoint (it is the same reasoning path the `mock` provider always uses), but sustained fallback
means the case is not getting the LLM's re-ranking/evidence-augmentation contribution -- treat a
sustained elevated rate as a provider incident to resolve, not a code bug in this repo, unless the
provider is confirmed healthy and the failures persist.

## Latency spike (`decide_latency_ms.p95` rising)

**Action**: check whether the spike correlates with `llm_calls_total` rate (a real-LLM call is
almost always the dominant cost in `decide()`) versus request volume (near the `throughput_cases_
per_sec` ceiling `scripts/load_smoke.py` measured locally). If it correlates with LLM calls, this
is a provider-latency issue (see above). If it correlates with request volume alone, this is a
capacity issue -- scale out replicas (the API is stateless per-request except for the case
repository, which must be a shared DB in a multi-replica deployment; see `docs/nova/deployment.md`
on why the in-memory repository cannot be used across replicas).

## Database unavailable

**Symptom**: `GET /ready`'s `case_repository` check fails, or individual requests return a
`persistence_error` (503).

**Action**: this is an infrastructure incident for whatever `CaseRepository`/`AuditRepository`
implementation is deployed (out of scope for this repository, which ships only the in-memory
implementation -- see `docs/nova/deployment.md`'s persistence section for what a real
implementation must guarantee). Once the database is reachable again, `/ready` should recover
without an application restart, since `get_production_config()`/`get_case_repository()` re-check on
every call rather than caching a "database is down" state permanently.

## Bad deployment (a new version is unhealthy)

**Action**: `/ready` failing on the new version's containers is the signal to halt rollout. Because
every SHA-tagged image built by the `production` CI job (`docs/nova/deployment.md`) is retained,
rollback is: stop routing traffic to the new SHA's containers, start containers from the last known
good SHA tag. No database migration is expected to need reverting as long as the new version's
schema changes were additive (see Remaining blockers on the lack of a migration mechanism -- a
non-additive change here currently requires manual coordination).

## Secret rotation

**Action**: `NOVA_API_KEYS` is read once per process into `ProductionConfig` (cached; see
`reset_production_config_cache()` for the test-only cache-clear hook -- a running production
process does not currently watch the environment for changes). Rotating an API key today means:
add the new key to `NOVA_API_KEYS` alongside the old one, redeploy (restarting the process picks up
both), confirm the new key works, then remove the old key and redeploy again. There is no live
key-revocation endpoint -- revoking a compromised key requires a redeploy. This is a real gap for a
high-urgency compromise scenario; see Remaining blockers.
