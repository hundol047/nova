# Operations

## Observability

### Structured logs

Every production log line goes through `production/logging_config.py`'s single call site,
`log_event(component, event, *, request_id, case_id, severity, latency_ms, error_type, **extra)`,
and is emitted as one JSON object per line (`JSONFormatter`) with a real ISO-8601 UTC timestamp
(microsecond precision via `datetime`, not `time.strftime`, which silently renders `%f` as the
literal two characters `%f` rather than microseconds -- a real bug caught and fixed during this
work). Any free-text field under `chief_complaint`/`content`/`message`/`text` is passed through
`production.redaction.redact_dict()` before being serialized, as a defense-in-depth layer on top of
the primary PHI control (`NOVA_LOG_RAW_TEXT=false` by default -- structured fields are logged, raw
patient free text is not).

### Metrics (`GET /metrics`, admin/service role)

`production/metrics.py`'s `MetricsRegistry` tracks, in-process:
- Counters: `requests_total`, `errors_total`, `observations_total`, `decide_calls_total`,
  `llm_calls_total`, `llm_success_total`, `llm_fallback_total`.
- Latency percentiles (p50/p95/p99 over a bounded 2000-sample rolling window per series):
  `decide_latency_ms`.
- Derived rates: `error_rate`, `llm_success_rate`, `llm_fallback_rate`, `llm_parse_failure_rate`
  (each `None`, not `0`, until its denominator has at least one sample -- never silently reported
  as a real zero when no calls have actually happened yet).

This is in-process only, by design (see `production/metrics.py`'s own docstring): a multi-replica
deployment aggregates at the infrastructure layer (a real Prometheus scrape per pod), not here.

### Health vs. readiness

- `GET /health` -- process liveness only (no dependency checks). Always `{"status": "ok"}` if the
  process is up.
- `GET /ready` -- dependency readiness: knowledge-base loadable (`kb_fingerprint()` succeeds), case
  repository reachable, and `ProductionConfig.validate()` passes. Returns `ready: false` with a
  per-check `ReadinessCheck` (name/ok/detail) for whichever check failed, so an operator or
  orchestrator can see exactly which dependency is the problem.

## Alertable conditions

Nothing here is wired to a real alerting backend (out of scope without one to integrate with), but
these are the signals an operator should alert on once `/metrics` is scraped by a real monitoring
stack:
- `error_rate` above a threshold (sustained, not a single blip).
- `llm_fallback_rate` rising -- the real LLM provider is degrading even though the deterministic
  fallback is keeping cases moving (see `docs/nova/runbook.md`'s "high fallback rate" entry).
- `decide_latency_ms.p95` rising -- see `docs/nova/runbook.md`'s "latency spike" entry.
- `GET /ready` returning `ready: false` for any check.
- A circuit breaker (`production/circuit_breaker.py`) staying open for longer than one cooldown
  cycle -- indicates the underlying provider is not recovering, not just a transient blip.

## Retention

`production/config.py` exposes `audit_retention_days` (default ~7 years, `2555`),
`clinical_event_retention_days` (same default), and `debug_log_retention_days` (default 30) as
configuration, not hardcoded constants -- deliberately, since the correct retention window is an
institutional/regulatory decision, not one this codebase should make unilaterally. **No automated
purge job reads these settings yet** -- they are the configured target, not yet an enforced
behavior. See Remaining blockers.
