# N.O.V.A. Round S — 관찰 보존·부정·위험 계획 수정 보고서

2026-10-09. 외부 LLM 없는 mock·합성 사례 검증이다. 공식 대회 점수 또는 임상 검증을 뜻하지 않는다. ‘만점’은 미리 정한 결론이 아니다.

## 코드와 검증 범위

기준선은 Round R의 로컬 runtime `18b994984d0e22c1ee15a3e9ffcc125d5056b46b`이며, 공개 `cf31e011244a9f5340ea36c05a723dc1d11177aa`와 전체 Git tree가 같다. 원격 작업 브랜치 `claude/determined-brahmagupta-wrfveb`는 시작 시 `02e56eb8e97ba0b6ce09061091d64222fee1c37a`, 공개 소스 검토 브랜치는 `8898b4351b632c10587a1e1465764541cc190a90`였다. main 및 원본 사용자 checkout을 변경하지 않았다. 저장소에서 AGENTS.md는 발견되지 않았고 CURRENT_STATUS 및 이전 P/Q/R 검토·수정 보고서를 읽었다.

새 코드·테스트·작업 명세는 별도 `codex/nova-round-s-repair` 작업 트리에서 작성했다. Top150 / Weighted RRF / Top25, 기존 사례·정답·분모·채점기·기본 시뮬레이터 응답을 유지했다. 기존 테스트 삭제나 단언 완화는 없다. 기존 테스트 변경은 현재 release schema 허용 목록의 v23/v24 추가뿐이다. 모델 다운로드·교체·학습·API 연결·blind v18/v19 실행은 하지 않았다. leakage 도구의 정적 참조 검사는 진단 평가 실행과 구분한다.

## 수정한 기전

| 문제 | 수정 위치 / 검증 방식 | 변경된 동작 |
|---|---|---|
| 부정된 나열에서 마지막 단어가 양성 근거가 됨 | `matching._strip_negated_spans_uncached`, `_protected_qualifier`; 직접/alias/canonical 최소 대조쌍 | comma-list 전체 부정 유지. 새 주어·긍정 서술어가 있으면 해당 절은 보존. 자세성 어지러움은 실제 증상과 자세 변화의 연결을 요구 |
| 실제 소견의 ‘absent’를 다음 소견까지 부정하는 cue로 처리 | `matching.explicitly_denied_in_findings`, `differential._score_phrase` | 실제 absent breath sounds와 ‘denies absent breath sounds’를 구분. 뒤따르는 tracheal deviation을 지우지 않음 |
| 모른다는 답변이 약명·알레르기·가족 위험으로 가산됨 | `state.answer_kind`, `_absorb_answer`, `all_findings_text`; `differential._score_disease` | unknown 원문은 대화/SOAP에 남기되 임상 내용으로 생성하지 않음. 알려진 약명과 모르는 용량은 구분. 가족 위험은 실제 해당 질환 내용 필요 |
| 복합 No와 실제 측정값의 충돌 | `state.record_ask`, `_absorb_answer`, `_already_reported` | AND 질문의 단순 No를 각 구성 요소의 부정으로 만들지 않음. 이미 관찰·측정된 양성과 충돌하면 그 사실을 기록 |
| 자세별 혈압이 다음 숫자에 잘못 연결됨 | `clinical_concepts._posture_bp` | 쉼표를 넘어 다음 측정값에 앞선 자세를 연결하지 않음. 혈압 하강을 추정하지 않음 |
| 실제 CTPA 결과에서 해부학적 맥락 누락 | `clinical_concepts.procedure_context_findings`, `state.objective_findings_text` | 실제 시행된 CTPA의 명확한 segmental/lobar filling defect만 기존 폐동맥 소견으로 연결. 비폐동맥·artifact·불확실·부정 결과는 제외 |
| 공통 시간 표현으로 다른 증상을 생성 | `matching._head_or_pattern_missing` | sudden onset headache가 sudden onset dyspnea/palpitations로 부분 매칭되지 않음 |
| 흔한 증상 부재의 감점이 포화된 특이 패턴을 압도 | `differential._score_disease` | 기존 generic symptom 분류를 재사용해, 관찰된 적 없는 흔한 동반 증상의 부재는 같은 증상 점수 계층에서 합산. 실제 양성과의 상충·구체적 반증·객관적 음성·명시적 reassuring 항목은 기존 강한 감점 유지. 질환 ID별 가산 없음 |
| 양성 진단명 때문에 측정된 위험 신호가 진료 계획에서 사라짐 | 새 `disposition`, `final_decision`, `history_followup`, SOAP/adapter | 실제 HR 이상+실신/전실신을 별도 안전 판단에 사용. ECG subtype를 만들지 않음. 진단 순위와 독립적인 긴급 계획을 SOAP·짧은 설명·metadata에 일치시킴 |
| 선택 진단과 근거 metadata/미분화 SOAP 불일치 | `uncertainty.assess_evidence`, `adapter`, `soap.build_soap` | 실제 제출 selected_id를 평가. working label과 확진의 의미를 분리. 미분화 상태의 누락 정보를 ‘없음’으로 표시하지 않음 |
| 객관 소견을 SAY 불가라는 이유로 EXAM까지 불가 처리 | `resolution.workup_coverage` | mapped bedside EXAM을 observed/pending/unknown/rejected로 별도 기록. 수행·거절·미확인·불가가 질환 배제로 바뀌지 않음 |

