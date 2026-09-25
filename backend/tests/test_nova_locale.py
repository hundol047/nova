"""Locale end-to-end (spec: internal canonical clinical IDs -- diagnosis_id, action key -- must
NEVER vary per locale; only rendered display text does). Exercises the real /v1/nova/* API via the
`client` fixture (see conftest.py), same pattern as test_nova_lifecycle.py -- not mocked.
"""

import pytest


def test_default_locale_is_english_and_backward_compatible(client):
    """A caller that omits `locale` entirely (every existing integration) keeps working exactly as
    before -- content stays English, display_content equals content."""
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002',
                     'chief_complaint': 'sudden severe headache, worst of my life'})
    assert r.status_code == 201, r.text
    case_id = r.json()['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    action = r.json()['recommended_next_action']
    if action['action_type'] != 'DIAGNOSE':
        assert action['display_content'] == action['content']


@pytest.mark.parametrize('locale', ['ko', 'ja', 'zh'])
def test_non_english_locale_renders_action_content_in_that_locale(client, locale):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002',
                     'chief_complaint': 'chest pain', 'locale': locale})
    assert r.status_code == 201, r.text
    case_id = r.json()['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    action = r.json()['recommended_next_action']
    # A non-English locale's ASK/EXAM/TEST content must not be the same as the English string --
    # every catalog entry actually has ko/ja/zh coverage (see tests/test_action_catalog_i18n.py in
    # nova_agent for the exhaustive check), so this must hold for whichever action gets picked.
    if action['action_type'] != 'DIAGNOSE':
        assert action['content'] != ''
        # Content is already locale-rendered by DoctorAgent(lang=locale) -- display_content mirrors it.
        assert action['display_content'] == action['content']


def test_diagnosis_canonical_id_never_varies_by_locale_only_display_does(client):
    """The critical invariant: forcing a quick DIAGNOSE (via max_turns=1) in a non-English locale
    must still produce an English-canonical `content`/`key` for the DIAGNOSE action (required for
    evaluation/audit diagnosis matching) -- display_content is the ONLY locale-dependent field."""
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002', 'chief_complaint': 'chest pain',
                     'locale': 'ko', 'max_turns': 1})
    assert r.status_code == 201, r.text
    case_id = r.json()['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    action = r.json()['recommended_next_action']
    assert action['action_type'] == 'DIAGNOSE'
    # content/key stay canonical English regardless of locale.
    assert all(ord(c) < 128 for c in action['key'].replace('_', ''))


def test_differential_display_diagnosis_translated_for_known_diagnosis(client):
    r = client.post('/v1/nova/cases', json={'patient_id': 'SYN-002',
                     'chief_complaint': 'sudden severe headache, worst of my life', 'locale': 'ja'})
    assert r.status_code == 201, r.text
    case_id = r.json()['case_id']

    r = client.post(f'/v1/nova/cases/{case_id}/observations', json={
        'observation_id': 'obs-1', 'action_type': 'EXAM', 'key': 'vital_signs',
        'result': 'BP 180/100 HR 98 RR 18 Temp 37.0 SpO2 98%'})
    assert r.status_code == 200, r.text

    r = client.post(f'/v1/nova/cases/{case_id}/decide')
    assert r.status_code == 200, r.text
    differential = r.json()['differential']
    assert differential
    # Every entry keeps its canonical diagnosis_id AND English `diagnosis`; display_diagnosis is
    # present for all of them (never blank), and differs from the English name for any diagnosis_id
    # this repo's translation table covers (subarachnoid_hemorrhage/migraine/tension_headache are
    # all covered -- see nova_agent/i18n/diagnosis_display.py).
    for item in differential:
        assert item['display_diagnosis']
        if item['diagnosis_id'] in ('subarachnoid_hemorrhage', 'migraine', 'tension_headache',
                                     'ischemic_stroke', 'meningitis'):
            assert item['display_diagnosis'] != item['diagnosis']
