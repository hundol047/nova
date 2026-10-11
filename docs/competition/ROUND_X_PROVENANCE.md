# Round X — 새 표현·규칙의 출처

모든 항목은 엔지니어링 에이전트가 작성했고 임상의 검토를 받지 않았다(`PENDING`). 위험도는 어떤 항목에서도 진단 점수를 올리지 않는다. 상태: VERIFIED = 인용 기준과 일치함을 작성자가 확인(임상 검토 아님), UNRESOLVED = 범위가 엔지니어링 판단, EXCLUDED = 검토 후 넣지 않음.

## 표현 (기존 KB 문구로만 연결)

| 대상 | 추가 | 출처 | 상태 |
|---|---|---|---|
| `polydipsia`, `polyuria`, `kussmaul breathing` | 갈증이 심하/너무, 목이 계속 말라, 물을 엄청 마시; 소변을 자주/계속 보, 화장실을 계속 가, 밤에도 소변; 숨이 깊고/깊게 | NICE NG17/NG18 (고혈당 증상: 갈증·다뇨, DKA의 깊고 빠른 호흡) | VERIFIED |
| `neck stiffness` | 목/고개를 못·안 숙이(굽히)다; won't let me bend her/his neck, can't bend his neck, won't put his chin on his chest | NICE NG240 (수막자극 징후) | VERIFIED |
| `photophobia` | 빛을 싫어하다·보면 울다·피하다; cries when the light is on, hates the light, turns away from the light | NICE NG240 | UNRESOLVED (영유아의 빛 회피를 photophobia로 보는 것은 보호자 관찰 해석) |
| 한국어 무능 표현 | "목을 못 숙여요"의 못은 부정이 아니라 소견 자체(`_KO_INABILITY_FINDINGS`); 뒤따르는 부정은 그대로 취소 | 엔지니어링 | — |

## 규칙

| 기전 | 스위치 | 내용 | 출처 | 상태 |
|---|---|---|---|---|
| 화자 자신의 건강 진술 | `NOVA_PROXY_REPORT` 범위 | "I'm just here for a check-up", "I have no symptoms myself", "저는 … 괜찮/아픈 곳/증상/검진" 같은 화자 본인 진술이 있으면 첫 관계어는 가족력(보호자 진술 아님). 보호자 행동 진술("I called an ambulance", "제가 해열제를 먹였어요")은 막지 않음 | 엔지니어링 언어 규칙 | — |
| SAH 명명 맥락 | `_REQUIRED_CONTEXT` | 지주막하출혈은 보고된 두통이 있을 때만 명명(목 강직·눈부심·구토는 수막염과 공유). 후보·점수·긴급 처분 불변 | NICE NG228 (2023) 1.1; Perry JJ et al., Ottawa SAH rule, JAMA 2013;310:1248 | VERIFIED |
| 수막염 대안의 긴급 앵커 | `NOVA_ALTERNATIVE_ANCHORS` | 수막염이 **대안**으로 긴급 계획을 만들려면 발열·목 강직·의식 변화·대천문 팽륜 중 하나가 필요(편두통의 눈부심만으로는 아님). 수막염 명명 자체, 활력 red flag는 불변 | Attia J et al., JAMA 1999;282:175 (세 소견 모두 없으면 성인 급성 수막염 사실상 배제); NICE NG143/NG240 (영아) | VERIFIED(성인) / UNRESOLVED(소아 일반화) |

## EXCLUDED

| 후보 | 이유 |
|---|---|
| SAH 명명에 "급성 발병 두통(thunderclap/worst/sudden)" 요구 | 개발 중 RoundM_096("머리가 깨질 듯이 아프고", 발병 시점 미기재) critical 회귀. 보고된 두통으로 완화 |
| 관찰을 설명하지 못하는 가설에 일반 감점(설명 안 된 발열 등) | 영향 범위가 너무 넓음. 다음 라운드 후보 |
