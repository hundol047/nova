# Round Q — 기술 검토 지적 결함 수리 보고서

> 모든 수치는 `NOVA_LLM_PROVIDER=mock`(결정적 mock)과 저자가 작성한 합성 사례로 측정했습니다. 실제 LLM 성능, 공식 점수, 임상 정확도가
> 아닙니다. 외부 LLM/API·키·모델 다운로드/교체/학습은 사용하지 않았고, 예선 TEST 없음은 그대로입니다. 공식 프로토콜과 실제 고정 모델은
> 여전히 **NOT VERIFIED**입니다. 정답·분모·제외 기준·채점·기존 시뮬레이터 응답은 바꾸지 않았습니다.

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `claude/determined-brahmagupta-wrfveb` |
| 시작 HEAD / 원격 | `ead1595de52f7f17d4a6b9283477ade502e18193` (원격 추적 브랜치와 동일, 작업 트리 clean, `origin/main`은 조상) |
| 최종 런타임 | `8257ba617802d5f2f2221b20717a3d1cd9b79277` (릴리스 레코드 v22: `artifacts/verification/local-release-8257ba6-v22.json`) |
| AGENTS.md | 저장소에 없음. `docs/CURRENT_STATUS.md`를 기준으로 확인 |
| 첨부 자료 | 기술 검토 보고서와 수정 작업서(Markdown 2개)만 업로드됨. 보고서가 언급한 재현 스크립트·evidence JSON·로그는 첨부되지 않아, 보고서의 표를 근거로 재현 스크립트를 새로 작성했습니다(`artifacts/round_q/repro/reproduce_review_defects.py`). |

## 1. 재현 (수정 전 `ead1595`)

`artifacts/round_q/repro/before_ead1595.txt` — 보고서의 지적을 그대로 가정하지 않고 실행으로 확인했습니다.

| 결함 | 수정 전 실측 |
|---|---|
| 문서 진단 범위 | 보고서 표의 12개 입력 중 **1개만** 기대와 일치. "was excluded"·"아니라고"·"cannot be excluded"·"의심"·가족력·2016년 과거 상태가 모두 긍정 문서 진단으로 집계되고, 엔진에서도 `documented diagnosis` +1.0점과 후보 주입이 발생 |
| 리듬 과대 해석 | `irregular rhythm with occasional pauses`가 `irregularly irregular rhythm`(확진 소견, +2.5)으로 매칭. 반대로 명시적 "pulse is irregularly irregular"는 매칭 실패 |
| 관찰된 맥박수 | HR 37·HR 172(규칙적)가 파싱되지만 arrhythmia 근거 0 |
| Yes/No/모름 | "Yes"/"No"/"I don't know"가 질문 대상과 무관한 `Yes`/`No` 소견으로 저장. "I cannot remember their names"가 약물 기록이 됨 |
| 종료 우회 | ValP_33: 점수 0·근거 없음·StopPolicy 거부인데 `not scored` 분기로 급성복증 진단. ValP_34: 어지럼 하나로 자궁외임신 |
| metadata–출력 불일치 | 모든 최종 진단에 `INSUFFICIENT_INFORMATION`이 있으나 primary·SOAP·설명은 구체 위험 진단. 설명이 "septic shock", "atrial fibrillation"으로 좁아짐 |

## 2. 수정 내용 (커밋 순)

