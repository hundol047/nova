# Round S 이후 수정 작업서 — 새 결과를 숨기지 않는 후속 구현

## 적용 기준

실행 기준 runtime은 `95d465b0f01023148d60ff02667596bf22c19b4a`, 공개 소스 동등 커밋은 `ed5a5e4131a04e37ca15559334794f5f817c2b35`이다. 아래 줄 번호는 이 runtime 기준이다. 먼저 CURRENT_STATUS와 ROUND_S_REPAIR_REPORT_KO를 읽고 원격 HEAD·작업 트리·실제 수정 대상을 확인한다. main reset 및 기존 사용자 변경 덮어쓰기를 금지한다.

Round S 결과는 이미 읽었으므로 이후에는 개발·회귀 세트다. 이번 Round S 동결본을 소급 수정하거나 같은 결과를 미사용 검증이라고 재명명하지 않는다. 다음 구현은 별도 커밋과 새 동결 검증으로 진행한다. 외부 LLM, 모델 변경·훈련, 공식 규격 추측, blind v18/v19 사용, 정답·분모·시뮬레이터·기존 단언 변경은 범위 밖이다.

## P0-1: 가족의 일반 증상이 현재 환자의 근거로 새어 들어옴

재현: `NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1 python scripts/reproduce_round_s_remaining.py`.

입력: `I have an itchy patch on my wrist. My father had an irregular heartbeat years ago.`

실제: documented_diagnosis_ids는 빈 목록이지만, diagnosis_evidence_text와 all_findings_text(include_family=False)는 아버지의 문장을 그대로 반환한다. 초기 1위 cardiac_arrhythmia, 점수 1.25, support `irregular heartbeat`. NewS_23 전체 예선 실행은 정상 초기 활력징후와 미확인 추가 정보 상태에서도 부정맥을 제출하고 긴급 계획을 낸다. 문서 진단의 부정문 함수만 고치는 것으로 해결되지 않는다.

기대: 아버지의 과거 심박은 가족력으로 원문 보존하고, 환자 본인의 현재 irregular heartbeat 근거로 사용하지 않는다. 환자의 손목 발진은 유지한다. 이 입력만으로 특정 심장 진단이나 그 진단에서 파생된 긴급 계획을 만들지 않는다.

수정 위치: `assertion_status.py:49`의 FAMILY_CUE와 기존 FIRST_PERSON/HISTORICAL/CURRENT cue, `documented_diagnosis.py:241` diagnosis_evidence_text, `state.py:738` all_findings_text, `differential.py:531` _score_disease. `candidate_generator.py`의 chief complaint 경로와 `final_decision.py:145` support_problems도 동일한 관찰 구간을 소비하는지 확인한다.

원인: 기존 masking은 인식된 **진단명 mention**만 대상으로 한다. bare symptom은 진단 목록에 없으므로 FAMILY_CUE가 이미 있어도 필터가 작동하지 않는다. 구조화 family_history만 제외해도 chief complaint 속 가족 절은 남는다.

구현 계약:

1. 모든 임상 feature 소비 전에 작은 공통 clause/mention 투영을 적용한다. 최소 source field, 원문 구간, experiencer(PATIENT/FAMILY/OTHER/UNKNOWN), temporality, assertion을 유지한다. 진단별 기존 mention 구조와 cue를 재사용한다. 관찰되지 않은 상태를 채우지 않는다.
2. current patient evidence, patient history/risk, family risk를 서로 다른 view로 만든다. 검색은 가족력 맥락을 참고할 수 있어도 이를 현재 증상 support로 바꾸면 안 된다. 일반 증상·alias·canonical·severity·SOAP 경로가 같은 범위를 사용한다.
3. 명시적 주어 전환은 다음 절에서 반영한다. 가족 cue 하나 때문에 뒤따르는 본인 증상을 지우지 않는다. 실제 원문은 수정하지 않는다. 질환 ID별 금지 목록이나 father 단어 하나 추가로 끝내지 않는다.

테스트: 가족/본인 최소 대조쌍, 과거/현재, EN/KO, 한 문장 안의 가족→본인 전환, 진단명 없는 증상, 인용된 타인 기록, 불분명한 주어. 직접 matcher부터 후보·support·adapter 최종 SOAP까지 확인한다. 본인의 실제 현재 irregular heartbeat는 보존하고, 가족력에 따라 적절히 수집할 위험 질문은 사라지지 않아야 한다.

완료: NewS_23에서 환자의 허위 arrhythmia support 및 그 근거만으로 발생한 긴급 계획이 사라진다. 일반 질환명 masking만 통과하는 것으로 완료하지 않는다. 새로운 표현에서 같은 불변식을 확인한다.

## P0-2: 배뇨 가능 여부 수식어가 탈락해 통증을 요폐로 해석

입력 대조:

| 원문 | 현재 unable to pass urine 매칭 | 기대 |
|---|---|---|
| Passing urine stings. | true (직접 및 alias) | false; dysuria 의미는 보존 |
| I pass urine in small amounts. | true | false; 적은 양이 곧 배뇨 불능은 아님 |
| I am unable to pass urine. | true | true |

NewS_05 전체 실행: `For two days, passing urine stings, and I return to the toilet every half hour for small amounts.` → Acute Urinary Retention, support `unable to pass urine`. 실제로 이 정보를 얻지 않았다. 이는 명칭 계층 차이가 아니라 허위 근거다. 검사 미실시를 정상 결과로 바꾸는 문제와도 구분한다.

