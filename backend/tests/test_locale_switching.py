"""Mid-case language switching (spec: "한국어 -> English" must preserve the existing case's
reasoning state -- never start a new case, only change the UI/explanation language).
"""


def test_switching_locale_mid_case_preserves_state_and_changes_next_action_language(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'chest pain',
                     'locale': 'ko'})
    assert r.status_code == 201, r.text
    case_id = r.json()['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    ko_action = r.json()['recommended_next_action']

    r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
        'observation_id': 'obs-1', 'action_type': ko_action['action_type'], 'key': ko_action['key'],
        'result': 'negative' if ko_action['action_type'] != 'ASK' else '아니요'})
    assert r.status_code == 200, r.text
    turn_count_before = r.json()['turn_count']

    r = client.patch(f'/v1/nova/cases/{case_id}/locale', json={'locale': 'en'})
    assert r.status_code == 200, r.text
    assert r.json()['locale'] == 'en'

    # Same case, same accumulated evidence -- next decide() renders in English now, not Korean.
    r = client.get(f'/v1/nova/cases/{case_id}')
    assert r.status_code == 200
    assert r.json()['turn_count'] == turn_count_before

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    en_action = r.json()['recommended_next_action']
    if en_action['action_type'] != 'DIAGNOSE':
        assert all(ord(c) < 128 for c in en_action['content'])


def test_locale_update_rejects_unsupported_locale(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'chest pain'})
    case_id = r.json()['case_id']
    r = client.patch(f'/v1/nova/cases/{case_id}/locale', json={'locale': 'fr'})
    assert r.status_code == 422


def test_locale_update_on_unknown_case_is_404(client):
    r = client.patch('/v1/nova/cases/does-not-exist/locale', json={'locale': 'ko'})
    assert r.status_code == 404
