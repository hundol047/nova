# N.O.V.A. Round U 수정·검증 보고서

## 검토 대상과 판정

- FINAL_REASONING_SHA: `da7cfca7eb80f09af82019326f9964a285946f1d`. 로컬 작업 브랜치 `codex/nova-round-u-final-reasoning`.
- 실행 기준선: `761fcda7f4f5b6c58b0e0b6e8b77047b37301782` (Round T). 공개 기준선 HEAD: `5549ab4f59120c96802076ebe2d495110af4a04b`.
- main, 원래 Claude 브랜치, 원본 사용자 checkout은 수정하지 않았다. AGENTS.md는 해당 checkout/상위 경로에 없었으며 CURRENT_STATUS와 이전 T 보고서/후속 작업서를 읽고 시작했다.
- 조건: `NOVA_LLM_PROVIDER=mock`, `NOVA_COMPETITION_RETRIEVAL=1`. 예선은 SAY/EXAM/DIAGNOSE, TEST 없음. TEST 허용 회귀는 별도 표다.
- 전체 동일 라벨 회귀: **FAIL**. 새 오답: `{"preliminary": ["RoundM_066"]}`. 새 위험 누락: `{}`.
- 새 Closing U8: 채점 4/4, 위험 2/2, 행동 26/26. 작고 구현을 읽은 작성자의 기전 대조군이므로 독립 임상/광범위 미사용 성능 검증이 아니다.
- 로컬 제출 패키지 무결성·독립 mock: **PASS**. 실제 GPT-OSS/공식 API: **미검증**. 공식 제출 상태는 **NOT READY**.

점수 95/100 또는 임상 완성을 선언하지 않는다. 프로토콜 형식, 후보 보존, 진단 정확도, 과잉 명명, 긴급 처분을 별도로 판단했다.

| 검수 범위 | 판정 | 의미 |
|---|---|---|
| 이번 수정 기전·단위 회귀 | PASS | 명시된 대조군과 전체 tests/ 기준 |
| 전체 오프라인 수용 | FAIL | 새 scored 회귀와 남은 과잉 명명/기존 위험 오답을 공개 |
| 마지막 새 합성 대조군 | PASS | Closing U8에 한정, 광범위 일반화 인증 아님 |
| 로컬 제출 패키지 무결성·mock | PASS | source/ZIP/실행 연결, 공식 호환성·사용권 승인 아님 |
| 실제 LLM·공식 인터페이스·독립 임상 | 미검증 | mock 수치로 대체하지 않음 |

## 구현 대응표

