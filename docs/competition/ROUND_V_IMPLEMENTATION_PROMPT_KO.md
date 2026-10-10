# N.O.V.A. Round V 수정 작업서 — Round U 후속 평가의 부족 영역 해결

기준 runtime: `e207801ce16faf38591fc0bed2dd2d238c1c1d7a`. 브랜치: `claude/nova-round-u-followup-20261009`(이 브랜치에 이어서 커밋한다).
main, codex 검토 브랜치(`codex/nova-round-u-source-review-20261009`), 원래 Claude 브랜치(`claude/determined-brahmagupta-wrfveb`)는 수정하거나 reset하지 않는다.
직전 상태와 점수 근거는 [ROUND_U_FOLLOWUP_REPAIR_REPORT_KO.md](ROUND_U_FOLLOWUP_REPAIR_REPORT_KO.md)를 본다. 자체 추정 약 64/100이다(공식 점수 아님).

## 0. 금지와 원칙 (Round U와 동일, 계속 적용)

- 외부 LLM/API 호출, API 키 요청, 모델 다운로드·교체·학습 금지. 공식 프로토콜 추측 금지.
- Blind v18/v19 실행·튜닝 금지, 새 blind 생성 금지. 기존 평가 문장·정답·분모·scorer·simulator 응답·라벨 수정 금지.
- 위험도 기반 진단 점수 보너스 금지(위험도는 안전 추적·행동 선택·처분에만). 사례 ID·정답 질환 하드코딩 금지. 단일 증상마다 특정 병명을 강제하는 규칙 금지. 관찰하지 않은 검사 결과 생성 금지.
- 새 임상 사실에는 출처를 기록한다. 출처가 없으면 빈칸/미해결로 둔다.
- 환자 텍스트를 프로세스 전체 캐시에 저장하지 않는다(case isolation).
- 별칭은 KB 문구 하나만 돕는 다단어 표현으로 둔다. `check_eval_leakage.py`가 표시하는 표현은 넣지 않는다.

## 1. 해결 대상과 우선순위

### V-A. 실제 GPT-OSS·공식 인터페이스 — BLOCKED (이 환경에서 해결 불가)

모델 다운로드·키·주최측 자료가 없다. 할 수 있는 일은 상태를 정직하게 유지하는 것뿐이다. `run.py` fail-closed, `NOT VERIFIED`, permission BLOCKED를 유지한다. 주최측 가이드가 제공되면 같은 회귀 세트를 실제 모델로 돌리는 별도 라운드로 진행한다. 점수 추정에서 이 항목은 올리지 않는다.

### V-B. 긴급 처분 과잉·과소 (P0)

- 위치: `nova_agent/disposition.py:disposition_for`, `_alternative_corroborated`; `final_decision.support_problems`.
- 재현:
  - 과잉: ValP_10, CloseUF_04(외상 후 흉벽 통증). 원인은 core tension pneumothorax 대안이 "chest pain after trauma" 하나로 supported 판정되는 것. FollowU_19(단순 방광염), FollowU_20(통풍).
  - 과소: FollowU_21, CloseUF_03(HR34 실신, 미분화).
- 명세:
  - "일반 증상 + 외상·운동 등 상황 맥락"으로만 이루어진 근거는 비특이 근거로 분류한다.
  - Tier-2 `dangerous` 메타데이터와 실제 임상 긴급도가 어긋나는 경우(통풍 등)를 측정한다. 처분 근거를 위험 플래그가 아니라 관찰 소견·선택 진단의 지지 근거로 설명할 수 있게 한다.
  - 처분 기준을 바꾸면 false negative가 생기는지 반드시 별도로 측정한다. 위험 활력징후, 증상성 맥박 이상, 선택된 위험 진단의 긴급 처분은 유지한다.
- 완료: 동결 세트의 처분 계약 FP·FN 각각 감소. 새 critical miss 0. 활력징후·맥박 기반 긴급 처분 회귀 0.

### V-C. 진단 혼동 (P0)

