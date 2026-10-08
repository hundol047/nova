# Round P — 예선 조건 오프라인 진단 성능 개선 보고서

> **모든 수치는 `NOVA_LLM_PROVIDER=mock`(결정적 mock 모델)과 저자가 작성한 합성 사례로 측정했습니다.**
> 실제 LLM 성능, 공식 대회 점수, 임상 정확도가 아닙니다. 외부 LLM 연결·API 키·모델 다운로드/교체/학습·공식 프로토콜 추측은 하지 않았습니다.
> 공식 규칙(턴 수, EXAM 허용 범위, 채점 방식)은 여전히 **미확인**이며 `evaluation/preliminary_driver.py::ORGANIZER_ASSUMPTIONS`의 가정을 그대로 사용했습니다.
> 예선 230건, Blind v5, Round N/O 세트는 모두 **개발·회귀 세트**입니다. 미사용 blind 성능으로 해석하면 안 됩니다.

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `claude/determined-brahmagupta-wrfveb` |
| 기준선 커밋 | `10e7de76f96eb42dc6ac8443fc1bc91077712dd2` (런타임 `f86bfcc`, 패키지 v20) |
| 최종 런타임 커밋 | `383155565a542ccd229edbf42f1fc02dfc29ccc2` (릴리스 레코드는 `artifacts/verification/CURRENT_RELEASE.json`이 가리키는 v21) |
| 원격 확인 | 작업 시작·종료 시 `origin/main`(`0ce4dc7`)은 HEAD의 조상이고, 원격 작업 브랜치에 로컬에 없는 커밋은 없었습니다. main으로 reset하거나 기존 변경을 덮어쓰지 않았습니다. |
| AGENTS.md | 저장소의 어느 브랜치에도 없습니다. `docs/CURRENT_STATUS.md`를 기준 문서로 읽었습니다. |

## 1. 기준선 재현

지시된 명령 `NOVA_LLM_PROVIDER=mock NOVA_COMPETITION_RETRIEVAL=1 python scripts/evaluate_preliminary_benchmark.py --workers 2 --gate`을
`10e7de7`의 깨끗한 worktree에서 실행해 제시된 기준선을 그대로 재현했습니다(`artifacts/round_p/baseline/prelim.json`).

| 지표 | 제시값 | 재현값 |
|---|---|---|
| Top-1 | 204/222 (91.9%) | 204/222 |
| Top-3 | 211/222 | 211/222 |
| 치명적 진단 재현율 | 80/85 | 80/85 |
| 평균 / 최대 상호작용 | 21.7 / 41 | 21.74 / 41 |
| 규칙 위반 / SOAP 근거 없는 줄 | 0 / 0 | 0 / 0 |

## 2. 새 검증 세트 동결 (변경 전)

| 항목 | 값 |
|---|---|
| 파일 | `evaluation/validation_cases_round_p.py` — 34건(scored 32, 치명적 13, 정답 미정 sparse 2) |
| SHA-256 | `82f82ffc4b6759179d039f566aadeed29cbae1365e9955c85210bd004118cda6` (`evaluation/validation_round_p_manifest.json`) |
| 동결 시점 | 커밋 `7020d17`, 부모 `10e7de7` — 알고리즘 변경 전. 이후 파일은 한 번도 수정되지 않았습니다(최종 시점 해시 재확인). |
| 범주 | 수막염/SAH/양성 두통, PE/심장/양성 흉통(흉막성 포함), 전해질 vs 내분비, 부정맥 vs 양성, 복부, 패혈증 vs 국소 감염, 뇌졸중 vs BPPV, 부정·과거력, 다증상, 한국어, 정보 부족 |
| 작성 방법 | 엔지니어링 에이전트 **단독 작성**(독립 작성자 없음). 사례 문장을 쓰기 전에 정답 라벨을 고정했고, 임상의 검토는 없습니다. |
| 사용 | 기준선 1회, 최종 런타임 직전(`0e6f800`, `730230c`) 및 최종(`3831555`)에서 측정. 각 측정 후 이 세트를 근거로 코드를 고치지 않았습니다(아래 §8 공개 사항). |

## 3. 지정 실패 사례 원인 분석 (단계별)

