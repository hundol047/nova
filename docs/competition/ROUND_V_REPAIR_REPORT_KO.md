# N.O.V.A. ROUND V REPAIR REPORT

모든 수치는 오프라인 mock LLM과 합성 개발 사례로 측정한 엔지니어링 근거이다. 공식 점수, 실제 모델 성능, 독립 임상 검증이 아니다. 작업서는 [ROUND_V_IMPLEMENTATION_PROMPT_KO.md](ROUND_V_IMPLEMENTATION_PROMPT_KO.md)이다. 기준선과 최종본에는 같은 명령, 같은 라벨·분모·채점기·시뮬레이터 응답을 썼다(`scripts/run_round_u_followup_suite.py`, 31단계). 실행별 명령, exit code, 로그 해시, 시각은 [ROUND_V_VERIFICATION_SUMMARY.json](ROUND_V_VERIFICATION_SUMMARY.json)에 있다. 사례별 비교는 `artifacts/round_v/final/comparison.json`, 처분·기본 "No" 집계는 `artifacts/round_v/final/disposition_and_default_no.json`에 있다. 새 임상 관계·어휘의 출처는 [ROUND_V_PROVENANCE.md](ROUND_V_PROVENANCE.md)에 있다.

```
BASELINE RUNTIME SHA: e207801ce16faf38591fc0bed2dd2d238c1c1d7a
FINAL RUNTIME SHA:    e16448e13431ab7af21d1e1c8abc5ecf2cf16e3c

PUBLIC BRANCH: claude/nova-round-u-followup-20261009 (main·codex 검토 브랜치·원래 Claude 브랜치는 수정하지 않음)

TESTS (pytest tests -q, NOVA_LLM_PROVIDER=mock, NOVA_COMPETITION_RETRIEVAL 미설정, 검증 worktree e16448e):
passed:     2499  (전체 실행 2498 + 로컬 v28 기록 생성 후 재실행한 release-binding 1)
failed:     0     (로컬 v28 ZIP/기록이 있을 때. ZIP을 공개하지 않은 공개 트리에서는 release-binding 1개가 기준선과 똑같이 실패)
skipped:    2     (torch 미설치; package-not-built — 기록 생성 후 재실행 시 통과)
새 테스트:  tests/test_round_v.py 38개

PRELIMINARY (230 cases / 222 scored, SAY·EXAM·DIAGNOSE, TEST 없음):
before: 218/222
after:  219/222   (new correct: RoundM_112, new wrong: 없음)
exam-rejection 변형:      216 → 217 (new wrong 없음)
unscripted-unknown 변형:  217 → 218 (new wrong 없음)
critical before/after: 85/85 → 85/85
average turns:    19.92 → 19.78 (max 35 → 30)
unnecessary EXAM: 238 → 296 (전체 EXAM 1225 → 1236)  ← 목표 미달

ROUND P (34 / 32 scored): 31/32 → 31/32, critical 13/13 → 13/13, 평균 턴 20.79 → 20.26
ROUND M (TEST 허용, 128 / 123 scored):
before: 117/123
after:  121/123   (new correct RoundM_109, RoundM_112, RoundM_114, RoundM_117; new wrong 없음)
critical: 43/43 → 43/43
long-tail Top1/Top5/Top10 (26): 20/23/25 → 24/26/26

비교 세트 전체(예선 3변형, P, Q, R, acceptance, S, T 4종, U 4종, follow-up 2종, TEST 허용 8종, Round M):
new scored wrong 0, new critical miss 0. TEST 허용 8종은 기준선과 동일.

ROUND V 개발 세트 (18 / 14 scored, 기준선 실행 후 소스 수정에 사용 → 개발 세트):
Top1 7/14 → 13/14, critical 2/3 → 3/3, 행동 계약 48/55 → 55/55
ROUND V CLOSING 세트 (12 / 10 scored, 최종 runtime 커밋 전에 동결, 기준선·최종에만 실행):
Top1 7/10 → 7/10, critical 1/2 → 1/2 (CloseV_03 기준선·최종 모두 miss), 행동 계약 33/35 → 35/35

DISPOSITION 계약 (긴급 처분 계약이 있는 67개 사례):
false positive 9 → 0, false negative 3 → 2 (아래 표)

기본 "No" 의존 정답 수 (기본 조건 정답 ∧ unscripted-unknown 오답): 2 → 1

RETRIEVAL (164개 개발 proxy): chief-only Top150/Top25 155/155 → 155/155 (변화 없음)
ASSERTION 10 contrast: 10/10 → 10/10
LEAKAGE: NO OBVIOUS LEAKAGE. ADVERSARIAL: ALL CHECKS PASSED

SUBMISSION:
source/mirror byte equality: PASS (audit source_submission_byte_equivalence=True)
package audit: PASS (secret scan PASS, clean-room ZIP validation all_pass, 새 디렉터리 mock 실행 PASS, run.py 공식 경로 fail-closed)
ZIP SHA256: f1eacf3ca16a4a5b0afdd12229eb4b45d65278488cab45fddd1bbd4445ebf64c (846,929 bytes; 로컬 전용, 공개하지 않음)

VERDICT:
- offline implementation: 완료(아래 변경), 테스트·동일 조건 회귀로 확인
- same-condition regression: PASS (모든 비교 세트 새 오답 0, 새 critical miss 0)
- disposition: PASS (FP 9→0, FN 3→2, 활력징후 기반 긴급 처분 회귀 0)
- HF vs pneumonia: PASS (HF 계열 4개 사례 모두 폐렴 과잉 명명 해소, 폐렴 대조군 유지)
- Round M ≥118: PASS (121)
- official API: NOT VERIFIED
- real GPT-OSS: NOT VERIFIED
- independent clinical validation: NOT PERFORMED
- overall: FAIL. 완료 기준 중 "불필요 EXAM ≤ 238" 미달(296). 나머지 측정 목표는 충족
```

