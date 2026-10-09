# N.O.V.A. Round T — 주체·관계·검색·최종 근거 개선 보고서

2026-10-09. 이번 작업은 만점 선언이 아니라 Round S에서 재현된 낮은 항목을 수정하고 회귀를 측정하는 작업이다. 구현 프롬프트를 먼저 저장한 뒤 실제 코드를 변경했다. 모든 진단 결과는 **오프라인 mock / 합성 사례**이며 공식 대회·실제 모델·독립 임상 성능이 아니다.

## 검토·실행 코드

- 기준 실행 runtime: `95d465b0f01023148d60ff02667596bf22c19b4a` (Round S).
- 기준 공개 소스: `ed5a5e4131a04e37ca15559334794f5f817c2b35`, 공개 기록 HEAD `e26c1aad518c76a70460955bf6e2a70956a53ca0`.
- **FINAL_REASONING_SHA: `761fcda7f4f5b6c58b0e0b6e8b77047b37301782`**.
- 작업 브랜치 `codex/nova-round-t-repair`; 공개 소스 runtime `0b9cd87c7509e2703b877939cb3fc89c70e0741d` on `codex/nova-round-t-source-review-20261009`. runtime97개+run.py/requirements 총99개가 실행 코드와 byte-identical이며 전체 Git tree 동등성은 주장하지 않는다.
- main, 기존 Claude 브랜치, 원본 사용자 checkout을 변경하지 않았다. AGENTS.md는 발견되지 않았고 CURRENT_STATUS 및 이전 보고서를 검토했다.

Top150 / Weighted RRF / Top25, 기존 정답·분모·scorer·시뮬레이터 기본 응답은 보존했다. 신규 테스트를 추가했고 기존 테스트 단언을 약화하지 않았다. 이전 테스트의 변경은 verification schema 허용 목록에 v25를 추가한 것뿐이다. 이번에 만든 EXAM-pruning 테스트는 해당 설계가 위험 회귀를 일으켜 계약을 철회한 경위를 기록하고, 미매칭 상태에서도 bedside EXAM을 보존하는 검사로 바꿨다. 이를 기존 테스트 약화와 혼동하지 않는다.

## 문제·수정·검증 대응표

| 문제 / 재현 입력 | 수정 위치 (최종 runtime) | 변경 동작·의미 있는 검사 |
|---|---|---|
| `My father had an irregular heartbeat years ago.`가 현재 환자 부정맥 근거로 가산 | `evidence_scope.py:23–109`, `documented_diagnosis.py:241`, `state.py`, `differential.py:530` | source/span/주체/시간/assertion clause view를 보존. 가족 과거력은 기록에 남기고 환자 현재 증상 support에서 제외. 명시적 가족→본인 전환·본인 과거 위험과 임상적 3인칭 보고는 보존 |
| `Passing urine stings.` / 소량 배뇨 → inability to pass urine | `matching.py:482` capability predicate, `clinical_concepts.py:178` | 할 수 없다는 수식어가 같은 행동·대상에 적용되어야 함. 통증·소량·불확실·불능을 구분. 기존 dysuria 개념을 질환 라벨 생성 없이 전달 |
| 가족 증상으로 끝나는 나열·한국어 조사·관계 없는 부정 누출 | `matching.py:469`, `evidence_scope.py:32`, `state._absorb_answer` | 절 전체 scope를 먼저 판단하고 기존 assertion cues 재사용. raw conversation을 삭제하거나 보지 못한 정보를 생성하지 않음 |
| 혈액검사와 기침을 합쳐 객혈 support 생성 | `matching.py:424`, `_protected_qualifier` | blood는 실제 배출물/가래의 수식어 또는 내용이어야 함. blood test/pressure 언급만으로 객혈 생성 금지. 실제 피를 뱉음·가래 속 피·blood-stained 양성 대조군과 부정 대조군 검사 |
| 맥박 하나로 부정맥 원인을 명명하거나 병명 보류 시 긴급 계획도 사라짐 | `final_decision.py:102,148`, `disposition.py` | 실제 rate는 중증도 근거로 보존하되 원인 특이 소견으로 취급하지 않음. 기존 marked pulse+loss of consciousness 안전 계획 보존. 전기적 검사 결과를 추측하지 않음 |
| lone productive cough로 pneumonia 명명 | `final_decision.py:123,148` | 단일 비특이 소견 명명 제한을 dangerous 여부와 무관하게 적용. 현재 문서 진단·구체적 객관 소견은 별도로 인정 |
| 새 표현이 canonical 개념으로는 알려져 있으나 검색 query에 전달되지 않음 | `retrieval_pipeline.py:99,152` | 관찰된 기존 canonical 개념 최대12개만 추가. 최대6개 signal query, Top150 유지. family/denied 개념은 확장하지 않음 |
| 위험성 그 자체를 rerank 가산 | `retrieval_pipeline.py:225` | dangerous/CRITICAL 점수 보너스 제거. 위험 후보 안전 추적은 유지. 기존 safety reinjection의 Top25 교체 구조는 남아 있어 완전한 분리는 아님 |
| 보호자 보고가 가족력으로만 처리되어 가능한 신경 진찰을 잃음 | `clinical_presentation.py:147`, `missing_info.py:154` | 환자 양성 증상으로 귀속하지 않고 unattributed current tags를 정보 수집에만 사용. pending bedside EXAM을 addressed-workup과 구분. 표현이 안 맞는다고 EXAM을 삭제하던 새 조건은 철회 |

