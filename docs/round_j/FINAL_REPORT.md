# N.O.V.A. STRUCTURAL DEFICIENCY REPAIR REPORT

FINAL_REASONING_SHA: `f315fbf27bafaaeecb43344428ac61d7fe1a7a05`

Target branch: `offline/nova-competition-agent-optimization`. Baseline remote/runtime checkout:
`887a7d9ba2c79aa4ef0a8a7b0dce4a7362787c30`. Main is unchanged. No reasoning edits follow this freeze.

## 결과와 해석

Round J는 **54개 새 합성 개발 사례**이며 52개를 채점합니다. 이 중 위험 사례는 20개이고,
나머지 2개는 OOD/정보 부족 동작을 관찰하는 비채점 사례입니다. Tier-2 이름을 포함한 4개
범위 확인 사례도 채점 분모에 포함했습니다. 수정 전 47/52 → 수정 후 48/52입니다.
기존 심층 KB에 해당하는 48개 중 47 → 48개를 맞췄지만, 이를 전체 질환 성능으로 표시하지 않습니다.

**Mock LLM, 동일 작성자 합성 개발 평가, 전문가 정답 검토 없음, 독립 임상 검증 없음.**
기존 KB의 용어와 인공적인 정상/음성 기본 응답을 이용한 개발 사례입니다. 실제 환자 정확도,
모델 학습 결과 또는 v18 대비 일반화 향상으로 해석할 수 없습니다. 자동 학습은 하지 않았습니다.

| Metric | Before | After |
|---|---:|---:|
| Top1 | 90.38% | 92.31% |
| Top3 | 90.38% | 92.31% |
| Top5 | 90.38% | 92.31% |
| Top10 | 92.31% | 94.23% |
| MRR | 0.9074 | 0.9258 |
| critical_Top1 | 100.00% | 100.00% |
| critical_Top3 | 100.00% | 100.00% |
| critical_Top5 | 100.00% | 100.00% |
| critical_recall | 100.00% | 100.00% |
| critical_miss | 0.00% | 0.00% |
| retrieval_truth_retention | 78.85% | 80.77% |
| rerank_truth_retention | 59.62% | 65.38% |
| active_truth_retention | 94.23% | 94.23% |
| critical_candidate_retention | 100.00% | 100.00% |
| action_selection_error_rate | 0.00% | 0.00% |
| final_ranking_error_rate | 3.85% | 1.92% |
| Mean turns | 29.59 | 26.19 |
| Mean TEST actions | 12.06 | 10.81 |
| Median true rank (active only) | 1; missing 3 | 1; missing 3 |
| Policy diagnostic delay | 0 (50 measured / 54) | 0 (50 measured / 54) |

위험질환 recall은 정답 라벨 일치 20/20이며 임상적 안전성 인증이 아닙니다. 행동 선택 오류율의
분모는 채점 사례 52개이고, 이 세트에서는 수정 전후 모두 해당 primary class가 0입니다.
별도 메커니즘 테스트에서 감별 검사 누락을 재현하고 수정했으나, 이를 52개 평가의 오류율 개선으로
바꿔 쓰지 않습니다. Final-ranking primary error는 2/52 → 1/52입니다.

Diagnostic delay는 현재 StopPolicy가 비강제 종료를 허용한 최초 시점과 실제 종료 시점의 차이입니다.
50개에서 측정됐고 나머지는 null입니다. 의료 전문가가 판단한 최적 진단 시점이 아니므로,
과잉 검사 감소는 실제 평균 TEST/turn 수로 별도 보고합니다.

## 실제 수정과 검증

