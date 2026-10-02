"""Bounded Korean/English clinical normalization; originals remain in patient state.

This dictionary is not a translator or comprehensive multilingual clinical NLP.
Only explicit phrases and their local negations are normalized.
"""
import re
from functools import lru_cache

TERMS = {
    '호흡곤란':'dyspnea', '숨이 차':'dyspnea', '가슴 통증':'chest pain', '흉통':'chest pain',
    '복통':'abdominal pain', '두통':'headache', '발열':'fever', '기침':'cough',
    '구토':'vomiting', '메스꺼움':'nausea', '설사':'diarrhea', '천식':'asthma',
    '쌕쌕거림':'wheeze', '편두통':'migraine', '의식 혼란':'confusion',
    '배뇨통':'dysuria', '옆구리 통증':'flank pain', '목 경직':'neck stiffness',
    '양성':'positive', '음성':'negative', '검사 대기':'pending',
    '혈압':'BP', '맥박':'HR', '호흡수':'RR', '체온':'Temp', '산소포화도':'SpO2',
}

@lru_cache(maxsize=4096)
def normalize_clinical_text(text: str) -> str:
    result = text
    for ko,en in sorted(TERMS.items(), key=lambda pair:len(pair[0]), reverse=True):
        result = re.sub(re.escape(ko)+r'\s*(?:은|는|이|가)?\s*(?:없(?:음|다|어요|습니다)?|아님)',
                        lambda _: 'no '+en+'; ', result)
        result = result.replace(ko, ' '+en+' ')
    for abbreviation,expanded in {'SOB':'dyspnea','DOE':'dyspnea on exertion','N/V':'nausea and vomiting'}.items():
        result = re.sub(r'(?<!\w)'+re.escape(abbreviation)+r'(?!\w)',expanded,result,flags=re.I)
    return re.sub(r'\s+',' ',result).strip()
