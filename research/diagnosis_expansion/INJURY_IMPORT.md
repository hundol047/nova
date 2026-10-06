# 외상·중독 진단 용어 추가 — 2026-10-02

요청: 기존 23,327개의 1.5배 = 34,990.5 → **34,991개 목표**.

이번에 **1,195개**를 추가해 합계 **24,522개**입니다. 목표에는 **10,469개 부족**하며 1.5배 확장을 완료한 것으로 표시하지 않았습니다.

CDC ICD-10-CM FY2027 원본에서 기존에 수집 범위 밖이었던 S 및 T00–T79의 외상·중독·독성 영향·약물 이상반응 진단 용어를 수집했습니다. 초기 진료 코드 하나만 선택하고 좌우·양측, 미상/기타, 진료 차수 반복 및 발생 의도만 다른 변형을 제외했습니다. 질병만이 아니라 손상·중독·상태의 세부 유형을 포함합니다.

기존 네임·별칭, 실행 카탈로그 코드, 격리된 코드와 세 검토 출처의 교차참조를 대조했습니다. 교차참조 공유를 임상적 동등성으로 확정하지 않고, 중복 가능성 때문에 보수적으로 제외합니다. 명칭 문자열 중복 제거가 완전한 임상 의미 중복 제거를 보증하지는 않습니다.

출처: https://ftp.cdc.gov/pub/health_statistics/nchs/publications/ICD10CM/2027/icd10cm-code-descriptions-2027.zip

원본 SHA-256: `93e3ad6004badf470c55bfe679b748ae88fd9b2b421851e409eec382c7713b9a`

`injury_review_candidates.json`에 원문명·코드·원본 위치·검토 상태를 보존했습니다. 모든 새 항목은 `NOT_VERIFIED`, `runtime_eligible=false`이며 자동 진단 경로에 넣지 않았습니다. 증상·치료법·한국어 번역을 임의로 생성하지 않았습니다.

```sh
python scripts/build_injury_review_candidates.py
python scripts/search_review_candidates.py abrasion --source injury
python scripts/audit_all_review_candidates.py
python -m pytest tests/test_injury_review_expansion.py tests/test_orphanet_review_expansion.py tests/test_mondo_review_expansion.py tests/test_review_candidate_expansion.py tests/test_expansion_validation_gate.py tests/test_ontology_catalog.py -q
```

기존 데이터 파일의 당시 목표·수치는 역사적 기록으로 유지했습니다. 현재 전체 수치와 새 목표는 `combined_manifest.json`에 있습니다. 실행 카탈로그는 1,280개 그대로이며, 미검증 후보는 합계 23,242개입니다. 이 작업은 진단 정확도 향상을 의미하지 않습니다.

검증: 관련 검사 **42개 통과**. 전체 검토 후보 **23,242개**를 원본에서 재생성해 대조했고 자동 검사 오류는 0건입니다. 임상 검증 완료를 뜻하지 않습니다.
