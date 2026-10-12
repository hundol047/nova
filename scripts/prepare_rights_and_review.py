"""Prepare current, hash-bound owner and clinician evidence; never impersonate a reviewer.

No patient samples, credentials, organizer calls or clinical runtime edits.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('artifacts/rights_and_review')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(root, path):
    return json.loads((root / path).read_text(encoding='utf-8'))


def write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def safe_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or out-of-scope evidence: ' + name)
    return path


def owner_errors(root, asset):
    evidence = asset.get('owner_evidence', {})
    try:
        path = safe_file(root, evidence['path'])
        if sha(path) != evidence['sha256']:
            return ['owner declaration changed']
        declaration = json.loads(path.read_text(encoding='utf-8'))
        if declaration.get('actor_type') != 'HUMAN_REPOSITORY_OWNER':
            return ['owner declaration is not a human statement']
        if not declaration.get('ownership_statement') or not declaration.get('permission_statement'):
            return ['missing owner statement or grant']
        if declaration.get('grant_scope') not in {'COMPETITION_AND_RELATED_RESEARCH', 'MIT'}:
            return ['unsupported owner grant scope']
        if declaration.get('assets', {}).get(asset['path']) != asset['sha256']:
            return ['owner declaration does not cover current asset bytes']
        grant = safe_file(root, declaration['license_file'])
        if sha(grant) != declaration.get('license_sha256'):
            return ['license changed or not evidenced']
    except (KeyError, ValueError, OSError, TypeError, AttributeError):
        return ['missing or invalid owner evidence']
    return []


def apply_owner(root, declaration_path):
    """Record supplied human rights declaration, retaining unknown generation/medical fields."""
    declaration = read(root, declaration_path)
    inventory_path = 'artifacts/compliance_hardening/clinical_asset_inventory.json'
    inventory = read(root, inventory_path)
    for asset in inventory['assets']:
        if asset['path'] not in declaration.get('assets', {}):
            continue
        candidate = dict(asset, owner_evidence={
            'path': declaration_path, 'sha256': sha(safe_file(root, declaration_path))})
        problems = owner_errors(root, candidate)
        if problems or sha(safe_file(root, asset['path'])) != asset['sha256']:
            raise ValueError('Invalid owner evidence for ' + asset['path'] + ': ' + str(problems))
    promoted = []
    for asset in inventory['assets']:
        if not asset['submission_included'] or asset['path'] not in declaration['assets']:
            continue
        if asset['status'] not in {'UNRESOLVED', 'TEAM_ORIGINAL_VERIFIED'}:
            raise ValueError('Cannot overwrite external rights evidence: ' + asset['path'])
        asset['owner_evidence'] = {'path': declaration_path, 'sha256': sha(root / declaration_path)}
        asset['status'] = 'TEAM_ORIGINAL_VERIFIED'
        asset['original_author'] = 'Repository owner/team, as declared by the human repository owner; AI assistance recorded in Git history'
        # Do not overwrite original_source/model/prompt/date: this is a rights declaration,
        # not retroactive recovery of historical generation records or external citations.
        asset['license'] = declaration['grant_scope'] + '; see ' + declaration['license_file']
        for field in ('research_publication_permission', 'redistribution_permission', 'modification_permission'):
            asset[field] = 'Owner-authorized within ' + declaration['grant_scope'] + '; third-party terms excluded'
        asset['authorship_status'] = 'OWNER_DECLARED_NOT_INDEPENDENTLY_AUDITED'
        asset['rights_status'] = 'OWNER_DECLARED_SCOPE_BOUND; clinical validity and historical generation remain separate'
        asset['source_reference'] = list(dict.fromkeys([*asset.get('source_reference', []), declaration_path, declaration['license_file']]))
        promoted.append(asset['path'])
    inventory['clearance'] = 'Owner-declared rights for scoped team assets; not clinical or official submission approval'
    write(root, inventory_path, inventory)
    return promoted


CONCERNS = [
    ('CR-01', 'HIGH', '진정수면제 의존과 사용장애의 구분',
     ['nova_agent/knowledge/clinical_profiles.json', 'nova_agent/clinical_profiles.py'],
     '용량 증가·금단·감량 어려움만으로 사용장애를 선택할 수 있음. 치료 중 생리적 의존과 사용장애의 동등성은 입증되지 않음.',
     '처방대로 복용하던 환자의 금단을 사용장애로 단정하지 않는지, 기능 손상·조절 실패·유해 사용 조건과 명칭을 검토.',
     'https://www.nice.org.uk/guidance/ng215/chapter/Recommendations', 'NG215 1.2, 1.3, 1.5; 사용장애 진단 기준 자체를 제공하는 근거는 아님'),
    ('CR-02', 'HIGH', '갑상샘 비대는 확진 검사가 아님',
     ['nova_agent/knowledge/clinical_profiles.json', 'nova_agent/clinical_profiles.py'],
     'Hyperthyroidism confirmatory_findings에 diffuse goiter가 포함됨. Graves와 thyrotoxicosis 명칭 범위도 별도 검토 필요.',
     '혈액검사 전 작업 가설과 확진을 구분하고, 미만성 비대만으로 원인 확진·확정 문구가 출력되는지 검토.',
     'https://www.niddk.nih.gov/health-information/endocrine-diseases/hyperthyroidism', 'How do doctors diagnose hyperthyroidism?'),
    ('CR-03', 'HIGH', '소아 성장속도와 사춘기 상태',
     ['nova_agent/clinical_profiles.py', 'nova_agent/knowledge/clinical_profiles.json'],
     '3≤나이<12에서 4~7 cm/year를 prepubertal로 투영하지만 실제 사춘기 단계는 확인하지 않음. 골연령 지연은 단독 확진이 아님.',
     '성별·사춘기 단계·키 백분위·측정 간격·부모키·만성 질환을 검토하고 성장호르몬 결핍 과진단 가능성 확인.',
     'https://pedsendo.org/patient-resource/short-stature/', 'What Kind of Growth Pattern is Atypical? / What Tests Might Be Used to Assess Your Child?'),
    ('CR-04', 'HIGH', '응급 전환과 부정·시간·가족 정보의 분리',
     ['nova_agent/safety.py', 'nova_agent/clinical_assertions.py', 'nova_agent/evidence_scope.py', 'nova_agent/vitals_parser.py'],
     '의식 저하와 단순 졸림, 현재 위험과 과거·가족·부정 소견은 서로 다른 근거임.',
     '성인·영아·소아의 실제 위험 소견, 정상 재측정, (-)/(+/-), 가족 병력만 존재하는 상황을 각각 검토.',
     None, '기존 위험 규칙 원출처 미확정; 해당 전문 분야의 최신 근거 필요'),
    ('CR-05', 'MEDIUM', '추적 간격과 약물 계획',
     ['nova_agent/knowledge/clinical_profiles.json', 'competition/nova_sdk_adapter.py'],
     '1주·1~2주·3~6개월 간격은 일부 일반화한 개발 휴리스틱. 심한 금단·의식 저하 등에 일률적 추적 간격 적용은 부적절할 수 있음.',
     '환자 상태별 추적 간격과 즉시 평가 예외, 임의 중단·증량 금지 및 치료 계획의 적용 대상을 검토.',
     'https://www.nice.org.uk/guidance/ng215/chapter/Recommendations', 'NG215 1.4, 1.5; 개별 간격의 검증을 의미하지 않음'),
    ('CR-06', 'HIGH', '시행 전 검사 계획과 실제 환자 근거의 분리',
     ['competition/nova_sdk_adapter.py', 'nova_agent/final_decision.py', 'nova_agent/soap.py'],
     '검사 권고·질문·외부 배경 문서는 실제 환자의 양성 검사 결과가 아님.',
     '감별·A/P·환자 설명이 같은 결정에 근거하는지, 시행되지 않은 검사·음성 근거가 확진 근거로 출력되는지 검토.',
     None, '실제 전문가 판독 및 독립 사례 필요; 합성 테스트는 검토 완료 증거가 아님'),
]


def prepare(root=ROOT):
    inventory = read(root, 'artifacts/compliance_hardening/clinical_asset_inventory.json')
    pointer = read(root, 'artifacts/verification/CURRENT_RELEASE.json')
    release = read(root, pointer['current_verification_artifact'])
    binding = {name: sha(safe_file(root, name)) for name in release['runtime_sha256']}
    if binding != release['runtime_sha256']:
        raise ValueError('Runtime no longer matches current verification')
    ledger = []
    for asset in inventory['assets']:
        path = asset['path']
        commits = subprocess.check_output(
            ['git', 'log', '--follow', '--format=%H|%aI|%an|%s', '--', path],
            cwd=root, text=True).splitlines()
        ledger.append({
            'path': path, 'sha256': asset['sha256'], 'status': asset['status'],
            'included': asset['submission_included'],
            'kind': 'code' if path.endswith('.py') else 'documentation' if path.endswith('.md') else 'data',
            'git_history': commits,
            'history_limit': 'Commit attribution is not legal ownership, exact model receipt or clinician review.',
            'owner_evidence': asset.get('owner_evidence'),
            'generation_status': 'NOT_RECOVERED' if asset.get('generation_prompt') == 'UNRESOLVED' else 'SEE_INVENTORY',
            'clinical_review': asset['clinician_review'],
            'source_reference': asset['source_reference'],
        })
    by_path = {a['path']: a for a in inventory['assets'] if a['submission_included']}
    declaration_path = BASE / 'owner_declaration.json'
    declaration = read(root, declaration_path) if (root / declaration_path).exists() else {}
    archive_rows = []
    for member, digest in release['submission']['member_sha256'].items():
        source = member if member.startswith(('nova_agent/', 'competition/')) else 'submission/' + member
        if source in by_path:
            status = by_path[source]['status']
            evidence = by_path[source]['source_reference']
        elif declaration.get('assets', {}).get(source) == digest:
            status = 'OWNER_DECLARED_SCOPE_BOUND'
            evidence = [str(declaration_path), declaration['license_file']]
        elif member == 'MANIFEST.json':
            status = 'GENERATED_PACKAGE_METADATA'
            evidence = [pointer['current_verification_artifact'], 'scripts/build_nova_submission.py']
        else:
            status = 'EXTERNAL_RIGHTS_NOT_VERIFIED'
            evidence = ['Organizer toolkit origin and byte identity were checked; explicit redistribution scope not yet evidenced.']
        archive_rows.append({'member': member, 'source': source, 'sha256': digest,
                             'rights_status': status, 'evidence': evidence})
    archive = {'schema': 'nova-archive-rights-v1', 'archive_sha256': release['submission']['sha256'],
               'members': archive_rows,
               'blocked_members': [r['member'] for r in archive_rows if r['rights_status'] in {'EXTERNAL_RIGHTS_NOT_VERIFIED', 'UNRESOLVED'}],
               'clinical_review': 'PENDING_EXTERNAL_CLINICIAN', 'official_submission_allowed': False}
    write(root, BASE / 'archive_rights.json', archive)
    write(root, BASE / 'asset_evidence.json', {
        'schema': 'nova-asset-evidence-v1', 'runtime_commit': pointer['verified_runtime_sha'],
        'status_counts': dict(Counter(a['status'] for a in inventory['assets'])),
        'assets': ledger, 'independent_legal_opinion': False})
    cards = []
    for path in sorted((root / 'nova_agent/knowledge/diseases').glob('*.json')):
        for row in json.loads(path.read_text(encoding='utf-8')):
            cards.append({'id': row['id'], 'name': row['name'], 'kind': 'core_profile',
                          'path': str(path.relative_to(root)), 'sha256': sha(path), 'current_profile': row})
    path = root / 'nova_agent/knowledge/clinical_profiles.json'
    for row in json.loads(path.read_text(encoding='utf-8'))['profiles']:
        cards.append({'id': row['id'], 'name': row['name'], 'kind': 'supplemental_profile',
                      'path': str(path.relative_to(root)), 'sha256': sha(path), 'current_profile': row})
    for card in cards:
        card['review'] = {'reviewer_name': None, 'qualification': None, 'date': None,
                          'decision': 'PENDING', 'evidence': [], 'corrections': [], 'scope_and_exceptions': None}
    concerns = [dict(zip(('id', 'priority', 'title', 'paths', 'observation', 'review_question', 'reference_url', 'source_section'), row)) for row in CONCERNS]
    packet = {'schema': 'nova-clinical-review-packet-v1',
              'runtime_commit': pointer['verified_runtime_sha'], 'runtime_sha256': binding,
              'review_status': 'PENDING_EXTERNAL_CLINICIAN', 'reviewer': None,
              'cards': cards, 'priority_review_questions': concerns,
              'tier2_scope': {'catalog_concepts': len(read(root, 'nova_agent/knowledge/tier2_catalog.json')['conditions']),
                              'reviewed': 0, 'clinical_validation': 'NOT_VERIFIED'},
              'limit': 'Engineering observations and literature leads only; no clinical approval or patient-outcome validation.'}
    write(root, BASE / 'clinical_review_packet.json', packet)
    response = {'schema': 'nova-clinician-response-v1', 'packet_sha256': sha(root / BASE / 'clinical_review_packet.json'),
                'reviewer': {'actor_type': 'HUMAN_CLINICIAN', 'name': None, 'qualification': None,
                             'credential_verification_reference': None, 'review_date': None,
                             'conflict_of_interest': None},
                'attestation': None, 'credential_verification': None, 'signature_evidence': None, 'items': []}
    write(root, BASE / 'clinician_response_template.json', response)
    lines = ['# 최신 임상 검토 전달 자료', '',
             '현재 검토자와 승인 기록은 없습니다. 아래 항목은 코드와 문헌을 읽은 엔지니어의 관찰입니다.', '',
             f"검토 대상 런타임: `{pointer['verified_runtime_sha']}`. 핵심 34개 + 추가 8개 프로필 = 42개 카드.",
             'Tier-2 1,246개 전체가 검토된다는 뜻은 아닙니다. 먼저 위험 규칙과 아래 6개 질문을 검토해 주세요.', '',
             '기계 판독 자료: `../../artifacts/rights_and_review/clinical_review_packet.json`.',
             '답변 양식: `../../artifacts/rights_and_review/clinician_response_template.json`.', '',
             '의사 등 적절한 분야의 의료 전문가가 성명·자격 확인 근거·일자·이해관계·서명 근거와 검토 범위를 남겨야 합니다.',
             '실제 환자 개인정보는 제출하지 않아도 됩니다. 판단은 APPROVE / CHANGES_REQUIRED / INSUFFICIENT_EVIDENCE 중 선택합니다.',
             '각 항목에 문헌 URL·버전·절, 적용 대상과 예외, 권고 수정을 적어 주세요. 부분 검토는 부분 검토로만 집계합니다.', '',
             '## 우선 검토 질문', '']
    for concern in concerns:
        lines += [f"### {concern['id']} — {concern['title']} ({concern['priority']})", '',
                  concern['observation'], '', concern['review_question'], '',
                  '검토용 근거: ' + (concern['reference_url'] or '별도 근거 필요') + ' — ' + concern['source_section'], '']
    lines += ['## 포함된 프로필', '', '| 유형 | ID | 이름 |', '|---|---|---|']
    lines += [f"| {c['kind']} | `{c['id']}` | {c['name']} |" for c in cards]
    (root / 'docs/clinical_review/CURRENT_REVIEW_KO.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return {'rights_status_counts': dict(Counter(a['status'] for a in inventory['assets'])),
            'archive_rights_unverified_members': archive['blocked_members'],
            'clinical_cards': len(cards), 'clinical_review': packet['review_status'],
            'runtime_unchanged': True, 'official_submission_allowed': False}


def release_review_gate(root=ROOT):
    """Whole-archive checks are separate from the legacy nova_agent inventory."""
    errors = []
    try:
        archive = read(root, BASE / 'archive_rights.json')
        pointer = read(root, 'artifacts/verification/CURRENT_RELEASE.json')
        release = read(root, pointer['current_verification_artifact'])
        if archive['archive_sha256'] != release['submission']['sha256']:
            errors.append('archive rights record is stale')
        if {r['member']: r['sha256'] for r in archive['members']} != release['submission']['member_sha256']:
            errors.append('archive rights coverage is incomplete or stale')
        declaration_path = str(BASE / 'owner_declaration.json')
        declaration_hash = sha(safe_file(root, declaration_path))
        for row in archive['members']:
            if row['member'] == 'MANIFEST.json':
                continue
            if sha(safe_file(root, row['source'])) != row['sha256']:
                errors.append('archive source changed: ' + row['source'])
            if row['rights_status'] == 'OWNER_DECLARED_SCOPE_BOUND':
                errors.extend(owner_errors(root, {'path': row['source'], 'sha256': row['sha256'],
                              'owner_evidence': {'path': declaration_path, 'sha256': declaration_hash}}))
        blocked = [r['member'] for r in archive['members']
                   if r['rights_status'] not in {'VERIFIED', 'TEAM_ORIGINAL_VERIFIED',
                                                'OWNER_DECLARED_SCOPE_BOUND', 'GENERATED_PACKAGE_METADATA'}]
    except (KeyError, ValueError, OSError):
        errors.append('missing or invalid archive rights evidence')
        blocked = ['ARCHIVE_EVIDENCE_NOT_VERIFIED']
    response_path = root / BASE / 'clinician_response.json'
    clinical = 'PENDING_EXTERNAL_CLINICIAN'
    if response_path.exists():
        response_result = validate_clinician_response(root, json.loads(response_path.read_text(encoding='utf-8')))
        clinical = response_result['evidence_status'] + '; independent identity/scope/corrections assessment required'
    return {'archive_rights_coverage': 'FAIL' if errors else 'PASS', 'errors': errors,
            'unverified_archive_members': blocked, 'clinician_review': clinical,
            'official_submission_allowed': False}


def validate_clinician_response(root, response):
    """Validate supplied evidence and scope; does not establish professional identity itself."""
    packet = read(root, BASE / 'clinical_review_packet.json')
    errors = []
    if response.get('packet_sha256') != sha(root / BASE / 'clinical_review_packet.json'):
        errors.append('stale or different review packet')
    for name, digest in packet['runtime_sha256'].items():
        try:
            if sha(safe_file(root, name)) != digest:
                errors.append('runtime changed: ' + name)
        except ValueError:
            errors.append('missing runtime: ' + name)
    reviewer = response.get('reviewer') or {}
    if reviewer.get('actor_type') != 'HUMAN_CLINICIAN':
        errors.append('reviewer is not a human clinician')
    for key in ('name', 'qualification', 'credential_verification_reference', 'review_date', 'conflict_of_interest'):
        if not reviewer.get(key):
            errors.append('missing reviewer ' + key)
    try:
        day = datetime.strptime(reviewer.get('review_date', ''), '%Y-%m-%d').date()
        if day > datetime.now(timezone.utc).date():
            errors.append('future review date')
    except (ValueError, TypeError):
        errors.append('invalid review date')
    if not response.get('attestation'):
        errors.append('missing human review attestation')
    for key in ('credential_verification', 'signature_evidence'):
        ref = response.get(key) or {}
        try:
            if sha(safe_file(root, ref['path'])) != ref['sha256']:
                errors.append('changed ' + key)
        except (KeyError, ValueError, TypeError):
            errors.append('missing ' + key)
    valid_ids = {c['id'] for c in packet['cards']} | {c['id'] for c in packet['priority_review_questions']}
    seen = set()
    for item in response.get('items', []):
        ident = item.get('id')
        if ident not in valid_ids or ident in seen:
            errors.append('unknown or duplicate review item: ' + str(ident))
        seen.add(ident)
        if item.get('decision') not in {'APPROVE', 'CHANGES_REQUIRED', 'INSUFFICIENT_EVIDENCE'}:
            errors.append('invalid review decision')
        if not item.get('supporting_sources') or not item.get('scope_and_exceptions'):
            errors.append('missing review evidence or scope')
        if item.get('decision') == 'CHANGES_REQUIRED' and not item.get('corrections'):
            errors.append('missing required corrections')
    if not seen:
        errors.append('no reviewed items')
    return {'evidence_status': 'FAIL' if errors else 'SUPPLIED_DOCUMENTS_HASH_VALID',
            'errors': errors, 'reviewed_items': len(seen),
            'scope': 'PARTIAL' if seen != valid_ids else 'PACKET_ITEMS_ONLY',
            'independent_identity_verification': False, 'automatic_clinical_approval': False,
            'official_submission_allowed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-declaration')
    parser.add_argument('--clinician-response')
    args = parser.parse_args()
    if args.clinician_response:
        result = validate_clinician_response(ROOT, read(ROOT, args.clinician_response))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(2 if result['errors'] else 0)
    if args.owner_declaration:
        apply_owner(ROOT, args.owner_declaration)
    print(json.dumps(prepare(), ensure_ascii=False, indent=2))
