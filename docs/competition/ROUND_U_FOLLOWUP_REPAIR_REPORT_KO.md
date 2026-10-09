# N.O.V.A. ROUND U FOLLOW-UP REPAIR REPORT

모든 수치는 오프라인 mock LLM과 합성 개발 사례로 측정한 엔지니어링 근거이다. 공식 점수, 실제 모델 성능, 독립 임상 검증이 아니다. 기준선과 최종본에는 같은 명령, 같은 라벨·분모·채점기·시뮬레이터 응답을 썼다(`scripts/run_round_u_followup_suite.py`). 실행별 명령, SHA, runtime 파일 해시, 환경, 시작·종료 시각, exit code, 로그·결과 해시는 [ROUND_U_FOLLOWUP_VERIFICATION_SUMMARY.json](ROUND_U_FOLLOWUP_VERIFICATION_SUMMARY.json)에 있다. 사례별 비교는 `artifacts/round_u_followup/final/comparison.json`, 지정 사례의 단계별 기록은 `artifacts/round_u_followup/case_mechanisms.json`에 있다.

```
BASELINE RUNTIME SHA: c01a8b754360131bfaef17a8b29e71ab61a72330  (public codex/nova-round-u-source-review-20261009 HEAD; runtime bytes = 82cb69e)
FINAL RUNTIME SHA:    e207801ce16faf38591fc0bed2dd2d238c1c1d7a

PUBLIC BRANCH: claude/nova-round-u-followup-20261009   (새 브랜치; main·codex 검토 브랜치·원래 Claude 브랜치는 수정하지 않음)
PUBLIC HEAD:   이 보고서를 포함한 커밋 (git log -1 origin/claude/nova-round-u-followup-20261009). runtime 바이트는 e207801과 동일

TESTS (pytest tests -q, NOVA_LLM_PROVIDER=mock, NOVA_COMPETITION_RETRIEVAL 미설정):
passed:     2462  (전체 실행 2460 + 로컬 v27 기록 생성 후 재실행한 release-binding 1, package-not-built skip 1)
failed:     0     (로컬 v27 ZIP/기록이 있을 때. ZIP을 공개하지 않은 공개 트리에서는 release-binding 1개가 기준선과 똑같이 실패)
skipped:    1     (torch 미설치: test_torch_training_and_checkpoint_roundtrip)
deselected: 0
baseline(깨끗한 checkout): 2423 passed / 1 failed(같은 release-binding, 비공개 v26 ZIP 부재) / 2 skipped

PRELIMINARY (230 cases / 222 scored, SAY·EXAM·DIAGNOSE, TEST 없음):
before: 209/222
after:  218/222
new correct: PrelimKo_Abd_Pancreatitis, RoundM_024, RoundM_066, RoundM_095, RoundM_098, RoundM_105, RoundM_110, RoundM_115, RoundI_long_tail
new wrong:   없음
critical before: 85/85
critical after:  85/85
average turns:    20.33 → 19.92 (max 34 → 35)
unnecessary EXAM: 371 → 238 (전체 EXAM 1377 → 1225)

ROUND P (34 / 32 scored):
before: 27/32
after:  31/32
critical: 11/13 → 13/13 (평균 턴 21.85 → 20.79, 새 오답 없음)

ROUND M (TEST 허용, 128 / 123 scored):
before: 115/123
after:  117/123
critical: 43/43 → 43/43
long-tail Top1:  18/26 → 20/26
long-tail Top5:  21/26 → 23/26
long-tail Top10: 23/26 → 25/26
(새 정답 RoundM_098, RoundM_115; 새 오답 없음; 평균 턴 22.91 → 22.98)

RETRIEVAL (164개 개발 사례 proxy; 정답은 검색 후 위치 확인에만 사용):
chief-only Top150 before/after: 118/164 (72.0%) → 155/164 (94.5%)
chief-only Top25  before/after: 117/164 (71.3%) → 155/164 (94.5%)
follow-up Top150 (전체 scripted history 상한): 152/164 → 164/164
follow-up Top25  (전체 scripted history 상한): 151/164 → 164/164
active retention (Round M 종료 시): 123/123 → 123/123 (종료 시 Top150 117 → 122, 진단 Top25 114 → 122)

ASSERTION:
10 contrast result: 10/10 → 10/10

REMAINING FAILURES: 아래 "남은 실패" 표

SUBMISSION:
source/mirror byte equality: PASS (nova_agent·competition ↔ submission/, audit source_submission_byte_equivalence=True)
package audit: PASS (secret scan PASS, clean-room ZIP validation all_pass, 새 디렉터리 mock 실행 PASS, run.py 공식 경로 fail-closed)
ZIP SHA256: e4944175bace8b671618b0e00968638eef7c19b974318ae5528711c917f7e1e8 (839,414 bytes; 로컬 전용, 공개하지 않음)

VERDICT:
- offline implementation: 완료. 아래 수정 모두 테스트·동일 조건 회귀로 확인
- same-condition regression: PASS. 27개 비교 세트(예선 3변형, P, Q, R, acceptance, S, T 4종, U 4종, follow-up 2종, TEST 허용 8종, Round M) 모두 새 오답 0, 새 critical miss 0
- fresh synthetic validation: 부분 PASS. Closing 세트 채점 4→5/7, 행동 계약 41→40/43 (새 실패 1, 아래)
- official API: NOT VERIFIED
- real GPT-OSS: NOT VERIFIED
- independent clinical validation: NOT PERFORMED
- overall: FAIL. 90점 기준 중 Round M ≥118/123 미달(117). 나머지 측정 목표는 충족
```