| 문제 | 수정 위치 | 직접 확인한 동작 / 증거 |
|---|---|---|
| 문서 진단의 배제·불확실·주체 범위 | `assertion_status.py:7`; 기존 `documented_diagnosis.py` 재사용 | 처음 제시된 AF excluded/한국어 부정 등 기존 10 대조문은 추출·후보 documented support에서 10/10 유지. `cannot be confirmed/established`도 확정/배제로 승격하지 않는다. U12에서 확정되지 않은 sepsis 문서와 friction rub의 과잉 명명 재현을 보존했다. |
| 식사·자세 언급이 증상 관계가 됨 | `feature_relations.py`; `matching.py:424`, `or_branches`, `_feature_present_with_aliases` | 알약을 식후 복용/단순 눕기만으로 식후 악화·누우면 호전을 만들지 않는다. 실제 악화/호전, 질문 문맥, 한국어 양성도 유지한다. |
| 회전감·짧은 지속·체위 관계 누락 | `feature_relations.py:observed_rotation_features`; `clinical_concepts.py` | 기존 ConfirmT_07에서 unknown→BPPV working label로 바뀌어 T 확인 개발 7/8→8/8. 지원하지 않는 Dix-Hallpike를 시행한 것으로 만들지 않는다. 지속시간·유발 관계가 실제 명시된 경우만 기존 특징으로 연결한다. |
| fluttering→불규칙 맥박 | `lay_language.py`; `test_round_u_relations.py` | 눈꺼풀 떨림·주관적인 느낌은 불규칙 맥박이 아니다. 실제 불규칙 맥박은 유지하며, 낮은 맥박만으로 리듬 원인을 명명하지 않는다. |
| 중증도·일반 증상이 원인 진단이 됨 | `final_decision.py:166` | hemodynamic-only, severe weakness, 단일 diarrhea, 일반 증상의 conjunction을 구별한다. 발열+인지 변화, 실제 위험 활력징후, 현재 확정 기록은 유지한다. |
| 음성 소견만 있는 후보가 양성 패턴을 앞섬 | `differential.py:234` | no chest pain/no palpitations만으로 실제 실신 패턴을 이기지 않는다. 원점수·반증·후보는 삭제하지 않는다. RoundJ_07 재현에서 vasovagal→orthostatic 회귀를 검출하고 교정했다. |
| 선택적 일반 증상 부재가 상세 패턴을 지움 | `differential.py:188` | 관찰된 전체 특징과 그 단편 비교에만 좁은 우선순위를 적용한다. 실제 양성의 직접 부정/특이 반증/독립 경쟁 근거는 보존한다. |
| 위험도 안전 장치가 진단 Top25를 교체 | `retrieval_pipeline.py:104`, `lightweight_rerank`; `candidate_generator.py` | Top150/Weighted RRF/진단 Top25 유지. 별도 safety watch는 점수·양성 근거가 아니다. 실제 근거가 생기면 기존 evidence rule로 재진입한다. legacy API 검사는 유지했다. |
| 실제 EXAM 소견이 검색에 전달되지 않음 | `clinical_presentation.py`; `candidate_generator.py:191` | 관찰된 EXAM에서 기존 catalog의 다단어 특징만 최대 12개 전달. 초기에 없던 pericarditis가 실제 friction rub 뒤 복귀. 부정/불확실/가족/미실시 대조군 유지. |
| 흉통 새 표현·한국어 구토 누락 | `feature_relations.py:observed_pressure_features`; `clinical_concepts.py` | sensation+anatomy와 pain+spread를 구성적으로 정규화. 위험 질환 개발 대조군 26개에서 critical 정답·urgent 유지. 한국어 '토하고/토했어요'를 실제 vomiting으로 인식한다. 진단이나 ECG 결과를 생성하지 않는다. |
| 복통의 severe/lower가 없는데 근거로 가산 | `feature_relations.py:RELATION_PATTERNS`; 공통 matching 보호 경로 | mild/diffuse만으로 severe diffuse 또는 lower abdominal을 만들지 않는다. 실제 강도·위치 양성, 부정·가족력 대조군과 alias 우회 검사를 추가했다. |
| 얕은 위험 대안의 공통 증상 하나가 응급 처분을 결정 | `disposition.py:72` | Tier-2/ontology 대안은 동반 양성, 현재 확정 문서, 실제 객관 소견 또는 기존 명시적 discriminator를 확인한다. 후보를 배제하지 않는다. 선택된 긴급 진단·활력징후/맥박 위험은 별도 유지. 이것은 임상 검증된 triage 기준이 아닌 엔지니어링 보호다. |
| 관찰된 맥박 위험의 ECG 계획 소실 | `soap.py:228` | 원인 미확정이어도 기존 증상성 맥박 위험이면 ECG 계획을 보존한다. 예선 TEST 수행/정상 ECG 생성은 하지 않는다. |

새 단위·회귀 검사: `tests/test_round_u_*.py`. 기존 테스트 삭제·단언 약화 없음. 기존 테스트 파일 수정은 verification v26 허용 추가뿐이다. 기존 평가 사례·정답·분모·제외·채점·시뮬레이터 응답은 그대로다.

## 반복 검증 중 철회한 후보