위치: `matching.py:424` _protected_qualifier, `:460` _feature_present_uncached, `:557` _head_or_pattern_missing. chief_complaint / clinical_presentation / candidate_generator의 canonical dysuria 전달, `final_decision.py:145`의 support 출처도 확인한다.

확인된 사실: 격리된 `Passing urine stings.`는 dysuria alias에도 true다. 따라서 dysuria 사전이 전혀 없다고 단정하면 안 된다. 전체 문장 routing→Top150→Top25→active에서 어느 단계가 이 의미를 누락하는지 각 점수·matched span을 남기고 그 단계만 수정한다.

구현 계약:

1. unable/cannot/difficulty/normal capability처럼 임상 의미를 바꾸는 수식어는 해당 행위와 같은 구간에서 일치해야 한다. pass urine 토큰 공통점만으로 inability를 충족시키지 않는다. 긍정·부정·불확실을 별개로 처리한다.
2. 배뇨 시 통증이라는 관계를 bounded canonical 개념으로 전달한다. 대규모 자유 query expansion, 방광염/요폐 정답별 가산, Top150 확대를 하지 않는다.
3. 성별만으로 해부학을 확정하지 않는다. 다만 관찰되지 않은 해부학에 의존하는 prostate/scrotal 질문의 우선순위는 이유를 설명할 수 있어야 한다. 필요하면 관련 해부학을 먼저 명확히 하는 질문으로 연결한다.

테스트: painless normal voiding, dysuria, small volume, true retention, trouble starting but still passing, denies inability, uncertain output, 한국어 대조쌍. ability/absence 표현을 공유하는 다른 기능(호흡·보행 등)에 대한 회귀도 검사한다. 기존 실제 요폐 정답과 긴급 소견은 보존한다.

완료: 존재하지 않는 `unable to pass urine` support가 없어지고, NewS_05 및 새로운 동형 사례의 추론 경로가 실제 관찰에 근거한다. 정확한 병명이 관찰만으로 구별되지 않으면 불확실성을 기록하며, 무조건 특정 정답을 강제하지 않는다.

## P1: 안전 후보·진단 순위·행동 효율을 분리

이번 변경 후 예선의 미해결 위험 대안이 남은 사례는 74→96/230, 새 세트는 14→24/24다. 새 세트 평균 상호작용도 20.42→24.46이다. 미해결이 곧 실제 위험 누락이라는 뜻은 아니지만, 정확도 상승만으로 무시할 수 없다.

`retrieval_pipeline.py:221` _rerank_score는 현재 dangerous 및 CRITICAL urgency 보너스를 더하며, `:254`부터 안전 후보 재삽입도 한다. 이 코드가 남아 있으므로 위험성과 진단 순위가 완전히 분리됐다고 선언하면 안 된다. 위험성 보너스 제거는 순위와 안전 추적의 분리를 먼저 설계하고 단독 ablation으로 검증한다. 위험 후보는 안전 목록에 남기되 진단 Top25 진입은 실제 증상·객관 소견·risk 관계로 설명한다. 결과를 보지 않고 전역 보너스만 지우는 수정은 금지한다.

`missing_info`, `resolution.workup_coverage`, `stop_policy`, `action_selector`에서 attempted/unknown/rejected/unavailable/excluded를 유지한다. bedside EXAM 가능 여부와 TEST 불가를 분리한다. 얻을 수 있는 최고 구별력 질문을 우선하고, 진단에 도움 없는 반복 EXAM은 줄인다. 정보 고갈로 종료할 수 있어야 하나 그것을 질환 배제로 표현해서는 안 된다. unsupported 위험 진단을 working label이라는 문구만 붙여 정당화하지 않는다.

평가: 수정 전후 동일 사례별 미해결 이유·선택하지 않은 행동의 점수·최종 support를 기록한다. 위험 누락, 불필요한 긴급 계획, 최종 충분성, 평균/최대 턴을 함께 비교한다. 예선에는 TEST를 넣지 않는다. 오래된 P의 4개 오답 및 acceptance의 2개 오답도 원인별로 분리하고 라벨 매칭을 느슨하게 바꾸지 않는다.

## P2: 새 검증과 최종 수락

수정 중에는 S를 개발 세트로 사용한다. 다음 검증은 구현자가 기존 실패를 보았다는 한계를 기록하고 별도 사례·정답·행동 계약을 실행 전에 hash로 동결한다. 이전 문장 단순 바꿔쓰기에 한정하지 않는다. 불명확한 사례를 억지로 단일 정답 처리하지 않는다. 결과를 본 뒤 코드에 손대면 그 세트는 개발 자료로 전환하고 새 검증으로 대체한다.

전체 tests/, 동일 조건 예선230/P/Q/R/S/이전 acceptance, TEST 경로 회귀/M, 최소 대조쌍·adapter SOAP, mirror byte equality, 격리 build·ZIP audit·mock 실행을 최종 runtime SHA에 묶는다. 원본을 덮어쓰는 build는 임시 worktree에서만 수행한다. 테스트 삭제/단언 완화, scorer 변경, 분모 변경으로 통과하지 않는다.

최소 수락: 기존에 맞힌 위험 사례의 새 누락 0, 위 두 허위 근거 기전 0, 새 사례에서 예선 TEST/규칙 위반/초과 턴 0, 미확인 정보의 음성·확진 변환 0, SOAP·metadata·실제 관찰 일치. 정확도·과잉 진단·효율 목표 미달은 실제 수치와 함께 FAIL/부분 완료로 보고한다. 실제 LLM·공식 인터페이스·임상 독립 검증은 근거가 없으면 미검증으로 남긴다. 임의 점수나 ‘만점’ 선언은 하지 않는다.