1. 심부전 대 폐렴(ValP_08, FollowU_23, CloseUF_09): crackles·호흡곤란은 공유 소견이다. S3, 함요부종, 기좌호흡, 야간 호흡곤란, 심근경색 병력이 Tier-2 HF 프로필로 전달되는지 확인한다. 부족한 특징은 출처가 있을 때만 보강한다. `heart_failure` 라벨과 카탈로그명의 관계는 명칭 문제로 따로 보고한다(scorer 변경 금지).
2. 선택적 특징 부정 감점 비대칭: 기본 "No"로 부정된 선택적 typical feature 하나가 −1.2로, 양성 하나(+1.0)보다 크다. 시뮬레이터 기본값 문제와 runtime 가중치 문제를 분리한다. `NOVA_*` 스위치 ablation으로 기본 응답 조건과 `--unscripted-unknown` 조건을 모두 측정한다.
3. 명칭 계층(PUD/duodenal ulcer, acute abdomen/perforated viscus): 자식 원인의 support가 부모 증후군의 support와 같은 관찰만으로 이루어진 경우의 정책을 설계·측정한다. scorer를 느슨하게 만들지 않는다.
4. Round M 117 → ≥118: RoundM_105/108/109/112/114/117을 단계별로 추적한다. 표현 누락, 기본 "No" 반박, 순위 문제로 분류하고 일반 기전으로만 고친다.

### V-D. 일반화와 견고성 (P1)

- 작업 시작 **전에** 새 합성 세트(Round V)를 동결한다(JSON fixture, 정답·critical·채점·행동 계약, SHA256 manifest). 기준선 `e207801`에서 먼저 실행한다. 이후 결과로 소스를 고치면 개발 세트로 승격한다.
- 최종 확인용 closing 세트를 최종 runtime 직전에 따로 동결하고, 기준선과 최종에만 실행한다.
- 시뮬레이터 기본 "No"에 기대는 정답 수를 보고한다(기본 조건 대 `--unscripted-unknown` 조건 차이). 새 수정이 그 의존을 늘리지 않게 한다.
- 개발 사례에서 얻은 별칭은 출처·노출 범위를 공개한다.

### V-E. 지식 깊이 (P1)

`artifacts/round_u_followup/tier2_priority.json`의 50개 중 공신력 있는 출처를 확인할 수 있는 항목만 필드별 provenance와 함께 보강한다. 위험도 편중(47/50)은 선정 기준 개선으로 보고한다. 질환 수 증가로 성과를 주장하지 않는다.

### V-F. 효율·SOAP (P2)

일반 범주 질문에 대한 의미 없는 "No"가 SOAP에 "onset: denied"처럼 기록되는 문제를 줄인다. 이를 위해 응답이 질문 범주와 맞지 않는 경우를 정보 미획득으로 표시한다. 평균 interaction ≤ 20, 불필요 EXAM ≤ 238을 유지한다.

## 2. 검증 (Round U와 같은 조건·명령)

`NOVA_LLM_PROVIDER=mock`, `NOVA_COMPETITION_RETRIEVAL=1`, `PYTHONDONTWRITEBYTECODE=1`. pytest는 기본 환경에서 실행한다.
`scripts/run_round_u_followup_suite.py`로 기준선 `e207801`과 최종 runtime의 다음 항목을 실행한다:
- 예선 3변형, P, Q, R, acceptance, S, T 4종, U 4종, follow-up 2종, Round V 세트
- TEST 허용 8종, Round M
- 검색 단계, adversarial, leakage, failure analysis, assertion 10문장, 전체 테스트

실행마다 명령, SHA, runtime 해시, 환경, 시각, exit code, 결과 해시를 기록한다. 패키지 mirror byte equality, audit, ZIP 검증, 새 디렉터리 mock 실행을 최종 SHA에 연결한다.

## 3. 완료 기준 (미달이면 FAIL로 보고)

- 테스트 failed 0. 모든 비교 세트에서 새 scored wrong 0, 새 critical miss 0.
- 예선 ≥218/222, critical 85/85, Round P ≥31/32, Round M ≥118/123, long-tail Top1 ≥20/26.
- 처분 계약: Round V·follow-up·closing 세트에서 FP·FN 각각 기준선 대비 감소 또는 동일. 활력징후 기반 긴급 처분 회귀 0.
- 심부전 대 폐렴: 동결 세트의 HF 계열 사례에서 폐렴 과잉 명명 감소.
- 평균 interaction ≤ 20, 불필요 EXAM ≤ 238. 기본 "No" 의존 정답 수 증가 없음.
- 공식 API·실모델은 NOT VERIFIED로 유지. 95/100점, 임상 안전, 독립 검증은 선언하지 않는다.

## 4. 보고 형식

Round U 후속 보고서와 같은 블록(BASELINE/FINAL SHA, TESTS, PRELIMINARY, ROUND P, ROUND M, RETRIEVAL, ASSERTION, REMAINING FAILURES, SUBMISSION, VERDICT)을 쓴다. 여기에 다음을 추가한다:
- DISPOSITION FP/FN 표
- 기본 "No" 의존 정답 수
- 자체 100점 추정표(공식 점수 아님, 항목별 근거)

미달 항목은 다음 작업서로 남긴다.
