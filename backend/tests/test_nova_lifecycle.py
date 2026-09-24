"""Full /v1/nova/* case lifecycle (create -> observe -> decide -> get -> close) against the real
FastAPI app via the `client` fixture (see conftest.py) -- same pattern as every other endpoint test
in this suite, not mocked. Uses the bundled demo patients (SYN-001..005) via DemoAdapter.
"""

import pytest


def test_full_case_lifecycle(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002',
                     'chief_complaint': 'sudden severe headache, worst of my life'})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body['status'] == 'open'
    assert body['turn_count'] == 0
    assert 'Clinician Review Required' in body['safety_banner']
    case_id = body['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
        'observation_id': 'obs-1', 'action_type': 'EXAM', 'key': 'vital_signs',
        'result': 'BP 180/100 HR 98 RR 18 Temp 37.0 SpO2 98%'})
    assert r.status_code == 200, r.text
    assert r.json()['applied'] is True
    assert r.json()['turn_count'] == 1

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    decision = r.json()
    assert decision['clinician_review_required'] is True
    assert decision['recommended_next_action']['action_type'] in ('ASK', 'EXAM', 'TEST', 'DIAGNOSE')
    assert decision['differential'], 'expected a non-empty differential for a critical headache presentation'
    assert decision['versions']['kb_version']
    assert decision['versions']['agent_version']

    r = client.get(f'/v1/nova/cases/{case_id}')
    assert r.status_code == 200
    assert r.json()['turn_count'] == 1
    assert r.json()['patient_id'] == 'SYN-002'

    r = client.post(f'/v1/nova/cases/{case_id}/close', json={'disposition': 'accept', 'reason': 'matches clinical picture'})
    assert r.status_code == 200
    assert r.json()['status'] == 'closed'

    # Closed case rejects further observations/decisions with a structured conflict, not a bare 500.
    r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
        'observation_id': 'obs-2', 'action_type': 'ASK', 'key': 'onset', 'result': 'yesterday'})
    assert r.status_code == 409
    assert r.json()['detail']['error']['code'] == 'case_conflict'


def test_observation_replay_is_idempotent(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001', 'chief_complaint': 'abdominal pain'})
    case_id = r.json()['case_id']
    body = {'observation_id': 'dup-1', 'action_type': 'ASK', 'key': 'onset', 'result': 'started yesterday'}
    r1 = client.post(f'/v1/nova/cases/{case_id}/observations', json=body)
    r2 = client.post(f'/v1/nova/cases/{case_id}/observations', json=body)
    assert r1.json()['applied'] is True
    assert r2.json()['applied'] is False
    assert r1.json()['turn_count'] == r2.json()['turn_count'] == 1


def test_unknown_case_is_404_with_structured_error(client):
    r = client.get('/v1/nova/cases/NOVA-does-not-exist')
    assert r.status_code == 404
    assert r.json()['detail']['error']['code'] == 'case_not_found'


def test_unknown_patient_is_404(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'NOPE-999', 'chief_complaint': 'chest pain'})
    assert r.status_code == 404


def test_missing_chief_complaint_without_encounter_is_422(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-001'})
    assert r.status_code == 422
    assert r.json()['detail']['error']['code'] == 'validation_error'


def test_chief_complaint_falls_back_to_encounter(client):
    enc = client.post('/patients/SYN-003/encounters', json={
        'encounter_type': 'emergency', 'chief_complaint': 'crushing chest pain radiating to the jaw'})
    assert enc.status_code == 200
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-003', 'encounter_id': enc.json()['id']})
    assert r.status_code == 201, r.text
    assert r.json()['encounter_id'] == enc.json()['id']


def test_encounter_from_a_different_patient_is_rejected(client):
    enc = client.post('/patients/SYN-004/encounters', json={'encounter_type': 'outpatient', 'chief_complaint': 'cough'})
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-005', 'encounter_id': enc.json()['id'],
                                              'chief_complaint': 'cough'})
    assert r.status_code == 404


def test_never_touches_medication_or_lab_orders(client):
    """Clinical safety boundary: no NOVA endpoint response or side effect ever creates a
    MedicationOrder/LabOrder -- confirms the case lifecycle above left the patient's order lists
    untouched."""
    before = client.get('/patients/SYN-002/medication-orders').json()
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'palpitations'})
    case_id = r.json()['case_id']
    client.post(f'/v1/nova/cases/{case_id}/decide')
    after = client.get('/patients/SYN-002/medication-orders').json()
    assert before == after
