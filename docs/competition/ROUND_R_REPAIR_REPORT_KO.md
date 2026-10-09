# N.O.V.A. Round R 수정 및 검증 보고서

2026-10-09. 외부 LLM 없는 mock·합성 사례 결과다. 임상 검증이나 공식 대회 점수가 아니다.

**재현된 주요 결함을 수정했고 회귀·패키지 검사는 통과했다. 그러나 전체 수정 요구사항과 새 사례의 임상적 안전성은 아직 FAIL이다.** 새 검증의 서맥 동반 실신에서 근거 없는 기립성 저혈압 및 일반 외래 계획이 남았다. 높은 단위 테스트 통과율이나 채점 정확도로 이 문제를 상쇄하지 않는다.

## 1. 코드 및 증거의 귀속

- 확인한 원격 작업 브랜치: `claude/determined-brahmagupta-wrfveb`.
- 실제 시작 remote HEAD: `02e56eb8e97ba0b6ce09061091d64222fee1c37a` (v22 runtime `8257ba617802d5f2f2221b20717a3d1cd9b79277`). 사용자가 제시했던 ead1595/v21은 이전 상태였다.
- **FINAL_REASONING_SHA (원격): `cf31e011244a9f5340ea36c05a723dc1d11177aa`**.
- 실제 검사를 실행한 로컬 SHA: `18b994984d0e22c1ee15a3e9ffcc125d5056b46b`. GitHub API 게시로 commit metadata만 달라졌고 전체 Git tree 및 runtime/ZIP 바이트는 같다. 원본 실행 기록의 SHA는 덮어쓰지 않았다.
- 이 SHA 이후 커밋은 제출 복사본·검증 기록·보고서만 변경한다. `nova_agent/`, `competition/`, 진입점의 실제 바이트를 git commit 및 ZIP과 비교했다.
- 임시 구현 브랜치 `codex/nova-round-r-repair`에서 작업했다. 원래 사용자 checkout/main을 reset하거나 덮어쓰지 않았다. 저장소에 AGENTS.md는 없었다. CURRENT_STATUS, Round P/Q 보고서 및 이전 검수·후속 작업서를 읽었다.
- 검증 버전 v23. `artifacts/verification/CURRENT_RELEASE.json` → `local-release-cf31e01-v23.json`.
- ZIP: `artifacts/verification/nova-pre-guide-v23.zip`, 815,013 bytes.
- ZIP SHA256: `60cc7bc0d8fd2b85d984e9f2877c30253b750fc8292d3b3c1b331eda417d2eca`.
- main 변경, force push, 모델 다운로드·교체·학습, API 연결, blind v18/v19 실행 없음. Top150 / Weighted RRF / Top25와 질환 수는 변경하지 않았다.

## 2. 이전 지적 사항과 구현 대응

줄 번호는 FINAL_REASONING_SHA 기준이다. 새 테스트는 삭제·완화 없이 추가했다. 기존 테스트 수정은 v23 허용 목록 한 항목뿐이며 ZIP/commit/hash 단언을 유지했다.