새 임상 표현/정책 근거는 `ROUND_S_CLINICAL_PROVENANCE.md`에 기록했다. 점수식·맥박 경계값은 공학적 규칙이며 검증된 확률이나 NICE의 정량 진단 기준으로 표현하지 않는다. 새 질환 프로필은 만들지 않았다.

## 개발 중 발견·수정한 회귀

중간 후보의 실패를 최종 성공 숫자에 합산하지 않는다. 원본 로그·중단 실행은 `artifacts/round_s/development/`에 남겼다.

- 초기 중간 후보: 실제 자세별 BP 해석, absent 소견/부정의 범위, 복부의 ‘분포’와 ‘퍼짐’ 혼동 때문에 기존 정답 4개가 틀렸다. 각각의 기전을 수정하고 4/4 재현했다.
- 다음 후보: `fever and chills? → No`가 실제 38.6°C 발열과 충돌해 ValP26을 단순 방광염으로 바꿨다. Boolean 답변과 관찰 충돌을 분리한 뒤 신우신염으로 회복했다.
- `ff10fe1` 후보: 예선 208/222였지만 RoundJ13을 새로 틀렸다. thunderclap/worst headache/neck stiffness가 보존돼 있었는데, 뒤늦게 받은 ‘no vomiting’의 감점이 포화 후에 적용되어 SAH 점수 2.5→1.3, meningitis 2.197에 역전됐다. 위험성 가산이나 정답 이름 규칙으로 해결하지 않았다.
- `5b15a56` 후보: 기존 단위 테스트가 ‘관찰된 양성을 나중에 부정하는 진짜 상충도 약해진다’는 경계를 잡았다. 테스트를 고치지 않고 runtime의 이 경우 감점을 원래대로 보존했다.

마지막 단위 테스트 실패 발견 때 새 세트는 **기준선만 일부 실행(22 trace, summary 없음)**했고, 수정본 실행은 아직 시작되지 않았다. 해당 출력 내용을 읽지 않고 중단했다. 이 사실과 첫 동결 철회 이유를 `development/candidate_5b15a56/reasoning_freeze.json`에 보존했다. 사례·정답·scorer는 변경하지 않았다. 최종 동결 이후 새 결과에 맞춘 수정은 금지했다.

## 평가 해석의 한계

P/Q/R, 예선230, 이전 검수32, TEST 경로 M 및 기타 개발 suite는 이미 개발에 사용한 자료다. 이들의 상승을 미사용 사례 성능이라고 부르지 않는다. 새 Round S도 작성자가 구현과 이전 실패를 읽었으므로 독립 임상 검증이 아니다.

기존 시뮬레이터는 정의되지 않은 질문에 기본 No를 줄 수 있다. 이번에는 그 응답이나 채점을 바꾸지 않았다. 무응답을 실제 부재와 구분하는 정책, 더 풍부한 임상 시뮬레이터, 전문가 검증은 별도 평가 작업이다. SOAP 문자열 보존 검사의 PASS가 모든 문장의 임상적 정확성을 증명하지 않는다. 위험 분모는 기존 `SyntheticCase.critical`을 유지하며 모든 임상적 위험 질환을 포괄하지 않는다.

