# Human Disease Ontology 추가 수집 — 2026-10-02

**974개 추가 → 전체 등록·검토 후보 합계 25,496개.** 34,991개 목표에는 9,495개 미달입니다.

출처: Human Disease Ontology / Disease Ontology team. 배포 버전 `releases/2026-09-30/doid.obo`.

- 공식 프로젝트: https://disease-ontology.org/
- 원본 주소: https://purl.obolibrary.org/obo/doid.obo
- 라이선스: CC0-1.0, `sources/DOID-LICENSE.txt`에 원문 보존.
- 원본 보존: `sources/doid-2026-09-30.obo.gz`
- 압축 해제 원본 SHA-256: `51e717b6b9f5d391f2793f9e16faf9c8629a661ab8f21c3a024458129f182ad2`

## 선별 결과

DOID 용어 14,854개를 대조했습니다. 폐기·상위 분류·질환 루트 밖 항목 및 소인 관련 항목 4,979개, 이름·정확 동의어 중복 가능성 7,389개, 코드·교차참조 중복 가능성 1,512개를 제외했습니다. 최종 974개를 검토 목록에 추가했습니다.

NCI/NCIT, UMLS_CUI/UMLS, 버전이 붙은 SNOMEDCT/SCTID, MIM/OMIM 등 코드 체계 표기를 맞춰 비교했습니다. 이 정규화를 적용하기 전의 잠정 후보 1,129개에서 추가 중복 가능성 155개를 제거했습니다. 교차참조가 겹친다는 이유만으로 임상적 동등성을 확정하지 않았습니다.

질환 루트 DOID:4의 하위 항목 중 하위 클래스가 없는 말단 항목을 선택했습니다. 세부 질환 유형을 포함하므로 레코드 수와 독립적인 임상 질환 수는 다를 수 있습니다. 명칭·정확 동의어·교차참조 검사로 모든 의미상 중복이 해결된 것은 아닙니다.

## 보존·검증 상태

원문 명칭, 정확 동의어, 상위 ID, 교차참조 및 출처 버전을 보존했습니다. 필터링·재구성한 파생 자료이며, 원출처가 NOVA를 승인하거나 임상 검증했다는 뜻은 아닙니다. 모든 새 항목은 `NOT_VERIFIED`, `runtime_eligible=false`로 자동 진단 경로에서 분리했습니다.

전체 실행 카탈로그 1,280개 + 검토 후보 24,216개 = 25,496개입니다. 코드나 모델의 진단 성능은 이번 수집으로 개선됐다고 주장하지 않습니다.

```sh
python scripts/build_doid_review_candidates.py
python scripts/search_review_candidates.py syndrome --source doid --limit 10
python scripts/audit_all_review_candidates.py
```

관련 데이터 검증은 `tests/test_doid_review_expansion.py`와 기존 출처·카탈로그·확장 게이트 검사를 함께 실행합니다. 전체 합계는 `combined_manifest.json`, 최신 전수 검사 결과는 `validation/summary.json`을 참조하세요.

검증 결과: 관련 검사 **45개 통과**. 전체 후보 **24,216개** 원본 재생성·상태·실행 경로 분리 검사 통과. 임상 검증 완료를 뜻하지 않습니다.