| 이전 문제 | 수정 위치 | 실제 재현 결과 | 판정 |
|---|---|---|---|
| 진단 첫 occurrence만 처리, 복수 진단의 부정·주어·시점 혼동 | `documented_diagnosis.py:89,137,157,174,235,266`; `assertion_status.py:16` | 기존 40+이전 검수 24 대조쌍: 48/64→64/64. 동일 이름 반복, 후행 명시적 정정, 가족→환자 전환, 한국어 절 분리 포함 | 해당 회귀 해결 |
| 추출 IDs가 비어도 부정/가족 AF가 일반 feature/risk 근거로 유입 | `documented_diagnosis.py:241`; `state.py:721`; `differential.py:517`; `severity_evidence.py` | 엔진 downstream에서 excluded/family/uncertain AF를 현재 긍정 근거로 사용하지 않음. 10개 전체 adapter 회귀도 10/10 | 해당 회귀 해결; 모든 임상 evidence에 범용 span 추적을 제공한 것은 아님 |
| mixed unknown 때문에 경련·약물이 통째로 소실 | `state.py:64,171,458,571` | cramps + 이유 모름, 약물명 + 용량 모름 보존. OR 질문의 Yes는 개별 두 증상으로 분해하지 않음 | 부분 해결: 새로운 unknown 문구는 남음 |
| urinary frequency+다른 통증을 dysuria로 매칭, 근육 경련→seizure, near-faint→LOC | `matching.py:437,807`; `multilingual_concepts.py` | 직접/alias 양쪽 배뇨통 관계 보호; 경련 span 중복 방지; Fresh18 및 NewR11 회복 | 해당 회귀 해결; 일반 부정된 목록·자세 관계는 미해결 |
| 일반 history 질문으로 세부 관찰 완료 처리, 정보 수집 문항 부재 | `history_followup.py:16`; `missing_info.py`; `taxonomy.py`; `preliminary.py` | 약 변경·구토·설사·섭취·마지막 투석·실제 LOC의 제한된 단일 질문, 4개 언어의 길이/의미 검사 | 부분 해결: 후보가 이미 top3·복수 근거여야 활성화되므로 약한 초기 후보 회복은 보장 못함 |
| ASK 수행/unknown/EXAM 거절/예선 TEST 불가 혼동 | `state.py:427,434,483`; `resolution.py:106,148`; `clinical_concepts.py`; `candidate_generator.py`; `adapter.py` | observed/unknown/rejected/unavailable를 분리; murmur 및 lung sounds는 지원되는 EXAM 연결; 거절 후 새 실제 관찰 갱신 허용 | 부분 해결: unknown 문구 미인식 및 모든 mapped EXAM의 coverage 표시 완전성은 후속 필요 |
| generic/risk-only 위험 진단 명명, pulse만으로 VT, 서맥 실신의 vasovagal 확정 | `final_decision.py:132,137,144,196`; `uncertainty.py` | Fresh25–32 정보 부족 8/8 unknown, Fresh23/24 broad arrhythmia; NewR17 VT→broad arrhythmia; ValP12 meningitis→unknown | 부분 해결: NewR18의 다른 benign label 우회 및 지원 metadata 불일치 남음 |
| 완료 판정·SOAP·위험 대안이 불일치 | `resolution.py:148`, `adapter.py` workup metadata 추가 | 관찰 미확인을 배제라고 표시하지 않는 audit 정보 추가 | 미완료: unsupported A 근거와 잘못된 P 긴급도, SUPPORTED/INSUFFICIENT 동시 표시 남음 |

### 문서 진단 필수 입력의 현재 출력

전체 mention 상태·근거 span은 `artifacts/round_r/final/assertion_examples.json`, 테스트 fixture는 `evaluation/assertion_regressions_round_r.json`.

| 입력 | documented IDs |
|---|---|
| The referral letter says atrial fibrillation was excluded | `[]` |
| 진단서에 atrial fibrillation 아니라고 적혀 있습니다 | `[]` |
| The letter confirms atrial fibrillation but excludes pulmonary embolism | `[cardiac_arrhythmia]` |
| The letter confirms atrial fibrillation; the patient has no fever | `[cardiac_arrhythmia]` |
| The letter says pulmonary embolism cannot be excluded | `[]`, uncertain |
| The letter says pulmonary embolism has not been ruled out | `[]`, uncertain |
| 진단서에는 pulmonary embolism이 의심된다고 적혀 있습니다 | `[]`, uncertain |
| The letter confirms atrial fibrillation in her father, but the patient has no known arrhythmia. | `[]`, 가족 진단을 환자 확진으로 가산하지 않음 |

진단 이름을 점수용 view에서만 가리며 원문은 보존한다. 현재 진단과 과거 위험·가족 위험은 분리한다. `tests/test_round_r_assertion_evidence.py` 69개는 기준선 48 pass/21 fail → 수정 후 69 pass다. `test_round_r_observation_grounding.py` 15개, `test_round_r_final_workup.py` 14개도 통과했다.

## 3. 동일 조건 성능 비교

`NOVA_LLM_PROVIDER=mock`, `NOVA_COMPETITION_RETRIEVAL=1`. 예선은 SAY/EXAM/DIAGNOSE만 사용한다. 기존 사례·정답·분모·매처·기본 응답은 그대로다. 기준선은 **현재 원격 v22**다. 이전 v21의 215/222를 현재 기준선 202/222와 혼동하지 않는다.

