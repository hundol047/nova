"""Exercise stale evidence, scope gaps, forged approvals and new-file clearance inheritance."""
import copy
import json
from pathlib import Path

import pytest

from scripts import prepare_rights_and_review as review
from scripts import refresh_runtime_inventory as refresh
from scripts.validate_runtime_provenance import validate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def owner_fixture(tmp_path):
    path = 'nova_agent/example.py'
    (tmp_path / 'nova_agent').mkdir()
    (tmp_path / path).write_text('# team fixture\n')
    (tmp_path / 'grant.md').write_text('Fixture permission for competition and research only.\n')
    declaration = {'actor_type': 'HUMAN_REPOSITORY_OWNER', 'ownership_statement': 'Fixture owner declaration',
                   'permission_statement': 'Fixture scoped grant', 'grant_scope': 'COMPETITION_AND_RELATED_RESEARCH',
                   'license_file': 'grant.md', 'license_sha256': review.sha(tmp_path / 'grant.md'),
                   'assets': {path: review.sha(tmp_path / path)}}
    review.write(tmp_path, 'owner.json', declaration)
    inventory = review.read(ROOT, 'artifacts/compliance_hardening/clinical_asset_inventory.json')
    asset = copy.deepcopy(next(a for a in inventory['assets'] if a['path'] == 'nova_agent/state.py'))
    asset.update(path=path, asset_id=path, sha256=declaration['assets'][path], status='UNRESOLVED')
    asset.pop('owner_evidence', None)
    review.write(tmp_path, 'artifacts/compliance_hardening/clinical_asset_inventory.json', {'assets': [asset]})
    review.apply_owner(tmp_path, 'owner.json')
    return tmp_path, review.read(tmp_path, 'artifacts/compliance_hardening/clinical_asset_inventory.json')['assets'][0]


def test_scoped_owner_grant_does_not_manufacture_clinical_approval(owner_fixture):
    root, asset = owner_fixture
    assert not review.owner_errors(root, asset)
    result = validate(root)
    assert result['permission_status'] == 'DOCUMENTED_FOR_STATED_SCOPE'
    assert not result['official_submission_allowed']
    assert asset['clinician_review'] != 'APPROVED'


@pytest.mark.parametrize('changed', ['owner.json', 'grant.md', 'nova_agent/example.py'])
def test_owner_clearance_is_invalidated_by_changed_bytes(owner_fixture, changed):
    root, asset = owner_fixture
    with (root / changed).open('a') as stream:
        stream.write(' ')
    if changed.endswith('.py'):
        asset['sha256'] = review.sha(root / changed)
    assert review.owner_errors(root, asset)


def test_label_without_owner_evidence_cannot_clear(owner_fixture):
    root, asset = owner_fixture
    asset.pop('owner_evidence')
    review.write(root, 'artifacts/compliance_hardening/clinical_asset_inventory.json', {'assets': [asset]})
    assert validate(root)['permission_status'] == 'BLOCKED'


def test_owner_evidence_cannot_escape_workspace(owner_fixture):
    root, asset = owner_fixture
    asset['owner_evidence']['path'] = '../outside-owner.json'
    assert review.owner_errors(root, asset)


def test_refresh_does_not_inherit_team_grant_for_new_files(tmp_path, monkeypatch):
    assets = copy.deepcopy(review.read(ROOT, 'artifacts/compliance_hardening/clinical_asset_inventory.json')['assets'])
    assets = [a for a in assets if a['path'] in {'nova_agent/state.py', 'nova_agent/knowledge/tier2_enrichment.json'}]
    for asset in assets:
        file = tmp_path / asset['path']
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('changed fixture bytes')
    (tmp_path / 'nova_agent/new_code.py').write_text('# fixture')
    review.write(tmp_path, 'inventory.json', {'assets': assets})
    monkeypatch.setattr(refresh, 'ROOT', tmp_path)
    monkeypatch.setattr(refresh, 'INVENTORY', tmp_path / 'inventory.json')
    result = refresh.build(False)
    rows = {a['path']: a for a in result['inventory']['assets']}
    assert rows['nova_agent/state.py']['status'] == 'UNRESOLVED'
    assert rows['nova_agent/new_code.py']['status'] == 'UNRESOLVED'
    assert rows['nova_agent/new_code.py']['license'] == 'UNRESOLVED'
    assert 'owner_evidence' not in rows['nova_agent/new_code.py']