| Files | Problem and change | Verification |
|---|---|---|
| `nova_agent/clinical_presentation.py`, `candidate_generator.py` | 후속 답변의 구체적 증상 문구가 큰 증상 분류로 축약돼 검색에서 유실됨. 관찰된 문구로 기존 심층 프로필을 조회하고, core 검색 결과는 원래 근거/검사 정보를 보존함. | 후속 증상으로 후보가 진입하는 새 테스트; Round J 24 오답 해결; Round I 17/19 → 18/19 |
| `nova_agent/differential.py` | 객관적 'absent' 소견의 지지 근거 누락, 양성 점수 상한에 감점이 묻히는 오류 수정. 부정 근거는 상한 적용 후 감점. UNKNOWN/NOT_ASKED/ABSENT/OBJECTIVELY_CONTRADICTED 추적. | 음성/정상 대조군, 포화 후 감점, 가족력의 확인 소견 오인 방지 테스트 |
| `nova_agent/resolution.py` | 검사 수행 여부만으로 결과 대기/미확인 상태를 해결로 처리하거나, 약한 안심 소견만으로 위험 대안을 종료하는 문제 수정. | pending/unavailable 결과, soft reassurance, 최소 검사 이후 남은 확인 검사 유지 테스트 |
| `nova_agent/missing_info.py`, `action_selector.py`, `config.py` | 상위 3개 후보의 구분, 위험 대안 해결, 좁은 근거 범위의 검사 가치를 별도 성분으로 계산. 광범위한 후보 포함 수가 곧 구분력이 되지 않도록 함. | 공유 검사와 특정 후보 구분 검사 대조 테스트 |
| `nova_agent/stop_policy.py` | 근거가 있는 위험 Top-5 후보의 미완료 검사 보호. 객관적 지지가 있고 순위 차이가 충분하며 남은 구분 가치가 낮으면 종료 가능. | 추가 확인이 필요한 위험 대안의 조기 종료 방지 및 충분한 검사 후 종료 테스트 |
| `nova_agent/syndrome_relationships.py` | 기존 source/systemic 역할과 관찰 근거의 동시 존재를 명시적으로 반환. 원인 관계나 우선순위를 자동 추정하지 않음. | 두 역할의 근거가 모두 있어야 반환; causality UNCONFIRMED; 순위 불변 |
| `scripts/trace_diagnostic_ranking.py`, Round J cases | 매 턴 raw 검색 순위, RRF, rerank, 활성 순위, 점수 구성, 음성 근거, 모순, 출처, active/resolved 상태, 행동 가치, 종료 시점 저장. | 54 + 54개 완전한 기록과 원본 hash 검증 |
| `scripts/audit_long_tail_depth.py` | 등록 개수와 임상 추론 깊이 분리 | Tier-2 1,246개 중 1,246개에서 점검한 6개 임상 필드가 모두 비어 있음 |
| `evaluation/current_blind.py`, integrity tests, submission mirrors | v18을 과거 검증으로 전환하고 현재 실행 코드와 보존된 과거 ZIP을 구분 | v18 원본/manifest/result hash 그대로; 현재 패키지와 원본 소스 일치 |

새 메커니즘 테스트의 초기 상태는 6개 실패 / 1개 통과였으며 실패 원인 확인 후 수정했습니다.
기존 무결성 테스트는 과거 런타임을 보존 ZIP과 비교하도록 옮겼고, 현재 런타임은 v11 검증에서
별도로 확인합니다. 과거 hash 검사를 삭제하거나 통과율을 위한 정답 조건을 추가하지 않았습니다.

점수는 보정된 확률이 아닙니다. generic/specific/objective/risk 성분은 실제 점수 연산의 signed raw sum,
`score_residual`은 포화와 안심 소견 감점입니다. medication 성분은 risk와 겹치며 추가로 더하지 않습니다.
추가 질문의 구분력은 메타데이터 기반 대리 지표입니다. 검사별 임상 likelihood ratio를 학습한 것은 아닙니다.

## Regression status

최종 릴리스 무결성 검사 3개를 포함한 전체 결과는 **849 passed, 0 failed, 1 skipped**입니다. 동결 이후 추론 코드는 변경하지 않았습니다.

- 코드·안전성·다국어·통합 회귀: 동결 직전 **846 passed, 0 failed, 1 skipped** (선택적 torch 미설치).
- Tuning 8/8, Held-out 15/15, Generalization-v2 18/18, Stress 8/8, Round D 6/6, Round E 6/6. 각 위험 사례 recall 유지.
- Round G: 11/12 및 위험 3/4 유지. 평균 turn 36.75 → 33.42. 기존 위험 오답 1개는 미해결.
- Round I: 17/19 → 18/19, 위험 8/8 유지. 미지원 long-tail 오답은 남음.
- OOD 32개: 비의료 탐지 6/8, 지원 사례 false OOD 0/12, 미지원 불확실 처리 20/20 유지.
  별도 Round I OOD 24개에서도 지원 불확실성 구분과 unsafe-confident 0/16 유지.
- 기존 검색·routing·specificity·adversarial·failure-analysis 명령 모두 exit 0. 결과 파일은 `artifacts/round_j/regression/`.
- 제출물 독립 프로세스 full-loop 20 turn 정상 종료. 기본 의존성·비밀정보/금지파일 검사 통과.
- 누출 검사: 15개 blind 모듈 717개 사례와 런타임 120개 파일의 명백한 유사/식별자 누출 없음.
  이 검사는 의미적 독립성이나 전문가 검토를 증명하지 않습니다.

## Failure attribution and long-tail depth

