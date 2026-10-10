# Post-Round-W — 새 임상 특징·어휘·규칙의 출처

모든 항목은 엔지니어링 에이전트가 작성했고 임상의 검토를 받지 않았다(`PENDING`). 위험도는 어떤 항목에서도 진단 점수를 올리지 않는다. 새 기전은 `NOVA_*` 스위치로 끌 수 있다. 상태 표기: **VERIFIED** = 인용 출처의 해당 기준과 일치함을 작성자가 확인(임상 검토 아님), **UNRESOLVED** = 출처는 있으나 표현 범위가 엔지니어링 판단, **EXCLUDED** = 검토 후 넣지 않음.

## KB 특징

| 위치 | 내용 | 출처 | 상태 | 범위 제한 |
|---|---|---|---|---|
| `infectious.json` sepsis `mottled skin on examination` | 얼룩덜룩·잿빛 피부 | NICE NG51 (2016, 2024 개정) high-risk criteria: mottled or ashen appearance | VERIFIED | 진찰 소견(질문하지 않음) |
| sepsis `grunting on examination` | 그렁거림(grunting) | NICE NG51 5세 미만 high-risk criteria; NICE NG143 Table 1 red feature | VERIFIED | 진찰 소견 |
| sepsis `temperature below 36 degrees` | 측정 체온 < 36 °C | NICE NG51 high-risk/moderate criteria(체온 < 36 °C) | VERIFIED | **지지 전용** 측정 임계값: 발열은 반박이 아님(저체온은 대안 양상) |
| `neuro.json` meningitis `bulging fontanelle on examination` | 대천문 팽륜 | NICE NG143 Table 1 red feature(bulging fontanelle); NICE NG240(2024) 영아 증상·징후 | VERIFIED | 진찰 소견 또는 보호자 진술, 부정·"soft/flat" 제외 |
| meningitis `high-pitched cry on examination` | 날카로운·고음 울음 | NICE NG143 Table 1(weak, high-pitched or continuous cry) | UNRESOLVED | NG143의 기준은 비특이적 중증 질환 신호다. 수막염 typical feature로 둔 것은 엔지니어링 판단이며, 단독으로는 명명 조건(비일반 특징)을 채우지 못한다 |

## 표현 문법 (기존 KB 문구로만 연결)

| 대상 | 추가 | 근거 |
|---|---|---|
| `bulging fontanelle on examination` | fontanelle/soft spot + bulging/swollen/raised/tense (양방향), 숫구멍·대천문 + 볼록·튀어나·팽팽, 大泉門 膨隆 | 위 NG143/NG240 |
| `high-pitched cry on examination` | high-pitched/shrill/piercing + cry/scream (양방향), 날카롭게·고음으로 울다, 甲高い泣き声 | NG143 |
| `mottled skin on examination` | blotchy skin, mottled limbs, 얼룩덜룩 | NG51 |
| `grunting on examination` | grunting with every breath, keeps grunting | NG51 |
| `diarrhea` | runny/watery poo(s) | NHS "Diarrhoea and vomiting" 일반인 표현 |
| `substernal pressure` | 직유("like an elephant sitting on my chest"), 명시적 무게("heavy weight pressing on my chest"); 직유·무게 없는 "the cat was sitting on my chest"는 제외 | 기존 Round W 이전 별칭 계열(압박·무게감)의 확장, ESC 2023 ACS guideline 흉통 묘사 |
| 한국어 대상포진·통풍·관절 | 띠/줄+물집, 한쪽·띠 모양 화끈거림, 엄지발가락, 관절+빨갛/뜨겁+붓 | NICE CKS "Shingles", "Gout", "Septic arthritis" |
| 처분 증상 | 쓰러지다, 기절 | NICE CG109 1.1.1 (Round W collapse 계열의 한국어) |
| 보호자 진술 | "아버지께서 …" 같은 존칭 조사 | Round W 보호자 진술 규칙의 한국어 확장(엔지니어링) |

## 규칙

| 기전 | 스위치 | 내용 | 출처 | 상태 |
|---|---|---|---|---|
| 해부학적 성별 적합성 | `NOVA_ANATOMIC_COMPAT` | 기록된 성별에 없는 장기의 질환(남성의 자궁외 임신·난소 염전, 여성의 고환 염전·전립선염 등, `anatomic_compat.py`의 명시 목록)은 후보에서 뺀다. 성별 미기록이면 아무것도 빼지 않는다. 유병률 prior가 아니며 어떤 후보도 나이·성별로 점수를 얻지 않는다 | 해부학적 전제 조건 | VERIFIED(정의상) |
| 유방 질환 | — | 양성 모두 발생하므로 목록에서 **EXCLUDED** | — | EXCLUDED |
| 진찰 효용: 카탈로그 채움 제외 | `NOVA_EXAM_UTILITY_V2` | KB에 아무것도 맞지 않아 전체 카탈로그로 채운 시간 민감 후보(관찰 근거·안전 플래그 없음)는 그 진찰을 "sweep 예외"로 만들지 못한다(붉은 눈에 복부 진찰 금지). 실제 출처가 있는 후보는 예외 유지 | 엔지니어링 규칙 | — |
| 결정 확실성 메타데이터 | `NOVA_DECISION_CERTAINTY` | 명명 진단 점수의 90% 이상인 top-5 경쟁 후보가 있으면 `certainty=PROVISIONAL`, `close_alternatives` 기록. 결정·점수·wire 형식은 바뀌지 않음 | 보정(calibration) 기록 | — |

## 검토 후 넣지 않은 것 (EXCLUDED)

| 후보 | 이유 |
|---|---|
| sepsis `body temperature below 36 degrees`를 측정 반박 특징으로 | 발열 패혈증(CloseV_03, PWCF_P01/P04)을 −1.2로 반박해 회귀. 지지 전용으로 바꿈 |
| "mottled skin", "grunting respirations"를 질문 가능한 증상으로 | 성인·소아 모두에게 질문으로 나가 대화가 길어지고 회귀. 진찰 소견 이름으로 바꿈 |
| 안전 가산(위험 질환 점수 부스트) | 작업서 원칙: 가장 작은 일반 수정, 위험도 가산 금지 |