`prioritize_tier2_depth.py`는 이미 사용한 개발 trace에서 434개의 Tier-2 후보를 관찰하고 50개 검토 우선순위를 계산했다. 빈도·Top150/25·active·dangerous·기존 feature 겹침·metadata 차원을 공개한다. **50개를 심화 완료했다고 선언하지 않는다. 이번 신규 심화 프로필은 0개다.** 기존 1,246개 Tier-2에 대한 임상 깊이·출처 심사는 여전히 부족하다.



## 최종 실행 결과와 판정

- FINAL_REASONING_SHA / 실제 실행: `95d465b0f01023148d60ff02667596bf22c19b4a`.
- 공개 동등 runtime: `ed5a5e4131a04e37ca15559334794f5f817c2b35`, 브랜치 `codex/nova-round-s-source-review-20261009`. 96개 runtime 파일과 run.py/requirements가 실제 실행 코드와 byte-identical이다. 상세 산출물을 제외했으므로 **전체 Git tree 동등성은 주장하지 않는다**.
- 최종 동결: 2026-10-09T06:47:47.519690Z. 동결 후 runtime 변경 없음.
- 새 S fixture SHA-256: `1e99c1ccb346d2b459103dcef5be217f5f32a83ce839e04bdabccc70cd3fc9a0`, 최초 fixture 동결 2026-10-09T05:52:27.940328Z. 동일 사례·정답·scorer로 기준선과 최종 실행.
- 모든 진단 수치는 mock. 예선은 `NOVA_COMPETITION_RETRIEVAL=1`, TEST 없음. TEST 허용 개발 suite는 별도 표기한다. workers=4는 실행 병렬도이며 모델·프로토콜·채점은 동일하다.

### 예선 경로 비교

| 세트 | 전체/채점 | 정답 전→후 | 위험 정답 전→후 | 평균 턴 전→후 | 최대 턴 전→후 | 새 정답/새 오답 |
|---|---:|---:|---:|---:|---:|---:|
| 예선 개발 | 230/222 | 203→211/222 | 85→85/85 | 20.04→20.04 | 35→38 | 8/0 |
| P 개발 | 34/32 | 28→28/32 | 11→11/13 | 20.03→21.47 | 32→34 | 0/0 |
| Q 개발 | 48/36 | 35→36/36 | 10→11/11 | 20.54→20.77 | 35→35 | 1/0 |
| 이전 검수 개발 | 32/18 | 16→16/18 | 4→4/5 | 26.69→26.59 | 36→36 | 0/0 |
| R 개발 | 24/12 | 11→12/12 | 4→4/4 | 23.42→26.88 | 33→37 | 1/0 |
| 새 S 검증 | 24/14 | 12→13/14 | 4→4/4 | 20.42→24.46 | 31→35 | 1/0 |

예선 정답은 91.4%→95.0%, 새 S는 85.7%→92.9%다. 이전 P runtime의 215/222=96.8%에는 아직 못 미친다. P 28/32와 이전 검수 16/18은 이번에 개선되지 않았다. 모든 비교에서 **채점 대상의 새 오답·새 위험 누락은 0**이다. 채점 제외 사례의 바뀐 위험 진단까지 안전하다는 뜻은 아니다.

새 정답: 예선 RoundM_026/099/101/103/104/109/116/117; Q DevQ_44; R NewR_12; S NewS_08. 전체 사례별 변화는 `artifacts/round_s/final/comparison.json`에 있다.

### 규칙·효율·SOAP

| 세트 | 의미 중복 질문 전→후 | 불필요 EXAM 전→후 | 미해결 위험 대안이 남은 사례 전→후 |
|---|---:|---:|---:|
| 예선 개발 | 18→19 | 299→309 | 74→96/230 |
| P 개발 | 2→3 | 53→58 | 11→11/34 |
| Q 개발 | 1→2 | 73→76 | 12→15/48 |
| 이전 검수 개발 | 1→1 | 167→168 | 31→32/32 |
| R 개발 | 0→4 | 51→118 | 11→24/24 |
| 새 S 검증 | 1→2 | 44→106 | 14→24/24 |

모든 위 예선 세트에서 TEST/규칙 위반/malformed/상한 초과/완전 동일 행동 반복은 0, 기존 문자열 기반 SOAP 정보 보존은 100%, unsupported line 검사는 0이다. **그러나 아래 의미 오류를 해당 SOAP 검사가 놓쳤다.** 따라서 SOAP의 임상 근거 보존 전체를 PASS로 선언하지 않는다. S의 조기 종료 heuristic flag는 1→6/24, EXAM 거절은 5→6회다. 미해결 위험 수는 배제를 만들어내지 않는 보수적 상태 표현의 영향도 받으므로 실제 위험 누락 수와 동일하지 않다. 효율 악화는 남은 문제다.

