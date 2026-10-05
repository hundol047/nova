# Submission and state boundaries (2026-10-05)

The official `submission/run.py` imports the provider lock and configuration only and exits
before reading patient input or constructing any model client. All providers, including mock,
fail closed. No environment switch, arbitrary base URL, proxy or CLI flag enables execution.
This establishes **APPLICATION_LEVEL_NETWORK_POLICY_VERIFIED** for this blocked path.
OS-level network isolation was not tested and is not claimed.

`python -m competition.local_runner` is an explicit offline mock harness with PLACEHOLDER
JSON-lines I/O. It is separately named and never invoked by official run.py. Existing network
clients in `nova_agent/llm_client.py` are development integrations, not organizer transports.
Their guessed compatibility fields/routes have not been adopted as an official contract.
The candidate ZIP retains these files for local engineering review; it is not officially cleared.

Development reachability: adapter -> DoctorAgent -> deterministic differential, safety,
action selection, static catalog/index and MockLLMClient. `fit`, `partial_fit`, optimizer,
backward, training checkpoints and hospital learning modules are not in this path. Calls
named `generate_candidates` or ordinary state updates are not training. `logging_store.py`
and `_synex.py` are bundled support files but not imported by DoctorAgent or official run.py;
the optional SQLite logger is not created here. No runtime downloads or remote data sources
are used by the local static catalog. Snapshot providers read local files only; none bundled.

Mutable state: adapter `_states`, `_pending_actions`, `_emitted_actions` are keyed per active
case, cleared on DIAGNOSE, explicit close, exception and a fresh initial observation with reused
ID. Continuation without active state is rejected. No patient tombstone/statistic is retained.
Per-case LLM counters live in PatientState. Client last-call flags are reset before each call;
they are development structured-output telemetry, not model-identity attestations. Catalog,
normalizer alias and knowledge caches cache static source data, not patient predictions.
No threaded/concurrent-call guarantee is claimed; interleaved sequential cases are tested.

`real_llm_verified` remains a legacy development metadata field. New `call_accounting`
explicitly separates `INTERNAL_STRUCTURED_OUTPUT_VALID` from
`OFFICIAL_CALL_RESPONSE_RECEIVED=NOT_VERIFIED`. The official per-case success count is unknown,
not a copied internal-JSON counter. Empty/malformed/preflight-only/other-case/fallback results
cannot unlock official run.py. Exact organizer receipt semantics, authorized retries and failure
framing remain blocked pending the guide; no unofficial wire failure action was introduced.

Local interaction count tracks emitted actions separately from internal model retries.
Over-budget emission raises; malformed local input terminates instead of inventing another ASK.
No scoring weights, medical features, stop thresholds or safety policies were changed.