새 임상 프로필은 추가하지 않았다. 관찰 범위·표현 정규화·보수적 명명 정책의 근거와 한계는 `ROUND_T_PROVENANCE.md`에 기록했다. 현재 Tier-2 catalog 1,246개, enrichment 파일 83개 항목은 품질 인증 수가 아니다. catalog와 ID가 일치하는 83개를 제외한 1,163개는 이 enrichment 파일에 항목이 없다. 이것은 파일 기준 수이며 임상 깊이의 검증된 완성률이 아니다. **이번 신규 임상 심화 완료 0개**다. 기존 프로필의 임상적 충분성/출처 심사는 남아 있다.

## 실패한 중간 후보와 데이터 사용 이력

실패/중단 실행은 최종 통과 수에 합산하지 않는다.

1. `b8fe0c6`: 처음 T32 실행에서 14/18→13/18, 위험3/3→2/3. 과도한 zero-support EXAM 필터가 뇌졸중 확인 진찰을 제거했다. 이32개는 개발로 전환했다.
2. `82f26cd`: routed EXAM 보존으로 해당 사례를 회복했으나 P27의 보호자 보고에서 같은 종류의 위험 누락이 발생했다. 추가 confirmation12는6/8→7/8, 위험4/4였지만 이후 코드를 바꿨으므로 개발 자료다.
3. `9842f8d`: 별도8개 probe에서4/4→3/4, 위험2/2→1/2. 보호자 표현이 다르면 exact routing에도 잡히지 않았다. 또한 blood test와 mucus가 합쳐져 객혈 근거가 만들어졌다. 이8개 역시 개발 전환했고 EXAM 삭제 조건을 철회했다.
4. `08d9e62`: 마지막 관계 검증에서 실제 `blood in my sputum` 등의 양성 표현 보존 결함을 발견해 `761fcda`로 교정했다. 중단된 전체 검사/평가는 최종 증거로 사용하지 않는다.
5. postfreeze12는08d9e62 시점에 작성·해시했고, 양성 문법 회귀 교정 후761fcda에서 처음 실행했다. fixture/정답/분모는 그대로다. 작성자는 구현과 앞선 실패를 알고 있으므로 독립 임상 검증이 아니다. 마지막 postfreeze 결과에 따른 runtime 변경은 하지 않았다.

T32/confirmation12/probe8의 재실행과 마지막 postfreeze12를 분리해 보고한다. final probe라는 과거 파일 이름이 미사용 검증이라는 의미는 아니다. fixture manifest와 사용 이력은 evaluation/에 남긴다. Blind v18/v19 실행·튜닝·새 blind 생성은 하지 않았다.

## 결과 해석 원칙

