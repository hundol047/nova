# Round T 남은 수정 작업서 — 확인된 결함과 수용 기준

검토 runtime: `761fcda7f4f5b6c58b0e0b6e8b77047b37301782`. 이 문서의 T32/confirmation12/probe8은 이미 개발 자료이며, 마지막 postfreeze12도 다음 구현부터 개발 자료다. 새 검증으로 다시 주장하지 않는다. 임상 검증·공식 API·실제 모델은 미검증이다.

## 1. P0: 근거가 약한 최종 병명과 선택적 증상 부재의 과도한 영향

위치: `nova_agent/final_decision.py`, `support_problems` / `decide_final`; `nova_agent/differential.py`, `_score_disease`의 `generic_symptom_penalty` / `_soft_saturate`; `nova_agent/history_followup.py`; `evaluation/preliminary_driver.py`의 기본 응답은 분석만 한다.

재현 A: `RoundI_enzyme_sparse` 예선에서는 lipase를 얻을 수 없다. 관찰된 양성 근거는 `epigastric pain radiating to back`이다. S에서는 pancreatitis를 출력했으나 T에서는 추가 질문 `associated_symptoms:nausea`에 기본 "No"가 들어가 1.5→0.3으로 낮아지고, `pain radiates to back` 하나뿐인 aortic dissection(1.25)을 최종 출력한다. 실제 원인 비교에서 위험도 가산점을 복구하면 이전 질문 순서·정답이 돌아온다. 해결책으로 위험도 가산점을 되살리지 않는다. 평가의 기본 No와 실제로 관찰한 임상 음성 소견의 문제를 구분한다.

재현 B (마지막 미사용 검사): PostT_07의 "I feel vague fluttering but cannot say when it happens ..."와 실제 HR48에서 `cardiac_arrhythmia`, support `irregular heartbeat`, `pulse rate below 50`을 제출한다. `lay_language.py:67`의 범용 fluttering→irregular heartbeat가 주관적인 느낌을 관찰된 리듬처럼 승격한다. 맥박 이상은 실제 소견이고 원인/리듬은 미확정이다. 미분화 행동 계약 FAIL이며 이를 곧바로 확진 부정맥이라고 표현하면 안 된다.

재현 C: PostT_08의 "I have been taking a water tablet and have felt drained after poor meals. I cannot describe any other symptom or recall the tablet name." → `gerd`, support `worse after meals`, completion supported. `matching.py:469–613`의 관계 단어 제외/부분 일치와 `lay_language.py:151`의 식사 별칭이 실제 증상의 식후 악화를 보존하지 못한다. 식사와 증상 악화의 관계가 없는데 GERD의 양성 근거를 만든다. baseline과 final 모두 실패이며 새 결과 확인 후 코드를 수정하지 않았다.

완료한 이전 사례: ConfirmT09/FinalT07의 가래 기침은 객혈 허위 근거를 더 이상 만들지 않고, 단일 productive cough의 pneumonia 명명도 제한했다. 이 과거 재현을 남은 미해결 사항처럼 보고하지 않는다. 다만 다른 비특이 객관 소견이 원인 진단까지 지지하는 경로(NewT30 등)는 실제 최종 trace를 기준으로 별도 확인해야 한다.