| 사례 | 기준선 출력 | 단계 | 원인 |
|---|---|---|---|
| PrelimKo_Fever_Meningitis | SAH | 근거 해석 | 한국어 "점상 출혈", "의식 저하/졸려"가 영어 개념(petechial rash, altered mental status)으로 연결되지 않아 수막염 고유 근거가 0. 공통 근거(경부강직·광선공포)만 남아 구토가 있는 SAH가 앞섬. 정답 순위 2. |
| RoundM_018 | 비후성 심근병증 | 근거 해석 + 순위 | "racing heart" 미인식, PE의 KB 전형 소견에 빈호흡·저산소가 없음 → PE 근거는 위험인자뿐(정답 순위 10). 증상 2개뿐인 HCM이 위험인자·객관 소견이 수렴하는 PE를 앞섬. |
| RoundM_041 | SIADH | 근거 해석 | "water tablet"(이뇨제)을 약물로 인식하지 못함. 같은 증상(혼돈·오심)만으로 SIADH가 앞섬. 정답 순위 7. |
| RoundM_054 | 부신 위기 | 후보 생성 | "generally weak and muddled" → 전신 쇠약 개념이 없어 중증 전해질 이상이 후보 목록에 아예 없음(정답 순위 없음). |
| RoundJ_25 | 천공성 소화성 궤양 | **명칭 계층** | 정답 라벨은 상위 범주 "급성복증", 출력은 그 하위의 구체적 원인. 근거(경직·반발통)는 둘 다 지지. 더 모호한 진단을 내도록 바꾸거나 매칭을 넓히지 않았습니다. |
| ValO_26 (Round O, TEST 허용) | 공황발작 | 근거 해석(검사 방향) | 질환이 저칼륨·고칼륨 양방향을 모두 확진 소견으로 가지는데, 저칼륨 결과가 "hyperkalemia" 문구의 **반대 근거**로 채점됨. |
| ValO_30 (Round O, TEST 허용) | 위장관 출혈 | 근거 해석 | "racing heart"를 빈맥성 부정맥 증상으로 인식하지 못함. |

## 4. 변경 사항 (모두 스위치로 끌 수 있고 기본 ON)

사례 ID·정답·사례 문장에 따른 분기는 없습니다. 시뮬레이터, 라벨, 분모, 채점, 동의어 매칭(`same_diagnosis`)은 바꾸지 않았습니다. 실행 중 평가 파일을 읽지 않습니다.

1. **`NOVA_EVIDENCE_V3` — 근거 해석**
   - 개념 추가: 이뇨제 사용(water tablet/pill, thiazide, furosemide …; **"stopped/ran out" 문맥이면 현재 사용으로 보지 않음**), 전신 쇠약, 불규칙 심박(리듬 명사 필수: "irregular bowel habit"은 제외), 빠른 심박(racing/pounding heart), irregularly irregular, 피로(washed out, wiped out …).
   - 한 관찰은 한 개념: "irregularly irregular"는 일반 "불규칙 심박"으로 이중 계산하지 않음.
   - 한국어 직접 매핑: 점상 출혈/자반, 졸려/기면/의식 저하/혼미/지남력 저하, 이뇨제, 기운이 없다, 쥐가 나다, 맥이 불규칙.
   - 복용 약물에 개념을 붙이고, 동반 증상·pertinent positive를 위험인자 출처로 사용.
   - 양방향 검사(나트륨·칼륨 저/고 모두 확진): 관찰된 방향의 문구만 채점, 반대 방향은 반대 근거로 쓰지 않음. "hypokalemia/low potassium" 검사 매핑 추가.
   - 부분 매칭: 방향어(low/high 등)가 있는 특징은 같은 방향어가 있어야 함("takes a tablet for blood pressure"는 "low blood pressure"가 아님). 시간 패턴(episodic, sudden, chronic …)도 일치해야 함.
   - KB(제공처 메모 포함): 중증 전해질 이상 +hypokalemia/low potassium/prominent U waves, +muscle cramps; PE +tachypnea/hypoxia.
