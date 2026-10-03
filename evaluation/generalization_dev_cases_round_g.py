"""Round G synthetic DEVELOPMENT cases; may be iterated, never blind/clinical validation."""
from evaluation.cases import SyntheticCase


def case(n, text, gt, *, age=46, sex='female', answers=None, exams=None, tests=None, category='development'):
    return SyntheticCase(case_id=f'RoundG_{n}', chief_complaint=text,
        demographics={'age':age,'sex':sex},ground_truth_diagnosis=gt,
        answers=answers or {},exam_results=exams or {},test_results=tests or {},category=category)

ROUND_G_CASES = [
 case('pleural', 'Breathing became difficult during a quiet afternoon; pain along the right ribs.', 'tension_pneumothorax',
      exams={'vital_signs':'BP 84/52, HR 126, RR 32, SpO2 86%', 'lung_auscultation':'unilateral absent breath sounds, tracheal deviation'},
      tests={'cxr':'large pneumothorax with mediastinal shift'}),
 case('pelvic', 'I nearly fainted and feel an ache low in my belly.', 'ectopic_pregnancy',age=32,
      answers={'associated_symptoms':'missed period and vaginal spotting', 'location':'unilateral pelvic pain'},
      exams={'vital_signs':'BP 88/56, HR 120', 'pelvic_exam':'adnexal tenderness'},
      tests={'beta_hcg':'positive beta-hCG', 'pelvic_ultrasound':'adnexal mass, free fluid, no intrauterine pregnancy'}),
 case('metabolic', 'Feeling weak and shaky after taking my usual diabetes medicine without lunch.', 'hypoglycemia',age=67,
      answers={'medications':'insulin', 'associated_symptoms':'sweating and confusion'},tests={'glucose_point_of_care':'glucose 39 mg/dL'}),
 case('infection', 'Fever with painful urination and now feeling faint.', 'sepsis',age=74,
      exams={'vital_signs':'BP 82/48, HR 124, Temp 39.3, RR 29'},tests={'lactate':'lactate 5.1 mmol/L','urinalysis':'pyuria and nitrites positive','cbc':'leukocytosis'}),
 case('ko', '저녁부터 복통과 설사가 있어요.', 'gastroenteritis',tests={'cbc':'normal CBC'},answers={'associated_symptoms':'watery diarrhea, vomiting', 'onset':'after a shared meal'}),
 case('ja', '夕方から腹痛と下痢が続きます。', 'gastroenteritis',tests={'cbc':'normal CBC'},answers={'associated_symptoms':'watery diarrhea, vomiting', 'onset':'after a shared meal'}),
 case('ko_mix', '복통, abdominal pain, 설사, diarrhea since dinner.', 'gastroenteritis',tests={'cbc':'normal CBC'},answers={'associated_symptoms':'watery diarrhea, vomiting', 'onset':'after a shared meal'}),
 case('en', 'Abdominal pain and diarrhea since dinner.', 'gastroenteritis',tests={'cbc':'normal CBC'},answers={'associated_symptoms':'watery diarrhea, vomiting', 'onset':'after a shared meal'}),
 case('neg_ko', '두통은 없어요. 소변을 볼 때 아파요.', 'uncomplicated_cystitis',answers={'associated_symptoms':'dysuria and urinary frequency'},tests={'urinalysis':'nitrites positive and pyuria'}),
 case('neg_ja', '頭痛はありません。排尿時に痛みます。', 'uncomplicated_cystitis',answers={'associated_symptoms':'dysuria and urinary frequency'},tests={'urinalysis':'nitrites positive and pyuria'}),
 case('reentry', 'A strange uncomfortable feeling, difficult to describe.', 'acute_coronary_syndrome',age=62,sex='male',answers={'associated_symptoms':'substernal pressure with diaphoresis and pain radiating to jaw'},tests={'ecg':'ST elevation', 'troponin':'elevated troponin'}),
 case('benign', 'Sour taste with burning behind the breastbone after a large meal.', 'gerd',answers={'aggravating':'worse after meals and lying down','relieving':'antacids help'},tests={'ecg':'normal ECG','troponin':'negative troponin'}),
]
