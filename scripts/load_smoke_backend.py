"""Concurrent load smoke test for the backend-integrated /v1/nova/* API (spec: error rate / P95
latency / memory growth / state isolation under concurrent load).

Same shape as scripts/load_smoke.py (the standalone production/ package's equivalent) -- in-process
over FastAPI's TestClient, not a real HTTP server + socket client, so it stays dependency-free and
runnable in CI without binding a port while still exercising the real request path (auth ->
validation -> NovaService -> repository -> response).
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import statistics
import sys
import threading
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def run(num_cases: int, concurrency: int) -> dict:
    os.environ.setdefault("SYNEX_AUDIT_PATH", "/tmp/nova_load_smoke_audit.sqlite3")
    os.environ.setdefault("SYNEX_IDEMPOTENCY_PATH", "/tmp/nova_load_smoke_idem.sqlite3")

    from fastapi.testclient import TestClient

    from app.main import app

    latencies_ms: list = []
    errors: list = []
    lock = threading.Lock()

    with TestClient(app) as client:
        def one_case(i: int) -> None:
            marker = f"load-{uuid.uuid4().hex[:12]}-{i}"
            start = time.perf_counter()
            try:
                r = client.post("/v1/nova/cases", json={"patient_id": "SYN-001", "chief_complaint": marker})
                if r.status_code != 201:
                    raise RuntimeError(f"create_case status={r.status_code} body={r.text}")
                case_id = r.json()["case_id"]
                r = client.post(f"/v1/nova/cases/{case_id}/decide")
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
        "num_cases": num_cases, "concurrency": concurrency, "succeeded": len(latencies_ms),
        "failed": len(errors), "error_rate": round(len(errors) / num_cases, 4) if num_cases else None,
        "wall_seconds": round(wall_seconds, 3),
        "throughput_cases_per_sec": round(num_cases / wall_seconds, 2) if wall_seconds > 0 else None,
        "latency_ms": {"mean": round(statistics.mean(latencies_ms), 2) if latencies_ms else None,
                        "p50": round(pct(50), 2), "p95": round(pct(95), 2), "p99": round(pct(99), 2)},
        "memory_rss_kb": {"before": mem_before_kb, "after": mem_after_kb, "growth": mem_after_kb - mem_before_kb},
        "errors_sample": errors[:5],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=150)
    parser.add_argument("--concurrency", type=int, default=15)
    parser.add_argument("--max-error-rate", type=float, default=0.0)
    parser.add_argument("--max-p95-ms", type=float, default=3000.0)
    args = parser.parse_args()

    result = run(args.cases, args.concurrency)
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