예선에는 TEST가 없다. TEST 허용 M/G/I/J 결과를 예선 성능으로 옮겨 쓰지 않는다. 검색 chief-only, scripted history upper bound, 실제 대화 종료 단계 지표도 구분한다. scripted history upper bound는 자율적으로 얻은 정보가 아니다.

기존 evaluator는 일부 미정의 질문에 기본 No를 제공한다. 이번에 이를 바꾸지 않았다. 질문 미실시/모름/EXAM 거절/예선에서 불가와 질환 배제는 별개다. SOAP 문자열 보존·행동 계약 PASS는 의미·임상 판단 전체 PASS가 아니다. 미해결 위험 대안 수는 실제 위험 오진 수가 아니다. dangerous-name proxy 역시 전문가가 판정한 과잉 진단율이 아니다.

명칭 계층 불일치, 임상적으로 정보 부족한 예선 라벨, 지원되지 않는 scripted EXAM 키는 알고리즘 오류와 별도 기록한다. 채점 matching을 느슨하게 바꾸지 않았다.

## 마지막 새 사례의 재현된 잔여 실패

postfreeze12는 총12, 채점6, 위험3이다. 정답6/6·위험3/3은 기준선과 같고, 사전 행동 계약은31/35→33/35다. 이전 수술 뒤 요폐 과거력이 현재 요폐로 잘못 명명되던 PostT10은 미분화로 회복했다. 그러나 채점 제외 정보 부족 사례 두 개는 여전히 실패한다.

- PostT07: vague fluttering+실제HR48 → cardiac_arrhythmia, support irregular heartbeat+pulse rate below50. `lay_language.py:67`의 fluttering 별칭이 주관적 느낌과 리듬 관찰의 차이를 흐린다. 미분화 계약 FAIL. 느린 맥박 관찰은 사실이며 리듬 원인 명명 충분성은 별도다.
- PostT08: water tablet+drained after poor meals → GERD, support worse after meals. `matching.py:469–613` / 식사 별칭에서 식후 악화 관계가 생성된다. 정보 부족이며 reflux 자체의 관찰은 없다. 미분화 계약 FAIL.

두 실패는 기준선에도 있었고, 마지막 결과 확인 후 코드를 바꾸지 않았다. 정답 분모에서 제외된 사례라고 숨기지 않는다. 문자열 기반 SOAP audit는 둘 다unsupported=0이라 의미 오류를 잡지 못한다. **새 사례 전체 수락은 FAIL**이다. PostT03의 scripted `leg_exam` 키는 현 catalog에서 지원하지 않는 fixture 한계도 있다. 실제 얻은 calf swelling 정보는 chief/history에서 왔으며, 그 EXAM을 수행했다고 주장하지 않는다.

## 최종 동일 조건 비교

예선은 mock + competition retrieval, TEST 없음. 이전과 같은 scorer·분모·기본 응답이다. 첫9행은 개발/회귀이며 마지막12개만 마지막 runtime에서 처음 실행한 새 확인이다.

| 세트 | 전체/채점 | 정답 전→후 | 위험 정답 전→후 | 평균 턴 전→후 | 최대 턴 전→후 | 새 정답/새 오답 |
|---|---:|---:|---:|---:|---:|---:|
| 예선 개발 | 230/222 | 211→209/222 | 85→85/85 | 20.04→19.95 | 38→33 | 0/2 |
| P 개발 | 34/32 | 28→26/32 | 11→11/13 | 21.47→21.29 | 34→34 | 0/2 |
| Q 개발 | 48/36 | 36→35/36 | 11→11/11 | 20.77→20.65 | 35→36 | 0/1 |
| R 개발 | 24/12 | 12→12/12 | 4→4/4 | 26.88→26.79 | 37→37 | 0/0 |
| S 개발 | 24/14 | 13→14/14 | 4→4/4 | 24.46→24.58 | 35→35 | 1/0 |
| 기존 검수 개발 | 32/18 | 16→16/18 | 4→4/5 | 26.59→26.41 | 36→36 | 0/0 |
| T32 개발 전환 | 32/18 | 14→15/18 | 3→3/3 | 24.53→24.75 | 34→34 | 1/0 |
| confirmation12 개발 전환 | 12/8 | 6→7/8 | 4→4/4 | 23.83→24.33 | 31→31 | 1/0 |
| probe8 개발 전환 | 8/4 | 4→4/4 | 2→2/2 | 25.12→25.50 | 37→37 | 0/0 |
| 새 postfreeze12 | 12/6 | 6→6/6 | 3→3/3 | 24.08→23.75 | 34→32 | 0/0 |