동작 명세:
- `lay_language.py:67`의 일반 fluttering은 명시적인 심장/맥박 대상이 있으면 palpitations 같은 주관 증상으로 한정한다. 실제 irregular/uneven rhythm/pulse와 현재 문서 진단은 별도다. 객관 소견 없이 불규칙 리듬을 생성하지 않는다. 정상/느린 맥박, 불안, 가족의 fluttering, 현재 불규칙 맥박 EXAM을 대조군으로 사용한다.
- `matching._protected_qualifier`를 재사용해 식사 전후라는 시간과 특정 증상이 악화된다는 술어 관계를 요구한다. 식사 부족/식사 후 약 복용/과거 식사 습관은 GERD support가 아니다. 실제 heartburn/acid regurgitation worsening after eating은 보존한다. 별칭에서 qualifier를 우회하는 경로도 동일 대조쌍으로 검사한다.
- 양성 관찰, 질환 위험 요인, 비특이 중증도, 선택적 동반 증상 부재, 질환에 특이적인 반증을 구분한다. 실제 양성과 충돌하는 진술·객관적 반증은 약화하지 않는다.
- 음성 소견이나 낮은 경쟁자 점수가 다른 질환의 양성 근거를 생성하지 않는다. dangerous 여부와 무관하게 특정 병명을 명명할 근거가 부족하면 기존 unknown 종료를 사용한다.
- 호흡기 증상 하나, 혈압/맥박 이상 하나만으로 원인 질환을 확정하지 않는다. 안전 조치·긴급 계획은 계속 가능해야 한다.
- 특정 질환 ID/사례 ID 우대나 정답 강제, generic penalty를 임의의 작은 상수로 줄여 점수 맞추기, TEST가 없으면 종료 금지 같은 규칙을 넣지 않는다.

회귀 대조군: 실제 ACS/PE/뇌졸중의 여러 수렴하는 관찰, 문서상 현재 확진, 증상만으로 합리적인 common working diagnosis, 음성 검사 결과의 실제 반증, 정보 부족, 내분비·감염·출혈·양성 원인 간 경쟁. 새 발화에서 원인 불명 중증 상태와 원인 지지 상태를 최소 대조쌍으로 재현한다.

완료 기준: 기존 scorer/기본 응답을 그대로 두고 모든 새 위험 누락·과잉 진단을 사례별 공개한다. 미분화 종료가 원래 라벨과 다른 경우 정확도 손실과 임상 모호성을 각각 기록한다. 전체 정확도만으로 안전 통과를 선언하지 않는다.

## 1b. P0: 실제 회귀 — 악화 방향을 호전으로 뒤집는 근거

위치: `state.py:575` `_absorb_answer`, `matching.py:424,469,590` 관계/partial matching, `lay_language.py` 별칭, `final_decision.py:148`.

현재 ValP29 trace: aggravating 질문에 `after big meals and lying down`을 받는다. 상태는 원문과 `worse with after big meals and lying down`을 함께 보존한다. 그러나 기립성 저혈압에 `improves with sitting or lying down`이 가산되고 최종 제출된다. 원래 정답 GERD가 S에서는 맞았으나 T에서는 틀린다. 이것은 계층 이름 불일치가 아니라 실제 방향/관계 오류다. 해당 trace의 `no breathlessness, no leg swelling, sour taste`에서 sour taste가 부정으로 처리되는 것도 보이지만, 명시적 긍정 cue 없는 comma 나열의 모호성과 별도로 보고한다.

수정 명세: 질문의 aggravating/relieving 관찰 맥락을 positive/negative와 별도 관계로 유지하고 `improves/worse`는 부분 매칭에서 생략 가능한 단어로 보지 않는다. 현재 `_protected_qualifier`와 source/span 구조를 활용해 행동·증상·방향이 같은 술어에 속하는지 검사한다. 원문을 임의로 고치거나 기본 응답을 바꾸지 않는다. aggravating에 lying down, relieving에 lying down, worsening after standing, family posture history, no posture effect 최소 대조쌍을 추가한다. 실제 기립 시 어지럼+측정된 자세 혈압 변화 대조군은 보존한다.

별도 ValP17: 실제 HR38+실신에서 ECG 없이 부정맥 원인 병명을 보류하여 scored 오답이 된다. 실제 최종 SOAP는 heart_rate=38, syncope를 보존하고 즉시 응급 평가 계획을 유지했다. 다만 추가검사 안내가 순위1 sepsis 항목을 따라가 ECG를 누락한 상태이므로, 미분화 final decision에서도 실제 위험 기전에 필요한 검사/재평가 안내를 별도 추적해야 한다. 점수를 위해 rate-only 원인 명명을 복구하지 않는다. 기존 라벨과 근거 충분성의 차이를 분리한다.

## 2. P1: 아직 약한 표현·행동 연결

위치: `clinical_concepts.py:canonical_findings_for`, `chief_complaint.py`, `clinical_presentation.py`, `missing_info.py`, `clinical_concepts.py:bedside_exam_for_feature`.