## 1. 90점 기준 대조

| 기준 | 결과 | 판정 |
|---|---|---|
| 전체 관련 테스트 failed = 0 | 로컬 v27 근거 기준 0. 공개 트리는 ZIP 미공개로 1 실패(기준선과 동일) | 조건부 PASS |
| 기존 critical recall 회귀 없음 / 새 critical miss 0 | 모든 세트 0 | PASS |
| RoundM_066 회귀 해결 | 해결(아래 단서 참조) | PASS |
| Fresh05 과잉 명명 원인 해결 | DKA 정답. 관찰된 근거가 DKA에 전달됨 | PASS |
| ValP_10/12/17/21 기전별 기록 | `case_mechanisms.json`과 §3 | PASS |
| 부정문 assertion 10/10 | 10/10 | PASS |
| source mirror byte equality / 패키지 audit | PASS / PASS | PASS |
| 실제 LLM·API | NOT VERIFIED로 표시 | 표시 완료 |
| 예선 Top1 ≥215/222 | 218 | PASS |
| 예선 critical ≥85/85 | 85 | PASS |
| Round P ≥29/32 | 31 | PASS |
| **Round M ≥118/123** | **117** | **FAIL** |
| long-tail Top1 ≥20 / Top5 ≥22 | 20 / 23 | PASS |
| chief-only Top150 ≥90% / Top25 ≥80% | 94.5% / 94.5% (개발 proxy, §4 단서) | PASS |
| 평균 interaction ≤20 | 19.92 | PASS (여유 작음) |
| 불필요 EXAM ≤371, 감소 | 238 | PASS |
| 새 scored wrong = 0 | 0 | PASS |

미달 항목이 하나라도 있으면 FAIL로 보고하라는 지시에 따라 **overall FAIL**이다. 95점, 100점, 임상 안전, 독립 검증은 선언하지 않는다.

## 2. 구현한 변경

모두 일반 기전이다. 사례 ID, 정답 질환, 채점기, 라벨은 하드코딩하거나 바꾸지 않았다. 위험도를 진단 점수 보너스로 쓰는 곳도 없다. 새 임상 관계의 출처는 [ROUND_U_FOLLOWUP_PROVENANCE.md](ROUND_U_FOLLOWUP_PROVENANCE.md)에 있다.

