# v36 임상 대화 개선 및 평가 범위

이 문서는 공식 점수 예측이 아니다. 실제 기준점은 사용자가 전달한 45.84/100이며, 이번 작업에서는 참가자 키나 공식 Doctor 모델을 사용하지 않았다. 사용자 후속 지시에 따라 필요한 질문 수를 늘리는 것을 허용했다.

## 수정 원칙

- 질문 시도와 사실 확인을 구분한다. 불확실한 답변은 음성 소견으로 바꾸지 않는다.
- 환자 본인, 가족, 과거력의 범위를 유지한다. 다른 약의 용량을 수면제 용량으로 옮기지 않는다.
- 새 답변 이후 이미 확인된 내용을 다시 판단하고, 동일한 단일 신체진찰을 중복 요청하지 않는다.
- 초기 진단을 고정하지 않는다. 새 관찰이 있고 진단이 불확실할 때만 제한적으로 Doctor 재평가를 수행한다.
- 안정 환자에게 진단 설명, 시간 범위가 있는 다음 단계, 악화 시 행동을 실제 SAY로 전달한다. 응급 의뢰는 지연시키지 않는다.
- 검사 계획과 시행된 검사 결과를 구분한다. 예선 SOAP의 `O.tests`는 비어 있어야 한다.

## 실패 유형 A–T와 이번 범위

| 유형 | 문제 | 처리 및 증거 |
|---|---|---|
| A | 물어보기만 했는데 확인 완료로 처리 | `topic_answered`와 `topic_attempted` 분리; unknown 회귀검사 |
| B | 가족 소견을 환자 소견으로 사용 | 기존 evidence scope를 문진 완료 판단에도 적용 |
| C | 부정·불확실성을 양성으로 사용 | 기존 assertion/negation 경로 유지; 불확실 절 제외 |
| D | 한국어 일반 약명만으로 구체적 약 이름 확인 | 수면제와 실제 성분명을 구분 |
| E | 다른 약의 숫자를 용량으로 연결 | 동일 절의 약물과 용량 연결; 쉼표 절 경계 |
| F | 시작 시점·체중 변화 누락 | 관련 프로필의 문진 종료 전 확인; 명시적 kg 변화만 계산 |
| G | 부모 한 명 키로 부모 키 수집 완료 | 아버지와 어머니 각각의 실제 수치 요구 |
| H | 연간 성장 속도 질문의 단답 수치 손실 | 명시적 1년 질문의 cm 단답만 기간 상속 |
| I | 답변에 포함된 다른 정보를 다시 질문 | 각 후속 질문 직전에 새 state로 재확인 |
| J | 동등한 신체진찰 반복 | 해부 부위와 시행 동작이 일치하는 단일 진찰만 중복 제거 |
| K | 새 정보 이후 진단 검토 없음 | 불확실하고 새 관찰이 있을 때 최대 두 번의 후속 라운드 |
| L | 같은 질환의 중복 등록을 모호한 별칭으로 거절 | 정확히 같은 canonical name의 단일 core identity만 통합 |
| M | 다른 질환이 공유하는 별칭을 임의 확정 | 거절 유지; 진짜 모호성 회귀검사 |
| N | Doctor 실패 시 객관적 증거 손실 | 실제 진찰·문진 관찰을 최종 근거 fallback에 유지 |
| O | 재시도에서 같은 동작 중복 실행 | PROVIDER_UNAVAILABLE도 동일 request_id 재시도 |
| P | 기록에는 교육이 있지만 환자에게 말하지 않음 | 실제 성공한 closing SAY를 교육 항목에 기록 |
| Q | 추적 시점·악화 시 행동 설명 부족 | 안정 환자 closing을 3회로 확대; 기존 프로필 계획 사용 |
| R | 질문 증가로 종료·제출 여유 소진 | 전체 목표 40턴, 기존 엔진 목표 26턴, closing 여유 예약 |
| S | 로컬 합성 평가를 공식 성능으로 오인 | 평가마다 mock/진단 재생/공식 미검증 구분 |
| T | 좁은 기존 사례군에서만 높은 진단 성능 | 외부 DDXPlus 2,000건 추가; 낮은 결과와 개선 없음 공개 |

## 서로 다른 평가군

