# Round R source-only review branch — not a complete release

이 브랜치는 수정한 runtime·회귀 테스트·동결 fixture와 제출 소스 mirror만 보존하는 중간 검토본입니다. 현재 verification pointer/v22 기록은 이전 runtime의 기록이며 이 브랜치의 최종 검증을 뜻하지 않습니다. 전체 v23 증거/ZIP까지 연결하기 전에는 release로 취급하지 마십시오.

- 로컬 검증 runtime: `18b994984d0e22c1ee15a3e9ffcc125d5056b46b`.
- 동일 전체 tree의 원격 runtime commit: `cf31e011244a9f5340ea36c05a723dc1d11177aa`.
- 로컬 전체 결과 commit: `410582359268f034f382e6717bcfa53eedcb3715` (검증 자료 포함, 원격 미게시).
- 로컬 전체 테스트: 2119 passed / 0 failed / 1 skipped. 예선 개발 202→203/222; 새 합성 10→11/12.
- 문서 assertion·혼합 답변·관찰/거절 구분 등을 수정했습니다. NewR18 서맥 실신의 잘못된 자세 근거/외래 계획, unknown 답변 변형, 기존 위험 누락은 남아 있어 전체 안전성 FAIL입니다.
- GitHub 공개 저장소에 압축된 합성 진료 추적 자료를 업로드하는 동작이 자동 승인 검토에서 차단되었습니다. 사용자의 해당 자료 공개 승인 대기 중입니다. 우회하여 게시하지 않았습니다.
- 원래 대상 `claude/determined-brahmagupta-wrfveb`와 main은 이 게시로 갱신하지 않았습니다.

승인 후 전체 증거를 올리면서 원격 runtime SHA에 verification pointer를 연결하고 동일 바이트/패키지 gate를 다시 확인해야 합니다. 실행한 로컬 SHA와 원격 동일 tree SHA는 별도로 기록하여 실행 이력을 바꾸지 않습니다. 실제 LLM 및 공식 API는 미검증입니다.