| 자료 | 전체/채점 | Top1 전→후 | 위험 Top1 전→후 | 평균 턴 전→후 | 최대 턴 전→후 | 새 정답/새 오답 |
|---|---:|---:|---:|---:|---:|---:|
| 예선 개발 전체 | 230/222 | 202→203 /222 (91.4%) | 85→85 /85 | 19.65→20.04 | 35→35 | 1/0 |
| Round P 개발 | 34/32 | 28→28 /32 (87.5%) | 11→11 /13 | 19.71→20.03 | 30→32 | 0/0 |
| Round Q 개발 | 48/36 | 33→35 /36 (97.2%) | 9→10 /11 | 20.38→20.54 | 35→35 | 2/0 |
| 이전 검수 32개, 이제 개발 | 32/18 | 15→16 /18 (88.9%) | 4→4 /5 | 21.75→26.69 | 30→36 | 1/0 |
| 새 Round R 합성 검증 | 24/12 | 10→11 /12 (91.7%) | 4→4 /4 | 22.71→23.42 | 32→33 | 1/0 |

전체 예선은 과거 Round P 215/222=96.8%에 **미달**한다. 새 Round R는 단 12개 채점 표본으로 높은 일반화 성능을 입증하지 않는다. 기존 세트의 향상은 개발 성능이다.

새 정답: RoundJ_51, DevQ_22, DevQ_28, Fresh18, NewR_11. 오답→다른 오답도 기록했다: ValP_12 meningitis→unknown, Fresh05 sepsis→pancreatitis(여전히 오답). 세부 사례별 변화는 `artifacts/round_r/final/comparison.json`.

| 지표 | 예선 개발 전→후 | 이전 검수 개발 전→후 | 새 Round R 전→후 |
|---|---:|---:|---:|
| 정확히 중복된 행동 | 0→0 | 0→0 | 0→0 |
| 기존 평가기의 의미 중복 질문 | 11→18 | 1→1 | 0→0 |
| 불필요 EXAM 집계 | 297→299 | 77→167 | 54→51 |
| 미해결 위험 대안이 있다고 집계된 사례 | 76→74 | 15→31 | 11→11 |
| 규칙 위반 / malformed / 상한 초과 | 모두 0 | 모두 0 | 모두 0 |
| SOAP 원문 보존 | 100%→100% | 100%→100% | 100%→100% |
| 기존 SOAP 검사 unsupported 줄 | 0→0 | 0→0 | 0→0 |

**효율은 일부 악화했다.** unknown을 정상 관찰처럼 소진하지 않으면서 이전 검수 세트의 EXAM·턴이 늘었다. 이 지표를 숨기지 않는다. 미해결 대안 집계는 기존 평가기의 rank1 제외 방식이므로 실제 selected_id 기준의 임상 배제 수가 아니다. SOAP 문자열 검사 0건은 A/P 의미 정확성을 뜻하지 않으며 NewR18이 반례다.

정보 부족 과잉 명명: 이전 검수 Fresh25–32 위험 명명 3/8→0/8, 새 NewR19–24는 3/6→0/6. Round Q의 unscored dangerous-named는 2건 남는다. 모호한 사례의 위험 working diagnosis를 모두 오진으로 간주하지 않으며 전체 임상 과잉 진단율은 미측정이다.

### TEST 사용 가능 경로는 별도로 확인

예선 수치에 합치지 않았다. `scripts/evaluate_pre_guide_regressions.py`의 held-out, generalization-v2, stress, D/E/G/I/J 8세트는 기준선 대비 새 오답·새 위험 누락 0. G 12/12, I 18/20, J 51/54이며 각 세트의 기존 critical 분모에서는 100%다.

전체 Round M 128개/123개 채점은 별도 전체 실행했다: Top1 108/123, critical 42/43, 평균 25.55턴, TEST 평균 10.12. 최종 retrieval@150 112/123=91.06%, rerank@25 96/123=78.05%, active 122/123=99.19%. 내부 aggregate의 `rerank_truth_retention`은 97/123으로 별도 정의다. 두 값을 같은 지표처럼 사용하지 않는다. long-tail 26개 Top1 12/26, Top5 17/26, Top10 21/26. 이 실행은 진단 assertion 수정을 검증하는 추가 회귀이며 30–80개 Tier2 임상 프로필 확장 작업은 수행하지 않았다.

기존 위험 누락 **RoundM_096 (SAH→meningitis), ValO_11 (PE→pneumonia)**는 여전히 재현됐다. 전자는 전체 M, 후자는 기존 benchmark runner로 개별 실행했다. 예선의 critical 85/85를 근거로 이 경로까지 안전하다고 판단하지 않는다.

## 4. 새 사례 동결과 실패 분석