새 scored 오답(동일 세트 비교):

- 예선 개발: PrelimKo_Abd_Pancreatitis, RoundI_enzyme_sparse
- P 개발: ValP_17, ValP_29
- Q 개발: DevQ_28

ValP17/DevQ28의 미분화는 rate-only 명명 제한의 채점 손실과 구분해 해석한다. ValP29의 악화→호전 역전, RoundI_enzyme_sparse의 선택적 증상 No 뒤 위험 대안 명명은 실제 잔여 기전이다. PrelimKo_Abd_Pancreatitis도 새 오답으로 남기며, 이를 제외하거나 정답으로 바꾸지 않았다.

### 효율·규칙·SOAP

| 세트 | 의미 중복 전→후 | 불필요 EXAM 전→후 | 미해결 위험 대안 사례 전→후 |
|---|---:|---:|---:|
| 예선 개발 | 19→18 | 309→319 | 96→91/230 |
| P 개발 | 3→3 | 58→59 | 11→12/34 |
| Q 개발 | 2→2 | 76→79 | 15→14/48 |
| R 개발 | 4→4 | 118→118 | 24→24/24 |
| S 개발 | 2→2 | 106→112 | 24→24/24 |
| 기존 검수 개발 | 1→1 | 168→167 | 32→32/32 |
| T32 개발 전환 | 1→1 | 133→150 | 32→32/32 |
| confirmation12 개발 전환 | 0→0 | 57→62 | 11→12/12 |
| probe8 개발 전환 | 0→0 | 31→42 | 7→8/8 |
| 새 postfreeze12 | 0→0 | 50→56 | 12→12/12 |

위 세트의 규칙 위반 0, 완전 동일 행동 반복 0, malformed 0, 문자열 기반 unsupported SOAP line 0. 세트 사이에 동일·유사 사례가 있으므로 합산해 독립 표본의 성능 분모로 사용하지 않는다. 전체적으로 효율 개선을 주장하지 않는다. SOAP 의미 오류는 앞서 별도 공개했다.

### TEST 허용 개발 회귀

| suite | 정답/분모 | 위험 정답/분모 | 새 오답 |
|---|---:|---:|---|
| held_out | 17/18 | 13/13 | 0 |
| generalization_v2 | 18/18 | 5/5 | 0 |
| stress | 8/8 | 5/5 | 0 |
| round_d | 6/7 | 3/3 | 0 |
| round_e | 6/7 | 5/5 | 0 |
| round_g | 12/12 | 4/4 | 0 |
| round_i | 18/20 | 8/8 | 0 |
| round_j | 51/54 | 20/20 | 0 |

M: 128전체/123채점, Top1 114→114/123, 위험 43→43/43; 새 오답 0. 평균 턴 25.50→22.55. 예선 점수와 혼합하지 않는다.
Long-tail 26개: Top1 17→17/26, Top5 20→21/26, Top10 22→23/26. Category 기반 개발 수치이며 임상 검증률이 아니다. 같은 M의 non-long-tail common/control은97/97이며 전체 common 질환 성능으로 일반화하지 않는다.

### 검색·재순위

| 입력 / 단계 | 기준선 | 최종 |
|---|---:|---:|
| chief-only / @150 | 109/164 (66.5%) | 117/164 (71.3%) |
| chief-only / 엄격 Top25 | 92/164 (56.1%) | 103/164 (62.8%) |
| chief-only / 안전 교체 전 evidence Top25 | 103/164 (62.8%) | 116/164 (70.7%) |
| scripted history upper bound / @150 | 146/164 (89.0%) | 152/164 (92.7%) |
| scripted history upper bound / 엄격 Top25 | 118/164 (72.0%) | 128/164 (78.0%) |
| scripted history upper bound / 안전 교체 전 evidence Top25 | 130/164 (79.3%) | 152/164 (92.7%) |

