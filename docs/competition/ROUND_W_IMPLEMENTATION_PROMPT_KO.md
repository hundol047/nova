# N.O.V.A. Round W 수정 작업서 — Round V 남은 실패 해결

기준 runtime: `e16448e13431ab7af21d1e1c8abc5ecf2cf16e3c`. 브랜치: `claude/nova-round-u-followup-20261009`(이어서 커밋).
main, codex 검토 브랜치, 원래 Claude 브랜치는 수정하거나 reset하지 않는다.
직전 결과와 남은 실패는 [ROUND_V_REPAIR_REPORT_KO.md](ROUND_V_REPAIR_REPORT_KO.md) §5·§7을 본다(overall FAIL: 불필요 EXAM 296 > 238).

## 0. 금지와 원칙 (Round V와 동일)

- 외부 LLM/API 호출, API 키 요청, 모델 다운로드·교체·학습 금지. 공식 프로토콜 추측 금지.
- Blind v18/v19 실행·튜닝 금지, 새 blind 생성 금지. 기존 평가 문장·정답·분모·scorer·simulator 응답·라벨 수정 금지.
- 위험도 기반 진단 점수 보너스 금지. 사례 ID·정답 질환 하드코딩 금지. 단일 증상마다 병명을 강제하는 규칙 금지. 관찰하지 않은 검사 결과 생성 금지.
- 새 임상 사실에는 출처. 없으면 미해결로 둔다. 환자 텍스트를 프로세스 전체 캐시에 저장하지 않는다.
- 별칭은 KB 문구 하나만 돕는 다단어 표현. `check_eval_leakage.py` 표시 표현 금지.
- Round V closing 세트(`frozen_validation_round_v_closing.json`)의 실패를 소스 수정 근거로 쓰면 그 세트는 개발 세트로 승격되고, 새 closing 세트를 최종 runtime 전에 따로 동결한다.

## 1. 해결 대상

### W-A. 실제 GPT-OSS·공식 인터페이스 — BLOCKED (변동 없음)

### W-B. 안전 (P0)

1. **영아·소아 패혈증 vs heat stroke (CloseV_03, critical miss).** 영아의 고열·빈맥·빈호흡·얼룩덜룩한 피부·처짐이 heat stroke로 명명된다. 열 노출 맥락이 없는 고열은 heat stroke의 명명 근거가 아니어야 한다(required context). 소아 패혈증 표현(floppy, mottled, not feeding, fewer wet nappies)이 기존 KB 문구에 닿는지 확인한다. 출처: NICE NG143 traffic-light red 특징, NICE NG51.
2. **HR 30대 실신 긴급 처분 FN (FollowU_21, CloseUF_03).** `disposition.symptomatic_rate_concern`이 해당 증상 표현을 인식하지 못하는 원인을 단계별로 찾고, 증상 표현 범위를 넓힌다. 리듬 subtype이나 부정맥 명명은 하지 않는다(Round T 계약 유지).
- 완료: 해당 사례 긴급 처분 PASS, 새 critical miss 0, 처분 FP 증가 0.

### W-C. 효율 (P0, Round V 미달 기준)

불필요 EXAM ≤ 238(지표 정의는 그대로). Round V 분석: 총 EXAM 수는 같고, 최종 상위 5개에 Tier-2 후보가 더 오래 남아 같은 진찰이 "불필요"로 집계된다. 다음을 측정·수정한다.
- 근거가 약하고 반박된 Tier-2 후보가 상위 5개에 남는 원인(bare "No" 반감 이후).
- 근거 없는 Tier-2 후보를 위한 진찰 선택.
- 평균 interaction ≤ 20 유지, 예선 정확도 회귀 0.

### W-D. 진단 표현 (P1)

- AOM이 viral URI로(CloseV_02), 흉벽 띠 모양 통증+수포가 GERD로(CloseV_12) 명명되는 원인을 표현·순위·진찰 연결로 분류해 일반 기전으로만 고친다.
- 형제 원인(RoundM_105 ovarian torsion/ruptured cyst, RoundM_108 PUD/duodenal ulcer): 같은 관찰로 구분 불가한 경우의 정책은 설계·측정만 하고, scorer를 느슨하게 만들지 않는다.
- ValP_08 명칭 불일치는 보고만 한다.

## 2. 일반화 절차

1. 소스 수정 **전에** Round W 합성 세트를 동결한다(라벨·critical·행동 계약·SHA256 manifest). 기준선 `e16448e`에서 먼저 실행한다.
2. 최종 runtime 커밋 직전에 Round W closing 세트를 따로 동결하고 기준선·최종에만 실행한다.
3. 기본 "No" 의존 정답 수(기본 대 `--unscripted-unknown`)가 늘지 않게 한다.

## 3. 검증

Round V와 같은 31단계 `scripts/run_round_u_followup_suite.py` + extra(follow-up 2종, Round V 2종, Round W 2종). `NOVA_LLM_PROVIDER=mock`, `NOVA_COMPETITION_RETRIEVAL=1`, `PYTHONDONTWRITEBYTECODE=1`; pytest는 기본 환경.

## 4. 완료 기준 (미달이면 FAIL)

- 테스트 failed 0. 모든 비교 세트 새 scored wrong 0, 새 critical miss 0.
- 예선 ≥219/222, critical 85/85, Round P ≥31/32, Round M ≥121/123.
- 처분 계약 FP ≤ 0(현재), FN < 2.
- 불필요 EXAM ≤ 238, 평균 interaction ≤ 20.
- Round W closing 세트 critical miss 0.
- 공식 API·실모델 NOT VERIFIED 유지. 95점·임상 안전·독립 검증 선언 금지.

## 5. 보고 형식

Round V 보고서와 같은 블록 + DISPOSITION FP/FN 표 + 기본 "No" 의존 수 + 자체 100점 추정표. 미달 항목은 다음 작업서로 넘긴다.
