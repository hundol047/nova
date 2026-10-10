# N.O.V.A. POST-ROUND-W 일반화·안정화 보고서

모든 수치는 오프라인 mock LLM과 합성 개발 사례로 측정한 엔지니어링 근거다. 공식 점수, 실제 모델 성능, 독립 임상 검증이 아니다. 이전 라운드 보고서(`docs/competition/ROUND_W_REPAIR_REPORT_KO.md` 등)는 수정하지 않았다.

```
TARGET BRANCH        offline/nova-competition-agent-optimization
START_REMOTE_HEAD    8d37c73 (Round W 이전 상태; claude 브랜치에서 fast-forward로 b7481d4까지 반영, force-push 없음)
BASELINE RUNTIME     b7481d4 (Round W f677d05 + 성능 memo, 행동 동일)
FROZEN RUNTIME       c593331 → 검증 commit ed61341 (closing set 동결만 추가, 런타임 동일)
RELEASE RECORD       dfb32f3: artifacts/verification/local-release-ed61341-v30.json
```

근거 파일: 기준선 `artifacts/post_round_w/baseline.json`, `analysis_baseline.json`; 최종 `final_metrics.json`, `analysis_final.json`; 치명 FN `critical_fn_analysis.json`; 출처 `docs/competition/POST_ROUND_W_PROVENANCE.md`.

## 1. 핵심 수치 (기준선 b7481d4 → 최종 ed61341)

| 묶음 | 사례 | Top1 | Top3/5 | critical | 평균 턴 | EXAM | SOAP 보존 / 근거없음 | 규칙 위반 |
|---|---|---|---|---|---|---|---|---|
| 예선 ALL | 230 (222 채점) | 98.6% → 98.6% | 99.1% → 99.1% | 85/85 → 85/85 | 19.75 → 19.64 | 1221 → 1207 | 100% / 0 | 0 |
| Round M | 128 (123) | 98.4% → 98.4% | 99.2% | 43/43 → 43/43 | 20.34 → 20.30 | 700 → 692 | 100% / 0 | 0 |
| Round J | 54 | 98.1% → 98.1% | 98.1% | 100% | 18.37 → 18.24 | 257 → 258 | 100% / 0 | 0 |
| Round I | 20 | 100% → 100% | 100% | 100% | 18.9 → 18.5 | 102 → 101 | 100% / 0 | 0 |
| 한국어 | 20 | 100% → 100% | 100% | 100% | 19.2 → 19.15 | 105 → 100 | 100% / 0 | 0 |
| EXAM 거절 변형 | 230 | 97.7% → 97.7% | | 100% | | | | 0 |
| 미기재 질문 "모름" 변형 | 230 | 98.2% → 98.2% | | 100% | | | | 0 |
| 동일 조건(frozen fixture 전체) | 284 (174) | 93.1% → 94.8% | 96.6/97.1 → 98.3/98.9% | 62/64 → 63/64 | 23.0 → 22.5 | | 100% / 0 | 0 |
| Round W closing (개발 사용됨) | 12 (10) | 7/10 → 10/10 | | 5/6 → 6/6 | 20.5 → 18.7 | | 100% / 0 | 0 |
| **Post-W closing (신규, 1회 실행)** | 12 (10) | **8/10** | 9/10 | **4/6** | 20.1 | 64 | 100% / 0 | 0 |

- 예선 불필요 EXAM: 283 → 270 (Round W 목표 238은 여전히 미달).
- TEST 행동 0, 중복 행동 0, 사례 간 누수 0(`tests/test_case_isolation.py`, `test_no_evaluation_time_learning.py`), 누수 스캔 NO OBVIOUS LEAKAGE.
- 동일 조건 새 오답 0. 남은 critical miss 1건(Fresh20, 전해질 이상)은 기준선부터.

## 2. 개발 반사실 세트 (원인 수정 전에 동결)

| 세트 | 내용 | 기준선 | 최종 |
|---|---|---|---|
| `post_round_w_counterfactual_dev` (26, 17 채점) | 영아 패혈증 스펙트럼(발열·저체온·무열, 한국어), 서맥 스펙트럼(운동선수·약물·쓰러짐), 표현 변형(임상/일반인/오타/한국어/혼용/짧음/김), 음성 대조 | Top1 11/17, 행동 75/77 | 17/17, 77/77 |
| `post_round_w_counterfactual_dev2` (7, 5 채점) | 영아 수막염 4표현(영/한, 진찰 소견 포함·미포함) + 음성 대조 3 | 1/5 (수막염 0/4) | 5/5, 21/21 |

## 3. 치명 FN 감사 (분류 A–L)