2. **`NOVA_RANKING_V3` — 순위**
   - 수렴 근거 우선: 위험 질환이 **4개 이상** 근거로 객관 소견과 위험인자 범주를 모두 갖추면, 증상만 2개 이하인 후보 위로 올림.
   - Round O escalation(전신 장기부전 소견 → 위험 전신 질환 우선)에 조건 추가: 위험 후보가 **국소 질환이 이미 쓰지 않은 자기 고유의 비일반적 근거**를 가져야 함. 패혈증의 lactate는 해당, 폐렴과 공유하는 흉막성 통증뿐인 PE는 비해당.
   - 같은 관찰 중복 배제: 구체적 객관 소견("irregularly irregular rhythm")이 있으면 같은 질환의 일반 증상("irregular heartbeat")은 추가 점수를 받지 않음.
3. **`NOVA_ACTION_V3` — 행동 선택**
   - 환자가 보고할 수 없는 소견(심잡음, 압통, 반사, 나트륨·칼륨 수치, ECG/CT …)은 SAY 질문으로 묻지 않음. "calf pain or tenderness"처럼 보고 가능한 부분이 있으면 질문 가능.
   - 예선(TEST 없음)에서 이런 객관 전용 판별 항목은 온톨로지 후보를 영구히 "미해결"로 묶어 두지 않음. KB 질환의 TEST 항목과 같은 정책이며, **음성 근거가 아니고 후보는 점수와 함께 감별에 남습니다.**
4. **`NOVA_STOP_V3` — 종료**
   - Round O 가드(위험 질환 1위는 객관적 확진이 있어야 조기 종료)는 그대로 두되, 예선 규칙에서 **침상에서 얻을 수 있는 최대 근거**(판별 EXAM 완료, 판별 질문 완료, 객관 소견 중 지지 항목 존재)가 갖춰지면 그 한 가지 가드만 우회.
   - 위험 **대안**이 실질 근거를 갖고 미해결이면 여전히 종료하지 않음(`dangerous_alternative_exists`, `pending_critical_alternative` 불변).
5. **`NOVA_DOCUMENTED_DX` — 문서화된 진단**
   - "referral letter says …", "diagnosed with …", "진단 받았" 같은 문맥의 진단명을 KB/카탈로그 이름으로 인식해 후보에 넣고 근거 1개로 계산. "?"·"possible" 같은 불확실 표현, "history of"(과거력)는 제외.

**되돌린 시도**: 부분 매칭에서 핵심 명사 일치를 요구하는 규칙은 5건을 새로 틀리게 해서(충수염 이동통 등) 제거했습니다. 이 규칙은 RoundJ_25를 맞혔지만 다른 사례 비용이 더 컸습니다.

## 5. 예선 조건 결과 (SAY/EXAM/DIAGNOSE, TEST 없음, 50턴, competition retrieval)

`artifacts/round_p/{baseline,final}/prelim.json`, 동일 명령(`--gate`), 230건(scored 222).

| 지표 | 기준선 `10e7de7` | 최종 `3831555` |
|---|---|---|
| **Top-1** | 204/222 (91.9%) | **215/222 (96.8%)** |
| Top-3 | 211/222 | 219/222 |
| **치명적 진단 재현율** | 80/85 | **84/85** |
| 평균 / 최대 상호작용 | 21.74 / 41 | 21.13 / 40 |
| 사례당 평균 EXAM | 5.67 | 5.51 |
| 불필요 EXAM(합계) | 428 | 404 |
| 의미 중복 질문(합계) | 104 | 100 |
| 규칙 위반 / malformed | 0 / 0 | 0 / 0 |
| SOAP 근거 없는 정보 / 정보 보존(최소) | 0 / 1.00 | 0 / 1.00 |
| gate 실패 | 없음 | 없음 |
| 비위험 정답에 위험 진단 출력(과잉 진단) | 6 | **3** |
| 진단 시 미해결 위험 대안(Top-2~5)이 남은 사례 | 51 | 61 (§7 참조) |

**새로 맞힘 11건 / 새로 틀림 0건**

- 치명적: PrelimKo_Fever_Meningitis, RoundM_018, RoundM_041, RoundM_054
- 비치명적: RoundM_026, RoundM_064, RoundM_070, RoundM_112, RoundJ_05, RoundJ_49, RoundJ_50

**남은 오답 7건**

