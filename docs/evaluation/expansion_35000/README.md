# 명칭 35,000개와 고난도 근거 검토 — 2026-10-02

서로 다른 정규화 명칭을 **35,000개**로 확장했다. 기존 동일 명칭 4쌍을 포함한 전체
레코드는 35,004개다. 기존 실행 카탈로그 1,280개와 오프라인 검토 후보 33,724개로 구성된다.
이번에 추가한 NCIt 명칭은 9,508개다. 세부 유형·병기·상위 분류를 포함한 용어 목록이며
독립된 질병 35,000개 또는 임상 검증된 자동 진단 범위 35,000개를 의미하지 않는다.

| 검사 | 결과 |
| --- | ---: |
| 전체 오프라인 후보 원본 재생성·실행 분리 검사 | 33,724/33,724 통과 |
| 오프라인 후보 간 ID·정규화 대표명 중복 | 0 |
| 전체 레코드의 서로 다른 정규화 대표명 | 35,000 |
| 전체 소프트웨어 테스트 | 550 통과, 1 건너뜀 |
| 7개 질환의 구조화 증거 검사 | 54/54 통과 |
| 기존 고난도 모의평가 | 17/24 (70.8%), 이전과 동일 |
| 이름이 있는 고난도 진단 | 15/22 (68.2%), 이전과 동일 |
| 위 고난도 평가의 위험질환 | 9/15 (60.0%), 이전과 동일 |

전체 소프트웨어 검사에서 의존성 deprecation 경고 1개가 있었다. JUnit XML에 551개
테스트 중 오류·실패 0, 건너뜀 1을 확인했다. 모의평가는 mock provider를 사용했다.
최신 소스 전수 검사는 `research/diagnosis_expansion/validation/summary.json`에 있다.
여러 출처에서 같은 참조 코드가 나오는 294개 그룹은 별도 의미 검토 대상으로 남겼다.

## 정확도 개선을 위해 추가한 것

기본 엔진에 감별 규칙이 없는 남은 7개 질환에 대해 출처가 있는 근거 초안,
감별 대상, 확인해야 할 검사·관찰, 적용 범위 제한을 작성했다. 현재 관찰을 과거력·추정·
부정 소견과 구분하고 충돌 기록은 긍정 증거로 세지 않는 오프라인 검토 코드도 추가했다.
입력 증거가 충분한지와 어떤 부분이 빠졌는지를 확인할 수 있다.

- [7개 질환 근거 검토 안내](../../../research/clinical_review/hard_seven/README.md)
- [구조화 근거 초안](../../../research/clinical_review/hard_seven/profiles.json)
- [NCIt 추가 출처·선택 기준](../../../research/diagnosis_expansion/NCIT_IMPORT.md)
- `evidence_probes.json`: 54개 구조화 입력의 전체 결과
- `hard_reference.json`: 기존 고난도 24개 모의 대화 결과
- `summary.json`, `software_tests.xml`, `software_tests.txt`, `expansion_gate.json`

**이번 변경으로 진단 정답률은 상승하지 않았다.** 54개 검사는 개발자가 만든 소프트웨어
증거 처리 검사이며 임상 검증이 아니다. 신규 명칭과 7개 근거 초안은 `NOT_VERIFIED`로
유지하며 자동 진단 경로에 넣지 않았다. 기존 게이트도 `BLOCKED`다. 전문가 검토와
별도 라벨 사례·실제 모델 평가 없이 검증 완료로 표시하지 않았다.

기준 커밋은 `cd9ec6a`다. v11 원문·정답·분모를 변경하지 않았고 모델 재학습이나
확률 수치 상향도 하지 않았다. 변경과 결과는 로컬 Git에 저장하며 원격 push·배포는 수행하지 않았다.

## 재현

```sh
python scripts/build_ncit_review_candidates.py
python scripts/audit_all_review_candidates.py
python scripts/review_diagnostic_evidence.py --output /tmp/evidence_probes.json
python scripts/run_danger_simulations.py --suite reference --output /tmp/hard_reference.json
python -m pytest tests/ -q --tb=short --junitxml=/tmp/software_tests.xml
python scripts/check_expansion_gate.py  # 예상 결과 BLOCKED, 종료 코드 1
```