1. **문서 진단 assertion 범위** (`4e9ad8f`) — `DiagnosisMention`(원문 offset, 근거 절, PRESENT/NEGATED/UNCERTAIN, CURRENT/HISTORICAL, PATIENT/FAMILY/OTHER, 임상의 보고/환자 추측). 불확실 복합구를 부정보다 먼저 소비, but/however로 술어 분리, 목록 항목은 술어 공유, 같은 진단의 마지막 진술 우선(충돌은 보존). 임상의가 기록한 현재·환자·PRESENT만 근거. 답변은 부정 분할 조각이 아닌 원문 전체로 읽음. `documented_diagnosis_ids()` 하위 호환.
2. **표현·답변** (`8ec8fe3`, `3510e89`, `67c586c`) 
   - `irregularly irregular`은 보호된 한정어(어간 처리 자체는 그대로). 일반 불규칙 맥은 `irregular heartbeat`에만 연결.
   - 현재 측정 HR <50 / ≥150을 rate 소견으로 보존(AHA 2020 성인 서맥/빈맥 알고리즘의 리듬 원인 시사 기준, KB에 출처 기록). 생리적 징후와 같은 낮은 가중치로만 반영하고 아형(AF/VT/AV block)은 만들지 않음.
   - "A or B" KB 문구는 존재 판정에서만 분기(부정 판정은 전체 문구).
   - 제한된 관찰 표현: reduced power→근력 저하, lightheaded, convulsive fit(단독 "fit"은 제외), heart took off, 투석→CKD(KDIGO G5D), missed dialysis(UKKA 고칼륨혈증 지침), 즉시 발생 두통→sudden onset severe headache, 한국어 심장 박동·배뇨 표현, 구조적 심질환(ESC 2018 실신 지침).
   - **답변 grounding (`NOVA_ANSWER_GROUNDING`)**: 단순 예/아니오/모름은 실제로 보낸 질문의 단일 feature에만 연결. 30자 안에 담기지 않아 일반 질문으로 나간 경우 일반 질문으로 기록하고 상세 판별 질문을 했다고 표시하지 않음. 모름은 unknown으로 보존. 이미 환자가 말한 내용과 충돌하는 단순 "No"는 부정이 아닌 충돌로 기록하고, 이후 환자가 직접 말하면 앞선 단순 부정을 철회(명시적 부정은 철회하지 않음).
3. **종료와 최종 결정** (`3ae7cf1`, `3510e89`, `37459bc`) 
   - **`NOVA_FINAL_DECISION`**: 종료 이유(supported / information_exhausted / budget)와 "구체 진단을 이름 붙일 근거"를 분리. 근거 없음, 위험 진단인데 일반 증상 하나뿐, 위험 진단이 일반 근거로만 동점, 필수 현재 맥락 없음(고혈압성 응급: 측정 혈압 ≥180/120, 객혈: 실제 혈담, SIADH: 저나트륨 기록, 자궁외임신: 임신 관련 소견 — 각 출처 기록)이면 이름을 붙이지 않고, 상위 5위 안에 더 잘 지지되는 후보가 있으면 그 후보, 없으면 "미분화 증상(진단 미확정)" 단일 완료값(`unknown`). 후보를 삭제하거나 부재로 만들지 않음.
   - 하나의 최종 결정이 primary·SOAP A(상태 문구 포함)·closing SAY·metadata(`final_decision`, `completion_reason`)를 모두 생성. 설명은 같은 범위의 이름만 사용(좁은 별칭 금지, 앞의 중증도 수식어만 생략 가능)하거나 이름 없는 정직한 문장.
   - 예선 'addressed'는 실제로 관찰된 EXAM만 인정(거절·결과 불명은 차단 상태로 남김).
   - 종료 직전, 실제 근거가 있는 위험 대안의 남은 침상 EXAM 하나를 먼저 수행.
   - 일반 질문으로만 나갈 수 있는 상세 질문은 일반 질문 키로 보내고, 이미 물었으면 다시 보내지 않음.
4. **평가 도구(별도 커밋 `f4cc800`)** — `--unscripted-unknown` 선택 옵션: 스크립트에 없는 질문에 기본 "No" 대신 "잘 모르겠다"로 답. 기본값 OFF, 동결 결과에는 사용하지 않음.
5. **누출 방지** (`173c183`, 동기화 `d662a6e`) — `check_eval_leakage.py`가 지적한 별칭 3개(reference blind 문장과 우연히 겹침, blind 파일은 열람하지 않음) 제거.

재현 결과(`artifacts/round_q/repro/after_3510e89.txt`): 문서 진단 12/12 일치, 일반 불규칙 맥 → 일반 근거만, HR 37/172 → rate 근거, 단순 답변이 질문 feature에 연결, 미확인 약물명 → 약물 기록 없음, ValP_33/34 → 미분화 완료와 정직한 설명, closing에서 AF·septic shock 사라짐.

