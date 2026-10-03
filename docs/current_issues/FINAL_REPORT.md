# N.O.V.A. CURRENT-ISSUES FIX REPORT

검증 시각: 2026-10-03T09:54:26.921179+00:00

- 저장소: https://github.com/hundol047/nova
- 대상 브랜치: `offline/nova-competition-agent-optimization`
- 시작 시 실제 원격 HEAD: `5727c6df71ab328b3eed68c1ae218443bf584fb1`
- 런타임 고정 시 확인한 REMOTE HEAD / LATEST REASONING SHA: `14e6644d5f0def1516ce165a7a5e1c7164cbc405`
- 보고서·검증 파일은 이 고정 커밋 뒤에 별도로 커밋한다. 최종 게시 HEAD는 GitHub 브랜치에서 확인한다.
- `main` 변경·병합 없음. Actions dispatch 없음. 외부 LLM 대체 없음.

## 변경과 해결 범위

| 파일 | 변경 이유와 결과 |
| --- | --- |
| `nova_agent/uncertainty.py` | 결정론적 후보의 중복 제거된 근거, 모순, 후보 간 점수 차이, 근거 출처, 증상 개념과 비의료 작업 의도를 함께 평가한다. 낮은 점수만으로 OOD를 반환하지 않는다. |
| `nova_agent/orchestrator.py`, `state.py` | 내부 근거 평가를 매 턴 갱신하고 예외 시 이전의 높은 신뢰 상태가 남지 않게 한다. 순위·안전 조사 경로는 유지한다. |
| `competition/adapter.py`, `schema.py` | 내부 `SUPPORTED_DIAGNOSIS` / `INSUFFICIENT_INFORMATION` / `OUT_OF_DOMAIN`과 wire 출력을 구분한다. 강제 출력은 `FORCED_FINAL_DIAGNOSIS`, `forced_due_to_protocol`, `internal_result`, `wire_result`로 기록한다. 실제 호출 성공이 False뿐 아니라 미확인(None)이어도 차단한다. |
| `nova_agent/llm_client.py` | 요청 모델과 응답의 모델 식별자가 `openai/gpt-oss-20b`인지 확인한다. 구조화 응답과 비어 있지 않은 action을 요구한다. timeout (0,120]초·retry 0~3회 범위 밖 설정을 거부한다. |
| `submission/run.py`, `scripts/preflight_competition.py` | 대회 연결/파싱 실패 시 시작 단계에서 `NOT READY`, 비정상 종료, stdout 응답 없음. mock만 명시적 개발 예외다. 공식 스키마 미확인은 제출 준비 완료 판정을 막는다. |
| `scripts/build_nova_submission.py` | 빌드의 실행 확인은 명시적 mock으로 수행한다. 이를 실제 모델 성공으로 표시하지 않는다. |
| `evaluation/ood_development.py`, 평가 스크립트·테스트 | 새 합성 개발 사례 32개, 저점수 위험 증상 보호, 내부/wire 분리, 미호출·예산 만료·사례 간 성공 이월 방지, timeout/retry/잘못된 모델/파싱 실패를 검사한다. |
| `evaluation/current_blind.py`, v17 무결성 테스트 | v17을 REFERENCE-ONLY로 전환한다. 기존 사례·manifest·결과를 그대로 보존하며 v8 ZIP에 보존된 런타임 해시를 확인한다. 한 번만 실행하는 기존 runner 제약은 유지한다. |
| `scripts/record_current_issues_verification.py`, v9 일치 검사 | 고정 커밋·현재 파일·제출 파일·ZIP의 실제 바이트와 해시를 검사한다. 실행된 JUnit 결과에서 통계를 읽는다. |

## OOD / UNSUPPORTED

Internal OOD state: **PASS (제한적인 개발용 휴리스틱)**. Forced protocol output distinguishable: **PASS**.

데이터는 새로 작성한 **합성 개발 사례**다. 독립 검증·전문가 정답 검토·환자 데이터가 아니다. 최종 턴의 근거 상태를 검사하며 진단 정확도를 재는 시험이 아니다. v17 문장이나 정답을 가져오지 않았다.

