# v37 문진·설명 완료 개선

사용자가 제공한 점수 화면: 총점 **51.977**. 정보수집 8.28/25, 진단추론 7.08/15, 검사·추적 3.44/10, 안전 10.00/15, 의사소통 3.17/15, 효율 20.00/20. 반올림된 영역 합계는 51.97이며 화면 총점과 구별한다. 이 화면만으로 감점 원인을 턴 부족으로 확정하지 않는다.

## 수정한 실제 문제

- 만성 수면·성장·체중 변화 문진의 내부 상한 12회가 기본 병력을 마치기 전에 종료를 유발할 수 있었다. 이를 24회로 확대했다.
- 전체 내부 목표 40→48턴, 일반 엔진 단계 26→30턴, Doctor 추가 질문 6→8개, 재평가 최대 2→3회로 조정했다. 종료 설명용 10턴은 문진 단계에서 먼저 확보한다. 필요한 정보가 이미 있으면 턴을 채우기 위한 질문을 만들지 않는다.
- 엔진의 조기 종료 후에도 시작 시점·경과·과거력·복약·알레르기·가족 질환·기능 영향·이전 진료의 미확인 항목을 확인한다. 출생 체중과 부모 키는 일반 과거력·가족력을 대체하지 않는다.
- 수면 관련 문진에 실제 수면 양상·시간·코골이·카페인·증상 시작 시점을 추가했다. 갑상샘의 특징적인 진찰 소견이 있어도 미확인 동반 증상을 자동으로 생략하지 않는다.
- 시작 시점·기간·경과 등 세부 질문의 답변을 최종 S.hpi와 C.C의 Onset에 정확히 배치한다. 기존에는 상세 키가 있으면 ROS로 잘못 분류될 수 있었다.
- 출생 체중 질문을 체중 감소 질문으로 오인해 모른다는 답 뒤 반복하던 문제, 약물 알레르기 부재를 복용 약 부재로 오인하던 문제를 수정했다.
- 환자의 우려를 묻고, 작업 진단·다음 단계·경고 증상·검사 목적·치료 방향·불확실성·이해 확인·추가 질문 기회를 실제 SAY로 제공한다. 이해 확인 답이 불명확하면 추적 시점을 다시 설명한다. 실제 답변을 교육 기록에 남기며 이해했다고 임의로 단정하지 않는다.
- 응급 위험과 마감 임박 상황에서는 확장 문진·긴 설명을 생략하고 핵심 조치와 최종 제출을 우선한다. 실제로 시행하지 않은 검사는 O.tests에 쓰지 않는다.

## 동일 조건 비교

3개의 합성 환자에 일반 병력과 수면·체중 관련 응답 채널을 명시해 양 버전을 같은 스크립트로 실행했다. 진단 정답을 런타임에 추가하거나 공식 증례를 재현한 결과가 아니다.

| 항목 | 이전 v36 | v37 |
|---|---:|---:|
| 합성 3건 평균 턴 | 12.00 | 29.00 |
| 명시한 문진 체크리스트 평균 충족률 | 43.29% | 100.00% |
| 환자에게 한 종료 질문·설명 | 각 3턴 | 각 10턴 |
| 질문 완전 동일 반복 | 0 | 0 |
| 평균 Doctor 요청 수(가짜 응답) | 2.67 | 2.33 |
| 3건 작업 진단 | 3/3 유지 | 3/3 유지 |

별도로 기존 개발 사례 230건의 complete 조건을 같은 fake SDK와 scripted Doctor로 각각 실행했다. 이는 신규 블라인드 평가가 아니며, 기존 1,150개 조건 전체를 새로 실행했다는 뜻도 아니다.

| 항목 | 이전 v36 | v37 |
|---|---:|---:|
| 채점 대상 | 222/230 | 222/230 |
| Top-1 | 203/222 (91.44%) | 203/222 (91.44%) |
| Top-3 / Top-5 | 217/222 (97.75%) | 217/222 (97.75%) |
| critical 라벨 진단 일치 | 80/85 | 80/85 |
| 평균 턴 | 16.94 | 21.85 |
| 턴 중앙값 / 90백분위 | 16 / 23 | 22 / 28 |
| 턴·글자 수·가짜 검사 결과 위반 | 0 | 0 |