### TEST 허용 회귀 — 예선 결과와 혼합 금지

Round M 128개/123채점: 108/123→114/123, 위험 42/43→43/43. 평균 턴 25.55→25.50. 새 정답 M096/099/101/103/104/119, 새 오답 0. ValO_11은 폐렴 오답→Pulmonary Embolism 정답, 43→15턴(실제 TEST 6회)이다. 이 회복을 TEST 없는 예선 성공으로 잘못 옮겨 적지 않는다.

| 별도 suite | 정답/분모 | 위험 정답/분모 | 전후 정답 변화 |
|---|---:|---:|---|
| held_out | 17/18 | 13/13 | 동일 |
| generalization_v2 | 18/18 | 5/5 | 동일 |
| stress | 8/8 | 5/5 | 동일 |
| round_d | 6/7 | 3/3 | 동일 |
| round_e | 6/7 | 5/5 | 동일 |
| round_g | 12/12 | 4/4 | 동일 |
| round_i | 18/20 | 8/8 | 동일 |
| round_j | 51/54 | 20/20 | 동일 |

### 검색·재순위·long-tail: 일괄 개선 아님

Round M 종료 단계의 @150는 112/123(91.1%)→111/123(90.2%), **엄격 Top25는 96/123(78.0%)→95/123(77.2%)**다. 안전 overflow 포함 reranked는 97→96/123이므로 Top25와 혼용하지 않는다. active는 122/123(99.2%) 유지, 최종 Top10 118→119/123, Top5 114→117/123이다. 초기 검색 지표가 아니라 종료 시점 추적치다.

M long-tail 26개: Top1 **12→17/26(65.4%)**, Top5 **17→20/26(76.9%)**, Top10 **21→22/26(84.6%)**. retrieval 26/26, 엄격 rerank25 25/26, active 25/26 유지. 개발 category 기반이며 전체 Tier-2/독립 임상 성능이 아니다.

44개 기존 검색 proxy: chief complaint만으로 @150 **61.4%→61.4%**, 모든 scripted history를 주면 **90.9%→90.9%**. 후자는 에이전트가 자율 수집한 정보가 아니다. benchmark 출력의 `baseline a1b92c8` 차이는 오래된 비교값이며 이번 R→S 향상으로 계산하지 않는다. **검색/재순위 개선 목표는 미달이다.** 현재 `_rerank_score`의 dangerousness/urgency 보너스도 남아 있다.

## 새 검증에서 남은 실패 — 전체 수락 FAIL

사전 행동 계약은 81/87→86/87이다. R은 19/19, 이전 acceptance는 14/14 유지다. 다음 오류를 새 결과 확인 이후 runtime에 추가 튜닝하지 않았다. 재현 스크립트 `scripts/reproduce_round_s_remaining.py`, 출력 `artifacts/round_s/final/remaining_reproductions.json`, 구체적 다음 작업은 `ROUND_S_FOLLOWUP_KO.md`.

1. **P0, NewS_23: 가족의 일반 증상이 환자에게 귀속됨.** `I have an itchy patch on my wrist. My father had an irregular heartbeat years ago.` → 문서 진단 ids는 []인데 현재 환자 rank1은 cardiac_arrhythmia(1.25), support irregular heartbeat. 정상 초기 활력징후·추가 미확인 정보에서도 부정맥과 긴급 계획을 제출. `state.py:738` all_findings_text는 chief complaint를 그대로 포함하고 `documented_diagnosis.py:241`은 인식된 진단명만 가린다. 일반 증상의 experiencer/시간을 분리하지 못한다. 기대는 가족 과거력 보존과 환자 증상 support에서의 제외다. 기존 문서 진단 부정문 회귀의 PASS와 다른 기전이다.
2. **P0, NewS_05: ‘소변 볼 때 따가움’에서 ‘소변을 못 봄’을 만듦.** `Passing urine stings.` 및 `I pass urine in small amounts.`가 unable to pass urine에 true. `matching.py:424/460/557`의 qualifier/partial match 문제. 전체 예선은 Acute Urinary Retention과 해당 허위 support·긴급 계획을 제출한다. 실제 dysuria alias는 격리 검사에서 true이므로 사전 추가만으로 해결됐다고 볼 수 없다. capability 수식어와 배뇨 통증 관계를 보존하고 후보 전달 단계도 추적해야 한다.
3. **모호성/과잉 명명 검토, NewS_15:** 채점 제외 사례에서 이전 미분화→cardiac_arrhythmia로 변경. 실제 HR<50은 관찰됐고 긴급 평가 필요성 계약은 충족하나, 질환 원인/subtype는 미확정이다. 단일 pulse feature를 SUPPORTED working label로 수락하는 기준은 별도 검토 대상이다. ‘새 오답 0’ 표에서 제외되는 변화이므로 숨기지 않는다. 이것을 가족력 누출과 동일한 허위 관찰로 단정하지 않는다.