24개 새 합성 조합을 `7fa7d68`에서 실행 전에 동결했다. 작성자는 구현과 기존 실패를 읽었으므로 독립 임상/외부 blind 검증이 아니다. 12개 작업 진단 채점 + 12개 모호/행동 사례로 사전에 나눴다.

- 파일: `evaluation/frozen_validation_round_r.json`.
- 동결: 2026-10-09T03:29:56.335173+00:00.
- SHA256: `65a1b2855712214dc69481eb1f3eda8e57e03c139b12ea322c4b325ba3879397`.
- 동일 fixture·driver·정답·기준으로 기준선과 최종 코드를 실행했다. 결과 열람 후 runtime 변경 없음.
- 사전 행동 계약: 15/19→19/19. 수치 통과와 별개로 **임상 안전성 FAIL**.
- critical 분모의 한계: NewR_04 truth `stroke`는 정답 matcher에서 ischemic stroke와 대응되지만 기존 `SyntheticCase.critical`은 이 alias를 포함하지 않는다. 4라는 기존 분모를 사후 수정하지 않았다.

### P0 — NewR_18: 부정된 자세가 양성 근거가 되어 서맥 실신을 benign으로 마무리

입력: `I briefly blacked out while seated reading. I was not frightened, hot, or standing up.` 실제 제공 활력 `BP 101/62, HR 39 regular, Temp 36.6, SpO2 97%`. 후속 `No standing or pain trigger.`

현재 출력은 **Orthostatic Hypotension**, supporting `lightheadedness on standing up`, routine/outpatient 계획이다. 실제 일어서다 어지러웠다는 관찰은 없다. cardiac_arrhythmia는 첫 turn에 rank3로 존재하고 pulse<50가 보존된다. 최종에도 score0.3으로 남지만 잘못 생성된 자세 근거 score1.5에 밀린다. cardiac auscultation·neuro·mental EXAM은 선택됐으나 Not assessed 응답이다. 이 상태에서 기립성 원인 확정과 일반 추적만으로 마무리하면 안 된다.

직접 재현: `feature_present('lightheadedness on standing up', [chief], scrub_negated_spans=True)`가 **True**. alias와 canonical expansion은 비어 있어 `matching.py:306,437`의 직접 매칭/부정 목록 범위가 원인임을 분리했다. `final_decision.py:144`의 위험 label 중심 필터를 benign label이 통과하고, `soap.py:310` 및 `competition/adapter.py:100`의 긴급도가 benign selected label 때문에 낮아진다. 이는 정답을 알고 만든 설명이 아니라 관찰에 없는 supporting 문구로 직접 증명된다.

사전 NewR18 계약은 arrhythmia candidate 유지·VT/vasovagal 금지만 요구해서 이 오류를 잡지 못했다. **평가기의 좁은 계약도 별도 결함**이다. 현재 정답·계약·결과는 고치지 않고 후속 회귀로 넘긴다.

### P1 — 새 unknown 문구와 가족 위험의 오염

`I cannot tell you that.`를 `state.py:171 answer_kind`가 unknown으로 인식하지 못한다. medication/allergy/modifier 등에 내용처럼 저장되고 family wrapper에서 `family history` risk0.4가 생긴다. `Not assessed.` EXAM 분리는 동작하지만 ASK까지 같은 수준으로 해결되지는 않았다. 입력 중 실제 기능 장애 `I cannot lift my arm`와 구별하는 후속 수정이 필요하다.

### P1 — NewR_12 일반 질환 표현 누락 및 과도한 긴급 계획

chief의 tight band/both temples, 후속 `Dull pressing bilateral headache`에서 KB `bilateral band-like pressure`를 못 잡는다. Tension Headache의 최종 근거는 `no nausea`뿐이어서 unknown. 최초 differential에 tension headache도 없고 후속 뒤 등장하므로 후보 회복 자체는 가능하지만 의미 매칭이 부족하다. 원문 표현 누락과 위험 대안의 nonspecific headache만으로 응급 계획이 생기는 경로를 별도로 다뤄야 한다. 세트 정답을 바꾸지 않았다.

### P1 — 선택 진단과 지원 metadata의 불일치

NewR_07/18에서 `final_decision.support=SUPPORTED`와 `internal_result=INSUFFICIENT_INFORMATION`이 함께 있다. 작업 진단 가능성과 확진 불가가 다른 축이라면 의미와 SOAP 표현을 일치시켜야 한다. 현재처럼 이유 없이 확정적으로 보이는 primary를 보내면 수정 요구사항을 충족하지 못한다.