| 문제 | 수정 위치 | 동작 |
|---|---|---|
| 영국식 철자 불일치("diarrhoea", "oedema", "haemoptysis"가 KB 문구와 전혀 매칭되지 않음) | `matching.py` `us_spelling` | KB 문구와 관찰을 같은 철자로 정규화한다. 같은 단어만 같게 만들고 동의어는 추가하지 않는다. memo는 결정 범위에만 둔다 |
| 관찰 표현이 기존 KB 문구에 닿지 않음(Fresh05의 type 1 diabetes·pump 중단·deep laboured breathing, ValP_10의 갈비뼈 압통·낙상, 심부전 표현 등) | `lay_language.py` | 문구 하나만 돕는 다단어 별칭을 추가했다. 기본 "No"가 이미 말한 사실을 부정으로 바꾸던 경로가 별칭 덕분에 conflict로 기록된다 |
| 별칭 안의 부정어("passed out without any warning")가 부정 제거로 지워짐 | `_strict_alias_present` | 별칭 내부 부정은 원문에서 매칭한다. 앞 사건("passed out")이 부정되면 매칭하지 않는다 |
| "A or B"의 공유 머리·보어("pain relieved or worsened by eating"), "A and B" 목록 특징이 다른 문장에 나뉘어 관찰됨 | `or_branches`, `and_branches`, `differential._score_phrase` | 존재 판정에만 쓰고 하나의 근거로 센다. 한쪽 부정은 짝 전체의 부정이 아니다 |
| EXAM 관찰이 앞선 bare "No"와 충돌 | `state.record_exam` | 관찰을 유지하고 conflict로 기록한다(환자 발화와 같은 규칙) |
| 단일 일반 증상(RoundM_066) | `final_decision.discriminated_by_answers` | 위험하지 않은 선두이고, 명시적 응답(unknown·거절 제외)으로 그 증상을 공유하는 경쟁 후보가 모두 반박되었고, 동점 후보와 양성 근거가 있는 위험 후보가 없을 때만 working diagnosis로 명명한다. 위험 질환은 이 경로로 명명하지 않는다 |
| 선두가 막혔을 때 일반 증상 두 개로 대안 명명(nausea+vomiting → pancreatitis) | `decide_final` | 대안은 비일반 관찰을 하나 이상 가져야 한다 |
| 통증 단독이 "임신 맥락"으로 인정됨(Round Q 설계 결함) | `_REQUIRED_CONTEXT['ectopic_pregnancy']` | 생리 지연·임신·질출혈·양성 검사만 인정한다. 후보 삭제·점수·긴급 계획은 바뀌지 않는다 |
| HR38+경고 없는 실신, 실신 전 두근거림이 부정맥 범주에 연결되지 않음 | `cardiac.json` | ESC 2018 Table 5 출처로 범주 특징 2개를 추가했다. 리듬 subtype은 만들지 않는다 |
| 진찰의 "focal neurological deficit"이 뇌졸중에 연결되지 않음 | `neuro.json` | objective-only 진찰 특징을 추가했다(출처 기재). 부정된 진찰은 매칭하지 않는다 |
| 한국어 상복부→등 방사·과음, 일본어 회전성 어지럼·寝返り·数秒 | `multilingual_concepts.py`, `feature_relations.py` | 기존 KB 문구의 현지어 표현을 추가했다. 吐き気는 구토 근거가 아니라 오심 근거로 고쳤다 |
| 주호소만으로 검색 Top150/Top25가 낮음 | `retrieval_vocabulary.py`, `retrieval_pipeline.retrieve_high_recall` | 기존 별칭·한/일 개념표만으로 관찰 표현을 **기존** KB 문구로 바꾼다. 최대 8개이며 기존 12개 확장 상한 안에 있다. 부정·가족·과거 문장은 제외하고, 자유 생성 질의와 위험도 가중은 쓰지 않는다. Top150, Weighted RRF, 진단 Top25 구조는 그대로다 |
| 근거 없는 후보에 대한 표적 sweep(불필요 EXAM 371) | `action_selector` + `NOVA_ACTION_FOCUS`(기본 ON, 예선 규칙에서만) | 관찰 근거가 없고 safety layer가 표시하지 않은 후보만 겨냥한 표적 ASK/EXAM은 건너뛴다. 일반 병력 질문, vital/general appearance, **time-critical 질환 관련 진찰**은 항상 유지한다(안전 추적 용도이며 진단 점수가 아니다). 건너뛰어도 아무것도 음성·배제로 표시하지 않는다 |
| Tier-2 깊이 | `scripts/prioritize_tier2_depth.py`, `tier2_enrichment.json` | 위험도를 우선순위 가중에서 빼고 안전 추적 열로만 남겼다. 개발 trace에서 50개 우선 subset을 선정했다(`artifacts/round_u_followup/tier2_priority.json`). 새 깊이 프로필은 출처가 확인된 Sjögren 1개뿐이다(필드별 provenance). 나머지는 미해결로 남겼다 |