1. `1b892b3`: 모든 이상 활력징후를 너무 넓게 묶은 명명 억제로 예선 위험 사례 8개가 새로 틀렸고, 양성 식사 문법 검사 2개도 실패했다. 철회했다.
2. `966e992`: 중증도 회귀를 교정했지만 실제 bedside 소견 전달이 빠진 별도 재현 때문에 채택하지 않았다.
3. `de076f3`: U20 행동 58/59와 RoundJ_07의 새 오답을 확인했다. 단일 diarrhea와 음성-only 우선순위를 교정했다.
4. `8ba4792`: 넓은 회귀에서 흉통 표현 누락이 명명 억제와 결합하여 위험 사례를 틀렸다. 관찰된 압박감의 구성적 정규화와 한국어 구토를 보강했다.
5. `a84e07f`: U10 6/6·행동 29/30. 관찰되지 않은 severe/lower 복통 근거와 단일 공유 증상의 응급 대안 승격을 발견했다. 관련 장기 검사는 취소하고 별도 후보로 다시 검증했다.
6. 격리 실험 `development/single_symptom_prelim`은 실행 중 소스 변경을 기록기가 감지하여 최종 근거에서 제외했다. 통과 숫자로 재사용하지 않았다.

최종 `da7cfca7eb80f09af82019326f9964a285946f1d` 이후 runtime 수정 없음. 중간 실패·취소와 최종 결과를 분리했다. U20/U12/U10은 결과를 수정에 사용했으므로 개발 자료이며, Closing U8만 마지막 소스에서 처음 실행했다.

## 동일 조건 성능

| 세트 | 총/채점 | 정답 전→후 | 위험 정답 전→후 | 평균 턴 전→후 | 최대 턴 전→후 | 새 오답 |
|---|---:|---:|---:|---:|---:|---|
| 예선 개발 | 230/222 | 209→209/222 | 85→85/85 | 19.95→20.33 | 33→34 | RoundM_066 |
| Round P 개발 | 34/32 | 26→27/32 | 11→11/13 | 21.29→21.85 | 34→34 | 없음 |
| Round Q 개발 | 48/36 | 35→35/36 | 11→11/11 | 20.65→20.83 | 36→34 | 없음 |
| R 개발 | 24/12 | 12→12/12 | 4→4/4 | 26.79→26.83 | 37→36 | 없음 |
| S 개발 | 24/14 | 14→14/14 | 4→4/4 | 24.58→26.46 | 35→40 | 없음 |
| 이전 수용 회귀 | 32/18 | 16→16/18 | 4→4/5 | 26.41→26.84 | 36→36 | 없음 |
| T 개발 | 32/18 | 15→15/18 | 3→3/3 | 24.75→25.16 | 34→34 | 없음 |
| T 확인→개발 | 12/8 | 7→8/8 | 4→4/4 | 24.33→22.83 | 31→29 | 없음 |
| T probe→개발 | 8/4 | 4→4/4 | 2→2/2 | 25.50→25.88 | 37→37 | 없음 |
| T postfreeze→개발 | 12/6 | 6→6/6 | 3→3/3 | 23.75→24.25 | 32→32 | 없음 |
| U20→개발 | 20/12 | 12→12/12 | 4→4/4 | 25.10→23.75 | 33→33 | 없음 |
| U12→개발 | 12/6 | 6→6/6 | 2→2/2 | 20.42→18.92 | 33→34 | 없음 |
| U10→개발 | 10/6 | 6→6/6 | 2→2/2 | 18.40→18.40 | 32→29 | 없음 |
| 새 Closing U8 | 8/4 | 4→4/4 | 2→2/2 | 22.75→21.25 | 32→29 | 없음 |

