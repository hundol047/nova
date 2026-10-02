# 현재 전체 현황

**기존 등록 1,280개 + ICD 6,309개 + Mondo 15,350개 + Orphanet 388개 + 외상·중독 1,195개 = 총 24,522개 레코드.**

이번 요청의 목표는 23,327개의 1.5배인 34,991개이며, 10,469개 미달입니다. 새 항목은 모두 미검증 후보로 자동 진단에 적용하지 않았습니다.

- 최신 추가 내역: [INJURY_IMPORT.md](INJURY_IMPORT.md)
- 이전 출처 내역: [ORPHANET_IMPORT.md](ORPHANET_IMPORT.md), [MONDO_IMPORT.md](MONDO_IMPORT.md)
- 현재 합계: `combined_manifest.json`
- 최신 전수 자동 검사: `validation/summary.json`, `validation/candidate_checks.jsonl`

아래는 ICD 출처만의 수집 내역입니다.

# 진단명 후보 추가 확장 — 공식 원본 한계 — 2026-10-02

**기존 등록 1,280개 + 검토용 후보 6,309개 = 총 7,589개 레코드.**

이번 요청은 6,400개의 5배인 **32,000개**입니다. 현재 CDC 원본과 중복 제외 기준으로는 도달하지 못했습니다. 이전 후보 5,120개를 모두 유지하면서 **1,189개를 추가**했고, **24,411개 부족** 상태를 JSON에 명시했습니다. 이는 이 원본과 선택 기준의 한계이며, 의학 전체의 질병 수 상한이라는 뜻은 아닙니다.
자동 진단의 종류를 5배로 활성화한 것은 아닙니다. 신규 목록은 원문 명칭을 검색하고 임상 검토를 준비하는 오프라인 자료입니다. 기존 진단 경로와 확장 차단 기준은 유지했습니다.

## 무엇을 늘렸는가

CDC ICD-10-CM FY2027 공식 파일의 진단·상태 세부 분류를 사용했습니다. 증상/외인/의료이용 코드 중심의 R, V–Z 범주와 일반 외상 S 범주는 제외했습니다. A–Q와 진료 관련 합병증 T80–T88에서 선택했습니다. 질환의 세부 유형과 상태를 포함하므로 '서로 독립적인 질병 7,589개'라는 의미가 아닙니다.

| 신규 후보 분류 | 개수 |
| --- | ---: |
| 혈액·면역 | 164 |
| 진료·시술 관련 합병증 | 205 |
| 순환기 | 306 |
| 선천성 | 452 |
| 소화기 | 496 |
| 귀 | 8 |
| 내분비·대사 | 345 |
| 눈 | 79 |
| 비뇨생식기 | 430 |
| 감염 | 634 |
| 정신·행동 | 373 |
| 근골격 | 659 |
| 종양 | 703 |
| 신경 | 347 |
| 주산기 | 295 |
| 임신·출산 | 274 |
| 호흡기 | 198 |
| 피부 | 341 |
| **합계** | **6,309** |

## 중복·출처 관리

- 공식 원문의 코드·영문 장문 명칭을 그대로 보존했습니다. 진단 기준, 증상, 한국어 번역, 치료법, 응급도는 생성하지 않았습니다.
- 진단 입력용 말단 코드만 선택하고, 기존 명칭·별칭·알려진 코드와 일치하는 항목을 제외했습니다.
- 좌/우/양측, 미상/기타, 임신 분기·태아 번호, 관해만을 구분하는 명칭을 제외했습니다. 합병증의 진료 차수 코드는 초기 진료형 하나만 수록했습니다.
- 전문 분야를 순환하며 선택해 특정 분야에만 몰리지 않게 했습니다. 임상 빈도나 진단 정확도 순으로 고른 것은 아닙니다.
- 신규 명칭끼리 정규화된 이름 중복은 없습니다. 기존 1,280개에는 동일 정규화 명칭 4개가 있으므로, 합친 **서로 다른 명칭 문자열 수는 7,585개**입니다. 임상적으로 같은 질환의 다른 표현인지 여부는 별도 전문가 검토가 필요합니다.
- 각 레코드는 `NOT_VERIFIED`, `runtime_eligible=false`이며 임상 의미·기존 질환과의 동등성 검토 상태는 `PENDING`입니다.

## 파일 및 재현

- `review_candidates.json`: 신규 후보 전체, 코드, 분류, 검증 상태, 기준 목록 ID, 출처 해시.
- `sources/icd10cm-code-descriptions-2027.zip`: 사용한 공식 원본 보존본.
- `scripts/build_review_candidates.py`: 결정적 재생성 스크립트. 원본에 충분한 적격 항목이 없으면 기본적으로 실패합니다. `--allow-source-limit`을 명시하면 확보 가능한 항목까지만 저장하고 미달 상태를 기록합니다. 임의 항목은 만들지 않습니다.
- `scripts/search_review_candidates.py`: 영어 명칭 일부 또는 ICD-10-CM 코드로 검토 목록 검색. 진단 엔진에 연결되지 않습니다.

```sh
python scripts/build_review_candidates.py --target-total 32000 --allow-source-limit
python scripts/search_review_candidates.py anesthesia --limit 10
python scripts/search_review_candidates.py T88.2XXA
python -m pytest tests/test_review_candidate_expansion.py tests/test_expansion_validation_gate.py tests/test_ontology_catalog.py -q
```

출처: https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip

원본 ZIP SHA-256: `93e3ad6004badf470c55bfe679b748ae88fd9b2b421851e409eec382c7713b9a`

공식 배포 안내: https://www.cdc.gov/nchs/icd/icd-10-cm/files.html

## 사용 범위

이 작업은 학습·재학습이나 임상 검증을 수행하지 않았습니다. 이전 고난도 v11의 위험 질환 정답 7/15라는 한계는 해결된 것으로 간주하지 않습니다. 신규 후보를 실시간 후보 검색이나 최종 진단에 투입하려면 임상 의미, 근거, 증상 연결, 코드 동등성과 별도의 독립 평가가 먼저 필요합니다. 기존 확장 게이트를 우회하거나 제출 패키지에 미검증 자료를 추가하지 않았습니다.

검증 결과: 출처 일치·중복·재현성·실행 경로 분리·기존 게이트 관련 검사 **27개 통과**. 진단 런타임 코드는 변경하지 않았습니다.
