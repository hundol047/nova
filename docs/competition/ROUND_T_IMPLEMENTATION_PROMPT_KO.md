# N.O.V.A. Round T — 낮은 평가 항목을 실제로 개선하는 구현 프롬프트

당신은 N.O.V.A. 오프라인 진단 파이프라인의 구현·검증 담당자다. 목표는 임의의 만점 선언이 아니라 허위 근거·과잉 진단을 줄이고 새 사례 성능을 높이는 것이다. 계획 작성에서 멈추지 말고 재현, 제한된 구현, 회귀, 새 동결 검증, 패키지 확인, commit/push까지 수행한다.

## 시작 상태와 금지사항

AGENTS.md가 있으면 먼저 읽고 CURRENT_STATUS, ROUND_S_REPAIR_REPORT_KO, ROUND_S_FOLLOWUP_KO를 읽는다. 실제 원격 상태를 fetch하고 브랜치와 전체 SHA를 기록한다. 기준 실행 runtime은 `95d465b0f01023148d60ff02667596bf22c19b4a`, 로컬 기록 HEAD는 `8d73c2f509159179b97954f61ddc7c6be99d7608`, 공개 S runtime은 `ed5a5e4131a04e37ca15559334794f5f817c2b35`다. main/원본 사용자 checkout을 보존하고 별도 Round T 브랜치에서 작업한다.

기존 정답·분모·scorer·simulator 응답·테스트 단언을 바꾸지 않는다. S를 포함해 읽은 사례는 개발 자료다. 외부 LLM/API 키 요청, 모델 다운로드·교체·훈련, 공식 규격 추측, blind v18/v19 평가·튜닝은 하지 않는다. 사용 가능한 공식 연결이 이미 있는지는 값 노출 없이 확인하며, 없으면 미검증으로 남긴다. 질환 수를 무작정 늘리지 않는다.

## 작업 순서

1. **주체·시간 범위 (P0):** 가족/타인의 bare symptom이 환자 현재 증상이 되는 경로를 수정한다. assertion_status의 기존 cue와 diagnosis mention 구조를 재사용한다. 원문·source·span·experiencer·temporality를 보존하는 최소 clause view를 만들고, 환자 현재 증상/과거 위험/가족력을 분리한다. chief complaint, 질문 답변, aliases/canonical, 후보·scoring·SOAP에서 동일 범위를 사용한다. 명시적인 가족→본인, 과거→현재 전환을 보존한다. 모호한 주어를 임의로 환자라고 확정하지 않는다.
2. **가능 여부·관계 (P0):** `Passing urine stings.`와 `I pass urine in small amounts.`를 unable to pass urine로 매칭하지 않는다. 정상 배뇨/통증/곤란/불능/불확실은 별개다. 직접·alias·canonical 경로를 함께 고친다. 기존 실제 요폐 양성은 보존한다. dysuria는 이미 alias에 있으므로 전체 routing→Top150→Top25→active에서 누락 지점을 추적해 bounded 개념 전달만 보강한다.
3. **근거 부족과 최종 명명 (P1):** 하나의 비특이적 측정 소견만으로 원인 질환을 확정하지 않는다. 위험 평가와 구체적인 진단 선택을 분리한다. 정보 고갈·검사 불가·EXAM 거절은 제외 근거가 아니다. 실제 예선 프로토콜이 지원하는 미분화/working diagnosis/불확실성 표현을 사용하고 SOAP·metadata·진료 계획을 일치시킨다. 위험 vital+증상에 대한 긴급 계획은 진단을 보류해도 보존한다.
4. **검색·재순위 (P1):** 기존 @150/Weighted RRF/Top25 예산을 유지한다. dangerous/urgency 보너스와 안전 재삽입을 진단 evidence 순위에서 분리하는 변경은 독립 ablation으로 검증한다. 위험 후보는 안전 추적에 남기되 이름/위험성만으로 진단 순위를 올리지 않는다. vocab/alias/질문 표현의 확인된 누락만 bounded expansion으로 고친다. 손실마다 retrieval rank, rerank evidence, 경쟁 후보를 남긴다.
5. **행동 효율 (P1):** 실제 후보를 구별하지 못하는 반복 질문/EXAM 원인을 trace로 확인한다. attempted/unknown/rejected/unavailable/negative를 유지하며, 가능한 bedside EXAM은 사용한다. 예선 TEST 금지. 정보 없는 답변 뒤 같은 기전 질문만 반복하지 않는다. 해부학이 필요한 질문은 관찰된 정보 또는 적절한 명확화에 근거해야 한다.
6. **임상 깊이 (P2):** 증상 목록 확대보다 기존 metadata를 정확히 활용한다. 새 임상 사실을 추가할 경우 권위 있는 출처와 필드별 provenance를 기록한다. 근거 없는 Tier-2 프로필을 만들지 않는다. 이번 범위에서 실제로 심화한 수와 미해결 수를 분리한다.