| 세트 | 행동 계약 전→후 | 반복 행동/의미 중복 후 | 규칙/형식/SOAP 미지원 후 | 미해결 위험 대안 사례 전→후 |
|---|---:|---:|---:|---:|
| 예선 개발 | 별도 요약 참조 | 0/18 | 0/0/0 | 91→90/230 |
| Round P 개발 | 별도 요약 참조 | 0/3 | 0/0/0 | 12→9/34 |
| Round Q 개발 | 별도 요약 참조 | 0/2 | 0/0/0 | 14→18/48 |
| R 개발 | 19/19→19/19 | 0/3 | 0/0/0 | 24→24/24 |
| S 개발 | 87/87→87/87 | 0/2 | 0/0/0 | 24→24/24 |
| 이전 수용 회귀 | 14/14→14/14 | 0/1 | 0/0/0 | 32→32/32 |
| T 개발 | 89/89→89/89 | 0/1 | 0/0/0 | 32→32/32 |
| T 확인→개발 | 31/31→31/31 | 0/0 | 0/0/0 | 12→12/12 |
| T probe→개발 | 23/23→23/23 | 0/0 | 0/0/0 | 8→8/8 |
| T postfreeze→개발 | 33/35→35/35 | 0/0 | 0/0/0 | 12→12/12 |
| U20→개발 | 55/59→59/59 | 0/0 | 0/0/0 | 20→20/20 |
| U12→개발 | 34/38→38/38 | 0/0 | 0/0/0 | 4→4/12 |
| U10→개발 | 27/30→30/30 | 0/0 | 0/0/0 | 5→5/10 |
| 새 Closing U8 | 25/26→26/26 | 0/1 | 0/0/0 | 3→4/8 |

규칙/형식/SOAP 미지원은 각각 위반 수, malformed 수, 지원되지 않은 SOAP 줄 수다. SOAP 보존 지표는 고정 시뮬레이터의 관찰 보존 검사이며 임상적 완전성 인증이 아니다. 반복 행동과 의미 중복은 다른 지표다. 미해결 위험 대안은 미검사·미확인 후보를 음성으로 처리하지 않았음을 포함하며, 그 수만으로 임상 안전을 판정할 수 없다.

새 정답/새 오답/진단명이 바뀐 사례 전체는 `artifacts/round_u/final/comparison.json`에 보존한다. 예선 초기 Round P의 215/222와 직접 혼합하지 말아야 한다. 이번 직접 비교 기준선은 Round T의 209/222다.

### 남아 있는 중요한 실패

- ValP_10은 양성 근골격 라벨인데 Tension Pneumothorax를 명명한다. `chest pain after trauma`라는 공유 근거 하나의 과잉 명명은 남아 있다.
- Fresh05는 insulin pump 중단, type 1 diabetes, polyuria/polydipsia와 관찰된 호흡 소견이 있지만 Acute Pancreatitis를 1위로 출력한다. DKA 후보는 2위다. 긴급 평가·glucose/ketone 계획은 보존되지만 위험 라벨 오답은 여전하다. Fresh16의 일반 위장관 소견도 pancreatitis로 명명한다.
- ValP_12의 전해질 라벨/미분화, ValP_17의 맥박·실신/원인 미확정, ValP_21의 acute abdomen/구체 원인 계층 차이, ValP_08의 심부전/폐렴 공유 소견은 해결 완료로 표시하지 않는다.
- RoundM_066 예선에서 단일 diarrhea 뒤 기존 gastroenteritis 라벨 대신 미분화로 끝나는 손실은 평가 점수상 회귀다. 단일 증상으로 원인을 확정하도록 되돌리거나 라벨을 고쳐 숨기지 않았다.

이 목록은 기존 실패가 남아 있다는 뜻이며, 이번 새 critical regression 여부와는 다른 지표다. 상세 동작 명세·수정 위치·대조군은 후속 작업서에 기록했다.

### TEST 허용 개발 회귀

| TEST 허용 세트 | 정답 전→후 | 위험 정답 후 | 새 오답 |
|---|---:|---:|---|
| held_out | 17→17/18 | 13/13 | 없음 |
| generalization_v2 | 18→18/18 | 5/5 | 없음 |
| stress | 8→8/8 | 5/5 | 없음 |
| round_d | 6→6/7 | 3/3 | 없음 |
| round_e | 6→6/7 | 5/5 | 없음 |
| round_g | 12→12/12 | 4/4 | 없음 |
| round_i | 18→18/20 | 8/8 | 없음 |
| round_j | 51→51/54 | 20/20 | 없음 |