기준선의 치명 FN 5건(CloseW_01, PWCF_P02/P03/P05/W02)은 모두 **F. evidence parser failed**였다: 후보는 생성·유지되고 대개 선두였지만, 명명에 필요한 관찰(대천문 팽륜·고음 울음, 저체온, 얼룩덜룩한 피부·grunting, 흉부 압박 직유)이 인식되지 않았다. 위험 가산은 쓰지 않고, 빠진 징후를 한 번씩 KB 특징 + 표현 문법으로 표현했다. 최종 개발 분석(515 사례)에서 치명 FN 0건.

Post-W closing의 2건(수정하지 않음, 다음 라운드 과제):

| 사례 | 분류 | 내용 |
|---|---|---|
| CloseX_03 4세 수막염 → 지주막하출혈 | **G. contradiction overweighted** | 목 강직·눈부심·발열은 인식. 사례에 "두통" 답이 없어 기본 응답 "No."가 headache를 반박(−1.2)으로 만들어 SAH가 앞섬. 어린 소아가 두통을 말로 표현하지 못하는 상황에서 bare "No"의 반박 강도 문제 |
| CloseX_05 15세 DKA(한국어) → 미분화 | **F. evidence parser failed** | "물을 엄청 마시고 화장실을 계속 가요 / 숨이 깊고 빨라요"(다음·다뇨·Kussmaul)가 한국어로 인식되지 않음. 지지 근거 0 |
| CloseX_10 편두통 | (처분) | 정답 명명, 그러나 긴급 계획(과잉 분류) |

## 4. 바뀐 것 (모두 일반 기전, `NOVA_*` 스위치)

| 기전 | 스위치 | 효과 |
|---|---|---|
| 패혈증 고위험 징후(NG51): 얼룩덜룩한 피부·grunting(진찰 소견), 측정 체온 < 36 °C(지지 전용) | KB | 무열·저체온 영아 패혈증 명명 |
| 영아 수막염 징후(NG143/NG240): 대천문 팽륜, 고음 울음 + 영/한/일 문법 | KB | 영아 수막염 0/4 → 4/4, CloseW_01 |
| 표현 문법: 흉부 압박 직유, 한국어 대상포진·통풍·관절·쓰러짐, 보호자 존칭 | — | PWCF_W02, CloseW_08/09, PWCF_B04 |
| 해부학적 성별 적합성 | `NOVA_ANATOMIC_COMPAT` | 남성 사례의 자궁외 임신 활성 10/155 → 0 (성별 미기록이면 제외 없음) |
| 진찰 효용: 카탈로그 채움 후보는 시간 민감 예외를 만들지 않음 | `NOVA_EXAM_UTILITY_V2` | 붉은 눈·통풍에 복부·심장 진찰 제거; 불필요 EXAM 283 → 270 |
| 결정 확실성 메타데이터(PROVISIONAL/LEADING, close_alternatives) | `NOVA_DECISION_CERTAINTY` | wire 형식·결정 불변 |
| 포함 관계 대안은 긴급 사유가 아님("rash" ⊂ "band-like blistering rash") | `NOVA_DISPOSITION_SUBSUMED` | 대상포진의 수막염 과잉 긴급 제거 |
| 한국어 보호자 진술 정밀화: 소유격 또는 주격(께서/가/이) 관계어는 환자, 단 화자가 자기("저는")를 말하면 가족력; 주제격(는/은)은 가족력 | — | NewT_20 회귀 방지 + PWCF_B04 |

동결 전 동일 조건 실행에서 발견해 고친 회귀: NewT_20(한국어 가족력이 환자 증상으로), CloseW_08(대상포진 과잉 긴급), PWCF_B04(1차 수정이 한국어 쓰러짐 보호자 진술을 놓침).

## 5. 일반화·연령·과잉 활성·순위·정지·보정 (개발 분석, `analysis_baseline.json` 540 → `analysis_final.json` 515 사례; 최종 분석은 acceptance 회귀 fixture 32건 제외, dev2 7건 포함)

| 항목 | 기준선 | 최종 |
|---|---|---|
| 전체 Top1 / critical recall | 94.9% / 96.7% (치명 FN 5) | 97.0% / 100% (0) |
| 영아(<1) Top1 / critical | 5/9 / 5/9 | 14/14 / 13/13 |
| 소아(1–11) Top1 | 77.8% | 88.9% |
| 고령(65+) Top1 | 93.4% | 96.0% |
| 같은 질환 표현 간 불일치 질환 수 | 12 | 7 (심낭염, 소화성 궤양, 췌장염, 중이염, 긴장성 두통, 부정맥, 위장관염) |
| 양성 사례 평균 활성 위험 후보 / 미해결 | 2.11 / 1.19 | 1.95 / 0.98 |
| 양성 사례 긴급 계획 비율 | 34.9% | 34.5% (여전히 높음) |
| 오답 중 near-miss / deep / top5 밖 | 9 / 5 / 6 | 5 / 4 / 2 |
| 21–30턴 구간 Top1 | 92.4% | 95.4% |
| >30턴 구간 Top1 | 96.2% | 100% |
| 근소 차(2위 ≥ 90%) 사례 Top1 | 77.3% (44건) | 86.5% (37건) |