| 지표 | 측정 결과 |
| --- | --- |
| 지원 가능 사례를 OOD로 잘못 분류 | 0/12 (0.00%) |
| 비의료 OOD 탐지 | 6/8 (75.00%) |
| 미지원·불충분 사례의 불확실성 표시 | 20/20 (100.00%) |
| 전체 중 정보 불충분 | 23/32 (71.88%) |
| 형식 제약으로 강제된 최종 질환명 | 29/32 (90.62%) |
| 미지원 사례에 SUPPORTED 판정을 준 비율(대리지표) | 0/20 (0.00%) |
| 근거가 있는 개발 사례의 SUPPORTED 판정 | 3/4 (75.00%) |

OOD 탐지 6/8과 불확실성 표시 20/20은 서로 다른 지표다. 놓친 비의료 요청 2개는 정보 불충분으로 남았다. 지원 범위의 증상 12개를 OOD로 제외하지 않았지만, 이것이 해당 12개를 정확히 진단했다는 뜻은 아니다. 근거가 있는 4개 중 1개도 불충분 판정이 남아 보수적 거절과 후보 범위를 더 평가해야 한다.

현재 RAG API에는 검증된 retrieval confidence와 독립 모델 간 합의 점수가 없으므로 `null`로 기록한다. 후보 출처 수를 독립적인 모델 합의로 포장하지 않는다. confidence 백분율을 만들지 않으며 `calibrated=false`다.

현재 기본 wire는 잠정 프로토콜의 DIAGNOSE다. 공식적으로 허용되는 abstention이 확인되지 않아 임의의 OUT_OF_DOMAIN wire label을 추가하지 않았다. 기존 실험 플래그가 켜진 경우만 INSUFFICIENT_INFORMATION과 불확실성 문구를 반환한다. 강제 질환명은 임상적으로 지지된 결과로 취급하면 안 된다.

## REAL GPT-OSS

| 항목 | 결과 |
| --- | --- |
| Endpoint available | **NO** — 별도 주소가 설정되지 않았으며 기본 localhost 최소 요청 실패 |
| Model target | `openai/gpt-oss-20b` |
| Revision | 지정된 revision 없음; 임의로 추정하지 않음 |
| Live call | **NOT VERIFIED** |
| Structured parse — 실제 모델 | **NOT VERIFIED** |
| Real-call gate | **PASS** — 미호출, 실패, 예산 만료, 새 사례 분리 검사 |
| A. mock | PASS — 독립 복사본에서 다중 턴 완료 |
| B. competition / unreachable | PASS — NOT READY, exit 1, stdout에 가짜 action 없음 |
| C. competition / local valid stub | PASS — HTTP·구조화 파싱·사례별 호출 횟수·다중 턴 연결만 검증 |
| D. 실제 endpoint | NOT VERIFIED — 사용할 수 있는 endpoint 없음 |

스텁의 모델 문자열은 실제 가중치나 revision의 증거가 아니다. `real_llm_verified`라는 기존 wire 필드는 해당 사례에서 HTTP 응답과 구조화 파싱이 성공했음을 뜻하며, 가중치 검증·정답 보증을 뜻하지 않는다. 시작 전 probe의 성공을 새 사례의 성공 횟수에 더하지 않는다.

## OFFICIAL API

**NOT VERIFIED.** Placeholder boundary clean: **PASS**.

`competition/schema.py`와 JSON-lines I/O는 PLACEHOLDER다. endpoint·모델 설정·실험적 abstention은 CONFIGURABLE이다. 이 저장소에 공식 API 문서와 규정 증빙이 없어 CONFIRMED OFFICIAL이라고 표시할 근거가 없다. HTTP 경로 `/chat/completions`, 응답 `model` 필드의 정확한 문자열 일치는 현재 가정이며 공식 서버가 다른 계약을 사용하면 증빙을 받아 어댑터를 수정해야 한다. strict 검증을 임의로 완화하지 않는다.

## SUBMISSION

| 항목 | 결과 |
| --- | --- |
| Runtime sync | **PASS** — 원본/미러/고정 커밋/ZIP 해시 일치 |
| Standalone | **PASS** — 격리 복사본, PYTHONPATH 없이 mock·stub 실행 |
| ZIP | `artifacts/verification/nova-submission-v9.zip` |
| ZIP size / under 50 MB | **254,138 bytes / YES** |
| SHA-256 | `ced836b9082d2d066d58707f14ec8f9cededbe04265d860b7a6dd148f4c29aa6` |
| Secret scan | **PASS** — 자격 증명 형태의 문자열 검사; 절대적인 무결점 보증 아님 |
| 파일·의존성 | run.py·requirements.txt 포함. pydantic만 필요. 외부 LLM SDK·frontend·backend·학습 산출물 없음 |