반복 검증 중에 발견해 되돌리거나 교정한 항목:

1. action focus가 ValP_27(보호자가 말한 뇌졸중 증상)의 신경 진찰을 건너뛰게 만들었다. time-critical 진찰 예외로 교정했다.
2. 같은 dict 안의 중복 키 `"seizure"`가 Round Q 별칭을 지웠다. 병합했다.
3. 환자 텍스트를 받는 함수에 `lru_cache`를 쓰면 사례 사이에 데이터가 남는다(case-isolation 위반). 결정 범위 memo로 바꿨다.
4. 별칭 하나("blacked out with no warning")가 reference-only blind 문장과 겹쳤다(누출 검사). 삭제했다.
5. 기존 "breathing deeply"→Kussmaul 별칭이 흉막성 통증을 Kussmaul로 읽어 NewT_12를 틀리게 했다. 삭제하고 흉막성 표현을 추가했다.
6. 吐き気가 구토 근거로 쓰였고, 새 "A and B" 규칙과 겹쳐 RoundM_092를 틀리게 했다. 교정했다.
7. "tender low on the right"→RLQ tenderness 별칭이 충수염 confirmatory로 이어져 RoundM_047(자궁외임신, critical)을 틀리게 했다. **되돌렸다.**

매 수정 뒤 전체 세트를 같은 조건에서 다시 돌렸다. 최종 `e207801`의 전체 실행에서 새 오답과 새 critical miss는 0이다.

## 3. 지정 사례 기전 기록 (기준선 → 최종)

