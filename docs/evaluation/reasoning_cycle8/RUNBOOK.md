# 고정 모델 비교 실행

저장소 루트에서 실행한다. Python 런타임 의존성은 `requirements-nova.txt`를 사용한다.
이미 고정된 `comparison_v1`을 평가할 때는 pyarrow가 필요하지 않다.

PowerShell 설정 예시:

```powershell
$env:NOVA_LLM_PROVIDER="competition"
$env:NOVA_COMPETITION_BASE_URL="<주최 측이 허용한 개발 API base URL>"
$env:NOVA_COMPETITION_MODEL="openai/gpt-oss-20b"
# NOVA_COMPETITION_API_KEY는 실행 환경의 보안 설정으로 주입한다.
# 키를 이 파일, 채팅, Git 또는 로그에 기록하지 않는다.
python scripts/run_model_comparison.py --dataset research/external_evidence/comparison_v1 --output comparison_check_v1 --validate-only
python scripts/run_model_comparison.py --dataset research/external_evidence/comparison_v1 --output comparison_smoke_v1 --limit 3
```

출력 폴더는 매번 새 이름을 사용한다. 기존 결과를 덮어쓰지 않는다.
기본 limit=3은 개발 연결 검사이며, 높은 정확도를 발표할 표본 크기가 아니다.
세 방식 모두 같은 고정 모델/client 설정을 사용한다. 추가 추론 호출 수·턴 수는 다를 수
있으므로 정확도 외에 calls, elapsed_seconds, turns 및 API 토큰 비용을 함께 검토한다.

- `direct`: 모든 제공 임상 정보로 모델이 직접 최종 답변을 생성한다.
- `nova_full`: 같은 정보가 NOVA 상태에 미리 들어간다. 없는 후속 관찰은 unknown이다.
- `nova_interactive`: 검토된 행동 키별 관찰만 순차 제공한다. 현재 자료는 매핑 미검토로 차단된다.

manifest는 모델 이름, 요구 revision, 설정, 런타임·평가 코드·입력·정답 해시를 기록한다.
`server_revision_verified=false`는 현재 코드가 서버의 실제 가중치를 검증하지 못한다는 뜻이다.
`summary.json`의 유효 실제 실행 수, 오류, fallback을 먼저 확인한다. 정확한 답변 문자열이
나와도 fallback에 의존한 실행을 실모델 성공으로 계산하지 않는다.

개발 실행이 안정화되면 `--limit 59`로 개발군을 평가한다. 실패 유형별로 코드 변경과 회귀
검증을 수행한 후 `--split validation --limit 50`을 실행한다. 코드를 동결한 최종 단계에만
`--split holdout --limit 100`을 사용한다. 결과를 열어보고 수정한 뒤 같은 holdout을 다시
사용하면 더 이상 미노출 최종 평가로 부르지 않는다.

정적 증례는 전체 정답 문자열 일치만 자동 채점한다. 동의어·원인/합병증 부분점수는
모델 답을 보기 전에 별도 임상 검토 기준을 확정하고 새 데이터 버전으로 기록해야 한다.
외부 위험도 정답과 calibration 자료가 없어 해당 지표는 측정 불가로 유지한다.

```bash
python -m pytest tests --ignore=tests/test_production_api.py -q
python scripts/build_nova_submission.py
python scripts/preflight_competition.py
```

첫 명령은 기존 API 테스트 정지 문제를 제외한 회귀이며 전체 서비스 검증이 아니다.
현재 비밀키 검사 회귀는 임시 파일을 런타임 디렉터리에 만들므로, 전체 테스트와 성능
평가는 동시에 실행하지 않는다. 테스트가 끝난 뒤 작업 트리와 런타임 해시를 확인하고
성능 평가를 시작한다. 평가 도중 코드 해시가 바뀌면 그 실행은 성능 근거에서 제외한다.
빌드 성공은 패키징 성공을 뜻한다. 공식 API 어댑터가 임시 상태이면 실모델 연결 여부와
관계없이 preflight가 NOT READY를 반환한다. 공식 문서에 맞춘 수정·계약 검증이 별도로 필요하다.