| 사례 | 정답 → 출력 | 분류 |
|---|---|---|
| RoundJ_25 (치명적) | 급성복증 → 천공성 소화성 궤양 | 명칭 계층(§3) |
| RoundM_108 | 소화성 궤양 → 십이지장 궤양 | 명칭 계층(하위 진단 출력) |
| RoundM_105 | 난소 염전 → 자궁외임신 | 순위(정답 3위), 위험 과잉 진단 |
| RoundJ_51 | 메니에르 → 자궁외임신 | 순위(정답 2위, 동점), 위험 과잉 진단 |
| RoundJ_52 | 심막염 → 급성 관상동맥 증후군 | 후보 생성/근거(정답 24위), 위험 과잉 진단 |
| RoundM_069 | 급성 췌장염 → 십이지장 궤양 | 정보 부족(정답 9위) |
| RoundI_long_tail | 쇼그렌 증후군 → SJS | 후보 생성(정답 없음) |

**EXAM 거부 시나리오**(`--exam-rejection`, 가정된 미지원 EXAM 목록): Top-1 202 → **213/222**, 치명적 79 → **83/85**, 평균 21.87 → 21.37, 새로 틀림 0건. 추가 오답 RoundM_030(신우신염 → 담관염), RoundM_087(SAH → SIADH, 치명적)은 거부된 EXAM 결과를 쓸 수 없는 경우로, 거부된 EXAM을 결과로 취급하지 않습니다. 의미 중복 질문은 104 → 105로 1건 늘었습니다.

**단계별 진행**(예선 230건)

| 단계 | Top-1 | 치명적 | 평균 턴 | 비고 |
|---|---|---|---|---|
| 기준선 | 204 | 80/85 | 21.74 | |
| 1 근거·순위·질문 필터 | 209 | 84 | 21.86 | |
| 2 패턴·리듬 개념, 침상 종료 | 209 | 85 | 20.97 | 핵심 명사 규칙 포함(5건 악화) |
| 3 문서화 진단, 핵심 명사 규칙 제거 | 215 | 84 | 21.06 | RoundJ_25 다시 오답 |
| 4 한 관찰 1회, escalation 근거 조건 | 215 | 84 | 21.07 | TEST 허용 회귀 2건 해결 |
| 최종(§6·§7 수정 포함) | 215 | 84 | 21.13 | |

## 6. TEST 허용 회귀 세트 (예선과 별도 표)

`NOVA_COMPETITION_RETRIEVAL=1`, mock, `scripts/evaluate_pre_guide_regressions.py`(`artifacts/round_p/{baseline,final}/test_enabled_regressions.json`).

| 세트 | 정확도 | 치명적 재현율 | 평균 턴 |
|---|---|---|---|
| held_out (18) | 17/18 → 17/18 | 13/13 → 13/13 | 28.6 → 28.8 |
| generalization_v2 (18) | 18 → 18 | 5/5 → 5/5 | 23.4 → 23.2 |
| stress (8) | 8 → 8 | 5/5 → 5/5 | 18.9 → **22.8** |
| round_d (7) | 6 → 6 | 3/3 → 3/3 | 32.9 → 31.3 |
| round_e (7) | 6 → 6 | 5/5 → 5/5 | 30.1 → 30.1 |
| round_g (12) | 12 → 12 | 4/4 → 4/4 | 25.8 → 25.8 |
| round_i (20) | 18 → 18 | 8/8 → 8/8 | 18.8 → 19.6 |
| round_j (54) | 48 → **51** | 20/20 → 20/20 | 21.5 → 19.5 |

- 새로 맞힘: RoundJ_49, RoundJ_50, RoundJ_51. 새로 틀림 0건.
- stress 턴 증가는 Stress05(뇌졸중 + 기존 심방세동) 한 건: 8 → 41턴(정답 유지). 심방세동이 실제로 있어 부정맥 후보가 진짜 근거(irregularly irregular)를 얻고, 1–2위 차이가 종료 기준(1.0) 미만으로 남습니다. 기준을 낮추거나 이 조합을 특별 취급하지 않았고 남은 과제로 둡니다.
- 개발 중 잡아서 고친 회귀: 3단계에서 Fever06(폐렴 → PE 과잉 격상)과 Stress05(뇌졸중 → 부정맥, "irregularly irregular" 이중 계산), 4단계 뒤 Stress07(같은 리듬 관찰 이중 계산으로 기준선 20 → 37턴, 최종 21턴).

**legacy 개발 세트**(`scripts/compare_round_n.py`, TEST 허용 legacy 모드)