## 1. 완료 기준 대조

| 기준 | 결과 | 판정 |
|---|---|---|
| 테스트 failed 0 | 로컬 v28 근거 기준 0. 공개 트리는 ZIP 미공개로 release-binding 1 실패(기준선과 동일) | 조건부 PASS |
| 모든 비교 세트 새 scored wrong 0 / 새 critical miss 0 | 0 / 0 | PASS |
| 예선 ≥218/222, critical 85/85 | 219, 85 | PASS |
| Round P ≥31/32 | 31 | PASS |
| **Round M ≥118/123** | **121** | PASS |
| long-tail Top1 ≥20/26 | 24 | PASS |
| 처분 FP·FN 각각 감소 또는 동일 | FP 9→0, FN 3→2 | PASS |
| 활력징후 기반 긴급 처분 회귀 0 | 0 (FN 목록에 새 사례 없음) | PASS |
| HF 계열 폐렴 과잉 명명 감소 | RoundV_08·RoundV_10·FollowU_23·CloseUF_09 모두 HF 명명 | PASS |
| 평균 interaction ≤ 20 | 19.78 | PASS |
| **불필요 EXAM ≤ 238** | **296** | **FAIL** |
| 기본 "No" 의존 정답 수 증가 없음 | 2 → 1 | PASS |
| 공식 API·실모델 NOT VERIFIED 유지 | 유지 | 표시 완료 |

미달 항목이 있으므로 **overall FAIL**이다. 95점, 임상 안전, 독립 검증은 선언하지 않는다.

**불필요 EXAM 미달의 내용.** 전체 EXAM 수는 거의 같다(1225 → 1236). 이 지표는 정답과 최종 상위 5개 중 **Tier-1** 질환의 `discriminating_exams`만 "필요"로 센다. Round V 이후 최종 상위 5개에 Tier-2 후보가 더 자주 남아(bare "No" 감점 완화, 아래 ablation) 같은 진찰이 "불필요"로 분류되는 비율이 늘었다. 예: PrelimKo_Mixed_Term_Pneumonia는 기준선 상위 5개에 있던 sepsis 대신 Tier-2 증상 개념이 들어와, 같은 피부·의식 진찰이 불필요로 집계되었다. 채점 지표는 바꾸지 않았다(금지 사항). 다음 작업서에서 Tier-2 후보의 상위 5개 잔류 자체를 줄이는 방향으로 다룬다.

## 2. 구현한 변경

모두 일반 기전이다. 사례 ID, 정답 질환, 채점기, 라벨은 하드코딩하거나 바꾸지 않았다. 위험도를 진단 점수 보너스로 쓰는 곳은 없다. 각 기전은 `NOVA_*` 스위치로 끌 수 있다.

