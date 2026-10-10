# N.O.V.A. ROUND W REPAIR REPORT

모든 수치는 오프라인 mock LLM과 합성 개발 사례로 측정한 엔지니어링 근거이다. 공식 점수, 실제 모델 성능, 독립 임상 검증이 아니다. 작업서는 [ROUND_W_IMPLEMENTATION_PROMPT_KO.md](ROUND_W_IMPLEMENTATION_PROMPT_KO.md), 출처는 [ROUND_W_PROVENANCE.md](ROUND_W_PROVENANCE.md), 실행 기록은 [ROUND_W_VERIFICATION_SUMMARY.json](ROUND_W_VERIFICATION_SUMMARY.json)이다. 사례별 비교는 `artifacts/round_w/final/comparison.json`, 처분·기본 "No" 집계는 `artifacts/round_w/final/disposition_and_default_no.json`, 불필요 EXAM 귀속 분석은 `artifacts/round_w/final/unnecessary_exam_audit_*.json`에 있다.

```
BASELINE RUNTIME SHA: e16448e13431ab7af21d1e1c8abc5ecf2cf16e3c (Round V final)
FINAL RUNTIME SHA:    f677d05eb3cd9b8a441c63a64ffdc9349b635d4f
(first final candidate 288d8d5: 같은 31+2단계 실행에서 새 오답 2개 발견 → 수정 후 f677d05로 처음부터 재실행)

TESTS (검증 worktree f677d05, NOVA_COMPETITION_RETRIEVAL 미설정):
passed 2526 + release-binding 재실행 1 / failed 0 (로컬 v29 기록 기준) / skipped 2(torch 미설치, package-not-built)
공개 트리는 ZIP 미공개로 release-binding 1개 실패(기준선과 동일). 새 테스트: tests/test_round_w.py

PRELIMINARY (230 / 222 scored): 219 → 219, critical 85/85 → 85/85, 평균 턴 19.78 → 19.75
exam-rejection 217 → 217, unscripted-unknown 218 → 218. new wrong 없음
unnecessary EXAM: 296 → 283 (전체 EXAM 1236 → 1221)  ← 목표 238 미달
ROUND P 31/32 → 31/32 (critical 13/13). ROUND M 121/123 → 121/123 (critical 43/43, long-tail Top1 24/26)
비교 세트 전체: new scored wrong 0, new critical miss 0. TEST 허용 8종 기준선과 동일
follow-up 신규 12 → 13/16 (critical 3/4 → 4/4, FollowU_21 새 정답)

ROUND W 개발 세트 (12 / 9 scored, 소스 수정 전 동결, 기준선 먼저 실행): 7/9 → 9/9, 행동 계약 35/35 → 35/35
ROUND W CLOSING (12 / 10 scored, runtime 커밋 전 동결, 소스 수정에 사용 안 함): 6/10 → 7/10, critical 4/6 → 5/6 (CloseW_11 청소년 DKA 새 정답; CloseW_01 영아 수막염은 기준선·최종 모두 miss)
ROUND V CLOSING (이번 라운드에서 개발 세트로 승격): 7/10 → 9/10, critical 1/2 → 2/2

DISPOSITION 계약 89개: FP 0 → 0, FN 2 → 0
기본 "No" 의존 정답 수: 1 → 1
LEAKAGE: NO OBVIOUS LEAKAGE. ADVERSARIAL: ALL CHECKS PASSED. ASSERTION 10/10
SUBMISSION: mirror byte equality PASS, package audit PASS(secret scan PASS), ZIP clean-room all_pass, fresh smoke PASS
ZIP SHA256 71237eeb5226783bb19a8f0b5ee2e1a94c2534e7f91a78e6ebed72eac71d3bf2 (852,119 bytes; 로컬 전용)

VERDICT: overall FAIL — "불필요 EXAM ≤ 238" 미달(283). 나머지 완료 기준 충족.
official API / real GPT-OSS: NOT VERIFIED. independent clinical validation: NOT PERFORMED.
```

## 1. 완료 기준

| 기준 | 결과 | 판정 |
|---|---|---|
| 테스트 failed 0 | 로컬 v29 근거 기준 0 | 조건부 PASS |
| 새 scored wrong 0 / 새 critical miss 0 | 0 / 0 (최종 f677d05) | PASS |
| 예선 ≥219, critical 85/85, Round P ≥31, Round M ≥121 | 219, 85, 31, 121 | PASS |
| 처분 FP ≤ 0, FN < 2 | FP 0, FN 0 | PASS |
| **불필요 EXAM ≤ 238** | **283** | **FAIL** |
| 평균 interaction ≤ 20 | 19.75 | PASS |
| Round W closing critical miss 0 | CloseW_01 miss(기준선부터) | **FAIL** |

## 2. 변경 (모두 일반 기전, 스위치로 끌 수 있음)