| 사례 | 처음 검색 Top150/Top25/active | 최종 support | 남은 구별 정보 | 실제 선택 행동(요지) | 최종 명명과 이유 | 위험 대안 처리 | SOAP |
|---|---|---|---|---|---|---|---|
| Fresh05 (DKA) | 기준 5/3/3 → 최종 2/1/1 | polyuria, polydipsia, nausea and vomiting, abdominal pain, kussmaul breathing(진찰), known diabetes, missed insulin doses | fruity breath, ketones/acidosis(검사 불가) | 병력·복부/피부/일반 진찰 | 기준 Acute Pancreatitis(동점 2.0을 삽입 순서로 승리) → **DKA 5.8** | pancreatitis 2.0 유지(배제 아님). 긴급 처분과 glucose/ketone **계획** 유지 | 관찰 보존, 검사 결과 생성 없음 |
| ValP_10 (MSK 흉통) | 22/7/12 → 43/15/8 (종료 시 5/6/1) | reproducible with palpation, worse with movement, recent trauma | localized tenderness(흉벽 진찰 키 없음) | 폐 청진·하지 진찰·병력 | 기준 Tension Pneumothorax(단일 "chest pain after trauma") → **MSK** | TP 1.5 잔존. 처분은 여전히 긴급(과잉 분류, 남은 문제) | 보존 |
| ValP_12 (전해질) | 처음 검색 밖 → 종료 시 active 2 | confusion, seizure("short fit"), diuretic use | low sodium(검사 불가), SSRI 연결 없음 | 약물·정신상태·신경 진찰·수막자극 | 기준 미분화 → SIADH(선두)는 저나트륨 문서가 없어 막히고, 비일반 근거(seizure)가 있는 **severe electrolyte disorder**를 대안으로 명명 | meningitis는 only_nonspecific로 명명되지 않음, 긴급 처분 | 보존 |
| ValP_17 (부정맥) | 처음 active 2 → 1/1/1 | pulse rate below 50, syncope without warning, structural heart disease | 리듬 기록(ECG 불가) | 병력·심장 청진·신경 진찰 | 기준 미분화 → **cardiac arrhythmia(범주)**. subtype은 명명하지 않음 | VT 등 subtype 미명명. ECG **계획**과 긴급 처분 유지 | 보존 |
| ValP_21 (acute abdomen) | 75/–/8 → 76/–/8 (종료 시 6/3/2) | rebound tenderness, rigid abdomen | free air(영상 불가) | 복부 진찰·병력 | 기준 Perforated Viscus → **Acute Abdomen**. perforated viscus는 "lying still"(시뮬레이터 기본 "No") 반박으로 점수가 낮아짐 | GI bleeding 선두는 only_nonspecific로 명명 안 됨 | 보존 |
| ValP_08 (heart_failure) | 라벨이 카탈로그명과 매칭되지 않음 | Pneumonia: crackles, dyspnea | — | 다수 표적 질문(fatigue/weight gain 기본 "No") | **Pneumonia 유지(오답)** | — | 보존 |
| RoundM_066 (gastroenteritis) | 처음 active 6 → 종료 2/1/1 | diarrhea | 구토, 경련성 복통, 접촉자 | 심계항진 질문으로 hyperthyroidism 반박 | 기준 미분화 → **gastroenteritis**(discriminated_by_answers) | 양성 근거가 있는 위험 후보 없음, 비긴급 처분 | 보존 |

ValP_08 분류: 라벨 `heart_failure`는 카탈로그의 "Chronic Heart Failure"·"Acute Decompensated Heart Failure"와 `same_diagnosis`로 매칭되지 않는다. 명칭 문제다. 동시에 실제 추론 문제도 남아 있다. 심부전 후보가 표적 질문(fatigue, weight gain)에 대한 기본 "No"로 크게 감점되고, crackles·dyspnea는 폐렴에만 연결된다. 채점기를 느슨하게 만들지 않았다.

RoundM_066 단서: 해결은 환자의 명시적 부정("No")에 기대고 있다. 이 fixture에서는 그 부정이 시뮬레이터 기본값이다. runtime은 실제 부정과 기본값을 구별할 수 없다. "모르겠다" 변형(`--unscripted-unknown`)에서는 설계대로 미분화로 남는다(212→217/222, critical 85/85, 그 변형에서도 새 오답 0).

RoundM_106: PID는 1턴에 검색 9위·rerank 11위였다. 이후 검색 14~15위에 머물렀지만 rerank Top25 밖으로 밀렸다. 동시에 관찰된 근거(lower abdominal pain, discharge, fever, dyspareunia, new partner)가 쌓여 active 1위로 유지되었다. Top25 손실은 rerank 점수가 fused rank 8위 밖의 일치 강도만 반영하는 정렬 문제다. active 유지는 evidence 기반 재진입·유지 경로의 결과다. 두 경로는 서로 독립적이다. 최종 Round M에서는 종료 시 진단 Top25가 114→122로 개선되었다.

## 4. 단서와 한계

