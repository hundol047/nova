# 불확실성 근거 해석과 추가 출처 검토 — 2026-10-02

기준 코드 `e603ac8`. 이번 작업은 후보 수를 늘리지 않았습니다. 총 25,496개 레코드 중 신규 검토 후보 24,216개는 여전히 임상적으로 미검증입니다.

## 추가 출처 조사

NCI 공식 설명에서 NCI Thesaurus(NCIt)를 확인했습니다:
https://www.cancer.gov/about-nci/organization/cbiit/vocabulary

질환뿐 아니라 약물·해부학 등 여러 종류의 개념을 포함하는 출처입니다. 질환 하위 분류를 선택하고 기존 NCIT 교차참조와 대조하는 작업이 선행돼야 하므로, 전체 개념 수를 진단명 수에 더하지 않았습니다. 이번에는 원본 수집·질환 선별·등록을 완료하지 않았고 추가 출처 후보로만 기록했습니다.

## 기존 자료 재검증

모든 24,216개 후보를 원본에서 재생성해 비교했고, 출처·검증 상태·실행 경로 분리 검사를 통과했습니다. 이름/ID 중복은 없지만, 정규화한 외부 코드를 여러 후보가 공유하는 **294개 그룹**을 별도로 발견했습니다. 참조가 상위 개념·관련 개념·동등 개념 중 무엇인지는 자동 판단하지 않았습니다.

`research/diagnosis_expansion/validation/shared_reference_review.json`에 전문가 검토 대상으로 보존했습니다. 이들 그룹은 중복 확정도 아니고 검증 완료도 아닙니다. 자동 병합·삭제·임상 승인 표시를 하지 않았습니다.

## 재현한 오류와 수정

환자 증상이나 확정 검사 없이 `possible ST elevation`, `cannot exclude ST elevation`만 주어도 확정 진단을 내리는 문제가 있었습니다. 불확실한 텍스트를 현재의 양성 근거로 사용하는 경로를 수정했습니다.

- 가능한/의심되는/배제되지 않은/불확실한 소견은 확정 근거에서 제외합니다.
- 질적 검사와 수치 검사에도 같은 원칙을 적용합니다.
- 별도 절의 확정 소견은 보존합니다. 문구에 확률을 임의로 부여하지 않습니다.
- 가능한 위험 질환을 배제했다는 의미로 바꾸지 않습니다. 분류명 미확정은 임상적으로 안전하다는 판정이 아닙니다.

## 모의 검사 설계

다섯 가지 근거 유형과 여덟 가지 불확실성 표현을 조합한 **40개 최종 턴 검사**를 코드 수정 전 동결했습니다. 개발/최종 확인 표현을 각 20개로 나눴고, 파일 해시를 `evaluation/uncertainty_v1/manifest.json`에 저장했습니다. 소견 외의 긍정 병력은 제공하지 않았습니다. 기대 출력 unknown은 근거 부족 시 판단 보류 정책의 검사이며, 실제 환자나 임상의가 확정한 질환 정확도 검사가 아닙니다.

40건의 기준 코드 결과는 4/40, 수정 후 40/40입니다. 개발 3/20 → 20/20, 별도 표현 확인 1/20 → 20/20입니다. 같은 다섯 근거 가족을 반복한 합성 검사이므로 독립 환자 40명으로 취급하지 않습니다.

기존 104개 자율 문진·검사 선택 시나리오와 고난도 v11 24건도 다시 실행했습니다. 확인용 결과에 맞춰 규칙을 추가하지 않았습니다. 실제 LLM 호출, 모델 가중치 재학습, 독립 임상 검증은 수행하지 않았습니다.

## 재현

```sh
python scripts/run_uncertainty_probes.py --repo /path/to/e603ac8 --split development --output /tmp/before-dev.json
python scripts/run_uncertainty_probes.py --split development --output /tmp/after-dev.json
python scripts/run_uncertainty_probes.py --split validation --output /tmp/after-validation.json
python scripts/run_robustness_simulations.py --split development --output /tmp/robust-dev.json
python scripts/run_robustness_simulations.py --split validation --output /tmp/robust-validation.json
python scripts/audit_all_review_candidates.py
python -m pytest tests/ -q --tb=short
```

## 최종 실행 결과

| 검사 | 기준 코드 | 수정 후 |
| --- | ---: | ---: |
| 불확실성 판단 보류 개발 20건 | 3/20 | 20/20 |
| 별도 불확실성 표현 20건 | 1/20 | 20/20 |
| 기존 104개 자율 문진 변형 | 104/104 | 104/104 |
| 위 104건의 위험 질환 변형 | 44/44 | 44/44 |
| 고난도 v11 전체 | 12/24 | 12/24 |
| 고난도 v11 위험 질환 | 7/15 | 7/15 |

소프트웨어 검사 **488개 통과, 1개 건너뜀**. 이번에 저장한 모의 실행 결과는 불확실성 40건의 전후 80회 + 자율 문진 104회 + v11 24회, 합계 208회입니다. 서로 다른 종류의 지표를 합쳐 하나의 정확도 숫자로 계산하지 않습니다.

불확실성의 과잉 확정을 줄인 결과이며, 별도 고난도 진단 정확도는 상승하지 않았습니다. 질환 후보를 더 모으거나 같은 모의 사례를 반복 실행하는 것만으로 실제 환자 정확도가 자동 향상되는 것은 아닙니다. 실제 모델·임상의 검토·독립 사례 검증은 미수행 상태이며 확장 게이트를 유지합니다.