## REGRESSION

**798 passed / 1 skipped / 0 failed.** 기존 회귀 테스트와 신규 경계 검사 포함. 1개 기존 skip은 선택적 torch 미설치로 실행하지 못한 학습 체크포인트 테스트다. FastAPI TestClient 의존성 경고 1개는 기존 사항이다.

아래는 **기존 합성·mock 평가군의 회귀 결과**다. 반복 사용된 테스트이므로 독립 임상 정확도나 새 블라인드 성적이 아니다. 비교 기준은 `artifacts/round_g/regression/competition_metrics.json`이다.

| 평가군 | 채점 대상 / 전체 | 채점 정답률 | 위험질환 재현율 | 정답률 / 위험 재현율 변화 |
| --- | --- | --- | --- | --- |
| tuning | 8 / 8 | 100.00% | 100.00% (6건) | +0.0% / +0.0% |
| held_out | 15 / 18 | 100.00% | 100.00% (13건) | +0.0% / +0.0% |
| generalization_v2 | 18 / 18 | 100.00% | 100.00% (5건) | +0.0% / +0.0% |
| stress | 8 / 8 | 100.00% | 100.00% (5건) | +0.0% / +0.0% |
| dev_round_d | 6 / 7 | 100.00% | 100.00% (3건) | +0.0% / +0.0% |
| dev_round_e | 6 / 7 | 100.00% | 100.00% (5건) | +0.0% / +0.0% |

- Round G 개발군: **11/12**, 위험 사례 **3/4**, 평균 **36.75턴**. 기존 결과와 상세 요약이 동일하며 남은 위험 사례 오류를 숨기지 않는다.
- 일반 모드 회귀도 채점 정답률·위험 재현율 유지. retrieval Recall@50은 초기 증상 **61.4%**, 증상+과거력 **93.2%**로 유지. routing의 기존 내부 검사 지표 유지. 다국어 검사 통과.
- 누출 검사: 기존 14개 blind 모듈 653개 사례와 runtime을 검사해 명시적 누출 미검출. 이 정적 검사가 모든 의미적 누출을 증명하는 것은 아니다.
- Generalization의 불필요 검사 수 대리지표는 실행 사이 소폭 달라져 이번 변경의 효율 개선으로 주장하지 않는다. 나머지 비교 수치는 JSON에 보존한다.
- Critical recall regression: **NO** — 검사한 기존 평가군 기준. 실제 임상 성능 보장은 아님.
- v17: **REFERENCE-ONLY**, 수정 0회·추가 실행 0회. 과거 48/55·24/25 수치는 새 런타임의 성능으로 제시하지 않는다. 새 blind는 이번 회차에 실행하지 않았다.

## 남은 문제와 다음 우선순위

1. **P0 외부 제출 준비**: 공식 endpoint·가중치/revision·API/규정 문서가 필요하다. 실제 최소 호출 및 짧은 사례 완주와 스키마 적합성 검증이 끝나기 전 제출 준비 완료가 아니다.
2. **P1 불확실성 평가**: 어휘 밖 비의료 요청, 미지원 임상 입력, 과도한 불충분 판정을 독립적인 전문가 검토 사례로 평가해야 한다. 보수적인 OOD 규칙의 6/8을 일반 OOD 성능으로 확대 해석하지 않는다.
3. **P1 후보 범위·위험 오류**: Round G 위험 오류 1개와 신규 근거 스냅샷의 미지원 후보 문제를 별도 개발 사례와 근거로 조사한다. 새 질환 대량 추가는 하지 않았다.
4. 런타임 수정이 끝나고 외부 조건이 갖춰지면 다시 고정한 뒤 **새로운** 블라인드 평가가 필요하다. 과거 v17을 반복 실행하거나 그 정답으로 조정하지 않는다.

세부 원시 로그: `artifacts/current_issues/`. 재현 가능한 검증 기록: `artifacts/verification/local-release-14e6644-v9.json`. 현재 포인터: `artifacts/verification/CURRENT_RELEASE.json`.