@pytest.fixture
def clinician_fixture(tmp_path):
    (tmp_path / 'rule.py').write_text('# clinical fixture')
    packet = {'runtime_sha256': {'rule.py': review.sha(tmp_path / 'rule.py')},
              'cards': [{'id': 'one'}, {'id': 'two'}], 'priority_review_questions': []}
    review.write(tmp_path, review.BASE / 'clinical_review_packet.json', packet)
    (tmp_path / 'credential.txt').write_text('Synthetic test credential evidence, not a real physician.')
    (tmp_path / 'signature.txt').write_text('Synthetic test signature evidence, not a real signature.')
    response = {'packet_sha256': review.sha(tmp_path / review.BASE / 'clinical_review_packet.json'),
                'reviewer': {'actor_type': 'HUMAN_CLINICIAN', 'name': 'SYNTHETIC TEST REVIEWER',
                             'qualification': 'TEST ONLY', 'credential_verification_reference': 'TEST ONLY',
                             'review_date': '2026-10-12', 'conflict_of_interest': 'TEST ONLY'},
                'attestation': 'SYNTHETIC TEST ATTESTATION',
                'credential_verification': {'path': 'credential.txt', 'sha256': review.sha(tmp_path / 'credential.txt')},
                'signature_evidence': {'path': 'signature.txt', 'sha256': review.sha(tmp_path / 'signature.txt')},
                'items': [{'id': 'one', 'decision': 'APPROVE', 'supporting_sources': ['TEST ONLY'], 'scope_and_exceptions': 'TEST ONLY'}]}
    return tmp_path, response


def test_partial_review_is_not_whole_system_approval(clinician_fixture):
    root, response = clinician_fixture
    result = review.validate_clinician_response(root, response)
    assert result['evidence_status'] == 'SUPPLIED_DOCUMENTS_HASH_VALID'
    assert result['scope'] == 'PARTIAL'
    assert not result['independent_identity_verification']
    assert not result['automatic_clinical_approval']


@pytest.mark.parametrize('mutation', ['AI', 'no_name', 'no_signature', 'stale_packet', 'duplicate', 'empty', 'changed_runtime', 'no_sources', 'future_date'])
def test_invalid_clinical_claims_are_rejected(clinician_fixture, mutation):
    root, response = clinician_fixture
    if mutation == 'AI': response['reviewer']['actor_type'] = 'AI_AGENT'
    if mutation == 'no_name': response['reviewer']['name'] = None
    if mutation == 'no_signature': response.pop('signature_evidence')
    if mutation == 'stale_packet': response['packet_sha256'] = '0' * 64
    if mutation == 'duplicate': response['items'] *= 2
    if mutation == 'empty': response['items'] = []
    if mutation == 'changed_runtime': (root / 'rule.py').write_text('# changed')
    if mutation == 'no_sources': response['items'][0]['supporting_sources'] = []
    if mutation == 'future_date': response['reviewer']['review_date'] = '2999-01-01'
    assert review.validate_clinician_response(root, response)['errors']


def test_current_review_packet_includes_all_34_plus_8_profiles():
    packet = review.read(ROOT, review.BASE / 'clinical_review_packet.json')
    expected = {r['id']: r for p in (ROOT / 'nova_agent/knowledge/diseases').glob('*.json')
                for r in json.loads(p.read_text())}
    expected.update({r['id']: r for r in review.read(ROOT, 'nova_agent/knowledge/clinical_profiles.json')['profiles']})
    assert len(packet['cards']) == len(expected) == 42
    for card in packet['cards']:
        assert card['current_profile'] == expected[card['id']]
        assert card['sha256'] == review.sha(ROOT / card['path'])
        assert card['review']['decision'] == 'PENDING'
    assert packet['reviewer'] is None
    assert len(packet['priority_review_questions']) == 6


def test_archive_gate_tracks_sdk_and_clinical_gap_separately():
    result = review.release_review_gate(ROOT)
    assert result['archive_rights_coverage'] == 'PASS'
    assert result['unverified_archive_members'] == ['nova_sdk.py']
    assert result['clinician_review'] == 'PENDING_EXTERNAL_CLINICIAN'
    assert not result['official_submission_allowed']
