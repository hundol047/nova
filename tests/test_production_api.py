"""Integration tests for production/api.py: the full case lifecycle through FastAPI's TestClient,
auth/RBAC enforcement, idempotent observation replay, input validation, and the mandated safety
banner / clinician_review_required contract on every clinically-facing response.
"""

from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from production.config import reset_production_config_cache
from production.repository import reset_repositories


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("NOVA_REQUIRE_AUTH", "true")
    monkeypatch.setenv("NOVA_API_KEYS", "clinkey:clinician,revkey:reviewer,svckey:service,adminkey:admin")
    reset_production_config_cache()
    reset_repositories()
    from production.api import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c
    reset_production_config_cache()
    reset_repositories()


CLIN = {"X-API-Key": "clinkey"}
REV = {"X-API-Key": "revkey"}
SVC = {"X-API-Key": "svckey"}
ADMIN = {"X-API-Key": "adminkey"}


def test_health_and_ready_need_no_auth(client):
    assert client.get("/health").status_code == 200
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json()["ready"] is True


def test_create_case_requires_auth(client):
    r = client.post("/v1/cases", json={"case_id": "c1", "chief_complaint": "chest pain"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "authentication_error"


def test_create_case_rejects_invalid_key(client):
    r = client.post("/v1/cases", json={"case_id": "c1", "chief_complaint": "chest pain"},
                     headers={"X-API-Key": "not-a-real-key"})
    assert r.status_code == 401


def test_reviewer_cannot_create_case(client):
    r = client.post("/v1/cases", json={"case_id": "c1", "chief_complaint": "chest pain"}, headers=REV)
    assert r.status_code == 403
    assert r.json()["error_code"] == "authorization_error"


def test_reviewer_can_read_case(client):
    client.post("/v1/cases", json={"case_id": "c1", "chief_complaint": "chest pain"}, headers=CLIN)
    r = client.get("/v1/cases/c1", headers=REV)
    assert r.status_code == 200
    assert r.json()["clinician_review_required"] is True


def test_service_cannot_decide(client):
    client.post("/v1/cases", json={"case_id": "c1", "chief_complaint": "chest pain"}, headers=SVC)
    r = client.post("/v1/cases/c1/decide", json={}, headers=SVC)
    assert r.status_code == 403


def test_full_case_lifecycle(client):
    r = client.post("/v1/cases", json={
        "case_id": "case-lifecycle", "chief_complaint": "sudden severe headache, worst of my life",
        "demographics": {"age": 45, "sex": "female"},
    }, headers=CLIN)
    assert r.status_code == 201
    body = r.json()
    assert body["turn_count"] == 0
    assert "Clinician Review Required" in body["safety_banner"]

    r = client.post("/v1/cases/case-lifecycle/observations", json={
        "observation_id": "obs-1", "action_type": "EXAM", "key": "vital_signs",
        "result": "BP 180/100 HR 98 RR 18 Temp 37.0 SpO2 98%",
    }, headers=CLIN)
    assert r.status_code == 200
    assert r.json()["applied"] is True

    r = client.post("/v1/cases/case-lifecycle/decide", json={}, headers=CLIN)
    assert r.status_code == 200
    decision = r.json()
    assert decision["clinician_review_required"] is True
    assert decision["next_action"]["action_type"] in ("ASK", "EXAM", "TEST", "DIAGNOSE")
    assert decision["differential"], "expected a non-empty differential for a critical headache presentation"
    assert decision["versions"]["kb_version"]

    r = client.get("/v1/cases/case-lifecycle", headers=CLIN)
    assert r.status_code == 200
    assert r.json()["turn_count"] == 1


def test_observation_replay_is_idempotent(client):
    client.post("/v1/cases", json={"case_id": "idem-1", "chief_complaint": "abdominal pain"}, headers=CLIN)
    body = {"observation_id": "dup-1", "action_type": "ASK", "key": "onset", "result": "started yesterday"}
    r1 = client.post("/v1/cases/idem-1/observations", json=body, headers=CLIN)
    r2 = client.post("/v1/cases/idem-1/observations", json=body, headers=CLIN)
    assert r1.json()["applied"] is True
    assert r2.json()["applied"] is False
    assert r1.json()["turn_count"] == r2.json()["turn_count"] == 1  # never double-recorded


def test_oversized_chief_complaint_rejected(client):
    r = client.post("/v1/cases", json={"case_id": "big1", "chief_complaint": "x" * 5000}, headers=CLIN)
    assert r.status_code == 422


def test_control_characters_rejected(client):
    r = client.post("/v1/cases", json={"case_id": "ctl1", "chief_complaint": "chest pain\x00\x07"}, headers=CLIN)
    assert r.status_code == 422


def test_malformed_case_id_rejected(client):
    r = client.post("/v1/cases", json={"case_id": "not a valid id!", "chief_complaint": "chest pain"}, headers=CLIN)
    assert r.status_code == 422


def test_unexpected_field_rejected(client):
    r = client.post("/v1/cases", json={"case_id": "extra1", "chief_complaint": "chest pain", "surprise": 1}, headers=CLIN)
    assert r.status_code == 422


def test_unknown_case_is_404(client):
    r = client.get("/v1/cases/does-not-exist", headers=CLIN)
    assert r.status_code == 404


def test_duplicate_case_id_is_conflict(client):
    client.post("/v1/cases", json={"case_id": "dupe", "chief_complaint": "chest pain"}, headers=CLIN)
    r = client.post("/v1/cases", json={"case_id": "dupe", "chief_complaint": "chest pain"}, headers=CLIN)
    assert r.status_code == 409


def test_metrics_requires_auth_and_permission(client):
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers=REV).status_code == 403
    r = client.get("/metrics", headers=ADMIN)
    assert r.status_code == 200
    assert "counters" in r.json()


def test_metrics_reflect_request_activity(client):
    client.post("/v1/cases", json={"case_id": "metrics-case", "chief_complaint": "chest pain"}, headers=CLIN)
    r = client.get("/metrics", headers=ADMIN)
    assert r.json()["counters"]["requests_total"] >= 1


def test_concurrent_requests_across_many_cases_never_cross_contaminate(client):
    """spec: no cross-case state leakage / race condition under concurrency. 25 threads each drive
    a distinct case (create -> decide -> read) simultaneously through the real FastAPI app; every
    case's own chief_complaint must come back unmodified and every call must succeed."""
    n = 25
    errors: list = []

    def worker(i: int) -> None:
        cid = f"concurrent-case-{i}"
        complaint = f"distinct complaint marker {i}"
        try:
            r = client.post("/v1/cases", json={"case_id": cid, "chief_complaint": complaint}, headers=CLIN)
            assert r.status_code == 201, r.text
            r = client.post(f"/v1/cases/{cid}/decide", json={}, headers=CLIN)
            assert r.status_code == 200, r.text
            r = client.get(f"/v1/cases/{cid}", headers=CLIN)
            assert r.status_code == 200
            assert r.json()["chief_complaint"] == complaint
        except Exception as exc:  # noqa: BLE001 - collected below, not raised inside a thread
            errors.append((i, repr(exc)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