- 검색 proxy 94.5%는 164개 개발 사례 기준이다. 사용한 별칭 어휘의 상당 부분은 이전 라운드와 이번 라운드에서 이 개발 사례를 보며 만들었다. 미사용 일반화 수치가 아니다.
- 이번에 추가한 별칭 다수는 개발 사례에서 발견한 표현이다. 각 별칭은 KB 문구 하나만 돕지만 개발 노출이 있었다.
- 새 fixture 두 개:
  - follow-up(24사례)은 수정 전에 동결하고 기준선에서 먼저 실행했다(sha256 `b1ebe504…`). 이후 결과를 보며 고쳤으므로 **개발 세트**다. 결과: 채점 9→12/16, 행동 78→78/82.
  - closing(12사례)은 최종 runtime 전에 동결했고(sha256 `e5ed6d76…`) 기준선과 최종에만 실행했으며 이 세트로 소스를 고치지 않았다. 결과: 채점 4→5/7, 행동 41→40/43.
  - closing의 새 행동 실패는 CloseUF_04(넘어진 뒤 흉벽 통증, 비긴급 계약)에 긴급 처분이 나온 것이다. 진단은 맞았지만 tension pneumothorax 대안이 처분을 긴급으로 만들었다. CloseUF_03(HR34 실신)은 기준선과 최종 모두 미분화이고 처분 계약도 실패한다. 둘 다 구현을 아는 작성자의 작은 세트이며 독립 임상 검증이 아니다.
- 평균 interaction 19.92는 목표 20에 가깝다. 예선 최대 턴은 34→35로 1 늘었다.
- Tier-2: 50개 선정 중 47개가 위험 질환이다(위험도 가중을 0으로 둬도 개발 trace에서 safety watch 때문에 자주 관찰된다). 깊이를 추가한 것은 Sjögren 1개다. 나머지 49개와 Tier-2 1,162개는 미해결로 남겼다. 수를 늘리는 방식으로 채우지 않았다.
- 공개 범위: 이전 공개 제한에 따라 ZIP, 로컬 v27 기록, 상세 trace/XML은 push하지 않았다. 해시는 요약 JSON에 있다. 공개 `CURRENT_RELEASE.json`은 역사 기록으로 둔다.
- 외부 LLM/API 호출, 키 요청, 모델 다운로드·교체·학습, Blind v18/v19 실행·튜닝, 새 blind 생성은 하지 않았다. `check_eval_leakage.py`는 정적 비교만 한다.

## 5. 남은 실패

| 사례 | 관찰된 근거 | 없는 근거 | 후보 단계 | 선택 행동 | 최종 진단 | 원인 | 상태 |
|---|---|---|---|---|---|---|---|
| ValP_08 (예선 P) | 노작성 호흡곤란, 발목 부종, 3개 베개, 야간 호흡곤란, crackles, S3, 함요부종 | — | 라벨이 카탈로그명과 불일치 | 표적 질문 다수(기본 "No") | Pneumonia | 명칭 매핑 + 기본 "No"로 HF 선택적 특징 감점 + crackles가 폐렴에만 연결 | 미해결 |
| RoundM_069 (예선) | "persistent upper belly pain", drinks daily | 방사, 구토, 식후 악화 | active 5 | 일반 질문 | 미분화 | 정보 부족(정당한 미분화일 수 있음) | 미해결 |
| RoundM_108 (예선·M) | burning upper pain, 야간 통증, 음식으로 완화, ibuprofen | — | active 2 | — | Duodenal Ulcer | 부모(PUD)–자식 계층 문제. 기본 "No"(bloating) 감점 | 미해결(명칭 계층) |
| RoundM_112 (예선·M) | 음낭 통증·종창, 배뇨통, 서서히 발생 | — | active 3 | 표적 질문 기본 "No" | Cystitis | 시뮬레이터 기본 "No"가 "gradual onset testicular pain"·fever를 반박 | 미해결(평가 도구 성격) |
| RoundJ_52 (예선) | "suspected pericarditis" 의뢰, 흉부 불편감 | 모든 추가 정보(대본 없음) | 검색 32위, active 밖 | 일반 질문 | 미분화 | 의심 진단은 근거가 아님(규칙). 추가 정보 없음 | 미해결(정당) |
| RoundM_105/109/112/114/117 (M, TEST 허용) | 각 사례 trace | — | — | — | 각각 ruptured cyst / pyelonephritis / cystitis / hypoglycemia / GERD | long-tail 순위·명명. Round M 117/123으로 목표 118에 1 부족 | 미해결 |
| CloseUF_03, CloseUF_04, FollowU_19/20/21 | — | — | — | — | — | 처분(긴급 여부) 계약 실패 | 미해결 |
| FollowU_23, CloseUF_09 | HF 증상(한국어/영어) | — | — | — | Pneumonia | ValP_08과 같은 HF 대 폐렴 기전 | 미해결 |

