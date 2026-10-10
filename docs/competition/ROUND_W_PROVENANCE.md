# Round W — 새 임상 관계·어휘·규칙의 출처

모든 항목은 엔지니어링 에이전트가 작성했고 임상의 검토를 받지 않았다(`PENDING`). 위험도는 어떤 항목에서도 진단 점수를 올리지 않는다. 각 기전은 `NOVA_*` 스위치로 끌 수 있다.

## 활력징후

| 위치 | 내용 | 출처 | 범위 제한 |
|---|---|---|---|
| `models.VitalSigns.respiratory_rate` 상한 60 → 120 | 영아의 RR 64는 실제(비정상) 측정값 | NICE NG143 Table 1(5세 미만 RR > 60 red feature) | 생리적 범위 검증 자체는 유지 |
| `vitals_parser.parse_vital_signs` | 범위를 벗어난 값 **하나만** 버림(이전에는 같은 줄의 모든 활력징후를 버려, 영아의 HR 192·체온 39.8이 사라졌다) | 버그 수정 | 원문은 physical_examinations에 유지 |
| `vitals_parser.fast_pulse_threshold` (`NOVA_PEDIATRIC_VITALS`) | 리듬 원인 검토 빠른 맥박 기준: 성인 ≥150, 영아(<1세) ≥220, 소아(1–11세) ≥180 | Topjian AA et al., 2020 AHA PALS Part 4, Circulation 2020;142:S469 (SVT vs sinus tachycardia) | 서맥 기준(<50)은 그대로 |
| `vitals_parser` "body temperature above 40 degrees" | 측정 체온 > 40 °C를 기존 KB 문구로 기록 | Epstein Y, Yanovich R. Heatstroke. N Engl J Med 2019;380:2449 | 측정값이며 진단이 아님 |
| `differential._measured_threshold` (`NOVA_MEASURED_THRESHOLDS`) | 숫자 활력 KB 특징 3개(BP > 180/120, 체온 > 40, 체온 < 35)는 **측정값**으로 판정: 충족 → 지지, 측정했으나 미충족 → 객관적 반박(−1.2) | Whelton PK et al., 2017 ACC/AHA guideline 11.2(고혈압 응급); Epstein 2019 | 측정하지 않았으면 지지·반박 모두 없음 |

## 명명 맥락

| 위치 | 내용 | 출처 | 범위 제한 |
|---|---|---|---|
| `final_decision._REQUIRED_CONTEXT['heat_stroke']` | 열사병 명명에는 환경 열 노출 또는 운동이 필요(정확한 정규식, 부정 문맥 제외) | Epstein 2019 (classic/exertional heatstroke 정의) | 후보·점수·긴급 처분은 바뀌지 않음 |
| `final_decision._curated_syndrome_on_same_observations` | Round V 명칭 계층 규칙에 "같은 장기계 category" 조건 추가(폐렴은 심부전의 상위 증후군이 아님) | 엔지니어링 규칙 | — |

## 보호자 진술 (`NOVA_PROXY_REPORT`)

첫 진술이 "my husband / Dad / my 14-month-old son / 우리 아들"처럼 관계어로 시작하고, 그 관계가 환자의 성별·나이와 맞으면 그 관계어가 **환자**를 가리킨다고 본다(보호자가 환자를 설명하는 상황). 이전에는 이런 문장 전체가 가족력으로 지워져, 의식 변화·경련·심부전 증상이 증거에서 사라졌다. 사례별로 한 번 감지해 그 사례 처리 중에만 적용하며(`contextvars`), 사례 간에 저장하지 않는다. 같은 문장 안의 다른 친척("his father had a stroke")은 계속 가족으로 처리한다. 엔지니어링 언어 규칙이며 임상 주장이 아니다.

## 증상·처분 표현

| 대상 | 추가 | 근거 |
|---|---|---|
| `symptomatic_rate_concern` 증상 | collapsed, collapse, keeled over | NICE CG109 1.1.1: 쓰러짐은 달리 밝혀질 때까지 일과성 의식소실로 평가 |
| `band-like blistering rash`, `burning pain on one side of body` | 수포·발진 + 띠/줄/선(양방향), 한쪽·띠 모양의 화끈거리는 통증(영/한/일 관계 문법) | NICE CKS "Shingles": 한쪽 통증 후 피부분절 수포 발진. 기존 별칭은 문법 안에 그대로 포함 |
| `recent cold` | after a runny nose, following a runny nose, had a cold last week | NICE CKS "Otitis media – acute": 상기도 감염 후 발생 |

## 순위·후보 유지

| 기전 | 스위치 | 내용 |
|---|---|---|
| 근거 있는 후보 유지 | `NOVA_RETAIN_EVIDENCED` | 직전 턴 감별에 있던 ontology 후보가 자기 관찰 근거(기존 MIN_EVIDENCED_ONTOLOGY_WEIGHT 규칙)를 계속 가지면, 이번 턴 rerank가 빠뜨려도 후보 pool에 남긴다. 점수 가산 없음 |
| bare "No" 반감의 패턴 조건 | `NOVA_PATTERN_V2` | Round V 반감 규칙은 관찰된 **비일반** typical feature 2개 이상인 가설에만 적용(흉통+호흡곤란 같은 공유 증상 둘은 패턴이 아님) |
| 선행 맥락 가중 | `NOVA_CONTEXT_V2` | "recent cold/infection/viral illness"는 typical feature여도 위험인자 가중(0.4)으로 순위에 반영 |