Round M: 114→115/123, 위험 43/43. 평균 턴 22.55→22.91; 평균 TEST 6.97→7.02. 새 오답 `[]`.

## 검색과 long-tail

| 측정 | 전 | 후 |
|---|---:|---:|
| 주호소만 / 164 개발 proxy Top150 | 117/164 (71.34%) | 118/164 (71.95%) |
| 주호소만 / 164 개발 proxy 진단 Top25 | 103/164 (62.80%) | 117/164 (71.34%) |
| 전체 scripted history / 상한 proxy Top150 | 152/164 (92.68%) | 152/164 (92.68%) |
| 전체 scripted history / 상한 proxy 진단 Top25 | 128/164 (78.05%) | 151/164 (92.07%) |
| M 종료 시 Top150 | 116/123 (94.31%) | 117/123 (95.12%) |
| M 종료 시 진단 Top25 | 100/123 (81.30%) | 114/123 (92.68%) |
| M 종료 시 active | 123/123 (100.00%) | 123/123 (100.00%) |

초기 주호소 proxy와 전체 scripted-history 상한은 자율 진료 성적이 아니다. 후자의 정보는 에이전트가 실제로 모두 얻었다는 뜻이 아니다. M 종료 시 retention도 초기 retrieval과 구분했다. 지표 정의와 분모를 바꿔 개선으로 만들지 않았다.

초기 주호소 Top150 90%, Top25 80% 목표는 **미달**이다. 종료 시 높은 retention으로 초기 손실을 숨기지 않는다. 위험 recall도 예선 85/85만으로 전체 세트 97% 이상 달성을 주장하지 않는다. P와 이전 수용 세트에는 기존 위험 오답이 남아 있다.

M long-tail 26개: Top1 17→18/26, Top5 21→21/26, Top10 23→23/26. 검색 개선과 최종 진단 개선을 혼동하지 않는다.

M의 long-tail 이외 공통/대조군 97/97은 유지했다. 반면 long-tail만의 종료 시 Top25 retention은 25/26→24/26으로 낮아졌다. RoundM_106(Pelvic Inflammatory Disease)이 새로 Top25 밖에 있지만 active 후보로 보존되어 최종 정답은 유지했다. 전체 rerank 개선으로 이 하위 집합의 손실을 숨기지 않는다. TEST 허용 Round J는 54개 분모이며 예선의 채점 52개와 다른 평가다.

이번에 새로 임상 깊이를 검증해 추가한 질환 프로필: **0개**. 전체 34 Tier-1/1,246 Tier-2/1,280개 유지. 기존 enrichment 파일 항목 83개, 항목 없는 Tier-2 1,163개. 83이라는 수는 임상 완성/의미 있는 감별 검증 수가 아니다. 얕은 이름을 새 사실로 채우지 않았다. 초기 검색과 장기 꼬리 진단의 남은 한계는 후속 작업서에 분리했다.

## 새 확인 세트의 사용 이력과 한계

| 세트 | 총/채점 | 사용 상태 |
|---|---:|---|
| U20 | 20/12 | 동결 후 재현 결과를 수정에 사용 → 개발 |
| U12 | 12/6 | 동결 후 결과를 수정에 사용 → 개발 |
| U10 | 10/6 | 동결 후 처분 실패를 수정에 사용 → 개발 |
| Closing U8 | 8/4 | 최종 소스 동결 후 최초 실행. 이후 runtime 변경 없음 |

Closing fixture SHA256: `47a0be58b0754a70f04a6289dfb763bda4640c751221c0da9f00a98e04583752`. 각 manifest는 작성 시각과 노출 범위를 기록한다. 모든 작성자가 구현과 기존 실패를 보았으며 독립 임상 평가가 아니다. 작은 기전 대조군으로 일반 환자 정확도나 실제 모델 성능을 추정할 수 없다.