## 6. 다음 수정 작업서 (미달 항목)

1. **Round M 118/123 (현재 117)**
   - 대상: RoundM_105(ovarian torsion vs ruptured cyst), 109(cellulitis vs pyelonephritis), 114(hyperthyroidism vs hypoglycemia), 117(mesenteric ischemia vs GERD), 112, 108.
   - 각 사례에서 "관찰됐지만 프로필 특징에 닿지 않은 표현"과 "기본 'No'로 반박된 선택적 특징"을 분리해 측정한다.
   - 사례 ID·정답을 하드코딩하지 않는다. 바꾸기 전에 Tier-2 프로필 깊이(출처 필수)부터 확인한다.
2. **심부전 대 폐렴 (ValP_08, FollowU_23, CloseUF_09)**
   - crackles·호흡곤란은 공유 소견이다. 심부전 쪽 근거(S3, 함요부종, 기좌호흡, 심근경색 병력)가 Tier-2 HF 프로필에 충분히 전달되는지 확인하고, 출처가 있는 특징만 보강한다.
   - `heart_failure` 라벨과 카탈로그명의 관계는 채점기를 바꾸지 않고 별도 명칭 문제로 보고한다.
3. **선택적 특징 부정의 감점 크기**
   - 현재 기본 "No"로 반박된 선택적 typical feature 하나가 −1.2로, 양성 하나(+1.0)보다 크다(ValP_08, RoundM_112, RoundM_110에서 관찰).
   - 시뮬레이터 기본값 문제와 runtime 가중치 문제를 분리해 ablation한다. 채점과 시뮬레이터는 바꾸지 않는다.
4. **처분(긴급 여부) 계약**
   - 진단은 맞지만, 얕은 위험 대안(tension pneumothorax 등)이 양성 흉벽 외상과 단순 방광염·통풍에 긴급 처분을 만든다.
   - 동결된 새 대조군으로 false positive와 false negative를 각각 측정한다.
5. **명칭 계층** (PUD/duodenal ulcer, acute abdomen/perforated viscus)
   - scorer를 느슨하게 만들지 않는다. 자식 원인의 support가 부모 증후군 support의 부분집합일 때의 명명 정책을 따로 설계하고 검증한다.
6. **Tier-2 깊이**
   - 선정한 50개 중 출처를 확보할 수 있는 항목부터 필드별 provenance와 함께 추가한다.
   - 위험도 편중(47/50)을 보정할 선정 기준(예: safety-watch 관찰 제외)을 검토한다.
7. **효율**
   - 평균 interaction 19.92는 목표에 가깝다. 일반 범주 질문에 대한 의미 없는 "No"(onset: denied 등)를 줄이는 질문 선택 개선을 별도로 측정한다.
8. **공개 검증**
   - 공식 인터페이스와 실제 GPT-OSS 연결 자료가 제공되면 별도로 검증한다. 그 전까지 NOT VERIFIED를 유지한다.