| 영역 | 문제 | 수정 |
|---|---|---|
| V-B 처분 | 2세 아동 HR 120·RR 24가 성인 기준으로 위험 활력징후 | `vitals_parser.red_flag_rules_for_age`(`NOVA_PEDIATRIC_VITALS`): 5세 미만은 NICE NG143 Table 1 기준(빈맥 >160/150/140, 빈호흡 >50/40). 활력 소견·safety·처분에 같은 규칙. SBP·SpO2·체온·서맥 규칙은 그대로 |
| V-B 처분 | Tier-2 카탈로그 1246개 중 945개가 `dangerous`(미검증 메타데이터). 통풍·소화성궤양이 라벨만으로 응급 처분 | `tier2_enrichment.json`에 출처 있는 `disposition: non_emergency`(gout: NICE NG219, peptic/duodenal ulcer: NICE CG184). 라벨 단독으로는 응급 처분하지 않음. 활력징후·맥박 이상·지지된 위험 대안(패혈성 관절염, 위장관 출혈)은 그대로 응급(`NOVA_DISPOSITION_V2`) |
| V-B 처분 | 위험 대안의 근거가 "suspected infection source" 같은 추정·위험인자·선행 맥락뿐(방광염 → sepsis 대안) | `disposition._context_only`: 그런 근거만으로는 처분 근거가 아님. 후보는 감별에 남음 |
| V-B 처분 | 선택 진단이 자기 자신의 "위험 대안"으로 이중 집계 | id 비교로 수정 |
| V-B 처분 | 남성 환자의 "sore spot on my ribs"가 질출혈 별칭 "spotting"과 같은 어간 → 자궁외임신 대안 | `matching._IRREGULAR_STEM_OVERRIDES`에 `spotting` 예외 |
| V-C.1 HF/폐렴 | crackles+호흡곤란 공유. HF는 특징 4개로 포화된 뒤 bare "No" 하나(−1.2)로 2개 특징의 폐렴에 역전. "sit up to breathe", "ankles are puffy", 한국어 기좌호흡·부종 표현 미인식 | 아래 V-C.2 가중치 수정 + 별칭(NICE CKS HF) + 한국어 개념 + HF Tier-2 confirmatory(S3, JVP; ESC 2021 Table 6)와 진찰 연결 |
| V-C.2 감점 비대칭 | 시뮬레이터가 모든 미스크립트 질문에 "No"로 답함. bare "No" 하나가 −1.2로 관찰 특징 +1.0보다 큼 | `NOVA_DENIAL_V2`: (a) bare "No"만으로 부정된 선택 특징은 관찰 특징 2개 이상인 가설에서만 0.5배, 포화 전 합산, 합계 −1.8 상한. 환자 자신의 말로 한 부정은 기존 가중 유지. (b) bare "No"는 환자 자신의 말로 보고한 같은 특징을 이기지 못함. (c) 이미 보고한 증상의 수식어 형태("worsening shortness of breath")에 대한 bare "No"는 conflict. (d) bare "No"가 지지하는 안심 소견("no chest pain")은 0.5배. (e) 핵심 증상 부정 확장은 명시적 부정만. (f) 정확한 동점은 관찰 소견 수로 정렬(삽입 순서 대신). (g) 이미 반박되고 선두의 80% 미만인 Tier-2 대안은 더 이상 질문·진찰을 쓰지 않음 |
| V-C.3 명칭 계층 | acute abdomen 사례가 영상 없이는 확인 불가한 "Perforated Viscus"로 명명(최초 최종 후보 7f180c2에서 ValP_21·DevQ_44 critical miss로 발견) | `NOVA_HIERARCHY_V2`: 검토되지 않은 Tier-2 원인이 자기 confirmatory 소견 없이, 상위 3위 안 Tier-1 증후군과 10% 이내이고 그 증후군의 근거 2개 이상을 같은 관찰로 공유하면 Tier-1 증후군을 명명. 점수·후보·위험도 불변 |
| V-C 맥락 | "recent viral illness"만으로 acute bronchitis 명명 | `NOVA_CONTEXT_V2`: 선행 맥락("recent …")만으로는 명명 불가. 다른 현재 소견과 함께면 판별 근거로 인정(심근염의 바이러스 전구) |
| 어휘 | 일본어 胸が締め付け/腕に広がる, 한국어 가슴이 조이/팔로 퍼지, "worse when taking a breath", "after hip surgery" 등 | `feature_relations.py`, `multilingual_concepts.py`, `lay_language.py`(출처·노출 범위는 PROVENANCE) |
| 진찰 연결 | Tier-2 신체 징후가 카탈로그 진찰에 연결되지 않음 | `NOVA_EXAM_LINKS_V2`: Tier-2 **confirmatory** 징후만(S3, 수포 등) 기존 진찰에 연결 |

반복 검증 중 되돌리거나 교정한 항목:

