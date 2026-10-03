# Mondo 추가 수집 결과 — 2026-10-02

**15,350개 추가 → 기존 등록·검토 후보 합계 22,939개.**

| 구분 | 항목 수 |
| --- | ---: |
| 기존 실행 카탈로그 | 1,280 |
| ICD-10-CM 검토 후보 | 6,309 |
| Mondo 신규 검토 후보 | 15,350 |
| 합계 | 22,939 |

이전 목표 32,000개까지는 9,061개 부족합니다. 이 수는 질환 세부 유형을 포함한 용어 레코드 수이며, 임상적으로 독립적인 질병 수 또는 자동 진단 가능한 질환 수가 아닙니다.

## 출처와 처리

Mondo Disease Ontology, Monarch Initiative의 `releases/2026-09-01` 배포본을 사용했습니다.

- 공식 안내: https://mondo.monarchinitiative.org/pages/download/
- 수집 주소: https://purl.obolibrary.org/obo/mondo.obo
- 라이선스: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
- 원본 압축 보존본: `sources/mondo-2026-09-01.obo.gz`
- 라이선스 전문: `sources/MONDO-LICENSE.txt`
- 원본 SHA-256: `50c8367f9bd9978321eedf84d4e2e79cb757efbed514c81effb00b9ad2e49994`

Mondo 기여자들의 원본을 필터링·재구성한 파생 데이터입니다. 원문 명칭, 정확 동의어, 상위 ID와 교차참조를 보존하고 NOVA의 검토 상태를 추가했습니다. 원출처의 승인이나 임상 검증을 의미하지 않습니다.

## 선택·중복 검사

- 인간 질환 루트 `MONDO:0700096`의 하위 항목 중 하위 클래스가 없는 말단 항목만 선택했습니다.
- 폐기 항목, 동물 전용 질환, 비질환·분류용 상위 항목, 질환 소인/감수성 분류를 제외했습니다.
- 기존 명칭·동의어 및 선택된 신규 항목의 정확 동의어와 겹친 927개를 제외했습니다. 짧은 동의어(5자 미만)는 약어 모호성 때문에 동의어 대조에서 제외했지만, 정식 명칭은 길이에 관계없이 대조했습니다.
- 기존 ICD 코드와 교차참조가 겹친 134개도 중복 가능성 때문에 보수적으로 제외했습니다. 교차참조를 동등한 코드라는 뜻으로 단정하지 않았습니다.
- 증상, 응급도, 진단 기준, 치료법, 한국어 번역은 생성하지 않았습니다.
- 명칭·코드 대조만으로 모든 의미상 중복을 제거했다고 주장하지 않습니다. 모든 신규 항목은 `NOT_VERIFIED`, `runtime_eligible=false`, 임상 의미와 기존 개념 동등성은 `PENDING`입니다.

## 사용·재현

```sh
python scripts/build_mondo_review_candidates.py
python scripts/search_review_candidates.py syndrome --source mondo --limit 10
python scripts/search_review_candidates.py anesthesia --source all --limit 10
python -m pytest tests/test_mondo_review_expansion.py tests/test_review_candidate_expansion.py tests/test_expansion_validation_gate.py tests/test_ontology_catalog.py -q
```

통합 검색은 ICD와 Mondo의 검토 후보를 검색합니다. 실행 카탈로그의 1,280개는 이 오프라인 검색 목록에 중복 추가하지 않습니다. 임상 실행 경로와 제출 패키지는 변경하지 않았습니다. 새 데이터로 모델을 학습하거나 임상 정확도를 평가한 작업도 아닙니다.

검증 결과: 원문 일치·인간 질환 필터·동의어 중복·재현성·합산 수치·통합 검색·실행 경로 분리 및 기존 게이트 관련 검사 **33개 통과**.