| 문제 | 원인(추적 결과) | 수정 |
|---|---|---|
| 영아 패혈증 → heat stroke (CloseV_03, critical) | RR 64가 모델 상한 60을 넘어 **활력징후 줄 전체**가 버려짐(HR 192·체온 39.8 소실). heat stroke는 "very floppy, hot"만으로 명명 | RR 상한 120, 범위 밖 값만 개별 폐기; 소아 빠른 맥박 기준(PALS); heat stroke 명명에 열 노출·운동 맥락 필요(정확한 정규식, 부정 제외) |
| 실제 열사병(RoundW_03) → sepsis | "My husband collapsed…"가 **가족 문장으로 통째로 삭제** | 보호자 진술 인식(`NOVA_PROXY_REPORT`): 관계어가 환자 성별·나이와 맞으면 환자로 처리. 사례 범위 contextvar |
| 저나트륨 경련(FollowU_21) 처분 FN | "Dad has become confused…, he had a fit"도 같은 삭제 | 위 보호자 진술(관계어로 시작하는 문장 포함) |
| HR 34 쓰러짐(CloseUF_03) 처분 FN | 증상 목록에 "collapsed" 없음 | collapse 계열 추가(NICE CG109) |
| 대상포진 → GERD/신우신염 (CloseV_12, RoundW_08) | 띠·줄·선 표현 미인식; RoundW_08은 진단 직전 rerank 재배치로 선두 후보가 pool에서 빠짐 | 대상포진 분포 관계 문법(영/한/일); 근거 있는 ontology 후보 유지(`NOVA_RETAIN_EVIDENCED`) |
| 중이염 → viral URI (CloseV_02) | "after a runny nose" 미인식 | `recent cold` 표현 추가. 단, 아래 선행 맥락 가중 변경으로 다시 실패(남은 실패) |
| 불필요 EXAM 296 | 귀속 분석: 전체 EXAM 수는 비슷하나 Tier-2 후보가 최종 상위 5개에 남아 Tier-1 진찰이 "불필요"로 집계 | 측정값 기반 활력 특징(`NOVA_MEASURED_THRESHOLDS`, 고혈압 응급 등), 선행 맥락은 위험인자 가중(`NOVA_CONTEXT_V2`), 명칭 계층에 같은 category 조건 → 283 |
| 패혈성 관절염(CloseUF_11) | "too painful to bend" 미인식 | 관절 운동 제한 표현 |

되돌리거나 끈 것: `NOVA_PATTERN_V2`(bare "No" 반감을 비일반 특징 2개 이상 가설에만 적용) — 불필요 EXAM을 261까지 줄였지만 첫 최종 후보에서 RoundM_109·CloseUF_11 새 오답을 만들어 **기본 OFF**. 정확도를 지표보다 우선했다.

## 3. DISPOSITION FP/FN (계약 89개)

| 세트 | FP 기준선 → 최종 | FN 기준선 → 최종 |
|---|---|---|
| follow-up 신규 | 0 → 0 | FollowU_21 → 없음 |
| follow-up closing | 0 → 0 | CloseUF_03 → 없음 |
| Round V 2종, Round W 2종, S·T·U | 0 → 0 | 0 → 0 |
| 합계 | **0 → 0** | **2 → 0** |

## 4. 기본 "No" 의존

| runtime | 기본 조건 | unscripted-unknown | 의존 정답 수 |
|---|---|---|---|
| e16448e | 219 | 218 | 1 |
| f677d05 | 219 | 218 | 1 |

## 5. 남은 실패

| 사례 | 내용 |
|---|---|
| CloseW_01 (영아 수막염, critical, closing) | 기준선·최종 모두 미분화. closing 세트라 소스 수정에 쓰지 않음 |
| CloseW_08 (한국어 대상포진, closing) | 신우신염 명명 |
| CloseW_09 (한국어 통풍, closing) | 미분화 |
| CloseV_02 (중이염) | viral URI. 선행 맥락 가중 변경의 대가 |
| 불필요 EXAM 283 | 목표 238 미달. 귀속 분석 결과는 다음 라운드 EXAM 효용 모델 과제 |
| 실제 GPT-OSS·공식 인터페이스 | NOT VERIFIED / BLOCKED |

## 6. 자체 100점 추정 (공식 점수 아님)

| 항목 | 배점 | Round V | Round W | 근거 |
|---|---|---|---|---|
| 실제 모델·공식 인터페이스 | 20 | 4 | 4 | BLOCKED |
| 예선형 진단 정확도 | 20 | 18 | 18 | 219/222, Round M 121 |
| 일반화 | 15 | 9 | 10 | Round V closing 9/10, Round W closing 7/10(기준선 6), 새 오답 0 |
| 안전·처분 | 15 | 12 | 13 | 처분 FN 2→0, FP 0; closing critical miss 1 남음 |
| 지식 깊이·출처 | 10 | 6 | 6 | 활력·명명 규칙 출처 추가, 깊이 보강은 소수 |
| 효율·SOAP | 10 | 7 | 7 | 19.75턴, 불필요 EXAM 283 |
| 검증·재현성 | 10 | 9 | 9 | 동일 조건 실행 2회(첫 후보 회귀 발견 후 재실행) |
| **합계** | **100** | **≈65** | **≈67** | |
