# N.O.V.A. FINAL COMPETITION-INTEGRATION REPORT

로컬 개선·검증·제출 패키지 작업을 완료했습니다. 실제 모델과 공식 API 연동은 외부 정보가 없어 **EXTERNAL BLOCKED**입니다. **새 v18 정답률은 70.69%, 위험 사례 정답률은 88.0%이며 위험 사례 3개를 놓쳤습니다.** 개발군의 개선을 실제 임상 성능으로 해석하지 않습니다.

BRANCH: `offline/nova-competition-agent-optimization`  
FINAL REASONING SHA: `d6e2b84aa2bb90c198fae39dade3870d6575c6f4`  
v18 AUTHORING SHA: `6f7bd2748c29b46d762953477ace316dc83bb75c`  
FINAL REMOTE SHA / LOCAL == REMOTE: 최종 push 후 실제 조회한 값은 전달 메시지에 기록합니다. 이 문서와 아래 증거는 최종 결과 커밋에 포함됩니다. Main 병합은 하지 않습니다.

## OFFICIAL DOCUMENTATION

| 항목 | 상태 |
| --- | --- |
| Official API docs found | NO — 공개 규정·평가·FAQ는 확인, 실행 가능한 계약은 미확인 |
| Schema | PLACEHOLDER |
| Auth / endpoint | NOT VERIFIED / NOT VERIFIED |
| Legal actions | 이름과 의미 CONFIRMED_OFFICIAL; JSON 표현은 PLACEHOLDER |
| Abstention allowed | NOT VERIFIED |