## 3. 결과 — 예선 조건 230건 (동결 시뮬레이터, competition retrieval)

| 지표 | 기준 `ead1595` | 최종 `8257ba6` |
|---|---|---|
| Top-1 | 215/222 | **202/222** |
| 치명적 Top-1 | 84/85 (RoundJ_25 누락) | **85/85** |
| 평균 / 최대 상호작용 | 21.13 / 40 | 19.65 / 35 |
| 불필요 EXAM / 의미 중복 질문 | 404 / 100 | 297 / 11 |
| 규칙 위반 / SOAP 근거 없는 줄 | 0 / 0 | 0 / 0 |
| 정답 미정 사례에 위험 진단 명명 | 7 | **0** (8건 모두 미분화 완료) |
| 비위험 정답에 위험 진단 | 3 | 3 |
| 채점 사례가 미분화로 끝남 | 0 | 6 |
| 진단 시 미해결 위험 대안이 남은 사례 | 61 | 76 |

- **새로 맞음**: RoundJ_25(치명적). **새로 틀림 14건(모두 비치명적)**:
  - 12건(RoundM_026·098·099·101·103·104·109·110·112·115·116·117): 동결 시뮬레이터가 스크립트에 없는 질문에 "No"를 돌려주는데, grounding 후 그 "No"가 실제 부정이 됨. 예: 담낭염 사례에서 "right upper quadrant pain?" → "No". 이 12건은 `--unscripted-unknown` 변형에서 모두 다시 맞습니다(평가 도구 문제).
  - RoundM_024: 기준선은 일반 불규칙 맥을 AF 확진 소견으로 **잘못** 읽어 맞았음. 요청된 과대 해석 수정의 결과.
  - RoundM_095: 1위가 "no hearing loss"(부재 소견)만으로 지지됨 → 미분화 완료.
- **EXAM 거절 시나리오**: 213/222, 83/85 → 201/222, **85/85**(RoundM_087 회복).
- **평가 도구 변형(`--unscripted-unknown`)**: 기준 215/222, 84/85 → 최종 213/222, 84/85. 새로 틀림 RoundM_024·095(위 설명).
- **Ablation**: grounding OFF 213/222·84/85, 최종 결정 OFF 203/222·85/85(정답 미정 사례 위험 진단 7건 재발).

## 4. 결과 — 별도 표 (TEST 허용 / legacy / 검증 세트)

**TEST 허용 회귀(competition retrieval, `evaluate_pre_guide_regressions.py`)**: 8개 세트 정확도·치명적 재현율 모두 동일, 새로 틀림 0, 평균 턴은 전 세트에서 감소(예: held_out 28.8→26.8, round_e 30.1→27.3).

**legacy 개발 세트(legacy retrieval, TEST 허용)**: Blind v5·Round M/J/N/O 포함 전 세트 정확도·치명적 재현율·턴 동일, 사례 변화 0.

**같은 세트를 competition 모드(TEST 허용)로**(기준선도 같은 모드로 재실행): **치명적 회귀 2건** — RoundM_096(지주막하출혈→수막염), ValO_11(폐색전증→폐렴). 둘 다 정의 소견("sudden onset severe headache", "sudden onset dyspnea")을 묻는 질문에 시뮬레이터 기본값 "No"가 와서 반대 근거가 된 경우입니다. 비치명적 회귀는 대부분 위 12건과 같은 원인. RoundM_087은 새로 맞음. 임의 가중치로 숨기지 않았고 **이 구성에서는 통과로 선언하지 않습니다.**

**Round P 동결 세트(34건, 이제 개발 자료)**: 24/32·9/13 → **28/32·11/13**, 새로 틀림 0(ValP_11·13·16·17 새로 맞음). EXAM 거절: 23/32·8/13 → 27/32·10/13. 남은 치명적 누락 ValP_12(SIADH 대신 수막염), ValP_21(급성복증 계층).

**새 대조 개발 세트** (`evaluation/dev_cases_round_q.py`, 48건 = 채점 36 + 기대 행동 12, 동결 sha256 `bbc03df6…`):

