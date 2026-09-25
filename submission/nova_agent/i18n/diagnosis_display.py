"""Diagnosis display-name table: diagnosis_id -> {locale: display string}.

Covers every diagnosis currently in nova_agent/knowledge/diseases/*.json (34 entries, spot-checked
against knowledge.retrieval.all_diseases() by tests/test_diagnosis_display.py so this table can
never silently drift out of sync as diseases are added). English is never listed explicitly here --
each disease's own KB `name` field already IS the canonical English display string, and is always
the fallback `translate_diagnosis()` returns for any (diagnosis_id, locale) pair this table doesn't
cover, so a not-yet-translated diagnosis is disclosed by falling back to a real, correct English
name -- never a fabricated or guessed translation.
"""

from __future__ import annotations

from typing import Dict, Optional

# diagnosis_id -> {"ko": ..., "ja": ..., "zh": ...}
DIAGNOSIS_DISPLAY: Dict[str, Dict[str, str]] = {
    "acute_abdomen": {"ko": "급성 복증(외과적 복부)", "ja": "急性腹症（外科的腹部）", "zh": "急腹症（外科腹部）"},
    "gi_bleeding": {"ko": "위장관 출혈", "ja": "消化管出血", "zh": "消化道出血"},
    "ectopic_pregnancy": {"ko": "자궁외 임신", "ja": "子宮外妊娠", "zh": "宫外孕"},
    "acute_pancreatitis": {"ko": "급성 췌장염", "ja": "急性膵炎", "zh": "急性胰腺炎"},
    "appendicitis": {"ko": "급성 충수염", "ja": "急性虫垂炎", "zh": "急性阑尾炎"},
    "gastroenteritis": {"ko": "급성 위장염", "ja": "急性胃腸炎", "zh": "急性胃肠炎"},
    "acute_coronary_syndrome": {"ko": "급성 관상동맥 증후군", "ja": "急性冠症候群", "zh": "急性冠状动脉综合征"},
    "aortic_dissection": {"ko": "대동맥 박리", "ja": "大動脈解離", "zh": "主动脉夹层"},
    "gerd": {"ko": "위식도 역류질환", "ja": "胃食道逆流症", "zh": "胃食管反流病"},
    "musculoskeletal_chest_pain": {"ko": "근골격계 흉통(늑연골염)", "ja": "筋骨格系胸痛（肋軟骨炎）",
                                    "zh": "肌肉骨骼性胸痛（肋软骨炎）"},
    "vasovagal_syncope": {"ko": "미주신경성 실신", "ja": "迷走神経性失神", "zh": "血管迷走性晕厥"},
    "cardiac_arrhythmia": {"ko": "심장 부정맥(예: 심방세동, 발작성 상심실빈맥)",
                            "ja": "不整脈（心房細動、発作性上室頻拍など）",
                            "zh": "心律失常（如心房颤动、室上性心动过速）"},
    "panic_attack": {"ko": "공황 발작", "ja": "パニック発作", "zh": "惊恐发作"},
    "diabetic_ketoacidosis": {"ko": "당뇨병성 케톤산증", "ja": "糖尿病性ケトアシドーシス", "zh": "糖尿病酮症酸中毒"},
    "severe_electrolyte_disorder": {"ko": "중증 전해질 이상(고칼륨혈증/저나트륨혈증 등)",
                                     "ja": "重症電解質異常（高カリウム血症/低ナトリウム血症など）",
                                     "zh": "严重电解质紊乱（高钾血症/低钠血症等）"},
    "hypoglycemia": {"ko": "저혈당증", "ja": "低血糖症", "zh": "低血糖"},
    "uncomplicated_cystitis": {"ko": "단순 방광염(하부요로감염)", "ja": "単純性膀胱炎（下部尿路感染症）",
                                "zh": "单纯性膀胱炎（下尿路感染）"},
    "pyelonephritis": {"ko": "급성 신우신염", "ja": "急性腎盂腎炎", "zh": "急性肾盂肾炎"},
    "nephrolithiasis": {"ko": "요로결석", "ja": "尿路結石", "zh": "尿路结石"},
    "sepsis": {"ko": "패혈증", "ja": "敗血症", "zh": "脓毒症"},
    "anaphylaxis": {"ko": "아나필락시스", "ja": "アナフィラキシー", "zh": "过敏性休克"},
    "viral_uri": {"ko": "바이러스성 상기도 감염", "ja": "ウイルス性上気道感染症", "zh": "病毒性上呼吸道感染"},
    "ischemic_stroke": {"ko": "허혈성 뇌졸중", "ja": "虚血性脳卒中", "zh": "缺血性脑卒中"},
    "subarachnoid_hemorrhage": {"ko": "지주막하 출혈", "ja": "くも膜下出血", "zh": "蛛网膜下腔出血"},
    "meningitis": {"ko": "세균성 수막염", "ja": "細菌性髄膜炎", "zh": "细菌性脑膜炎"},
    "migraine": {"ko": "편두통", "ja": "片頭痛", "zh": "偏头痛"},
    "tension_headache": {"ko": "긴장성 두통", "ja": "緊張型頭痛", "zh": "紧张性头痛"},
    "bppv": {"ko": "양성 발작성 체위성 현훈", "ja": "良性発作性頭位めまい症", "zh": "良性阵发性位置性眩晕"},
    "orthostatic_hypotension": {"ko": "기립성 저혈압", "ja": "起立性低血圧", "zh": "体位性低血压"},
    "pulmonary_embolism": {"ko": "폐색전증", "ja": "肺塞栓症", "zh": "肺栓塞"},
    "tension_pneumothorax": {"ko": "긴장성 기흉", "ja": "緊張性気胸", "zh": "张力性气胸"},
    "pneumonia": {"ko": "지역사회획득 폐렴", "ja": "市中肺炎", "zh": "社区获得性肺炎"},
    "asthma_copd_exacerbation": {"ko": "천식/만성폐쇄성폐질환 악화", "ja": "喘息/COPD増悪",
                                  "zh": "哮喘/慢阻肺急性加重"},
    "acute_bronchitis": {"ko": "급성 기관지염", "ja": "急性気管支炎", "zh": "急性支气管炎"},
}


def translate_diagnosis(diagnosis_id: str, locale: str, fallback_display: str) -> str:
    """Returns the locale-appropriate display name for `diagnosis_id`, falling back to
    `fallback_display` (the KB's own English `name` field -- callers always have this on hand from
    the differential/disease entry) when the locale isn't "ko"/"ja"/"zh", or when this specific
    diagnosis_id has no row here yet. Never fabricates a translation."""
    row = DIAGNOSIS_DISPLAY.get(diagnosis_id)
    if row is None:
        return fallback_display
    return row.get(locale) or fallback_display