| 세트 | 정확도 | 치명적 | 평균 턴 |
|---|---|---|---|
| Blind v5 (dev, 44) | 0.977 → 0.977 (43/44) | 20/20 → 20/20 | 17.0 → 17.2 |
| Round O 세트 (dev, 35) | 0.943 → **1.000** (33 → 35/35) | 15/16 → **16/16** | 18.5 → 18.1 |
| Round N 세트 (dev, 42) | 0.976 → 0.976 | 20/20 → 20/20 | 16.5 → 16.6 |
| Round M dev (128) | 0.756 → 0.772 | 42/43 → 43/43 | 16.9 → 16.9 |
| Round J dev (54) | 0.889 → 0.889 | 20/20 → 20/20 | 14.1 → 13.1 |
| tuning / held_out / gen_v2 / stress | 변화 없음 | 변화 없음 | 19.2 / 17.4 / 13.4→14.9 / 13.2→14.8 |

- Round O: ValO_26, ValO_30 새로 맞힘. **Round O 세트는 Round P에서 개발 데이터로 썼습니다**(지정 실패 사례).
- 최종 직전 런타임 `0e6f800`에서 ValO_02(패혈증 → 폐렴, **새 치명적 누락**)가 나왔습니다. 원인은 4단계의 escalation 조건("국소 질환보다 근거 수가 적으면 격상 취소")이었습니다. 근거 수 대신 "국소 질환이 쓰지 않은 고유 근거"로 바꿔(`730230c`) 해결했고, Fever06(PE 과잉 격상 방지)도 유지됩니다.

## 7. 새로 생긴 위험 신호와 조치

1. **진단 시 미해결 위험 대안 증가**(예선, `unresolved_critical_alternative`): `730230c`에서 51 → 80사례.
   - 원인 추적(`artifacts/round_p/analysis/`): 새 항목 36개 중 대부분이 온톨로지(Tier-2) 후보(SIADH, DVT, 길랭-바레, 난소 낭종 파열)였습니다. 이들의 판별 질문에 "low sodium", "loss of reflexes" 같은 객관 전용 항목이 있는데, ACTION_V3가 이를 묻지 않게 되면서 영구 미해결이 됐습니다. 기준선은 환자에게 "low sodium 있으세요?"라고 묻고 기본 답("아니요")을 받아 "해결"로 셌습니다. 이것은 정보 부족을 정상으로 간주한 것입니다.
   - 조치(`3831555`): 예선에서 객관 전용 판별 항목은 KB 질환의 TEST 항목과 같은 정책으로 처리(§4-3). 결과 80 → **61사례**.
   - 남은 증가분(기준선 51 대비 +10): 대부분 근거 1개짜리 온톨로지 후보입니다(근거 2개 이상인 항목은 기준선 0 → 최종 1). 기존 종료 정책은 근거가 이만큼 얇은 대안을 차단 조건으로 쓰지 않으며, 침상 종료(STOP_V3)로 진찰이 짧아져 그 대안의 일반 질문까지 가지 않은 경우입니다. SOAP A에는 감별 진단이 근거와 함께, P에는 남은 검사가 기록됩니다.
2. **조기 진단(premature)**: 기준선 0 → 1(RoundM_105). 기준선에서도 오답이던 사례이며, 정답(난소 염전)이 이제 3위의 미해결 위험 대안으로 남아 지표 정의상 premature로 집계됩니다.
3. **과잉 진단**: 비위험 정답에 위험 진단을 낸 사례 6 → 3. 정보 부족 사례(ValP_33 "I just feel a bit off" → 급성복증, ValP_34 "어지러워요" → 자궁외임신)는 기준선과 같게 위험 진단을 냅니다. 정답 미정 사례라 채점되지 않지만 남은 과제입니다.

## 8. 동결 검증 세트 결과 (Round P, 예선 조건)

| 지표 | 기준선 | 최종 `3831555` |
|---|---|---|
| Top-1 | 23/32 | **24/32** |
| Top-3 | 26/32 | 27/32 |
| 치명적 재현율 | 8/13 | **9/13** |
| 평균 / 최대 턴 | 23.1 / 36 | 22.7 / 34 |
| 불필요 EXAM / 의미 중복 질문 | 78 / 16 | 77 / 17 |
| 규칙 위반 / SOAP 근거 없는 줄 | 0 / 0 | 0 / 0 |
| EXAM 거부 시나리오 Top-1 / 치명적 | 23/32, 8/13 | 23/32, 8/13 |