## 테스트와 완료 조건

먼저 최소 대조쌍과 실패 사례를 재현한 뒤 의미 있는 회귀 테스트를 추가한다. 가족/본인/다른 사람, 과거/현재, 복수 절, EN/KO, bare symptom/문서 진단, 배뇨 통증/불능, 불확실·부정, 정보 부족·EXAM 거절·위험 vital를 포함한다. 함숫값만 아니라 후보·support·최종 진단·SOAP·plan 전체 경로를 확인한다.

수정 중 S/P/Q/R/예선230/이전 acceptance를 개발 회귀로 사용할 수 있다. 정상 대조군, 위험 mimics, 관찰된 양성과 이후 부정의 상충을 함께 확인한다. 최종 코드가 준비되면 새 합성 사례와 채점·행동 계약을 실행 전에 동결/hash한다. 기준선과 최종 코드에 동일하게 적용하고 결과 이후 runtime을 튜닝하지 않는다. 작성자는 구현/기존 실패를 보았으므로 독립 임상 검증이라고 표현하지 않는다.

전체 tests/, 동일 조건 예선 및 TEST 허용 개발 회귀, 새 사례, 제출 mirrors byte sync, 격리 build/ZIP audit/mock 실행을 실제 FINAL_REASONING_SHA에 묶는다. 이전 기록을 최신 실행인 것처럼 재사용하지 않는다. 구체적 기준: 새 위험 누락 0, 새 scored 오답 0을 우선하며, 허위 가족 증상·capability 근거 0, 규칙 위반/상한 초과 0, 거절/미확인의 음성 변환 0을 검사한다. 목표 미달은 숨기지 않고 case별 원인과 실제 수치를 보고한다.

출력: 변경 대응표, 동일 조건 성능/위험 누락/과잉 진단/턴/중복/미해결 대안 표, 검색·재순위 손실 분석, 새 검증 한계, 테스트 pass/fail/skip, package/runtime hash, 공개 branch/SHA, 구현/새 사례/패키지/실제 모델/공식 API의 별도 판정. 점수를 높이려고 미검증 항목을 통과로 바꾸지 않는다. 공개 소스·보고서 게시와 제한된 상세 실행 기록/ZIP 공개는 구분한다.

## 실행 중 발견된 차단 사유와 검증 구분 (추가 기록)

첫 동결 후보 `b8fe0c6`의 새 T 사례에서 실제 위험 질환 회귀가 발견되었다. 이 후보의 통과 선언을 취소하고, 읽은 32개 T 사례를 개발 데이터로 전환했다. `evaluation/frozen_validation_round_t_usage.json`에 사용 이력을 별도로 남겼고 원래 fixture·정답·채점은 보존했다. 원인 수정 뒤 추가 12개 confirmation 사례를 실행 전에 동결했다. 최종 보고서는 초기 실패, 개발 재실행, 추가 미사용 confirmation을 섞어 평균내거나 독립 검증으로 표현하지 않는다. 초기 confirmation12와 이어진 final-probe8에서도 결함을 발견해 각각 개발로 전환했다. 마지막 grammar 양성 회귀 교정 후 runtime 761fcda에서 postfreeze12를 실행하며, 이 마지막 결과에 맞춘 runtime 수정은 하지 않는다. 원래 fixture·정답·분모·hash는 모두 보존한다.
