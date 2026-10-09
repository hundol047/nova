# Round R 이후 남은 수정 작업서

기준 원격 runtime `cf31e011244a9f5340ea36c05a723dc1d11177aa`, v23. 실제 실행 로컬 `18b994984d0e22c1ee15a3e9ffcc125d5056b46b`과 전체 Git tree가 같다. 이 문서는 미구현 항목이다. 현재 새 검증 결과를 본 뒤 추가 튜닝하지 않았으며 아래 사례는 다음 작업에서 개발 회귀로 취급한다. 정답/분모/시뮬레이터를 바꿔 통과시키지 않는다. 최종 보고서와 raw trace를 함께 읽는다.

## 1. P0: 자세·유발 관계와 부정된 목록의 범위

위치: `nova_agent/matching.py:302–322,437–532`, `state.py:64–102`, `final_decision.py:144–219`.

재현 입력: `I briefly blacked out while seated reading. I was not frightened, hot, or standing up.`
현재 `feature_present('lightheadedness on standing up', [text], scrub_negated_spans=True)` → True. NewR18 전체 실행에서 primary orthostatic_hypotension, score1.5. HR39와 이후 `No standing or pain trigger.`는 기립성 양성 근거가 아니다.

수정 명세:

1. 진단 assertion의 절 경계/원문 span 처리와 matching의 qualifier 보호 패턴을 재사용한다. 부정 cue가 목록의 세 항목 모두를 지배하는 경우 각각 NEGATED로 유지한다. comma를 만났다는 이유만으로 마지막 `standing up`을 양성으로 풀지 않는다.
2. 관계형 feature에는 증상과 유발/시간 관계의 실제 연결이 있어야 한다. 어지러움이나 실신과 멀리 떨어진 standing 토큰만으로 `lightheadedness on standing up`을 만들지 않는다. 기존 dysuria 수정처럼 범위를 제한하고 전체 fuzzy threshold를 일괄 올리지 않는다.
3. leader/alternative 모두 같은 positive evidence·contradiction 조건을 통과해야 한다. benign label이라고 단 하나의 불완전한 관계를 확정 근거로 허용하지 않는다. observed HR 하나로 arrhythmia subtype를 명명하는 우회는 금지한다.
4. counterexample에서 unsupported posture support가 없어지고, 직접 명시된 “어지러움이 일어설 때 발생하고 누우면 호전” 대조군의 매칭은 유지돼야 한다. sitting 당시 실신만 보고된 경우 기립성 병인을 새로 만들지 않는다.

추가 검사: no A/B/or C; A present but B absent; standing without lightheadedness; near-faint vs blackout; EN/KO 자세 표현; alias/direct 두 경로; 전체 엔진 support와 wire A/P. 완료: NewR18의 허위 support 0, subtype 추정 0, 일반 orthostatic/vasovagal 대조군 새 오답 0.

## 2. P0: 위험 관찰을 최종 label과 독립적으로 disposition에 보존

위치: `competition/adapter.py:100,109,248`, `nova_agent/soap.py:265–326`, `final_decision.py:196`, `uncertainty.py`.

현재 NewR18은 unresolved cardiac_arrhythmia와 pulse<50를 보유하면서 conservative care/outpatient를 생성한다. NewR12는 generic headache 위험 대안 때문에 unknown→응급 계획으로 기울어지는 반대 문제도 있다.

명세: safety tracking을 진단 순위와 분리하되 **실제 관찰된 위험 신호와 그 미해결 상태**를 공통 disposition 입력으로 사용한다. 위험 후보가 목록에 있다는 사실만으로 모두 응급 처리하거나, benign primary라는 사실만으로 위험을 지우지 않는다. EXAM unknown/rejected는 배제 근거가 아니다. 기존 지원되는 SOAP/설명 필드에서 원인 미확정·남은 위험을 표시하고 예선 TEST를 요구하며 무한 대기하지 않는다. 검사 예정은 실제 검사 결과와 분리한다.

새 임상 규칙은 공식 지침 provenance를 남긴다. 현재 측정 rate threshold를 subtype 확진 threshold로 전환하지 않는다. `SUPPORTED`/`INSUFFICIENT_INFORMATION`이 서로 다른 축이면 의미를 명시하고 같은 selected_id·observation snapshot을 사용한다. CompletionReason는 action 소진이지 clinical exclusion이 아님을 유지한다.

완료: 서맥+설명되지 않은 실신, 빈맥+presyncope, 정상 pulse의 명확한 vasovagal, 양성 두통, 모든 EXAM 거절 대조군에서 wire 설명·SOAP A/P·metadata가 일관됨. 응급 과소/과잉 판단은 별도 집계하고 라벨 정확도로 숨기지 않는다.

## 3. P1: unknown/거절 응답을 임상 내용으로 만들지 않기

위치: `state.py:171,458,571,721`, `differential.py:517–577`, `resolution.py:148`, `soap.py:131`.

재현 `I cannot tell you that.`를 onset/medication/family_history 답으로 입력한다. 현재 unknown_findings는 비고 action은 observed로 취급되며, `family history of I cannot tell you that`가 ACS generic family risk 근거가 된다.

