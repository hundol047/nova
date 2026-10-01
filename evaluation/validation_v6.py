"""Fresh, author-created synthetic checks frozen before their first run.

Not independently clinician-adjudicated and not an official competition sample.
Authored by the same implementer; report separately from development V5. Never
change labels/text in response to results. These are deliberately mixed initial
presentations, with multiple competing findings; all are synthetic.
"""
from evaluation.cases import SyntheticCase as C

VALIDATION_V6 = [
 C(case_id='V6_01',chief_complaint='I became sweaty and sick walking uphill',demographics={'age':66,'sex':'female'},ground_truth_diagnosis='acute_coronary_syndrome',
 answers={'onset':'started during exercise 45 minutes ago','character':'heavy substernal pressure','associated_symptoms':'nausea and left arm pain','past_medical_history':'diabetes'},
 exam_results={'vital_signs':'BP 148/90 HR 104 RR 20 Temp 36.8 SpO2 97%'},test_results={'ecg':'ST depression','troponin':'elevated troponin'}),
 C(case_id='V6_02',chief_complaint='Breathing hurts and I have started coughing',demographics={'age':47,'sex':'male'},ground_truth_diagnosis='pulmonary_embolism',
 answers={'onset':'abrupt onset','associated_symptoms':'hemoptysis and unilateral calf swelling','past_medical_history':'recent orthopedic surgery'},
 exam_results={'vital_signs':'BP 114/70 HR 124 RR 28 Temp 37.3 SpO2 88%','extremity_exam':'unilateral leg swelling'},test_results={'ct_chest_angio':'filling defect in the pulmonary artery','d_dimer':'elevated D-dimer'}),
 C(case_id='V6_03',chief_complaint='I cannot keep food down and my head hurts',demographics={'age':33,'sex':'female'},ground_truth_diagnosis='meningitis',
 answers={'onset':'progressive over 18 hours','associated_symptoms':'fever, stiff neck, light sensitivity; denies rash'},
 exam_results={'vital_signs':'BP 120/72 HR 102 RR 20 Temp 39.2 SpO2 98%','neuro_exam':'neck stiffness without focal deficits'},test_results={'lumbar_puncture':'CSF pleocytosis; gram-negative diplococci'}),
 C(case_id='V6_04',chief_complaint='Unusually thirsty and too tired to work',demographics={'age':24,'sex':'male'},ground_truth_diagnosis='diabetic_ketoacidosis',
 answers={'onset':'two days','associated_symptoms':'polyuria, polydipsia, vomiting','past_medical_history':'type 1 diabetes','medication':'missed insulin'},
 exam_results={'vital_signs':'BP 100/62 HR 118 RR 30 Temp 36.9 SpO2 98%','general_appearance':'dehydration, fruity breath odor, Kussmaul breathing'},test_results={'glucose_point_of_care':'glucose 420 mg/dL','ketones':'large ketones','abg':'metabolic acidosis'}),
 C(case_id='V6_05',chief_complaint='Low belly pain with dizziness',demographics={'age':29,'sex':'female'},ground_truth_diagnosis='ectopic_pregnancy',
 answers={'onset':'sudden unilateral pelvic pain','associated_symptoms':'missed period and vaginal bleeding'},
 exam_results={'vital_signs':'BP 96/60 HR 112 RR 20 Temp 37.1 SpO2 99%','pelvic_exam':'adnexal tenderness'},test_results={'beta_hcg':'positive beta-hCG','pelvic_ultrasound':'adnexal mass; no intrauterine pregnancy'}),
 C(case_id='V6_06',chief_complaint='Chills with soreness in my side',demographics={'age':41,'sex':'female'},ground_truth_diagnosis='pyelonephritis',
 answers={'associated_symptoms':'flank pain and painful urination; no confusion','onset':'two days'},
 exam_results={'vital_signs':'BP 124/80 HR 90 RR 16 Temp 38.4 SpO2 98%','abdominal_exam':'costovertebral angle tenderness'},test_results={'urinalysis':'positive nitrites and leukocyte esterase','lactate':'lactate 1.0 mmol/L'}),
 C(case_id='V6_07',chief_complaint='My legs feel weak and my heart feels odd',demographics={'age':71,'sex':'male'},ground_truth_diagnosis='severe_electrolyte_disorder',
 answers={'past_medical_history':'chronic kidney disease','associated_symptoms':'muscle weakness and palpitations','medication':'spironolactone'},
 exam_results={'vital_signs':'BP 136/78 HR 60 RR 16 Temp 36.6 SpO2 98%'},test_results={'bmp':'potassium 6.9 mmol/L','ecg':'peaked T waves','glucose_point_of_care':'glucose 105 mg/dL'}),
 C(case_id='V6_08',chief_complaint='I nearly fainted and was shaking',demographics={'age':57,'sex':'female'},ground_truth_diagnosis='hypoglycemia',
 answers={'medication':'insulin','associated_symptoms':'diaphoresis, tremor, confusion','onset':'after a missed meal'},
 exam_results={'vital_signs':'BP 130/78 HR 104 RR 18 Temp 36.7 SpO2 98%'},test_results={'glucose_point_of_care':'glucose 48 mg/dL'}),
 C(case_id='V6_09',chief_complaint='Belly discomfort has changed location',demographics={'age':22,'sex':'male'},ground_truth_diagnosis='appendicitis',
 answers={'onset':'periumbilical pain migrating to right lower quadrant','associated_symptoms':'anorexia, nausea, low grade fever'},
 exam_results={'vital_signs':'BP 120/76 HR 96 RR 18 Temp 37.8 SpO2 99%','abdominal_exam':'focal right lower quadrant tenderness; no rigid abdomen'},test_results={}),
 C(case_id='V6_10',chief_complaint='The room moves when I turn my head',demographics={'age':54,'sex':'female'},ground_truth_diagnosis='bppv',
 answers={'character':'brief episodic vertigo','aggravating':'triggered by head position change','associated_symptoms':'no hearing loss, no focal weakness'},
 exam_results={'vital_signs':'BP 128/76 HR 74 RR 14 Temp 36.8 SpO2 99%','neuro_exam':'no focal neuro deficit','dix_hallpike':'positive positional nystagmus'},test_results={}),
 C(case_id='V6_11',chief_complaint='I feel woozy after getting out of bed',demographics={'age':76,'sex':'male'},ground_truth_diagnosis='orthostatic_hypotension',
 answers={'associated_symptoms':'improves with sitting; no chest pain, no palpitations','medication':'new antihypertensive medication'},
 exam_results={'vital_signs':'BP 142/84 lying HR 72; BP 108/64 standing after 2 minutes HR 88; RR 16 Temp 36.8 SpO2 98%'},test_results={'ecg':'normal sinus rhythm'}),
 C(case_id='V6_12',chief_complaint='My chest burns after late dinners',demographics={'age':38,'sex':'female'},ground_truth_diagnosis='gerd',
 answers={'character':'burning chest pain and sour taste','aggravating':'worse after meals and worse lying down','relieving':'relieved by antacids','associated_symptoms':'no exertional pain or dyspnea'},
 exam_results={'vital_signs':'BP 118/74 HR 76 RR 14 Temp 36.8 SpO2 99%'},test_results={'ecg':'normal','troponin':'normal'}),
]