실제 M 대화 **종료 시점**: @150 111→116/123, 엄격 Top25 95→100/123, safety overflow 포함 96→101/123, active 122→123/123. 초기 검색 proxy와 다르다. M에서 retrieval≥90%, strict rerank≥80%, active≥95%는 달성했으나 초기 chief-only 목표와 전체 예선 회귀 기준은 미달이다.

### 테스트·패키지·판정

전체 tests/: **2,287 passed / 0 failed / 1 skipped / 0 deselected**. runtime·NCIt·release-binding의 서로 겹치지 않는 실행이다. 별도 반복한 문서/최소 대조쌍 검사는 중복 합산하지 않았다. skip은 torch training roundtrip 환경 부재다. 문서 진단 추출+실제 후보 가산10/10. static leakage scan807사례/16module/158core파일은 NO OBVIOUS LEAKAGE이며 blind 실행이 아니다. specificity audit의 reviewed 표시는 의미 정확성 보증이 아니다.

97개 root/submission runtime 바이트 일치, 임시 checkout 빌드, ZIP 감사·secret scan·validation·독립 mock PASS. 99개 runtime+launcher 파일이 공개 소스 commit과 byte-identical이다. 로컬 v25 ZIP SHA-256: `252220bb578639d3c88d0a53805de01e26d8a1871c2068cefcaafaac8573eeeb`, runtime761fcda에 연결했다. 자산 hash coverage와 별개로86개 제출 자산의 권한/저자 확인은 미해결이다.

| 판정 | 결과 |
|---|---|
| 실행한 전체 테스트 | PASS |
| 오프라인 구현 전체 수락 | **FAIL — 일부 기전 개선, 새 scored 회귀 남음** |
| 마지막 새 사례 전체 수락 | **FAIL — 6/6 진단 점수와 별개로 정보 부족2건 명명 실패** |
| 로컬 패키지 무결성·독립 mock | PASS |
| 완결된 공개 v25 배포 | 미완료 — 소스 검토 브랜치만 게시 |
| 실제 GPT-OSS / 공식 API | **미검증 / 미검증** |
| 독립 임상 검증 | **미검증** |

이전 자동 승인 검토가 상세 평가 묶음 공개를 거절한 범위를 넘어 새 trace/XML/ZIP을 게시하지 않았다. 공개 CURRENT_RELEASE는 이전 배포 기록이며 이 소스 검토 브랜치의 완결된 release binding이 아니다. 로컬 원본 기록에는 실패 후보·중단 실행·최종 실행을 분리 보존했다. main/원래 Claude 브랜치 이동·force-push는 없다.

## 남은 구조적 한계

- 일반 음성 하나가 특이적 양성의 순위를 지나치게 낮출 수 있다. `RoundI_enzyme_sparse`에서 예선 lipase는 얻지 못했고, 추가 nausea 질문의 기본 No가 원래 양성 패턴을 낮추는 경로가 재현됐다. danger 점수 보너스를 되살려 수치를 복구하지 않았다.
- 측정됐다는 사실과 원인 특이성은 다르다. rate-only 제한을 개선했지만 다른 비특이 중증도에서 원인 명명까지 가는 경로도 남았다. NewT30은 실제 저혈압/빈맥 등에서 adrenal crisis를 명명한다. 긴급 계획 보존과 특정 원인 명명의 충분성을 분리해 검토해야 한다.
- 회전성/체위성 새 표현과 실행 가능한 bedside EXAM 연결이 부족하다. 이전 ConfirmT07의 `dix_hallpike`는 catalog의 실행 가능한 키가 아니어서 실제 시행된 결과로 취급할 수 없다.
- safety reinjection이 evidence Top25를 교체하는 구조, 얕은 Tier-2 임상 깊이, 실제 대화에서의 초기 검색 손실은 남았다.
- 독립 임상 검증·실제 GPT-OSS·공식 API는 미검증이다. API 키 요청·모델 다운로드·외부 호출은 하지 않았다.

구체적 구현 위치·재현·대조군·완료 조건은 `ROUND_T_FOLLOWUP_KO.md`에 있다. 후속 작업은 이 문서에서 읽은 사례를 개발 자료로 취급해야 한다.
