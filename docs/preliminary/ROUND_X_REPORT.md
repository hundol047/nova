# N.O.V.A. ROUND X 보고서

모든 수치는 오프라인 mock LLM과 합성 개발 사례로 측정한 엔지니어링 근거다. 공식 점수, 실제 모델 성능, 독립 임상 검증이 아니다. 이전 보고서는 수정하지 않았다.

```
BASELINE RUNTIME   ed61341 (post-Round-W 검증 런타임)
REASONING FREEZE   263f243
VERIFIED RUNTIME   aeda1a0 (closing set 동결만 추가, 런타임 동일)
RELEASE RECORD     artifacts/verification/local-release-aeda1a0-v31.json
```

근거: `artifacts/round_x/final_metrics.json`, `artifacts/round_x/final/round_m_*.json`, 출처 `docs/competition/ROUND_X_PROVENANCE.md`.

## 1. 출발점

Post-W closing(1회 실행)의 실패 3건을 클래스로 보고, 같은 클래스의 새 표현과 음성 대조로 개발 세트를 먼저 동결했다(`evaluation/round_x_dev.json`, 14 사례).

| 클래스 | Post-W closing 사례 | 개발 세트 기준선 |
|---|---|---|
| 한국어 고혈당 표현(갈증·다뇨·깊은 호흡) | CloseX_05 DKA → 미분화 | DKA 1/3 |
| 소아 수막자극을 보호자가 묘사, 두통 없음 → SAH 승리 | CloseX_03 수막염 → SAH | 소아 수막염 1/3 |
| 화자 본인 진술이 있는데 첫 관계어를 환자로 읽음 | (NewT_19, 기준선부터) | 가족력 계약 실패 |
| 편두통에 수막염 대안이 긴급 계획 | CloseX_10 | 편두통 긴급 |

기준선 6/10, critical 3/7, 행동 41/44 → 최종 10/10, 7/7, 44/44.

## 2. 수정 (모두 일반 기전)

| 기전 | 스위치 | 효과 |
|---|---|---|
| 한국어 갈증·다뇨·깊은 호흡 → 기존 DKA 소견; 배뇨통·절박과 함께인 잦은 배뇨는 다뇨 아님 | — | CloseX_05, RX_D01/D02; 방광염(CloseV_06) 보호 |
| 보호자 묘사 수막자극(목을 못 숙여요, won't let me bend her neck, 빛을 싫어해요, cries when the light is on); 한국어 "못"이 소견 자체인 경우 | — | RX_M01/M02 |
| 화자 본인 건강 진술이 있으면 첫 관계어는 가족력 | `NOVA_PROXY_REPORT` 범위 | RX_F01, NewT_19 계약 통과 |
| SAH 명명에는 보고된 두통 필요 | `_REQUIRED_CONTEXT` | CloseX_03, RX_M01/M02 |
| 수막염·SAH가 **대안**으로 긴급 계획을 만들려면 앵커(수막염: 발열·목 강직·의식 변화·대천문; SAH: 급성 두통·목 강직·의식 변화) | `NOVA_ALTERNATIVE_ANCHORS` | CloseX_10, RX_B01 편두통 비긴급 |

개발 중 발견해 고친 회귀: RoundM_096(SAH 명명 조건을 "급성 발병 두통"으로 했을 때 critical 회귀 → "보고된 두통"으로 완화), CloseV_06(방광염 빈뇨가 다뇨로 → 배뇨통 동반 제외), CloseX_10(SAH 대안 → SAH 앵커).

## 3. 결과 (ed61341 → aeda1a0)

| 묶음 | 결과 |
|---|---|
| 예선 ALL 230 | Top1 98.6% → 98.6%, critical 85/85, 평균 19.64턴, EXAM 1207, 불필요 EXAM 270, SOAP 100%/0, 규칙 위반 0 (사례 단위 동일) |
| Round M | 98.4%, critical 43/43 |
| 한국어 | 100% / 100% |
| EXAM 거절 / 미기재 "모름" | 97.7% / 98.2% |
| 동일 조건 284 | Top1 94.8%, critical 63/64 (변화 없음) |
| 비교 329 사례 | 개선만: CloseX_03·CloseX_05 정답, CloseX_10·NewT_19 계약 통과. 새 오답·새 처분 오류 0 |
| Round X 개발 세트 | 10/10, critical 7/7, 행동 44/44 |
| Post-W closing(이제 개발 사용) | 10/10, 6/6, 36/36 |

## 4. Round X closing set (동결 후 작성·커밋, 1회 실행, 튜닝 없음)

12 사례 / 11 채점: **Top1 10/11, Top3 11/11, critical 4/4**(평가기 정의; manifest의 예상 6), SOAP 100%/0, 규칙 위반 0, 평균 17턴, 행동 35/36.

| 사례 | 결과 |
|---|---|
| 대동맥 박리, 긴장성 기흉(한국어), 보호자 묘사 패혈증, 저혈당, 위장관 출혈(한국어), 요로결석, 방광염(한국어), BPPV, GERD, 영아 상기도 감염(한국어), 가족력만 있는 음성 대조 | 정답 |
| **CloseY_06 천식 악화 → 폐색전증** | 오답(정답 3위). 쌕쌕거림·천식 병력은 인식, 저산소·빈맥이 PE를 앞세움 |
| **CloseY_04 저혈당** | 정답 명명, 그러나 **긴급 계획 없음**(과소 분류) |

## 5. 검증

| 항목 | 결과 |
|---|---|
| pytest | py3.13 2596 / py3.11 2543 / py3.12 2543 passed, failed 0(release-binding은 v31 기록 후 재실행 32 passed), skipped 2 |
| 동일 조건 실행 | 모든 단계 runtime 해시 불변, pytest 외 exit 0; leakage NO OBVIOUS LEAKAGE; adversarial ALL CHECKS PASSED |
| 패키지 | 860,320 bytes, sha256 `745e63cf837e86f011ffac0bfc57c315911d54b196b2b6d9c8fe8cd9a9d1d3bf`, validate all_pass, fresh 디렉터리 run.py fail-closed(exit 1), local_runner 행동 출력. ZIP은 로컬, 멤버 해시는 v31 기록에 고정 |
| 공식 상태 | `openai/gpt-oss-20b@4d7ae49…` NOT VERIFIED, transport BLOCKED, fail-closed. PRE-GUIDE CANDIDATE / NOT OFFICIALLY READY |

## 6. 다음 과제

1. 저혈당의 긴급 처분(CloseY_04): 인슐린 사용자 의식 변화는 응급(NICE NG17). 처분 규칙 점검.
2. 천식 악화 vs 폐색전증(CloseY_06): 쌕쌕거림·천식 병력이 있을 때 PE를 앞세우는 저산소·빈맥 가중.
3. 양성 사례 긴급 계획 비율(post-W 34.5%), 불필요 EXAM 270(목표 238).
4. ConfirmU_09(가족 부정맥 근거 누수, 기준선부터), 같은 질환 표현 불일치 7종.
5. 모든 사례 합성, 저자 동일; 실제 GPT-OSS·공식 인터페이스·임상 검토 미수행.