NewS_05/23에서 확인한 근거 없는 위험 명명은 **최소 2건**이며 모든 사례에 대한 독립 임상 과잉 진단율을 측정한 것은 아니다. 새 행동 계약도 모든 의미 오류를 포괄하지 못한다. P의 기존 위험 오답 2개, acceptance의 기존 위험 오답 1개는 남아 있다(서로 겹칠 수 있어 단순 합산 금지). M의 9개 남은 오답은 final ranking 7/stop heuristic 1/active 1로 분류됐고, 이는 코드 기반 휴리스틱이지 임상적 원인 확정은 아니다. 예를 들어 PUD/duodenal ulcer 계층 차이는 별도로 보존하며 scorer를 느슨하게 바꾸지 않았다.

## 테스트·패키지·공개 상태

전체 tests/: **2,208 passed / 0 failed / 1 skipped / 0 deselected / 0 미실행**. runtime 2,202 + NCIt 연구 검사 3 + release binding 3의 서로 겹치지 않는 실행이다. skip은 torch 미설치로 training roundtrip 미실행이며 모델을 다운로드하지 않았다. 경고 1개. 테스트 통과는 임상 안전성 보증이 아니다.

root/submission 96개 runtime byte sync, 원본 보존 임시 worktree build, ZIP audit/secret scan/validation, 새 디렉터리의 독립 mock 실행 PASS. run.py는 공식 연결이 없어 fail-closed. v24 ZIP SHA-256은 `91ca5e1342b2bbbcd6972cb8f76c2c7fd06eb78a33161653053340182fd116fe`, 실제 runtime 95d465b에 연결된다. 로컬 상세 검증 `artifacts/verification/local-release-95d465b-v24.json`. 임상 자산 hash coverage PASS와 별개로 permission 검증은 BLOCKED, 미해결 자산 85개다.

공개 브랜치는 **소스 검토용**이다. 이전 자동 승인 검토가 상세 평가 묶음의 공개를 거절했고, 이후 허용된 범위를 넘어 v24 ZIP/신규 trace/XML을 게시하지 않았다. 공개 CURRENT_RELEASE 포인터는 이전 값에 남으므로 이 브랜치를 완결된 v24 배포본으로 사용하면 안 된다. 로컬 v24 검증, 공개 runtime byte 일치, 실제 공식 제출 준비 여부는 다른 항목이다.

| 판정 항목 | 결과 | 근거 |
|---|---|---|
| 공학적 회귀 / 구현된 계약 | PASS | 2,208 tests, 새 채점 오답·새 위험 누락 0 |
| 오프라인 구현 전체 수락 | **FAIL / 부분 완료** | 가족 주체 누출·capability 오매칭 잔존 |
| 새 사례 전체 수락 | **FAIL** | 13/14와 86/87; 허위 근거·과잉 판단 잔존 |
| 로컬 제출 패키지 무결성·mock | PASS | sync/audit/ZIP/격리 실행, 실제 SHA 연결 |
| 완결된 v24 공개 배포 | 미완료 | 소스/보고서만 공개, 상세 배포 증거 별도 |
| 실제 GPT-OSS / 공식 API | **미검증 / 미검증** | 실제 연결·호출·공식 규격 증거 없음 |
| 독립 임상 검증 | **미검증** | 합성 사례·구현 노출 작성자 |

만점이나 공식 성능 점수로 환산할 근거가 없다. 이번에는 관찰 보존·위험 누락 일부를 개선했고, 남은 실패를 재현 가능한 다음 작업으로 분리했다.
