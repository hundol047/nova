# Orphanet 추가 수집 — 2026-10-02

**388개 추가 → 기존 등록·검토 후보 합계 23,327개.** 32,000개 목표까지 8,673개 부족합니다.

| 구분 | 레코드 수 |
| --- | ---: |
| 기존 실행 카탈로그 | 1,280 |
| ICD 검토 후보 | 6,309 |
| Mondo 검토 후보 | 15,350 |
| Orphanet 신규 검토 후보 | 388 |
| 합계 | 23,327 |

## 출처·라이선스

Orphanet / INSERM, Orphadata product 1, 원본 생성일 `2026-06-23 07:53:50`.

- 원본: https://www.orphadata.com/data/xml/en_product1.xml
- 기관: https://www.orphadata.com/
- 원본 XML이 명시한 라이선스: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/
- 압축 원본 보존: `sources/orphanet-product1-2026-06-23.xml.gz`
- 압축 해제 원본 SHA-256: `df8d562a0c6011af36a74eb4000ce81ca7d723e8031010819fb71727c0962bbb`

Orphanet 기여자들의 원본 명칭·별칭·코드·매핑 관계를 보존하고, 필터링과 JSON 재구성 및 NOVA 검토 상태를 추가한 파생 데이터입니다. 원출처가 NOVA를 승인하거나 임상 검증했다는 의미는 아닙니다.

## 대조 결과

원본 11,645개 중:

- 비활성·역사적 항목·분류 그룹·생물학적 이상 등 제외: **4,698개**
- 기존 명칭·별칭 또는 신규 후보끼리 겹침: **5,178개**
- 기존 코드·교차참조와 중복 가능성: **1,381개**
- 신규 검토 후보: **388개**

원본의 질환·증후군·질환 세부 유형을 선택했습니다. 같은 교차참조를 공유해도 반드시 동일 질환은 아니므로, 이 경우는 중복 가능성으로 보수적으로 제외했으며 동등성을 확정하지 않았습니다. 매핑의 넓음/좁음/동등함 관계와 원출처의 매핑 검증 상태는 원문대로 보존합니다. 원출처의 매핑 검증과 NOVA의 임상 검증 상태는 별개입니다.

숫자는 질환 세부 유형을 포함한 용어 레코드 수입니다. 모든 의미상 중복이 제거됐다거나 이 수만큼 자동 진단이 가능하다는 주장은 하지 않습니다. 모든 신규 항목은 `NOT_VERIFIED`, `runtime_eligible=false`이며 의미·동등성 검토는 `PENDING`입니다.

## 재현·검색

```sh
python scripts/build_orphanet_review_candidates.py
python scripts/search_review_candidates.py ORPHA:27 --source orphanet
python scripts/search_review_candidates.py syndrome --source all --limit 10
python -m pytest tests/test_orphanet_review_expansion.py tests/test_mondo_review_expansion.py tests/test_review_candidate_expansion.py tests/test_expansion_validation_gate.py tests/test_ontology_catalog.py -q
```

통합 검색과 합계 manifest에 세 출처를 연결했습니다. 진단 런타임, 학습 모델, 제출 패키지 및 임상 확장 차단 기준은 변경하지 않았습니다. 한국어 번역·증상·진단 기준·치료법은 임의 생성하지 않았습니다.

검증 결과: 원문·매핑 관계 일치, 비활성 항목 제외, 재현성, 통합 검색·합산, 실행 경로 분리 및 기존 검증 **38개 통과**.
