# Round V — 새 임상 관계·어휘·처분 메타데이터의 출처

모든 항목은 엔지니어링 에이전트가 작성했고 임상의 검토를 받지 않았다(`PENDING`). 위험도는 어떤 항목에서도 진단 점수를 올리지 않는다. 각 기전은 `NOVA_*` 스위치로 끌 수 있다.

## KB 특징·메타데이터

| 위치 | 추가 내용 | 출처 | 범위 제한 |
|---|---|---|---|
| `knowledge/tier2_enrichment.json` `chronic_heart_failure`, `heart_failure_acute` `confirmatory_findings` | `third heart sound`, `raised jugular venous pressure` | McDonagh TA et al., 2021 ESC Guidelines for heart failure, Eur Heart J 2021;42:3599, Table 6 ("more specific signs") | 진찰에서 실제로 관찰될 때만 지지. 필드별 `provenance` |
| `knowledge/tier2_enrichment.json` `gout`, `peptic_ulcer_disease`, `gi_duodenal_ulcer` `disposition: non_emergency` | 이 라벨 **자체만으로** 응급 처분을 만들지 않음 | NICE NG219 Gout (2022) 1.1–1.4; NICE CG184 Dyspepsia and GORD (2014, 2019 update) 1.1–1.2, 1.6 | 처분 메타데이터만. 진단 점수 영향 없음. 활력징후 red flag, 증상성 맥박 이상, 지지된 위험 대안(패혈성 관절염·위장관 출혈 등)은 그대로 응급 처분 |

## 처분·활력징후 규칙

| 위치 | 내용 | 출처 | 범위 제한 |
|---|---|---|---|
| `vitals_parser.red_flag_rules_for_age` (`NOVA_PEDIATRIC_VITALS`) | 5세 미만: 빈맥 > 160(< 1세), > 150(1세), > 140(2–4세); 빈호흡 > 50(< 1세), > 40(≥ 1세) | NICE NG143 Fever in under 5s (2019), Table 1 traffic-light amber 기준 | 나이는 정수 연도라 0세는 6–12개월 값을 씀. SBP·SpO2·체온·서맥(< 50) 규칙은 그대로. 나이 미상이면 성인 기준 |
| `disposition._context_only` (`NOVA_DISPOSITION_V2`) | 위험 대안의 지지 근거가 위험인자·선행 맥락("recent …")·추정("suspected …")뿐이면 처분 근거로 쓰지 않음 | 엔지니어링 규칙(관찰 소견과 맥락의 구분). 새 임상 주장 아님 | 후보는 감별에 남고 제외되지 않음 |
| `disposition.disposition_for` | 선택 진단이 자기 자신의 "위험 대안"으로 이중 집계되던 문제 수정(id 비교) | 버그 수정 | — |

## 어휘(의미 동일성, 새 임상 주장 아님)

| 대상 KB 문구 | 추가 표현 | 근거 |
|---|---|---|
| `unable to lie flat` | four/several/two/extra pillows, sit up to breathe, sit up to catch my breath, sleep sitting up, sleep in a chair | NICE CKS "Heart failure – chronic": orthopnoea |
| `dysuria`, `urinary frequency`, `burning upper abdominal pain`, `pain relieved by eating`, `recent immobility or long travel`, `calf pain or tenderness`, `warmth and redness of leg`, `worsening shortness of breath`, `recent cold`, 대상포진 confirmatory 문구 | 환자 표현 변형 | 기존 KB 문구의 동의 표현(`lay_language.py` Round V 블록). Round V 동결 세트 개발 중 발견되었음을 공개 |
| `vaginal bleeding`의 별칭 `spotting` | 형태소 예외: `spotting`은 명사 `spot`("아픈 부위")과 같은 어간이 아님 | 버그 수정(`matching._IRREGULAR_STEM_OVERRIDES`) |
| 일본어·한국어 `substernal pressure`, `radiates to arm or jaw` | 胸が締め付け/圧迫/重苦しい, 腕・肩・顎に広がる; 가슴이 조이/짓누르/압박, 팔·어깨·턱으로 퍼지/뻗치 | 기존 영어 관계 문법(`feature_relations.py`)의 번역 |
| 한국어 `unable to lie flat`, `leg swelling`, `shortness of breath on exertion` | 누우면 숨이 막혀/앉아서 자요, 다리·발목이 부어, 계단을 오르면 숨이 차 | 기존 KB 문구의 한국어 표현(`multilingual_concepts.py`) |

## 점수·질문 기전(가중치)

| 기전 | 스위치 | 내용 |
|---|---|---|
| 선택적 특징 부정 | `NOVA_DENIAL_V2` | 관찰되지 않은 선택적 typical feature의 부정은 −0.6(기존 −1.2)이고, 포화 **전** 합계에서 뺀다. 이런 부정의 합은 −1.8로 제한. 이미 관찰된 특징과 충돌하는 부정, 객관 소견 반박은 기존 그대로 |
| 핵심 증상 부정 | `NOVA_DENIAL_V2` | "숨이 차지 않다"는 "sudden onset dyspnea"도 부정(앞쪽 시간·강도 수식어만 제거, 3단어 이하 부정 구간만) |
| 수식어 질문의 bare "No" | `NOVA_DENIAL_V2` | 이미 보고한 증상의 수식어 형태("worsening shortness of breath")에 대한 bare "No"는 부정이 아니라 conflict로 기록 |
| 진찰 연결 | `NOVA_EXAM_LINKS_V2` | Tier-2 신체 징후(S3, 수포, 경부강직, 종아리 부종 등)를 기존 카탈로그 진찰에 연결. 환자 보고 증상은 연결하지 않음 |
| 맥락 | `NOVA_CONTEXT_V2` | "recent …" 선행 맥락과 "… after trauma/exercise" 상황 맥락은 진단 명명 근거가 아님(순위에는 남음) |