## 5. 남은 기존 문제와 평가 한계

- ValP11/13/16/17은 정답 유지. ValP12는 unknown으로 과도한 meningitis 명명을 줄였지만 전해질 정답 회복은 실패했다. sodium/검사 결과는 생성하지 않았다.
- ValP08 heart_failure→pneumonia, ValP10 MSK chest pain→tension pneumothorax, ValP21 acute abdomen→GI bleeding는 남는다. 이름 계층 검사와 실제 근거 오류를 별도로 추적해야 하며 scorer를 느슨하게 바꾸지 않았다.
- Fresh05 electrolyte→pancreatitis, Fresh16 gastroenteritis→pancreatitis도 남는다. 배뇨통/감염의 허위 근거 제거가 곧 올바른 최종 진단을 보장하지 않았다.
- 기존 시뮬레이터는 정의되지 않은 질문에 No를 주는 경로 및 질문 key로 응답하는 경로가 있다. 새 문항이 유용한지에 대한 임상 검증 대신 기본 No가 채워질 수 있다. 이번 평가에서는 기존 응답을 변경하지 않았다.
- 새 fixture의 unknown 응답도 runtime 해석을 시험하는 관찰이지 자동으로 누락 처리되는 metadata가 아니다. 예상 밖 표현의 미인식은 runtime 결함이다.
- CASE 이름/분모/critical alias·SOAP provenance·위험 대안 집계는 별도 평가 도구 과제로 제안한다. 수정으로 점수를 부풀리지 않았다.

## 6. 검사와 최종 판정

전체 `tests/` 2,120개를 중복 없는 3개 프로세스 묶음으로 실행: 일반 2,114개(2,113 pass/1 skip), NCIt research 3 pass, release binding 3 pass. **합계 2,119 passed / 0 failed / 1 skipped / 0 deselected / 0 미실행 테스트**. skip은 torch 부재의 학습 roundtrip이며 모델 학습을 실행하지 않았다. 초기 개발 실행에서 generic question coverage의 IndexError가 발견되어 18b9949에서 수정한 뒤 전체 회귀를 재실행했다. 실패·부분 로그는 로컬 중간 개발 기록에 보존했고 공개 최종 결과에 포함하지 않았으며 성공 수에 더하지 않았다.

분리 이유는 research 테스트의 메모리 누적 방지와 release artifact 생성 순서다. 최종 JUnit 3개에서 testcase 중복 및 실패가 없는지 recorder가 검증한다. 공개 자료에는 `artifacts/round_r/final/test_summary.json`의 집계와 원본 해시를 포함하며 상세 XML은 로컬 커밋에 보존한다. 원본을 덮어쓰는 제출 빌드는 별도 worktree에서 실행했다.

- 소스·submission mirror 파일 집합/바이트: 일치.
- ZIP audit, ZIP 독립 Python 실행, 한국어 전체 mock encounter: PASS.
- runtime inventory hash coverage: PASS. 기존 권리/임상 provenance 미해결 84개: 제출 권한 확보를 뜻하지 않음.
- leakage static scan: PASS(기존 도구 기준). blind 실행은 아님.
- 공식 run.py는 NOT READY로 fail-closed. 실제 모델·공식 호출 수치는 없음.

| 검수 범위 | 판정 | 의미 |
|---|---|---|
| 이번에 추가한 수정 회귀·기존 전체 테스트 | PASS | 명시한 테스트 계약 통과 |
| 전체 오프라인 수정 요구사항 | **FAIL / 부분 완료** | unknown·일반 부정 범위·지원/계획 일관성 및 기존 누락 남음 |
| 새 사례 임상 안전성 | **FAIL** | NewR18 semantic failure, 작은 합성 표본 |
| 제출 패키지 오프라인 구조·동기화 | PASS | v23 바이트 및 격리 실행 검증 |
| 실제 LLM·공식 인터페이스 | **미검증** | 외부 연결·성능 검증 수행 안 함 |

재현 명령·case-level 결과·후속 수정 명세는 `ROUND_R_FOLLOWUP_KO.md`, `artifacts/round_r/README.md`를 참조한다. 이번에 읽은 새 사례는 다음 구현부터 개발 자료다. 다음 변경은 이 실패들을 회귀로 고정하고 별도의 미사용 사례를 동결해 평가해야 한다.