- 새로 맞힘: ValP_07(PE, 치명적). 새로 틀림: 0건.
- 계속 오답(9건): ValP_11·12·13 중증 전해질 이상(치명적, 2건은 부정맥, 1건은 SIADH로 출력), ValP_21 급성복증(명칭 계층: 천공성 장기로 출력, 치명적), ValP_08 심부전(라벨 "heart_failure"가 기존 매처에서 "Chronic Heart Failure"와 일치하지 않음, 매니페스트에 기록), ValP_10 근골격 흉통, ValP_16·17 부정맥.
- **해석**: 개발 세트 개선(예선 +11)이 새 사례로는 일부(+1)만 일반화됐습니다. 전해질 이상 개선(이뇨제·전신 쇠약 개념)은 개발 사례 표현에 가깝고, 새 표현에는 충분하지 않습니다.
- **공개 사항**
  1. 단일 작성자(에이전트)가 검증 세트와 개선 코드를 모두 만들었습니다. 독립 검증이 아닙니다.
  2. 이 세트는 `0e6f800`, `730230c`, `3831555`에서 측정했습니다. `0e6f800` 이후의 두 수정은 Round O 개발 세트 회귀(ValO_02)와 예선 지표(미해결 대안) 분석에서 나왔고, 이 세트의 결과를 보고 바꾼 것이 아닙니다. 세 측정의 Top-1과 치명적 재현율은 같습니다(`artifacts/round_p/interim_*`).
  3. 정답 미정 sparse 2건은 채점에서 빠집니다.

## 9. Ablation (4단계 `f2ae078`, 예선 230건, 하나씩 OFF)

| 스위치 OFF | Top-1 | 치명적 | 평균 턴 | 불필요 EXAM | 의미 중복 | 악화 사례 |
|---|---|---|---|---|---|---|
| (모두 ON) | 215 | 84 | 21.07 | 403 | 103 | — |
| `NOVA_EVIDENCE_V3` | 206 | 81 | 21.00 | 400 | 103 | 9건(치명적 3: 수막염, RoundM_041, RoundM_054) |
| `NOVA_RANKING_V3` | 214 | 83 | 21.07 | 403 | 103 | RoundM_018(PE, 치명적) |
| `NOVA_ACTION_V3` | 215 | 84 | 21.11 | 401 | **100** | 없음 |
| `NOVA_STOP_V3` | 215 | 84 | 21.60 | 426 | 109 | 없음(턴·EXAM 증가) |
| `NOVA_DOCUMENTED_DX` | 213 | 84 | 21.20 | 411 | 103 | RoundJ_49, RoundJ_50 |

- ACTION_V3는 4단계에서 정확도 효과가 없고 의미 중복 질문을 3건 늘렸습니다. 최종 런타임에서는 §7 조치 후 의미 중복이 100(기준선 104)입니다.

## 10. 테스트와 패키지 검증

- 전체 `pytest tests`(최종 런타임 `3831555`, mock): **1893 passed, 0 failed, 1 skipped, 3 deselected**.
  - skipped 1: `test_torch_training_and_checkpoint_roundtrip`(torch 미설치, 기존과 동일).
  - deselected 3: 릴리스 레코드·인벤토리를 읽는 테스트(`test_current_runtime_exact_archive_and_commit`, `test_complete_round_m_denominators_and_failure_coverage`, `test_current_inventory_has_complete_hash_coverage_but_no_fake_clearance`). v21 레코드 작성 후 별도로 실행했습니다(아래).
  - 첫 전체 실행에서 2건 실패(`test_safety_regression.py`): 이번에 추가한 스위치 OFF 테스트가 `NOVA_COMPETITION_RETRIEVAL`이 남은 상태에서 설정을 다시 읽어 이후 테스트로 새어 나간 **테스트 격리 결함**이었습니다. 런타임 문제가 아니며, 환경 복원 후 설정을 다시 읽도록 고친 뒤 위 결과를 얻었습니다.