1. `symptomatic bradycardia` 파생 특징(2018 ACC/AHA/HRS 정의)을 넣었으나, "측정 맥박+실신만으로 리듬 원인을 명명하지 않는다"는 기존 Round T 계약 테스트를 깼다. 되돌렸다. RoundV_05는 남은 실패다.
2. 핵심 증상 부정 확장이 시뮬레이터 기본 "No"("shortness of breath: No" ← 환자는 "gasping")를 증폭해 RoundM_019 긴장성 기흉을 잃었다. 명시적 부정에만 적용했다.
3. `NOVA_CONTEXT_V2` 첫 설계(선행 맥락을 위험인자처럼 취급)가 RoundM_116 심근염을 막았다. "맥락만 있는 경우"로 좁혔다.
4. 반감 규칙이 Tier-2 후보를 오래 남겨 interaction이 20.5로 늘었다. 반박된 후행 Tier-2 대안의 질문·진찰 중단과 "관찰 특징 2개 이상" 조건으로 19.78이 되었다.
5. 첫 최종 후보(7f180c2)의 동일 조건 실행에서 새 critical miss 3개(ValP_21·DevQ_44 acute abdomen, NewR_02 PE)를 발견했다. 위 명칭 계층 규칙과 흉막성 통증·수술 표현으로 고치고, 최종 후보(e16448e)를 처음부터 다시 실행했다.
6. 누출 검사가 별칭 3개("gnawing pain in my upper stomach", "calf has been swollen and aching")를 표시했다. 삭제했다.

## 3. DISPOSITION FP/FN

긴급 처분 계약(`round_s_expect.urgent`)이 있는 동결 사례. FP = 계약은 비긴급인데 응급 계획, FN = 계약은 긴급인데 응급 계획 없음.

| 세트 | 계약 수 | FP 기준선 → 최종 | FN 기준선 → 최종 |
|---|---|---|---|
| Round V 개발 | 11 | RoundV_01·03·14·17 → 없음 | RoundV_18 → 없음 |
| Round V closing | 9 | CloseV_01·02 → 없음 | 없음 → 없음 |
| follow-up 신규 | 12 | FollowU_19·20 → 없음 | FollowU_21 → FollowU_21 |
| follow-up closing | 7 | CloseUF_04 → 없음 | CloseUF_03 → CloseUF_03 |
| Round S, T 4종, U 4종 | 28 | 없음 → 없음 | 없음 → 없음 |
| **합계** | **67** | **9 → 0** | **3 → 2** |

남은 FN 2개(FollowU_21, CloseUF_03)는 HR 30대 실신 사례로 기준선부터 실패했다. 증상성 맥박 이상 규칙(`symptomatic_rate_concern`)이 해당 표현을 인식하지 못하는 문제이며, 이번에 바꾼 규칙과는 무관하다(새 FN 없음).

## 4. 기본 "No" 의존과 감점 ablation

기본 "No" 의존 = 기본 시뮬레이터에서 정답이지만, 미스크립트 질문을 "I don't know"로 답하게 하면(`--unscripted-unknown`) 오답이 되는 예선 사례.

| runtime | 기본 조건 정답 | unscripted-unknown 정답 | 의존 정답 수 |
|---|---|---|---|
| 기준선 e207801 | 218 | 217 | 2 |
| 최종 e16448e | 219 | 218 | 1 |

`NOVA_DENIAL_V2` ablation(최종 코드 e16448e, 같은 명령, 예선 230 사례):

| 조건 | 기준선 e207801 | 최종, DENIAL_V2 끔 | 최종, DENIAL_V2 켬 |
|---|---|---|---|
| 기본 응답("No.") Top1 / critical | 218 / 85 | 218 / 85 | 219 / 85 |
| 기본 응답 평균 턴 / 불필요 EXAM | 19.92 / 238 | 20.03 / 258 | 19.78 / 296 |
| unscripted-unknown Top1 / critical | 217 / 85 | 218 / 85 | 218 / 85 |
| unscripted-unknown 평균 턴 | 26.23 | 26.17 | 26.10 |

`DENIAL_V2`를 켜서 새로 맞힌 예선 사례는 RoundM_112 하나이고, 켜서 잃은 사례는 없다. 불필요 EXAM 지표 증가(258 → 296)의 대부분이 이 스위치에서 온다(§1). 예선 집계에 드러나지 않는 효과는 HF 대 폐렴 사례(RoundV_10, FollowU_23, CloseUF_09)와 실신 사례에서 나타났다(§2). 원본: `artifacts/round_v/final/abl_denial_off_*.json`.