근거와 요소별 네 가지 상태 분류는 [공식 인터페이스 감사](../competition/OFFICIAL_INTERFACE_AUDIT.md)에 기록했습니다. [공식 규정](https://nova.snubhai.org/rules/), [평가](https://nova.snubhai.org/evaluation/), [FAQ](https://nova.snubhai.org/faq/)를 기준으로 했으며, 비공개 참가자 메일에 추가 문서가 없다고 단정하지 않습니다.

## REAL GPT-OSS

| 항목 | 상태 |
| --- | --- |
| Target model | `openai/gpt-oss-20b` |
| Expected revision | `4d7ae4984b7db7de8f8457170b3f1a419ee76d52` |
| Endpoint configured | NO; NOT_CONFIGURED, 시도 0회 |
| Authentication / live HTTP / model identity | 모두 NOT VERIFIED |
| Revision runtime verification | NOT_VERIFIABLE_FROM_RUNTIME |
| Structured real-model output | NOT VERIFIED |
| Real-call success gate | PASS — 로컬 HTTP stub·격리 사례 테스트 |
| Real-model short multi-turn case | NOT VERIFIED |
| Real-model development comparison | 실행하지 않음; EXTERNAL BLOCKED |

설정 없음, 연결 실패, 인증 실패, 모델·revision 불일치, 구조 파싱 실패를 별도 상태로 보고합니다. 응답에 revision이 없다는 이유만으로 실패시키지 않고, 문서화되지 않은 revision 요청 파라미터도 보내지 않습니다. 서버가 반환한 모델명은 실제 가중치의 독립적인 증명이 아닙니다. 사전 점검 성공은 새 사례의 성공 횟수로 이월되지 않습니다. 현재 사례에 파싱된 HTTP 성공이 없으면 최종 competition 답변을 차단합니다. 의료 내용 문자열을 바꾸지 않는 구문 복구와 제한된 재시도를 검증했습니다.

## OOD / UNCERTAINTY

새 Round I 요청 범위 검사 24개, 강제로 한 턴만 허용한 합성 개발 평가입니다.

| 지표 | 결과 |
| --- | --- |
| Supported false-OOD | 0/8 |
| OOD detection | 9/9 (수정 전 0/9) |
| Insufficient-information detection | 7/7 |
| Insufficient-information 전체 비율 | 15/24 |
| Unsafe confident unsupported diagnosis proxy | 0/16 |
| Protocol-forced diagnosis rate | 24/24 |
| Hard medical inputs retained in medical scope | 2/2 |

이 검사의 OOD는 증상 진단 업무 범위 밖 요청을 뜻합니다. 행정·약 보관 질문도 포함하되 현재 증상이나 과다복용 문맥이 있으면 배제하지 않습니다. 강제 프로토콜 병명과 내부 판단 불확실 상태는 다릅니다. 이전 32개 OOD 회귀군은 6/8 탐지, 지원 사례 오탐 0/12로 유지됐습니다. 2/2는 희귀질환 진단 정확도가 아니라 의료 문맥 보존입니다.

## ACCURACY DEVELOPMENT

| 지표 | 수정 전 → 수정 후 |
| --- | --- |
| Top1 / Top3 / Top5 / Top10 | 각각 16/19 (84.21%) → 17/19 (89.47%) |
| MRR | 0.84421 → 0.89474 |
| Median true rank | 1 → 1; 양쪽 모두 순위 미포함 2건 별도 |
| Critical Top1 / Top5 | 각각 7/8 → 8/8 |

새 20개 사례 중 명확한 정답 가설 19개를 채점했습니다. 양성 신경학적 소견이 부정형 안심 근거에도 일치하던 오류를 수정했습니다. 검색·점수 가중치·Safety·행동 선택·종료 정책을 재설계하지 않았습니다. 실패별 전체 검색/재정렬/활성 순위와 근거 구성은 `artifacts/round_i/baseline.json`, `after.json`에 있습니다. 성공 사례는 마지막 단계만 보관했습니다. 기여도는 제한값이 있는 점수의 차이이며 확률이 아닙니다.

## REGRESSION

Tests passed: **833** / failed: **0** / skipped: **1**. Skip: 선택적 torch 없음. FastAPI 테스트 도구의 사용 중단 예고 1건은 남아 있습니다. v18 승격 과정에서 과거 v16 테스트가 현재 버전을 v17로 고정한 오류를 발견해 역사 보존 조건으로 바꿨고, 최종 전체 테스트를 다시 통과했습니다. 진단 코드나 정답은 바꾸지 않았습니다.

| 대회 구조/mock 회귀군 | 정답 | 위험 사례 |
| --- | --- | --- |
| Tuning | 8/8 | 6/6 |
| Held-out | 15/15 (전체 18 중 사전 제외 3) | 13/13 |
| Generalization-v2 | 18/18 | 5/5 |
| Stress | 8/8 | 5/5 |
| Round D | 6/6 (전체 7) | 3/3 |
| Round E | 6/6 (전체 7) | 5/5 |
| Round G | 11/12 | 3/4 |
| Round I | 17/19 (전체 20) | 8/8 |

Retrieval regression: **NO**. Chief-only R@20 56.8%, R@50 61.4%; chief+history 75.0%, 93.2% (44개 합성 검색 검사). 이 출력의 과거 baseline 대비 향상은 이번 변경 효과가 아닙니다. Critical recall regression: **NO** — 동일 기존 회귀군 기준. Round G의 기존 위험 사례 오답은 해결되지 않았습니다. Adversarial, failure analysis, routing, specificity 및 leakage 검사 모두 통과했습니다. v18 포함 누출 검사는 717개 blind 사례/15개 모듈/120개 코어 파일 대상으로 명백한 누출을 발견하지 못했습니다. 의미상 독립성을 증명하는 검사는 아닙니다.

## BLIND v18

| 항목 | 결과 |
| --- | --- |
| Provider | COMPETITION-STRUCTURE / MOCK-LLM |
| Case count | 64; 채점 58, 위험 25, 사전 비채점 6 |
| Scored accuracy | **41/58 = 70.69%** |
| All-case correctness | 41/64 = 64.06% (비채점 사례 포함한 별도 참고값) |
| Critical recall | **22/25 = 88.0%** |
| Critical miss | **3/25 = 12.0%** |
| Average turns | 33.578125 |
| Average TEST | 14.125 |
| Malformed / duplicate | 0 / 0 |
| Run count | **1** |
| Case SHA-256 | `4444c4c8b8eede5534cf2f063a19a8d3d8687943639dc442d159657412f12980` |
| Manifest SHA-256 | `304d6b48c6e3656f8a7e0ffbbb83b6814bddf263490c4e1a6376598d870fba71` |

코드 고정 커밋을 원격에 게시한 뒤 새 문장을 작성했고, 정답 식별자·스키마·중복 검증 후 사례·실행기·런타임 해시를 동결해 게시했습니다. 원자적 실행 표식을 만든 다음 한 번 실행했습니다. 기존 v17 문장과 결과로 조정하지 않았으며 v17 파일/결과는 원본 그대로입니다. 같은 개발자가 작성한 합성 평가로, 외부 독립 임상 검증이나 전문가 정답 검토는 아닙니다. 모델 학습도 하지 않았습니다.

17개 채점 오답 모두 `blind_v18_failure_review.json`에 남겼습니다. 위험 오답은 긴장성 기흉 1건과 뇌졸중 2건입니다. 세 사례 모두 정답이 Top5에 있었으나 최종 선택되지 않았고, 뇌졸중 2건에서는 준비된 MRI 결과를 요청하지 않았습니다. 이 관찰만으로 정확한 점수 원인을 확정하지 않았습니다. 검색 내부 단계가 없는 holdout 기록에서 검색 실패라고 단정하지 않습니다. v18을 재실행하거나 결과에 맞춰 런타임을 수정하지 않았습니다.

비채점 6건의 `unsupported_case_success_rate=1.0`은 루프가 종료됐다는 기존 지표일 뿐, 올바른 임상 판단·안전한 기권 성공률이 아닙니다. 합성 기본 응답의 부정/정상 가정과 문자열 정답 매칭도 한계입니다.

## SUBMISSION

ZIP: `artifacts/verification/nova-submission-v10.zip`  
Size: **257390 bytes**, 77 archive entries including MANIFEST  
SHA-256: `6b0a376df6787a73c70b1ec7c0afdbcb55f3b434b55773020790581529369ed3`

Under 50MB: YES (<50,000,000 bytes). Runtime sync: PASS. Secret scan: PASS. `run.py`, `requirements.txt` 포함. 패키지는 코어/어댑터와 필수 파일만 포함하며 learning/web/frontend/backend/가중치는 없습니다. 추가 의존성 없이 pydantic만 필요합니다. PYTHONPATH를 지운 격리 복사본으로 mock 전체 루프, 연결 실패 시 stdout 차단·비정상 종료, 로컬 HTTP stub을 검증했습니다.

MOCK LOOP: PASS  
LOCAL PROTOCOL STUB: PASS — 실제 모델 검증 아님  
REAL MODEL: NOT VERIFIED  
OFFICIAL API: NOT VERIFIED

v10은 ZIP 파일 수를 실제 아카이브 항목에서 집계합니다. 이전 v9 기록의 파일 수는 테스트 이름 수를 잘못 사용한 값이므로 현재 패키지의 근거로 사용하지 않습니다. 역사 아카이브/기록은 보존했습니다.

## VERIFICATION

Schema: **nova-verification-v10**. Runtime SHA: `d6e2b84aa2bb90c198fae39dade3870d6575c6f4`. CURRENT_RELEASE: PASS; 현재 포인터, 실행 manifest, 결과, ZIP 및 원본/복사본 SHA-256이 일치합니다. 최종 테스트 수는 실행한 JUnit 결과를 파싱했습니다. 고정 후 런타임 변경 없음. [기계 판독 결과](../../artifacts/verification/local-release-d6e2b84-v10.json).

## 변경 파일과 이유

| 파일/영역 | 변경과 해결 문제 |
| --- | --- |
| `nova_agent/config.py`, `llm_preflight.py`, `llm_client.py` | 설정/전송/정체성/파싱 상태 구분, 토큰 노출 경로 축소, 문자열 보존 구문 복구 |
| `nova_agent/matching.py`, `differential.py` | 실제 부정 표현이 있을 때만 부정형 안심 근거 적용 |
| `nova_agent/uncertainty.py` | 새 요청 범위 OOD 처리, 현재 의료 문맥 보호 |
| `competition/readiness.py`, `submission/run.py` | 로컬 전송 성공과 공식 제출 준비 상태 분리; 실패 시 출력 차단 |
| `submission/nova_agent/`, `submission/competition/` | 원본과 바이트 단위 동기화 |
| `evaluation/generalization_dev_cases_round_i.py`, `scripts/evaluate_round_i.py` | 새 개발군 및 실패 단계·근거 기록 |
| `evaluation/blind_*v18*`, `evaluation/current_blind.py` | 고정 후 새 64개 평가·해시·단일 실행 보호 |
| `scripts/check_blind_v18_integrity.py`, `record_verification_v10.py`, `build_nova_submission.py` | 누출/정답 형식/증거 기록/패키지 크기 검증 |
| `tests/test_round_i_integration.py`, `test_blind_v18_integrity.py`, `test_verification_v10_consistency.py`와 역사 테스트 | 재시도·부정·사례 격리·동결/아카이브 무결성 회귀 |
| `README.md`, `CHANGELOG.md`, `docs/competition/`, `docs/round_i/`, `artifacts/` | 실제 성능, 구현 범위, 오답, 외부 제약 공개 |

## REMAINING EXTERNAL BLOCKERS / 다음 우선순위

1. 공식 참가자 API/입출력/run.py 규격 및 abstention 허용 여부 확보 → 경계만 변경하고 공식 예제 계약 테스트.
2. 주최 측 허용 모델 endpoint/token 확보 → 최소 실제 호출, 짧은 사례, 개발군 비교 순서로 검증. 현재 실제 모델 호출 성공률·파싱률·지연 p50/p95·진단 성능은 측정하지 못했습니다.
3. P0/P1: 새로운 개발 자료와 전문가 정답 검토를 통해 위험 후보가 Top5에 남아도 잘못 선택되는 문제, 필수 확인 검사 누락을 조사. 이번 v18을 튜닝 자료로 사용하거나 재실행하지 않음.
4. 긴 꼬리 질환과 양성 유사 증상 후보 처리, 과도한 검사 비용 개선. 안전성을 낮춰 평균 턴 수를 줄이지 않음.

## FINAL STATUS

Local software: **READY — 로컬 빌드·회귀·패키지 수준**  
Real gpt-oss integration: **NOT VERIFIED**  
Official API integration: **NOT VERIFIED**  
Official submission: **EXTERNAL BLOCKED**

99.99%/100% 또는 임상 사용 준비 완료라고 주장할 근거는 없습니다.
