# N.O.V.A. Operations (Backend-Integrated)

## Structured logs

`backend/app/services/nova_observability.py`'s `log_event()` is the single call site every
`/v1/nova/*` code path uses (via `main.py`'s `nova_call()` choke point). One JSON object per line
on the `synexagent.nova` logger (a child of this app's existing `synexagent` logger -- no separate
logging configuration to wire up). Fields: `timestamp`, `level`, `request_id`, `case_id`,
`component`, `event`, `latency_ms`, `error_code`. PHI-minimized by construction -- there is no
`chief_complaint`/`result` parameter on `log_event()` at all, so a caller cannot accidentally log
raw patient free text through this path.

## Metrics (`GET /v1/nova/metrics`, admin-only)

`NovaMetricsRegistry` tracks, in-process:
- Counters: `nova_requests_total`, `nova_errors_total`, `nova_llm_calls_total`,
  `nova_llm_success_total`, `nova_llm_fallback_total`, `nova_safety_blocks`.
- Latency percentiles (p50/p95/p99, bounded 2000-sample rolling window): `nova_latency_ms`,
  `nova_llm_latency_ms`, `nova_turn_count`.
- Derived rates: `nova_error_rate`, `nova_llm_success_rate`, `nova_llm_fallback_rate` (each `None`,
  not `0`, until its denominator has at least one sample).

In-process only, same as this project's other metrics registry (`production/metrics.py`) -- a
multi-replica deployment aggregates at the infrastructure layer (a real Prometheus scrape per pod),
not here. **Known gap**: `nova_parse_failure` (from the spec's requested metric list) is not
currently tracked -- `nova_agent.state.PatientState` does not expose a distinct
LLM-output-parse-failure counter separate from its general `llm_failure_count`, so this metric was
not fabricated from a signal that doesn't actually exist. See Remaining blockers.

## Health vs. readiness

- `GET /health` -- process liveness only (pre-existing, unchanged).
- `GET /health/subsystems` -- per-subsystem detail (pre-existing, unchanged).
- `GET /ready` (new) -- checks: auth actually configured for this `NOVA_ENV` (in production, must
  be `oidc`, not `demo`), the N.O.V.A. case repository/service initialized, the N.O.V.A. knowledge
  base loads (`kb_fingerprint()` succeeds), the EMR adapter responds, and -- **in
  `NOVA_ENV=production` only** -- the real LLM provider is configured (`NOVA_LLM_PROVIDER != mock`
  fails readiness in production; a mock provider is "ready" in dev/test). Returns HTTP 503 (not
  200) when any check fails, matching standard Kubernetes readiness-probe semantics.

## Alertable conditions

Nothing here is wired to a real alerting backend. Once `/v1/nova/metrics` is scraped by a real
monitoring stack, alert on:
- `nova_error_rate` sustained above a threshold.
- `nova_llm_fallback_rate` rising -- the real LLM provider is degrading even though the
  deterministic fallback keeps cases moving.
- `nova_latency_ms.p95` / `nova_llm_latency_ms.p95` rising.
- `GET /ready` returning `ready: false` for any check.
- A `decide()` response with `llm_degraded: true` appearing repeatedly -- the circuit breaker has
  opened (see `docs/NOVA_RUNBOOK.md`).

## Load testing

Concurrency safety (20 simultaneous cases, 15 simultaneous observations on one case, 10 racing
identical-`observation_id` requests) is covered by `backend/tests/test_nova_concurrency.py` and
passes cleanly.

`scripts/load_smoke_backend.py` (same shape as the standalone `production/` package's
`scripts/load_smoke.py`) drives concurrent case-create + decide cycles through the real FastAPI app
and reports throughput/latency percentiles/memory growth. Measured locally at 100 cases /
concurrency 10: 0% error rate, p50 469ms / p95 577ms / p99 654ms, ~18 cases/sec, ~6MB bounded
memory growth. This is a local, single-process, mock-provider measurement -- not a substitute for a
real load test against a deployed multi-replica instance with a real LLM provider and a real
database-backed repository, which has not been performed.