1. **기존 예선 회귀 230건:** 기존 개발 사례이며 새 blind test가 아니다. before/after 같은 기존 드라이버를 사용한다.
2. **SDK 대화 1,150회:** 위 230개 사례 각각에 complete, unscripted unknown, exam unavailable, history unavailable, opening disclosure의 5가지 관찰 조건을 적용한다. 1,150개의 독립 질환 사례라고 주장하지 않는다. 사례 단위 60/20/20으로 먼저 나누고 변형을 같은 split에 둔다. 기존 사례 저자 노출 때문에 진정한 미노출 검증이 아니다.
3. **외부 DDXPlus 2,000건:** 원래 train/validate/test에서 1,200/400/400건, 49개 질환. 완전한 evidence-code 구성이 중복되는 행은 나이·성별·정답이 달라도 제외했다. 영어 합성 설문 관찰을 기존 state로 재생한다. 실제 한국어 문진, 검사 선택, 의사소통, triage를 평가하지 않는다. 외부 정답·중증도는 런타임에 주지 않는다.
4. **32건 closing/계획 재생과 3건 fake SDK:** 흐름·교육·계획 일관성 점검이다. scripted Doctor가 제공하는 답은 실제 모델 추론 능력의 증거가 아니다.
5. **Round M 128건:** 현재 릴리스 바인딩에 필요한 기존 회귀. historical blind v18/v19와 별개이며 해당 reference-only 자료를 새 평가로 실행하지 않는다.

전체 실행 전 데이터와 split을 고정했다. 외부 before 집계 결과가 최종 코드 동결 전에 노출되었으므로 완전히 독립적인 맹검 연구라고 부르지 않는다. holdout 개별 오답에 맞춘 진단 규칙·정답 테이블은 추가하지 않았다.

## SDK 평가 지표의 정확한 한계

정보수집 proxy는 scripted answer key 중 얻은 비율이고, 임상적으로 충분한 병력의 독립 심사가 아니다. 불필요한 기존 answer key를 모두 묻는 것이 최선이라는 뜻도 아니다. 진단 proxy는 scripted Doctor가 정답을 주지 않을 때의 최종 엔진 fallback 정확도다. 검사·추적 proxy는 계획의 존재와 기간 표식, 의사소통 proxy는 실제 closing·기간 표식·교육 기록을 검사한다. 실제 발언이 환자에게 명료한지, 계획이 질환마다 적절한지는 별도 검토가 필요하다. 안전 proxy의 critical flag는 참고용이며 정식 triage 정답이 아니다. 효율 proxy는 40턴/16 Doctor 요청 이내라는 로컬 기준이다.

따라서 여섯 proxy의 가중치를 공식 배점에 맞췄어도 공식 점수로 환산하거나 공식 45.84와 직접 비교할 수 없다. fake SDK usage 상수와 병렬 평가의 벽시계 시간은 실제 모델 토큰·지연·비용이 아니다.

초기 before SDK trace는 bilingual display label 때문에 Top1 집계가 잘못되었다. 저장된 primary 출력에 동일한 평가 전용 catalog identity comparator를 적용해 다시 계산했다. 정답은 바꾸지 않았다. before trace에는 differential 이름과 dangerous-primary 필드가 없어서, Top3/Top5의 기존 원시 결과를 사용하고 dangerous false primary before 값은 미측정으로 둔다. 이 차이를 숨기지 않는다.

## 재현

키를 설정하지 않는 로컬 명령:

```bash
python -m pytest tests -q
python scripts/evaluate_preliminary_benchmark.py --workers 2 --gate --output /tmp/preliminary.json
python scripts/evaluate_clinical_quality.py --protocol evaluation/clinical_quality_v36_protocol.json --split all --workers 3 --output /tmp/sdk-stress.json
python scripts/evaluate_external_ddxplus.py --cohort evaluation/external_ddxplus_v36 --split all --workers 2 --output /tmp/ddxplus.json
python scripts/evaluate_official_fixture_efficiency.py --output /tmp/fixtures.json
python scripts/evaluate_rubric_proxy.py --output /tmp/closing.json
```

외부 데이터의 출처·라이선스·수정 범위는 `evaluation/external_ddxplus_v36/README.md`와 manifest에 보존했다. 해당 데이터와 정답은 제출 ZIP에 포함하지 않는다.