나이 사용: 나이는 활력 기준(소아 빠른 맥박·RR 한계)과 징후 표현에만 쓰였고, 후보 점수를 나이·성별로 올리지 않는다. 음성 대조(운동선수 서맥, 이 나는 영아, 유열 없는 상기도 감염 영아, 긴장성 두통 성인, 가족력만 있는 성인)는 모두 비긴급·비위험 명명을 유지했다.

보정: 기존 confidence band는 LOW 사례도 Top1 98.5%로 과소 확신 쪽에 치우쳐 있다. wire 형식을 바꾸지 않기 위해 내부 메타데이터 `certainty`(PROVISIONAL = 90% 이내 경쟁 후보)만 추가했다. 이를 사용자 표시 확신도로 연결하는 것은 하지 않았다.

## 6. 검증

| 항목 | 결과 |
|---|---|
| pytest (검증 worktree ed61341) | py3.13 2574 passed / py3.11 2521 / py3.12 2521 (CI 범위), failed 0 (release-binding은 v30 기록 후 재실행 통과), skipped 2 |
| 동일 조건 실행 | 36단계, 모든 단계에서 런타임 해시 불변, pytest 외 exit 0 |
| 누수 / adversarial / assertion | NO OBVIOUS LEAKAGE / ALL CHECKS PASSED / 통과 |
| 패키지 | `run.py`·`requirements.txt` ZIP 루트, 102 파일 + MANIFEST, 858,058 bytes, sha256 `6ffd14d1b7db4a71462ceddb37ed11d65be1cf359a3bea15403eddf7c5aa8244`, validate_submission_zip all_pass, fresh 디렉터리: run.py fail-closed(exit 1), local_runner 행동 출력 |
| 상태 | PRE-GUIDE CANDIDATE / NOT OFFICIALLY READY |

**CI release-binding 처리.** CI 실패의 근본 원인은 공개 CURRENT_RELEASE가 v22를 가리키는데 R–W 기록·ZIP은 이전 공개 제한으로 로컬에만 있었던 것이다. 테스트를 건너뛰거나 기준을 낮추지 않고, v30 기록(파일 해시·ZIP sha·**ZIP 멤버별 sha**)을 커밋하고 ZIP은 로컬에 두었다. 기록이 `publication=LOCAL_ONLY`이면 테스트는 각 ZIP 멤버 해시를 커밋된 `submission/` 미러 바이트와 대조한다(ZIP은 미러에서 빌드되므로 같은 내용 검증). ZIP을 공개하는 쪽을 원하면 ZIP을 커밋하고 이 분기를 제거하면 된다.

## 7. 출처 상태

`docs/competition/POST_ROUND_W_PROVENANCE.md`: VERIFIED 5(NG51 3항목, NG143/NG240 대천문, 해부학 정의), UNRESOLVED 1(고음 울음을 수막염 typical feature로 둔 판단), EXCLUDED 4(반박형 저체온, 질문형 징후, 안전 가산, 유방 질환). 모든 항목 임상의 검토 PENDING.

## 8. 공식 상태

- 공식 모델 `openai/gpt-oss-20b` revision `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`: **NOT VERIFIED**
- 공식 transport: **BLOCKED**, fail-closed 유지(`run.py` → NOT READY)
- 95점 / 임상 안전 / 독립 검증 주장 없음

## 9. 목표 대비

| 목표 | 결과 |
|---|---|
| ALL Top1 ≥ 85%, critical ≥ 95% | 98.6%, 100% (개발 세트) |
| Round M Top1 ≥ 80%, critical ≥ 95% | 98.4%, 100% |
| 한국어 critical ≥ 95% | 예선 한국어 100%; **신규 closing 한국어 critical 1/2 (CloseX_05 DKA miss)** |
| 신규 closing critical | **4/6 — 미달** |
| SOAP 보존 100%, 근거없음 0, 규칙 위반 0, TEST 0, 누수 0 | 충족 |

## 10. 한계와 다음 과제

1. 신규 closing critical 4/6: 개발 세트 수치(100%)는 저자가 같은 낙관적 추정이다. 독립 저자 세트에서 더 낮을 가능성이 크다.
2. bare "No"가 소아의 표현 불가 증상을 반박하는 문제(CloseX_03), 한국어 다음·다뇨·쿠스마울 호흡 표현(CloseX_05).
3. 양성 사례 긴급 계획 34.5% — 과잉 분류. CloseX_10, CloseW_09(통풍 vs 패혈성 관절염은 안전 쪽으로 유지).
4. 불필요 EXAM 270(목표 238).
5. NewT_19 / ConfirmU_09: 가족의 "irregular heartbeat"가 환자 근거로 들어감(기준선부터).
6. 같은 질환 표현 불일치 7종.
7. 실제 GPT-OSS·공식 인터페이스 미검증, 임상 검토 미수행, 모든 사례 합성.
