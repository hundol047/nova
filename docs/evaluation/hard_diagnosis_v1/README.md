# 고난도 진단 개선 — 개발 평가

기준 커밋: `aad2297`. 모든 실행은 합성 환자와 mock provider를 사용한다.
실제 환자 진단 정확도, 실모델 성능 또는 임상 검증을 의미하지 않는다.
v11 사례의 정답·내용·해시는 변경하지 않았고, 희귀질환도 분모에서 제외하지 않았다.
이번에는 v11 실패 내용을 직접 분석했으므로 명시적으로 **개발/회귀 평가**로 취급한다.

| 평가 | 수정 전 | 수정 후 |
|---|---:|---:|
| 고난도 전체 정답 | 12/24 (50.0%) | 14/24 (58.3%) |
| 고난도 중 위험질환 정답 | 7/15 | 8/15 |
| 단위·출혈 개발 대화 | 4/8 | 8/8 |
| 기존 표현 변형 회귀 | 72/72 | 72/72 |
| 기존 불확실성 회귀 | 20/20 | 20/20 |

고난도에서 개선된 것은 한·영 혼합 복통 및 출혈 증상 사례 2개이며,
기존 정답이 오답으로 바뀐 사례는 없다. 출혈 사례에서는 CBC와 hemoglobin
결과 키 불일치가 그대로 남아 있어, 이 사례의 개선을 단위 변환 효과라고
해석해서는 안 된다. 단위 변환은 별도 단위 쌍과 근거 해석 테스트로 확인했다.

## 변경

- 혈색소 g/L → g/dL, 크레아티닌 umol/L·µmol/L·μmol/L → mg/dL의 명시적 변환.
  숫자 바로 뒤에 붙은 단위만 해석한다. 이웃 검사 단위를 빌리지 않는다.
  지원하지 않는 단위, 불확실·과거 결과와 충돌하는 수치는 계속 보류한다.
  크레아티닌 상승 하나만으로 급성 신손상을 확진하는 규칙은 추가하지 않았다.
- 복부 사분면과 한국어 복부 위치 표현을 후보 검색에 반영.
  초기 복부 증상 표현이 인식되지 않은 채 미열만 인식되어 복부 후보를 잃던 문제를 수정.
  위치만으로 충수염을 확진하지 않는다.
- melena·hematemesis·hematochezia를 출혈 후보 검색에 반영.
  일상적인 출혈 표현을 증상 근거로 인식하고, 별칭의 모든 내용 단어를 요구한다.
  부정·추정 표현을 양성 근거로 바꾸지 않는다.

## 평가 해석

`before.json`과 `after.json`은 전체 24개 사례의 정답, 최종 진단,
검사 선택 및 후보 순위 경로를 담는다. 결과 요약은 `summary.json` 참조.

새 `hard_units_v1`은 변경 전에 내용을 고정한 4개 사례군의 단위 쌍, 총 8개 대화다.
기준 4/8, 첫 수정 후 6/8이었다. 이 실패를 보고 누락된 출혈 임상용어 검색을
수정했으므로 최종 8/8은 **개발 결과**다. 독립 검증으로 주장하지 않는다.
단위 쌍을 8명의 독립 환자로 계산해서도 안 된다.

별도로 기존 72개 표현 변형 검증(18개 원본 사례군)과 20개 불확실성 검증을
회귀 검사했다. 해당 사례나 정답은 이번 변경에 맞춰 고치지 않았다.
이 역시 외부 임상의가 작성한 독립 임상 데이터는 아니다.

남은 v11 실패는 희귀질환 7개(GBS, 심낭염, 갈색세포종, Fabry병, 크루프,
전자간증, 급성 신손상), 대동맥박리, 원인 불명 여행 후 발열, 복합 심폐질환이다.
미검증 Tier-2 규칙을 켜거나 정답을 강제로 주입하지 않았다.
시뮬레이터는 검사 키가 정확히 일치해야 결과를 전달한다. 예를 들어
`ct_aorta`와 사례의 `ct_angiogram`, `cbc`와 사례의 `hemoglobin`은 자동 매핑되지 않는다.
점수를 높이기 위해 시뮬레이터나 채점기를 바꾸지 않았으며, 이런 전달 문제와
진단 추론 실패를 후속 평가에서 분리해야 한다.

## 근거와 한계

- [NIDDK 성인 eGFR 방정식](https://www.niddk.nih.gov/research-funding/research-programs/kidney-clinical-research-epidemiology/laboratory/glomerular-filtration-rate-equations/adults): 크레아티닌 µmol/L를 mg/dL로 바꿀 때 88.4로 나눈다.
- 혈색소 g/L ÷ 10 = g/dL은 부피 단위의 정확한 변환이다. 기존 성인 참고 임계값은 바꾸지 않았다. 연령·성별·임신별 해석은 여전히 제한적이다.
- [NIDDK 위장관 출혈 증상](https://www.niddk.nih.gov/health-information/digestive-diseases/gastrointestinal-bleeding/symptoms-causes): 출혈을 의심하게 하는 대변 및 구토 양상의 근거. 이 증상만으로 출혈 원인을 확진하지 않는다.
- [NIDDK 충수염 증상](https://www.niddk.nih.gov/health-information/digestive-diseases/appendicitis/symptoms-causes): 복통 위치에 관한 참고. 위치 표현은 후보 검색에만 추가했다.

## 재실행

```sh
python scripts/run_hard_units.py --output /tmp/hard_units.json
python -m evaluation.blind_benchmark_v11
python -m pytest tests/ -q --tb=short
```

기준 코드 비교에는 `run_hard_units.py --repo /tmp/nova-hard-baseline`을 사용했다.
모델 가중치 학습, 배포 또는 원격 push는 수행하지 않았다.

전체 테스트: **513 passed, 1 skipped**, 의존성 deprecation 경고 1개.
제출용 코드 동기화와 독립 실행 smoke test도 통과했다.