`ConfirmT_07`의 "rolled over ... room spun ... half a minute ... turn that way"가 실제 회전성/체위성 증상으로 충분히 정규화되지 않는다. 얻은 support는 `no hearing loss`뿐이고 unknown으로 끝난다. fixture의 `dix_hallpike` 키는 현재 EXAM catalog의 실행 가능한 검사 키로 연결되지 않아 얻지 못했다. 이 검사가 시행됐다고 간주하면 안 된다. 주어진 정보만으로 확진을 요구하지 않는다.

수정 명세: 기존 증상·자세 관계 개념과 source/span을 이용해 관계를 보존하는 제한된 표현 정규화를 만든다. 단어 "turn" 또는 "spin"만으로 BPPV를 우대하지 않는다. 가능한 로컬 EXAM 매핑과 별도 프로토콜 미확인 검사를 구분한다. 새 공식 검사 이름을 추측하지 않는다. fixture 지원되지 않는 키는 평가 도구의 별도 이슈로 기록하고 이번 결과를 수정하지 않는다.

대조군: 계속되는 현훈, 실신 전 어지럼, 가족의 현훈, 체위와 무관한 증상, 새 신경학적 결손, EXAM 거절. 후속 구체적 소견 후에 후보가 복귀하는지 확인한다.

## 3. P1: 재순위 안전 보존이 진단 후보를 밀어내는 구조

위치: `retrieval_pipeline.py:lightweight_rerank`, `candidate_generator.py:_broaden_with_open_world`; 분석 도구 `scripts/audit_retrieval_stages.py`와 기존 `scripts/analyze_rerank_losses.py`.

T는 diagnostic score에서 dangerous/CRITICAL 가산점을 제거했지만 기존 safety reinjection 교체 계약은 보존했다. 최종164개 개발 proxy에서 chief-only는 evidence Top25에 있던 정답14개가 안전 교체 후 빠지고1개가 구제된다. scripted-history upper bound에서는24개가 빠지고 구제0개다. retrieval 자체 손실과 이 교체 손실을 분리한다. 이전 점수 보너스를 복구하거나 Top150을 늘려 해결하지 않는다.

수정 명세: diagnostic Top25와 safety watch 후보의 역할·예산을 명시적으로 분리하는 작은 API 설계를 먼저 검토한다. safety watch가 진단 점수·support를 갖게 해서는 안 된다. 원래 안전 보존 테스트를 삭제해 통과시키지 않는다. API 계약 전환이 필요하면 구버전 동작과 실제 새 production 경로를 모두 검증하고 차이를 공개한다. 이후 새로운 관찰이 후보를 diagnostic/active set에 다시 넣을 수 있어야 한다.

측정: 초기 chief-only / 실제 대화 후속 관찰 / 모든 scripted 답을 미리 준 upper bound를 분리한다. Top150, Top25, active, 최종 Top1을 같은 숫자로 보고하지 않는다. 입력에 truth를 넣지 않는다.

## 4. 검증과 패키지

S, P/Q/R, 기존 acceptance, M, T32, 이번 confirmation12/probe8/postfreeze12는 다음 라운드부터 개발·회귀 데이터다. 새 fixture/정답/분모/행동 기준의 해시를 실행 전에 고정하고 같은 fixture를 이전/최종 runtime에 적용한다. 작성자의 구현 노출과 임상 모호성을 공개한다. 한 번 검사한 세트에서 수정하면 이를 개발로 전환하고 새 확인 세트를 별도로 작성한다.

최종 단계: 전체 tests/ (passed/failed/skipped/deselected/미실행 구분), 230개 예선, TEST-enabled M/G/I/J, 새 사례, 제출 소스 바이트 동기화, 임시 checkout에서 빌드/ZIP 감사/독립 mock. 공식 연결과 임상 전문가 검증을 mock으로 대체하지 않는다. 새 사실은 권위 있는 출처 없이는 추가하지 않는다. 대규모 질환 프로필 생성이나 모델·학습으로 우회하지 않는다.