ClosingU_05는 원인이 특정되지 않은 복막 자극 소견의 안전 대조군이다. 사전 계약은 긴급 처분이며 진단 보류 강제가 아니다. 따라서 채점 제외의 모든 명명을 일률적으로 과잉 진단으로 계산하지 않는다. 나머지 명명 보류 계약과 위험 대안의 잔존은 별도로 확인한다. 고정 evaluator의 premature 지표도 그대로 보존한다.

## 테스트·패키지·출처

- 최종 전체 tests/: **2425 passed / 0 failed / 1 skipped / 0 deselected**. runtime, research, release binding의 고유 테스트를 합쳤다. 최초 전체 실행의 package-not-built skip 1개는 감사된 동일 ZIP 배치 후 해당 검사만 다시 실행해 PASS로 완료했다. 원래 JUnit과 보충 JUnit을 모두 보존하고 중복 합산하지 않았다.
- skipped: `[{"test": "tests.test_learning_training.test_torch_training_and_checkpoint_roundtrip", "reason": "torch not installed (IMPLEMENTED_BUT_NOT_EXECUTED)"}]`. 모델 다운로드·교체·훈련으로 skip을 숨기지 않았다.
- 98 tracked runtime 파일 및 launcher/requirements 2개: 커밋·원본·제출 mirror·ZIP 바이트 연결. 아카이브 101개, 830977 bytes, SHA256 `b5c2c704c9463b9f12d941cf97e1997986faf245daa7d604ff2ddc1fffb39369`.
- 격리 worktree에서 빌드했다. 비밀 문자열/금지 파일/학습 코드 포함 감사, ZIP 검증, 독립 디렉터리 mock 전체 encounter를 수행했다. `run.py`의 공식 경로는 NOT READY로 차단된다.
- 해시 기록은 tracked source를 기준으로 한다. 작업 공간의 임시 복사본이 소스/로그로 혼입되는 것을 막고, 실행 종료 시 출력·exit code·조건·전후 runtime hash를 함께 기록한다. 이 변경은 검증 도구의 기록 방식이며 채점 변경이 아니다.
- 임상 출처/정규화 범위: `ROUND_U_PROVENANCE.md`. provenance inventory hash 갱신은 출처 사용권이나 임상 검토 상태를 상향하지 않는다.
- provenance coverage는 PASS지만 permission 상태는 BLOCKED다. 패키지 무결성 PASS는 공식 제출 허가나 임상 안전 승인이 아니다.
- 부정문 대조 10/10, adversarial 12개 검사 PASS. 특징 specificity·routing·retrieval·정적 leakage 검사도 실행했다. `failure_analysis`는 정상 종료했지만 채점 제외 정보부족 `Headache02_InsufficientInfo`에서 Bacterial Meningitis 명명이 남음을 보고한다. 실행 성공을 진단 정확도 PASS로 바꾸지 않는다.
- Blind v18/v19 실행·튜닝·새 blind 생성 없음. `check_eval_leakage.py`는 정적 비교만 수행했다.
- 실제 GPT-OSS / 공식 API 호출·정확도 / 독립 임상 검증: **미검증**.

공개 범위는 소스·새 합성 fixture·읽을 수 있는 보고서·집계 요약이다. 이전 자동 승인 검토의 상세 traces/XML/ZIP 공개 제한을 유지한다. 공개 CURRENT_RELEASE 포인터는 역사적 기록을 보존하며 현재 공개 소스 전체를 인증한다고 표시하지 않는다. 로컬 v26의 실행 SHA와 공개 소스의 byte parity는 별도 기록한다.

후속 작업: [ROUND_U_FOLLOWUP_KO.md](ROUND_U_FOLLOWUP_KO.md). 구현 프롬프트: [ROUND_U_IMPLEMENTATION_PROMPT_KO.md](ROUND_U_IMPLEMENTATION_PROMPT_KO.md).