두 버전의 230건 주진단은 전부 일치했다. 신규 버전 최대 사용 턴은 35였다. 기존 정보수집·의사소통 대리 지표는 이 사례군에서 변하지 않았다. 따라서 진단 정확도나 공식 점수 향상을 입증했다고 해석하지 않는다. 3건의 상세 문진 체크리스트 개선과 공식 점수는 다른 지표다.

기존 Round M 128건(123건 채점)은 위 230건에 모두 포함된다. 현재 릴리스의 Round M 파일은 이 실제 SDK 실행 결과의 정확한 부분집합이다. TEST를 사용하는 과거 후보 단계 추적 방식과 비교하지 않는다. 불필요하게 시작한 과거 추적 실행은 중단했고 그 부분 결과는 검증 근거로 사용하지 않았다. `scripts/extract_round_m_sdk_evidence.py`에 변환과 분모 검증이 있다.

## 재현 및 제출

실행 소스 커밋은 `62a08223f429ac52966c8649809d9bb92a850c13`. 로컬 실행 커밋 `4389c463722bc34ac179049a78df56ba213d8503`와 Git tree `3df3d6fa80ea5641e0d0771c3ed8bfaeae449b40`가 같다. 전체 소스·제출 폴더·ZIP 구성원 해시를 결합해 확인한다. 빌드 시 SOURCE_DATE_EPOCH는 실행 소스 커밋의 시간을 사용한다.

제출 파일: `artifacts/releases/nova-v37-submission.zip`.

검증 수치와 배포 해시는 `artifacts/verification/CURRENT_RELEASE.json`, `artifacts/clinical_quality_v37/comparison.json`, `artifacts/releases/nova-v37-publication.json`을 따른다. Python 3.11과 3.12에서 각각 **2,852개 통과, 1개 건너뜀(선택적 Torch 학습 테스트)**. 핵심 2,830개와 릴리스 결합·검토 기록 22개를 합친 수치다. 최종 집중 검사는 187개 통과했다. 자세한 테스트 결과는 `artifacts/clinical_quality_v37/validation/`에 있다.

```bash
python -m pytest -q tests --ignore=tests/test_current_pre_guide_release.py --ignore=tests/test_rights_and_review_evidence.py
python scripts/evaluate_official_fixture_efficiency.py --output fixture.json
python scripts/evaluate_clinical_quality.py --protocol evaluation/clinical_quality_v36_protocol.json --split all --mode complete --workers 4 --output sdk230.json
python scripts/validate_submission_zip.py submission/submission.zip --output zip-validation.json
```

실제 Doctor 모델·공식 서버 채점·참가자 키 호출은 실행하지 않았다. 공식 점수는 사용자 재제출 결과로 확인해야 한다. 외부 DDXPlus 평가를 이번 버전에서 다시 실행하지 않았고, 과거 결과를 새 버전의 결과로 재표기하지 않았다. 기록의 기존 NOT READY·미검증 표시는 모의 테스트로 승격하지 않는다.

## 확인한 1차 자료

- NOVA 개발 가이드, 2026-10-13 확인: https://nova.snubhai.org/docs/ — 50턴, SAY/EXAM 30자, 예선 검사 계획과 실제 결과 구분, 실제 대화의 교육 기록. 이날 문서는 Doctor를 openai/gpt-6-luna로 안내하고 이전 openai/gpt-oss-20b ID도 Doctor로 처리한다고 명시한다. 기존 SDK 별칭을 유지했으며 실제 모델 동작은 검증하지 않았다.
- NIDDK 갑상샘항진증: https://www.niddk.nih.gov/health-information/endocrine-diseases/hyperthyroidism — 증상·진찰과 기능 검사, 원인 평가의 구분 참고.
- Pediatric Endocrine Society 저신장: https://pedsendo.org/patient-resource/short-stature/ — 종적 성장 기록, 가족 성장 양상과 필요 시 추가 평가 참고.

새 약물 용량이나 독자적인 검사 결과를 추가하지 않았다. 기존 임상 계획과 추적 간격의 검토 필요성은 유지된다.
