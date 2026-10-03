> Historical v10 handoff. The current structural-repair release is described in [Round J](../round_j/FINAL_REPORT.md) and the [release pointer](../../artifacts/verification/CURRENT_RELEASE.json). v18 is now REFERENCE-ONLY.

# 주최 측 연동 정보 인계

현재 로컬 릴리스는 `d6e2b84aa2bb90c198fae39dade3870d6575c6f4` 런타임을 검증합니다.
공식 endpoint/token, 관찰·행동 JSON, `run.py` 호출 방식과 기권 허용 여부는 아직 확인되지
않았습니다. 공개 문서의 모델·행동 이름만으로 실행 계약을 추정하지 않습니다.

1. 주최 측 문서/예제에서 endpoint, 인증 방식, 입출력 스키마, 실행 명령, 네트워크 허용
   범위, 모델명과 revision 반환 여부를 확인하고 출처를 `OFFICIAL_INTERFACE_AUDIT.md`에 기록합니다.
2. 그 계약이 현재 가정과 다르면 `competition/`과 `submission/run.py`의 경계만 새 작업
   사이클에서 수정하고 공식 예제 기반 계약 테스트를 추가합니다. 실제 근거 없이
   `OFFICIAL_API_STATUS`를 VERIFIED로 바꾸지 않습니다.
3. 주최 측이 허용한 설정만 환경 변수로 주입합니다. 키는 안전한 로컬 비밀 저장소/숨김
   입력으로 설정하고 파일·스크린샷·로그·Git에 넣지 않습니다.

   ```sh
   export NOVA_LLM_PROVIDER=competition
   export NOVA_COMPETITION_BASE_URL="<official base URL>"
   export NOVA_COMPETITION_API_KEY="<official token if required>"
   export NOVA_COMPETITION_MODEL=openai/gpt-oss-20b
   python scripts/preflight_competition.py
   python scripts/smoke_real_llm.py
   ```

   위 URL/토큰은 실행 가능한 값이 아닌 자리표시자입니다. 현 API 인증이 Bearer와 다르면
   해당 전송 경계를 먼저 맞춥니다. 임의 외부 LLM이나 공개 서버로 대체하지 않습니다.
4. 최소 구조화 HTTP 응답부터 확인합니다. 인증, 모델명, 합법적 행동, 실제 파싱, 지연과
   제공되는 토큰 사용량을 검증합니다. 기대 revision은
   `4d7ae4984b7db7de8f8457170b3f1a419ee76d52`입니다. API가 revision을 노출하지 않으면
   `NOT_VERIFIABLE_FROM_RUNTIME`으로 남기고 문서에 없는 요청 필드는 보내지 않습니다.
5. `smoke_real_llm.py`는 최소 호출 성공 뒤 짧은 합성 개발 사례 하나를 진행합니다.
   사례별 실제 성공 횟수가 새로 시작되고, 실패하면 최종 competition 진단을 차단하는지
   확인합니다. 이후 동일 개발군에서 실제 모델과 mock을 별도 평가합니다.
6. 전체 회귀·안전·공식 계약 테스트를 통과한 뒤 `python scripts/build_nova_submission.py`를
   실행하고 원본/제출 복사본의 해시, 크기, 비밀정보, 격리 실행을 다시 확인합니다.
7. 실제 모델과 공식 경계가 모두 증거로 검증되기 전에는 공식 제출 READY로 표시하지 않습니다.

로컬 stub은 전송/형식 시험입니다. 실제 모델 검증으로 승격할 수 없습니다. endpoint가
없으면 `NOT_CONFIGURED`, 시도 0회가 정상이며, 값을 READY로 만들려고 코드를 바꾸지 않습니다.

v18은 이미 **한 번 실행된 합성 holdout**입니다. 재실행하거나 그 정답으로 튜닝하지 않습니다.
런타임을 바꾸는 차기 작업에서는 v18을 REFERENCE-ONLY로 바꾸고, 새로운 검증 계획을 별도로
수립해야 합니다. 이번 완료 작업에서는 v19를 만들지 않습니다.