명세: 내용 없는 epistemic/응답 거절 표현을 UNKNOWN/REJECTED로 분류하되 `I cannot lift my arm` 같은 실제 기능 장애는 임상 내용이다. mixed 답의 알려진 절은 보존하고 알 수 없는 속성만 unknown으로 둔다. family risk는 관계만 보고 가산하지 말고 **실제로 보고된 가족의 질환/위험 내용**을 요구한다. 가족 정보 자체는 원문에 유지한다. 여러 모듈의 unknown 분류를 공통 helper에 위임하되 대규모 state refactor는 불필요하다.

관찰한 unknown은 음성이 아니며 약명·알레르기·통증 modifier가 되면 안 된다. `workup_coverage`에서 mapped bedside EXAM을 discriminator에서만 얻는 경우도 observed/pending/rejected/unknown 중 하나에 표시한다. 단순 skipped objective field가 되어선 안 된다.

검사: unknown EN/KO, 실제 arm weakness, 약물명+용량 모름, 부정+긍정 혼합, 가족 MI 긍정/부정/모름, EXAM 거절→후속 실제 측정. 완료: 거짓 risk/medication/allergy 0; 원문 보존; 유한 턴 종료; known-risk 대조군 유지.

## 4. P1: 전해질·부정맥의 초기 약한 후보에서 얻을 수 있는 관찰

위치: `history_followup.py:16`, `missing_info.py`, `action_selector.py`, `matching.py`, `final_decision.py`.

현재 followup은 top3와 supporting 2개에 의존한다. NewR18에서 cardiac_arrhythmia의 measured pulse 하나는 유지되지만 LOC 확인 문항이 추가되지 않는 경로가 있다. 상세 질문 추가만으로 초기 회복을 보장하지 못한다. ValP12/Fresh05도 오답이다.

실제 관찰과 missing evidence를 바탕으로 다음 행동의 구별 가치를 판단한다. 정답 질환이 이미 높은 순위여야만 그 질환을 구별하는 질문을 허용하는 순환을 줄이되, 약 하나/weakness 하나로 모든 환자에게 전해질 문항을 강제하지 않는다. 진단 가중치 상향보다 실제 medication change, 손실/섭취, renal/dialysis, 의식소실 관찰을 먼저 수집한다. 질문 선택 utility와 탈락 이유를 trace로 남긴다.

고정 개발 대조군: electrolyte, DKA/hypoglycemia/hyperthyroidism, gastroenteritis/dehydration, panic, vasovagal, common infection. source 관찰만으로 구별 불가하면 unknown 및 필요한 추가 정보로 끝낸다. Na/K/ECG를 추정하지 않는다. 정확도뿐 아니라 현재 늘어난 턴/불필요 EXAM도 전후 비교한다.

## 5. P1: 일반 질환 표현과 기존 위험 누락

NewR12 `Dull pressing bilateral headache` → KB `bilateral band-like pressure` 미매칭. 표현·관계에 한정된 개념 정규화를 검토하고 일반 headache 하나를 특이 근거로 확대하지 않는다. 새 표현은 임상 출처와 positive/negative 대조군을 갖춰야 한다.

RoundM096/ValO11 TEST 경로는 여전히 critical miss다. `artifacts/round_r/final/round_m_verified/traces/traces.tar.xz`와 `val_o11.json`을 시작점으로 기존 simulator의 bare No와 initial 관찰 충돌을 구별한다. 원문과 실제 관찰을 기준으로 source conflict 해결이 필요하며 old case-specific pair를 넣지 않는다. ValP08/21은 먼저 명칭/계층 차이와 실제 evidence mismatch를 분리한다. scorer 완화로 얻은 점수를 runtime 향상으로 보고하지 않는다.

## 6. 평가 도구는 별도 변경

- 현재 Round R 정답·제외·19개 계약·critical 분모를 사후 수정하지 않는다. 다음 버전에서 NewR18과 같은 unsupported benign reasoning 및 disposition을 검출하는 독립 의미 검사 추가.
- source span/assertion/experiencer를 SOAP A의 supporting/contradictory까지 검사한다. S/O 문자열 보존 100%와 분리.
- 위험 대안 지표는 실제 selected_id 제외로 새 이름/버전 부여. unknown reply와 실제 음성을 구분하는 simulator 개선은 별도 비교.
- critical alias 누락은 별도 명칭 audit로 고치고 이전과 분모가 바뀐 수치를 같은 성능처럼 비교하지 않는다.
- 다음 미사용 사례는 구현·회귀 완료 후 실행 전에 작성/동결/hash. 작성자의 노출을 밝히며 임상적으로 모호한 사례는 사전 행동 계약으로 분리. 결과를 본 뒤 runtime을 수정하면 그 세트는 개발로 전환하고 새 검증이 필요하다.

## 7. 완료와 패키지 기준

필수 재현 + 전체 tests + 예선230 + P/Q/이전 검수 + TEST8세트/M 및 기존 critical 개별회귀 + 새 미사용 검증. 정답·분모·scorer 동일, 모든 새 오답/위험 miss/과잉 명명/턴 증가를 기록한다. 정확도 목표 숫자를 맞추려고 exclusion을 늘리지 않는다.

새 runtime SHA를 먼저 고정하고 별도 worktree에서 mirror/ZIP 빌드, byte sync, audit, fresh mock을 실행한다. 다음 local verification 버전을 쓰고 stale runtime hash를 복사하지 않는다. 실제 LLM·공식 API가 없으면 미검증으로 종료하며 키/모델/가상 공식 schema를 요구하지 않는다. blind v18/v19 실행 금지. main 및 사용자 변경 보존.