시뮬레이터 기본값 문제와 runtime 가중치 문제의 분리: runtime 쪽은 "bare 'No'가 관찰된 패턴을 뒤집는 비대칭"(V-C.2)을 위 (a)–(g)로 줄였다. 시뮬레이터 쪽("gasping"이라 말한 환자에게 "shortness of breath?" → "No.")은 채점·시뮬레이터 응답 수정 금지라 바꾸지 않았고, runtime이 그 답을 conflict로 기록하거나 약하게 반영하도록만 했다.

## 5. 남은 실패

| 사례 | 세트 | 결과 | 분류 |
|---|---|---|---|
| CloseV_03 (영아 패혈증, critical) | Round V closing | heat stroke 명명 — 기준선·최종 동일 | closing 세트라 소스 수정에 쓰지 않음. 다음 작업서 1순위 |
| CloseV_02 (AOM) | Round V closing | viral URI — 기준선·최종 동일 | 귀 통증 표현 |
| CloseV_12 (대상포진) | Round V closing | GERD — 기준선·최종 동일 | 흉벽 띠 모양 통증+수포 표현이 Tier-2 대상포진에 닿지 않음 |
| RoundV_05 | Round V 개발 | 미분화(긴급 처분은 정상) | Round T 계약과 충돌하는 라벨. 되돌림 |
| ValP_08 | Round P | "Acute Decompensated Heart Failure" 명명, 라벨 `heart_failure` 불일치 | **명칭 문제**: 라벨이 카탈로그 id·별칭과 매칭되지 않음. scorer·라벨은 바꾸지 않음 |
| RoundM_105 (ovarian torsion → ruptured cyst), RoundM_108 (PUD → duodenal ulcer) | Round M | 기준선부터 실패 | 명칭 계층(자식/형제 원인). 108은 같은 관찰로 PUD와 duodenal ulcer를 구분할 수 없음 |
| FollowU_21, CloseUF_03 | follow-up | 긴급 처분 FN | 기준선부터. §3 |
| 불필요 EXAM 296 | 예선 | 목표 238 미달 | §1 |

## 6. 자체 100점 추정 (공식 점수 아님)

엔지니어링 추정이다. 직전 라운드의 추정(대화상 약 64/100)은 항목별로 기록하지 않았으므로 아래 표는 Round V 시점만 항목별로 매기고, 비교는 합계로만 한다. 실제 GPT-OSS·공식 인터페이스는 이 환경에서 검증할 수 없어(BLOCKED) 올리지 않았다.

| 항목 | 배점 | Round V 추정 | 근거 |
|---|---|---|---|
| 실제 모델·공식 인터페이스 | 20 | 4 | NOT VERIFIED 유지(BLOCKED). 오프라인 패키지·fail-closed만 확인 |
| 예선형 진단 정확도(개발 세트) | 20 | 18 | 예선 219/222, Round M 121/123, Round P 31/32, 새 오답 0 |
| 일반화(동결·closing 세트) | 15 | 9 | Round V 개발 13/14(개발 세트로 승격), closing 7/10(기준선과 동일, 개선 없음) |
| 안전·처분 | 15 | 12 | 처분 FP 9→0, FN 3→2; closing critical miss 1(기준선부터, 미해결) |
| 지식 깊이·출처 | 10 | 6 | 출처 있는 보강은 소수(HF confirmatory, 처분 메타데이터 3개) |
| 효율·SOAP | 10 | 7 | 평균 19.78턴; 불필요 EXAM 지표 296(목표 미달) |
| 검증·재현성 | 10 | 9 | 31단계 동일 조건 실행 두 번(첫 후보의 회귀 발견 후 재실행), 기록·해시, 패키지 audit |
| **합계** | **100** | **≈65** | 직전 추정 ≈64 대비 소폭. 가장 큰 감점은 여전히 실모델·공식 인터페이스 미검증 |

## 7. 다음 작업서로 넘길 항목

1. CloseV_03: 영아 고열·빈맥·얼룩덜룩한 피부 → 패혈증 대신 heat stroke. 소아 패혈증 표현과 heat stroke 맥락 요구조건.
2. 불필요 EXAM: Tier-2 후보의 최종 상위 5개 잔류 감소(지표는 그대로 두고).
3. HR 30대 실신 FN 2개: `symptomatic_rate_concern` 표현 범위.
4. 명칭 계층의 형제 원인(ovarian torsion/ruptured cyst, PUD/duodenal ulcer)은 같은 관찰로 구분 불가 — 정책 설계 필요.
5. 실제 GPT-OSS·공식 인터페이스: 주최측 가이드가 오면 같은 회귀 세트로 별도 라운드.