| 지표 | 기준 `ead1595` | 최종 |
|---|---|---|
| 채점 Top-1 / 치명적 | 27/36 / 9/11 | **33/36** / 9/11 |
| 기대 행동 충족(미채점 12) | 5/12 | **11/12** |
| 정보 부족 사례에 위험 진단 | 9 | 3 |
| 미분화 완료(미채점) | 0/12 | 6/12 |

남은 오답 DevQ_22(한국어 전해질→위장염), DevQ_28(서맥 실신→미주신경성), DevQ_44(급성복증→위장관 출혈). 미충족 DevQ_33(이소성 박동을 부정맥으로 명명).
**공개**: 이 세트는 수정을 설계한 뒤 같은 에이전트가 작성한 개발 자료이며, 첫 실행 후 그 사례에서 드러난 표현 별칭 5개(both sides pressing, screens, can't stand the heat, something terrible will happen, tingling fingers)와 한국어 박동·배뇨 표현을 추가했습니다. 따라서 위 수치는 일반화 근거가 아닙니다.

## 5. 테스트와 패키지

- 전체 `pytest tests` (최종 런타임, mock): **2018 passed, 0 failed, 1 skipped**(torch 미설치 학습 테스트), **3 deselected**(릴리스 레코드·인벤토리 테스트, v22 기록 후 별도 실행).
- 신규 테스트: `tests/test_documented_diagnosis_assertion_scope.py`(64), `tests/test_round_q_expression_answers_final_decision.py`(61).
- 제출 동기화: `submission/nova_agent`·`submission/competition` 94개 파일이 런타임과 **SHA-256 바이트 동일**(파일 집합 동일).
- 패키지: `artifacts/verification/nova-pre-guide-v22.zip` 809,590 bytes, sha256 `d92f9c57b38737e9003d60f091a269d16939956fceee7d8de8b7a2d2f239f03f`; clean-room 전 항목 PASS, fresh-directory smoke OK(`run.py` fail-closed), package audit PASS, `check_eval_leakage` 이상 없음, 인벤토리 `--check` 0건, README 수치 일치, 임상 검토 항목은 모두 PENDING.

## 6. 남은 문제와 다음 우선순위

1. **평가 도구**: 스크립트 없는 질문에 "No", 숨은 key 기준 응답, 넓은 EXAM 응답 — grounding이 올바르게 동작할수록 동결 결과가 나빠지는 원인입니다. 사실의 known/unknown 구분과 실제 질문 의도 기준 응답을 별도 평가 버전으로 만들어야 합니다(이번에는 선택 옵션만 추가).
2. **TEST 허용 competition 모드 치명적 회귀 2건**(RoundM_096, ValO_11) — 위 1과 같은 원인. 미해결.
3. 미분화 완료가 채점 사례 6건에서 발생(근거 0 또는 부재 소견뿐인 1위) — 근거 수집 부족을 드러내는 것이지 해결은 아닙니다.
4. 진단 시 미해결 위험 대안 61→76: 거절·불명 EXAM을 더 이상 'addressed'로 세지 않은 결과. 보조 지표 분해(실행 가능/차단/반증)가 필요합니다.
5. 서맥 실신(DevQ_28), 한국어 전해질(DevQ_22), 증후군↔원인 계층(ValP_21, DevQ_44), SIADH 대신 수막염(ValP_12).
6. 세부 질문(구토/설사/섭취, 투석 일정, 약물 변경 시점) 생성은 이번에 구현하지 않았습니다(작업서 2D).
7. 실제 고정 모델과 공식 인터페이스 검증은 여전히 하지 않았습니다.

부수 사항: 중단된 실행 하나가 컨테이너 루트(`/`)에 무효 출력 파일 3개(`/prelim_exam_rejection.json`, `/prelim_exam_rejection.txt`, `/prelim_unscripted_unknown.txt`)를 남겼습니다. 저장소 밖이며 아무 곳에서도 쓰이지 않습니다. 루트 삭제는 안전 장치로 막혀 있어 남겨 두었습니다.