각 개발 오답에는 정확히 하나의 primary class를 부여합니다. 검색 → rerank → active set →
근거/행동/종료/최종 순위를 순차 점검하는 개발용 휴리스틱이며 전문의 판정은 아닙니다.

Before: `{"RETRIEVAL_MISS": 2, "FINAL_RANKING_ERROR": 2, "RERANK_MISS": 1}`.
After: `{"ACTIVE_SET_MISS": 1, "RETRIEVAL_MISS": 1, "RERANK_MISS": 1, "FINAL_RANKING_ERROR": 1}`.

남은 Round J 49–52는 clinical depth가 없는 Tier-2 범위 확인 사례입니다. 검색 2/4, rerank Top25 1/4는
수정 전후 동일합니다. 활성 후보 포함은 2/4 → 1/4로 감소했으며 Top5/Top1은 모두 0/4입니다.
이는 심층 프로필이 없는 항목의 검색/활성 유지가 아직 충분하지 않음을 보여줍니다.
이름을 환자 문구에서 발견해도 확인된 현재 진단으로 승격하지 않았습니다.

기존 소스에 임상 근거가 없는 1,246개 항목을 임의의 사실로 채우지 않았습니다. 새로운 cause,
manifestation, complication 관계도 원천 메타데이터에 없으면 추가하지 않았습니다.
임상 출처 확보·사용 조건 확인·전문가 정답 검토를 거친 선별 확장은 후속 작업입니다.

## Blind discipline / competition

v18은 **REFERENCE-ONLY**입니다. 사례/runner/manifest/result는 수정하거나 재실행하지 않았습니다.
v19는 만들지 않았습니다. 새 개발 사례는 v18을 import하지 않고, 기존 KB를 바탕으로 작성했습니다.

현재 API schema는 PLACEHOLDER이며 실제 GPT-OSS 및 공식 API 검증은 **NOT VERIFIED / EXTERNAL BLOCKED**입니다.
기존 [공식 인터페이스 확인 기록](../competition/OFFICIAL_INTERFACE_AUDIT.md)의 조건을 유지합니다.
이번 변경은 offline 결정 규칙/개발 평가에 한정됩니다. 실제 사용자 의료정보를 수집하거나
추가 로그 전송을 하지 않습니다. 런타임은 개발 사례나 trace script를 import하지 않고 제출물에 포함하지 않습니다.

## Reproduction / evidence

```bash
NOVA_COMPETITION_RETRIEVAL=1 python scripts/trace_diagnostic_ranking.py --output-dir /tmp/nova-round-j
python scripts/audit_long_tail_depth.py --output /tmp/nova-depth.json
python -m pytest tests -q
python scripts/build_nova_submission.py
python scripts/verify_submission_standalone_full_loop.py
```

수정 전 비교는 baseline SHA의 별도 checkout에서 동일한 Round J cases와 개발 trace script만 복사하여 실행합니다.
v18 runner를 호출하지 않습니다. 보고된 after 실행은 dirty 개발 checkout에서 수행되었고,
동결 전 전체 회귀와 `freeze_preconditions.json`의 파일 hash로 최종 코드를 대조했습니다.

- [Before metrics](../../artifacts/round_j/before/summary.json), [after metrics](../../artifacts/round_j/after/summary.json)
- [Before complete trace archive](../../artifacts/round_j/before/traces.tar.xz), [after complete trace archive](../../artifacts/round_j/after/traces.tar.xz)
- 각 archive member는 `RoundJ_NN.json`입니다. summary에 개별 원본 SHA-256과 archive SHA-256이 기록되어 있습니다.
- [Clinical-depth audit](../../artifacts/round_j/long_tail_depth.json), [pre-freeze checks](../../artifacts/round_j/freeze_preconditions.json)
- [Current verification](../../artifacts/verification/CURRENT_RELEASE.json)

## Remaining architectural weaknesses / next priorities

1. **P1 — 위험 대안과 근거 가중치**: Round G 위험 오답 1개가 남고, 문구 매칭·광범위한 confirmatory 필드·음성 해석은 여전히 휴리스틱입니다. 별도 고난도 개발 사례와 전문가 검토로 근거 추출/가중치 오류를 구분해야 합니다.
2. **P1 — 검증과 행동 가치**: 검사별 outcome likelihood와 임상적으로 독립적인 정답 데이터가 없습니다. 이번 action value와 stop delay는 대리 지표이며 real model/API 검증도 남아 있습니다.
3. **P3 — 실제 long-tail 임상 깊이**: Tier-2 1,246개에 확인 근거와 workup이 없습니다. 개수 확대보다 출처가 확인된 소수 프로필의 전문가 검토·독립 검증을 먼저 진행해야 합니다.
