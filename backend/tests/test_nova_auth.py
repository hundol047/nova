"""RBAC matrix for /v1/nova/* (spec: nova:read/nova:invoke/nova:review, least privilege). Uses
AUTH_MODE=demo's SYNEX_DEMO_ROLE override (same mechanism backend/tests/test_auth.py already
exercises for the rest of the app) to drive each role through these endpoints -- no new auth
scaffolding needed, reusing services/auth.py exactly as-is.

Deliberately a SINGLE `client` fixture instance per test, with SYNEX_DEMO_ROLE flipped mid-session
via monkeypatch (get_current_user() reads it fresh on every request, never cached) -- entering a
SECOND `with TestClient(app) as c:` block re-runs the app's lifespan and resets NovaService's
in-memory case store, which would make a case created under one role invisible to a second
TestClient instance for a reason that has nothing to do with RBAC.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_clinician_can_drive_the_full_lifecycle(client, monkeypatch):
    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'clinician')
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'fever and cough'})
    assert r.status_code == 201
    case_id = r.json()['case_id']
    assert client.post(f'/v1/nova/cases/{case_id}/decide').status_code == 200
    assert client.get(f'/v1/nova/cases/{case_id}').status_code == 200
    assert client.post(f'/v1/nova/cases/{case_id}/close', json={'disposition': 'accept'}).status_code == 200


def test_clinician_readonly_can_read_but_not_invoke_or_review(client, monkeypatch):
    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'clinician')
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'fever'})
    case_id = r.json()['case_id']

    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'clinician_readonly')
    assert client.get(f'/v1/nova/cases/{case_id}').status_code == 200
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'cough'})
    assert r.status_code == 403
    r = client.post(f'/v1/nova/cases/{case_id}/close', json={'disposition': 'accept'})
    assert r.status_code == 403


def test_pharmacist_can_read_but_not_invoke(client, monkeypatch):
    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'clinician')
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'fever'})
    case_id = r.json()['case_id']

    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'pharmacist')
    assert client.get(f'/v1/nova/cases/{case_id}').status_code == 200
    assert client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'cough'}).status_code == 403


def test_admin_has_full_access_including_metrics(client, monkeypatch):
    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'admin')
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'fever'})
    assert r.status_code == 201
    assert client.get('/v1/nova/metrics').status_code == 200


def test_clinician_cannot_read_metrics(client, monkeypatch):
    monkeypatch.setenv('SYNEX_DEMO_ROLE', 'clinician')
    assert client.get('/v1/nova/metrics').status_code == 403


def test_unauthenticated_oidc_mode_is_401(tmp_path, monkeypatch):
    monkeypatch.setenv('AUTH_MODE', 'oidc')
    monkeypatch.setenv('OIDC_ISSUER', 'https://issuer.example')
    monkeypatch.setenv('OIDC_AUDIENCE', 'nova-backend')
    monkeypatch.setenv('SYNEX_AUDIT_PATH', str(tmp_path / 'audit.sqlite3'))
    monkeypatch.setenv('SYNEX_IDEMPOTENCY_PATH', str(tmp_path / 'idempotency.sqlite3'))
    with TestClient(app) as c:
        r = c.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'fever'})
        assert r.status_code == 401
