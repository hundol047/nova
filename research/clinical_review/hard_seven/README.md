# 고난도 진단 근거 초안 7종

현재 고난도 v11의 미해결 대상 7종을 임상 검토에 넘길 수 있도록 근거·감별·검사 필요사항을
`profiles.json`에 구조화했다. 대상은 Guillain–Barré syndrome, 심낭염, 갈색세포종,
Fabry병, 크루프, 전자간증, 급성 신손상이다. 질환마다 원문 URL·버전·확인일을 기록했다.

이 파일은 개발자가 작성한 **임상 미검증 초안**이다. 현재 엔진이 읽는 지식베이스에
넣지 않았고 전문가 검토 또는 임상 평가를 완료했다고 표시하지 않았다.
정량적 진단 확률이나 최종 진단을 생성하지 않는다.

## 검토 코드의 역할

`scripts/review_diagnostic_evidence.py`는 검토자가 구조화한 관찰값을 받아 증거 묶음이
있는지와 어떤 증거가 빠졌는지를 반환한다. 각 관찰값에 `feature`, `status`, `temporality`를
반드시 명시한다. 현재의 긍정 관찰만 사용하며 부정·추정·미측정·과거 소견은 이를 대신하지
못한다. 같은 특징의 기록이 충돌하면 긍정 근거에서 제외한다. 진단명 자체는 증거 코드로
받지 않는다. 이 코드는 자유 문장, 수치, 연령, 성별, 임신 주수를 자동 판독하지 않는다.

모든 출력에 `final_diagnosis=null`, `probability=null`, `disease_excluded=false`가 있다.
패턴이 없다는 결과는 질환 배제가 아니다. 예를 들어 전형적인 운동형 외의 GBS,
비전형 Fabry, 산후·기존 고혈압에 동반된 전자간증은 이 좁은 패턴의 범위를 벗어날 수 있다.

## 확인한 소프트웨어 동작

54개 합성 관찰 입력으로 현재·부정·추정·과거·누락·충돌의 해석과 증거 경로를 확인했다.
단일 높은 크레아티닌만 있는 경우, 단백뇨 없이 장기 이상이 있는 경우 등 비교 입력도 포함한다.
입력과 기대 동작은 같은 개발자가 작성했다. 독립 임상의 라벨 사례나 실제 진료 자료가 아니며
54/54를 진단 정확도 100%로 표현하면 안 된다. v11 정답·분모·원문은 수정하지 않았다.

## 근거 출처

1. [EAN/PNS GBS 2023](https://onlinelibrary.wiley.com/doi/full/10.1111/ene.16073)
2. [ACC 심낭염 2025 안내](https://www.acc.org/latest-in-cardiology/journal-scans/2025/08/05/19/05/new-concise-clinical), [ESC 2025](https://www.escardio.org/guidelines/clinical-practice-guidelines/all-esc-practice-guidelines/myocarditis-and-pericarditis/)
3. [Endocrine Society PPGL 2014](https://academic.oup.com/jcem/article/99/6/1915/2537399)
4. [GeneReviews Fabry 2024](https://www.ncbi.nlm.nih.gov/sites/books/NBK1292/)
5. [RCH 크루프 2024](https://www.rch.org.au/clinicalguide/guideline_index/croup_laryngotracheobronchitis/)
6. [NICE NG133](https://www.nice.org.uk/guidance/ng133/chapter/recommendations)
7. [KDIGO AKI 2012](https://kdigo.org/wp-content/uploads/2016/10/KDIGO-2012-AKI-Guideline-English.pdf)

출처를 참고해 작성한 내부 검토 패턴이지, 각 기관이 승인한 알고리즘이 아니다.
심낭염은 2025 ACC·ESC 전문 조정 검토를 남겨 두었다. AKI 2026 공개 검토 초안은
최종 지침으로 간주하지 않는다.

## 재현과 다음 단계

```sh
python scripts/review_diagnostic_evidence.py --output /tmp/evidence_probes.json
python -m pytest tests/test_hard_seven_evidence_review.py -q
```

실행 엔진에 반영하기 전 질환별 전문가 검토, 용어·검사 매핑 검토, 개발 데이터와 분리한
실제 모델 평가가 필요하다. 이를 완료한 뒤 후보 검색 → 추가 질문·검사 → 최종 판단을
연결해야 위험질환·고난도 정답률이 개선되는지 평가할 수 있다. 현재 점수 개선은 주장하지 않는다.