- 신규 테스트 `tests/test_round_p_preliminary_reasoning.py`(67): 부분 매칭(방향·시간 패턴), 개념과 부정·중단 약물, 한국어, 양방향 검사, 후보 생성, 수렴 근거 PE 순위, 폐렴을 PE로 바꾸지 않음, 패혈증 escalation 유지, 리듬 관찰 1회 계산, 객관 전용 질문 필터, 온톨로지 판별 항목 정책, 침상 종료, 문서화 진단, 스위치 OFF.
- `scripts/build_nova_submission.py`: 95 files, 0.75 MB, secret scan OK, mock standalone smoke OK. 바이트 단위 재현 빌드(테스트 통과).
- `artifacts/verification/nova-pre-guide-v21.zip`: 791,611 bytes, sha256 `bc59f4a68e34abbfb4c4a448ab7e2a733e05c912dd6f96b8641d920aefe8770c`.
- clean-room ZIP 검사(`artifacts/integration/clean_room_zip_report.json`) 전 항목 PASS, `scripts/smoke_fresh_package.py` OK(`run.py`는 공식 인터페이스 전까지 fail-closed).
- `validate_runtime_provenance` 실행(권리 상태 BLOCKED 그대로, 자동 승인 없음), `refresh_runtime_inventory --check` 변경 0건, `check_eval_leakage` 이상 없음, `audit_pre_guide_package` 통과, `check_readme_numbers` 일치.
- 제출 소스 동기화: `submission/nova_agent`는 런타임과 동일(경계·동기화 테스트 통과, 레코드의 해시가 런타임 커밋·ZIP과 바이트 일치).
- 임상 검토 문서(`docs/clinical_review/`)는 KB 변경을 반영해 갱신했고 모든 항목은 **PENDING**(검토 완료로 표시한 항목 없음).
- 릴리스 레코드: `artifacts/verification/local-release-3831555-v21.json`(스키마 v21). 예선 조건 결과와 동결 검증 결과를 함께 기록했습니다.

## 11. 단위·표현 정책

- 포도당 mmol/L 값은 기존 정책대로 해석하지 않습니다(기존 테스트가 고정, 변경하려면 소유자 결정 필요). 단위가 불명확한 값을 추측하지 않았습니다.
- 한국어 SAY 질문 일부에 영어 특징명이 섞입니다("rapid heart rate 있으세요?"). 기존 `_FEATURE_FRAME` 설계이며 이번에 바꾸지 않았습니다.
- 기존 테스트 수정: `tests/test_current_pre_guide_release.py`, `tests/test_verification_v7_consistency.py`의 허용 스키마에 v21 추가(릴리스 레코드 갱신). 이번 라운드에 작성했다가 되돌린 핵심 명사 규칙의 테스트 한 줄("washed out" 거짓 매칭을 단언)은 규칙과 함께 제거했습니다. 기존 테스트의 단언을 약화하거나 삭제하지 않았습니다.

## 12. 남은 과제와 다음 우선순위

1. **전해질 이상의 일반화**(ValP_11·12·13): 새 표현에서 여전히 부정맥·SIADH로 출력됩니다. 객관 소견 없이 침상에서 구별할 근거(약물, 구토·설사, 신부전)를 질문으로 끌어내는 행동 선택이 필요합니다.
2. **위험 과잉 진단**: 자궁외임신(RoundM_105, RoundJ_51, ValP_34), ACS(RoundJ_52), 정보 부족 시 위험 진단(ValP_33). 근거가 얇은 위험 1위를 진단으로 확정하기 전에 판별 질문을 우선하는 정책 검토가 필요합니다.
3. **명칭 계층**(RoundJ_25, ValP_21, RoundM_108): 라벨이 상위 범주일 때 하위 원인을 출력합니다. 매칭을 넓히지 않는 한, 근거가 하위 원인을 특정하지 못할 때 상위 범주를 고르는 순위 규칙이 필요합니다(되돌린 핵심 명사 실험처럼 부작용 검증 필수).
4. **미해결 위험 대안 +10사례**와 Stress05의 긴 진찰(공존 질환이 1–2위 차이를 좁힘).
5. 한국어 질문의 영어 혼용, 포도당 mmol/L 정책(소유자 결정).
6. 실제 고정 모델(`openai/gpt-oss-20b`)과 공식 인터페이스 검증은 여전히 **NOT VERIFIED**입니다.
