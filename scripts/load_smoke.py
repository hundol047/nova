"""Basic concurrent load smoke test for the production API (spec: throughput / P95 / error rate /
memory growth under concurrent load).

Deliberately in-process (FastAPI's TestClient over the ASGI app, not a real HTTP server + socket
client) -- this keeps the smoke test dependency-free and runnable in CI without binding a port,
while still exercising the exact same request path (auth -> validation -> orchestrator.decide() ->
repository -> response) a real deployment would. Not a substitute for a real external load test
against a deployed instance; it is a cheap regression guard against an obvious throughput or
memory-leak regression in this codebase.
"""

from __future__ import annotations

import argparse
import os
import resource
import statistics
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run(num_cases: int, concurrency: int) -> dict:
    os.environ.setdefault("NOVA_REQUIRE_AUTH", "false")
    os.environ.setdefault("NOVA_LLM_PROVIDER", "mock")

    from production.config import reset_production_config_cache
    from production.repository import reset_repositories

    reset_production_config_cache()
    reset_repositories()

    from fastapi.testclient import TestClient

    from production.api import create_app

    client = TestClient(create_app())

    latencies_ms: list = []
    errors: list = []
    lock = threading.Lock()

    def one_case(i: int) -> None:
        cid = f"load-{uuid.uuid4().hex[:12]}-{i}"
        start = time.perf_counter()
        try:
            r = client.post("/v1/cases", json={"case_id": cid, "chief_complaint": "sudden chest pain and sweating"})
            if r.status_code != 201:
                raise RuntimeError(f"create_case status={r.status_code} body={r.text}")
            r = client.post(f"/v1/cases/{cid}/decide", json={})
            if r.status_code != 200:
                raise RuntimeError(f"decide status={r.status_code} body={r.text}")
        except Exception as exc:  # noqa: BLE001 - collected, not raised inside a worker thread
            with lock:
                errors.append(repr(exc))
        else:
            with lock:
                latencies_ms.append((time.perf_counter() - start) * 1000)

    mem_before_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    wall_start = time.perf_counter()

    remaining = list(range(num_cases))
    while remaining:
        batch, remaining = remaining[:concurrency], remaining[concurrency:]
        threads = [threading.Thread(target=one_case, args=(i,)) for i in batch]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    wall_seconds = time.perf_counter() - wall_start
    mem_after_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    ordered = sorted(latencies_ms)

    def pct(p: float) -> float:
        if not ordered:
            return 0.0
        idx = min(len(ordered) - 1, int(round(p / 100.0 * (len(ordered) - 1))))
        return ordered[idx]

    return {
        "num_cases": num_cases,
        "concurrency": concurrency,
        "succeeded": len(latencies_ms),
        "failed": len(errors),
        "error_rate": round(len(errors) / num_cases, 4) if num_cases else None,
        "wall_seconds": round(wall_seconds, 3),
        "throughput_cases_per_sec": round(num_cases / wall_seconds, 2) if wall_seconds > 0 else None,
        "latency_ms": {
            "mean": round(statistics.mean(latencies_ms), 2) if latencies_ms else None,
            "p50": round(pct(50), 2), "p95": round(pct(95), 2), "p99": round(pct(99), 2),
        },
        # ru_maxrss is a high-water mark, not a live sample, so this can only ever show growth,
        # never shrinkage -- still a useful coarse regression guard for an obvious leak.
        "memory_rss_kb": {"before": mem_before_kb, "after": mem_after_kb, "growth": mem_after_kb - mem_before_kb},
        "errors_sample": errors[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--max-p95-ms", type=float, default=2000.0)
    args = parser.parse_args()

    result = run(args.cases, args.concurrency)
    import json
    print(json.dumps(result, indent=2))

    if result["error_rate"] is not None and result["error_rate"] > args.max_error_rate:
        print(f"FAIL: error_rate {result['error_rate']} exceeds max {args.max_error_rate}")
        return 1
    if result["latency_ms"]["p95"] and result["latency_ms"]["p95"] > args.max_p95_ms:
        print(f"FAIL: p95 latency {result['latency_ms']['p95']}ms exceeds max {args.max_p95_ms}ms")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
