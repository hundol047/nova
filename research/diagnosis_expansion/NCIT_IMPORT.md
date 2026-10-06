# 명칭 35,000개 확장 — 2026-10-02

미국 국립암연구소 NCI EVS의 NCIt 26.09d 원본에서 **9,508개** 검토용 명칭을 추가했다.
이 버전은 원본 ReadMe에 따르면 2026-09-28 편집 완료된 개발 주기 빌드다.

| 집계 | 수 |
| --- | ---: |
| 기존 실행 카탈로그 | 1,280 |
| 기존 오프라인 후보 | 24,216 |
| 새 NCIt 후보 | 9,508 |
| 총 레코드 | 35,004 |
| 기존 동일 명칭 4쌍을 제외한 서로 다른 정규화 명칭 | **35,000** |

새 후보는 종양 6,654개, 비종양 질환 2,854개다. 원본에서 자식 개념이 없는 항목
8,573개와 자식이 있는 명명된 질병 분류 935개를 포함한다. 병기·조직학적 세부 유형과
상위 분류도 포함하며, 임상적으로 독립된 질병 수로 해석하지 않는다.

## 선택과 검증

Disease or Disorder(C2991)의 하위 개념 중 비인간 질환(C22187) 하위는 제외했다.
질병·종양·선천 이상·정신행동 관련 의미 유형만 선택한다. 폐기·잠정·헤더 등 상태가
있는 항목은 선택하지 않는다. 다만 헤더 노드는 계층 연결을 위해 보존한다.
이 연결을 삭제하면 헤더 아래의 정상 질병 개념까지 누락되기 때문이다.

명칭, 별칭, 알려진 NCIt 코드가 기존 자료와 겹치면 제외한다. 적격 후보 15,434개 중
말단 항목을 먼저 선택하고 두 범주를 순환한다. 임상 빈도나 정확도에 따른 선택은 아니다.
원문 코드·명칭·별칭·부모 코드·의미 유형을 보존하며 정의문이나 한국어 번역을 만들지 않았다.

자동 검사는 전체 후보 33,724개에 대해 원본으로 재생성한 내용과 일치하는지,
ID·정규화 대표명 중복이 없는지, 실행 경로와 분리돼 있는지 확인한다. 원본 버전과
원문 일치만으로 임상 의미·동등성이 입증되지는 않는다. 기존 여러 출처에서 같은 참조
코드를 갖는 294개 그룹은 의미 검토 대상으로 유지한다.

후보는 모두 `NOT_VERIFIED`, `runtime_eligible=false`다. 임상 검증 완료 신규 후보는
0개이며 자동 진단 활성화나 기존 확장 게이트 해제는 하지 않았다.

## 출처와 재현

- 원본: https://evs.nci.nih.gov/ftp1/NCI_Thesaurus/Thesaurus_26.09d.FLAT.zip
- SHA-256: `3c2743ffb33302226f6f4df3ee683d2812d2c8726f4094237b80a496cf48411b`
- 보존본: `sources/Thesaurus_26.09d.FLAT.zip`, `sources/NCIT-26.09d-README.txt`
- 이용조건: CC BY 4.0, `sources/NCIT-Terms-of-Use.htm`
- 저작자 표시: NCI Enterprise Vocabulary Services, CBIIT, National Cancer Institute.
- 변경 사항: 질병 계층·의미 유형 필터, 중복 후보 제외, 목표 수량 선택.
- 파생 자료 이름: **Derived NCIt disease review subset (NCI EVS source)**.
  NCI가 이 파생 목록이나 진단 기능을 보증한다는 의미는 아니다.

```sh
python scripts/build_ncit_review_candidates.py
python scripts/search_review_candidates.py C3007 --source ncit
python scripts/audit_all_review_candidates.py
python -m pytest tests/test_ncit_review_expansion.py -q
```
