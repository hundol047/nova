"""Same-author development vignettes for 34 added entries, not an independent holdout.

Cases and qualitative report interpretations are authored for software regression.
They are not real patient data, calibrated accuracy evidence, or clinical adjudication.
Unknown unscripted results are deliberately not converted to normal findings.
"""
from evaluation.cases import SyntheticCase

# Diagnosis, presenting narrative, scripted observations. Labels never enter patient state.
VIGNETTES = [
('acute_pericarditis', 'Pleuritic chest pain; pain improves leaning forward; pain worse supine.', {'ecg':'Diffuse ST elevation with PR depression.', 'cardiac_auscultation':'A pericardial friction rub is heard.'}),
('acute_heart_failure', 'New orthopnea; paroxysmal nocturnal dyspnea; bilateral leg edema.', {'cxr':'Bilateral interstitial pulmonary edema.', 'echocardiogram':'Reduced left ventricular systolic function.'}),
('pleural_effusion', 'Progressive dyspnea with pleuritic discomfort and reduced breath sounds at base.', {'cxr':'Blunted costophrenic angle on the left.', 'thoracic_ultrasound':'Anechoic pleural collection.'}),
('acute_cholecystitis', 'Persistent right upper quadrant pain; right shoulder radiation; pain after fatty meal.', {'abdominal_ultrasound':'Thickened gallbladder wall; pericholecystic fluid.'}),
('acute_cholangitis', 'Right upper quadrant pain with jaundice and rigors.', {'abdominal_ultrasound':'Common bile duct stone.', 'liver_panel':'Elevated bilirubin and alkaline phosphatase.', 'blood_culture':'Growth of Escherichia coli.'}),
('acute_diverticulitis', 'Left lower quadrant pain and change in bowel habit; left lower quadrant tenderness.', {'ct_abdomen':'Inflamed sigmoid diverticula; pericolonic fat stranding.'}),
('small_bowel_obstruction', 'Abdominal distension with obstipation and bilious vomiting.', {'ct_abdomen':'Dilated proximal small bowel; transition point with collapsed distal bowel.'}),
('acute_mesenteric_ischemia', 'Sudden severe abdominal pain; pain out of proportion to examination; bloody diarrhea.', {'ct_mesenteric_angio':'Superior mesenteric artery occlusion; reduced bowel wall enhancement.'}),
('ovarian_torsion', 'Sudden unilateral pelvic pain and vomiting after intermittent unilateral pelvic pain.', {'pelvic_ultrasound':'Enlarged edematous ovary; twisted vascular pedicle.', 'beta_hcg':'Negative.'}),
('pelvic_inflammatory_disease', 'Bilateral pelvic pain; dyspareunia; abnormal vaginal discharge.', {'pelvic_exam':'Cervical motion tenderness; mucopurulent cervical discharge.', 'beta_hcg':'Negative.'}),
('hemorrhagic_ovarian_cyst', 'Acute pelvic pain during midcycle; unilateral pelvic tenderness.', {'pelvic_ultrasound':'Lacy internal echoes in ovarian cyst; avascular clot in ovarian cyst.', 'beta_hcg':'Negative.'}),
('intracerebral_hemorrhage', 'Abrupt severe headache; sudden focal weakness; reduced consciousness.', {'ct_head':'Acute intraparenchymal hematoma; surrounding perihematomal edema.'}),
('subdural_hematoma', 'Head trauma last week followed by worsening headache and progressive drowsiness.', {'ct_head':'Crescentic extra-axial hematoma; subdural mass effect.'}),
('epidural_hematoma', 'Head trauma; lucid interval followed by deteriorating consciousness.', {'ct_head':'Biconvex extra-axial hematoma; adjacent skull fracture.'}),
('brain_abscess', 'Progressive headache; focal seizure; focal neurological deficit.', {'mri_brain_contrast':'Intraparenchymal ring-enhancing lesion; central restricted diffusion.'}),
('subdural_empyema', 'Recent sinusitis followed by progressive headache and a focal seizure.', {'mri_brain_contrast':'Enhancing subdural collection; restricted diffusion in subdural collection.'}),
('lung_abscess', 'Persistent productive cough with foul smelling sputum; aspiration history.', {'ct_chest':'Thick-walled pulmonary cavity; air-fluid level within cavity.'}),
('renal_infarction', 'Sudden flank pain; hematuria; flank tenderness.', {'ct_abdomen':'Wedge-shaped renal perfusion defect; renal artery filling defect.'}),
('obstructive_uropathy', 'Reduced urine output; flank discomfort; difficulty voiding.', {'renal_ultrasound':'Hydronephrosis with obstructed ureter.'}),
('acute_urinary_retention', 'Unable to pass urine; painful suprapubic distension after urinary hesitancy.', {'bladder_scan':'Markedly distended bladder; high postvoid residual.'}),
('acute_kidney_injury', 'Oliguria and reduced urine output after recent volume depletion.', {'bmp':'Acute rise in creatinine from baseline over 48 hours.'}),
('hyperosmolar_hyperglycemic_state', 'Profound dehydration; polyuria; polydipsia and lethargy.', {'serum_osmolality':'Markedly elevated serum osmolality.', 'glucose_point_of_care':'Severe hyperglycemia.', 'ketones':'Minimal ketonemia.', 'abg':'pH 7.38, bicarbonate 24 mmol/L.'}),
('iron_deficiency_anemia', 'Exertional fatigue; pica; pallor.', {'cbc':'Microcytic anemia.', 'iron_studies':'Low ferritin.'}),
('primary_hypothyroidism', 'Cold intolerance; weight gain; constipation.', {'thyroid_panel':'Elevated TSH; low free T4.'}),
('hyperthyroidism', 'Heat intolerance; weight loss despite appetite; fine tremor and palpitations.', {'thyroid_panel':'Suppressed TSH; elevated free T4.'}),
('deep_vein_thrombosis', 'Unilateral leg swelling and calf pain after recent immobilization.', {'venous_ultrasound':'Noncompressible femoral vein containing intraluminal venous thrombus.'}),
('cellulitis', 'Painful skin redness; spreading skin erythema starting at a skin break.', {'skin_exam':'Warm tender erythematous skin; spreading ill-defined erythema.'}),
('herpes_zoster', 'Burning dermatomal pain; skin hypersensitivity; unilateral painful rash.', {'skin_exam':'Grouped vesicles in a unilateral dermatomal distribution.'}),
('septic_arthritis', 'Acute swollen joint; pain with passive joint movement; inability to bear weight.', {'synovial_fluid':'Bacteria on synovial Gram stain; purulent synovial fluid.'}),
('acute_gout', 'First metatarsophalangeal pain; podagra; abrupt joint pain.', {'synovial_fluid':'Needle-shaped crystals; negatively birefringent monosodium urate.'}),
('acute_hepatitis', 'Jaundice; dark urine; anorexia.', {'liver_panel':'Acute hepatocellular injury pattern with elevated ALT and AST.'}),
('rhabdomyolysis', 'Severe muscle pain; muscle swelling; dark urine after exertion.', {'creatine_kinase':'Markedly elevated creatine kinase.', 'urinalysis':'Heme positive with few red cells.'}),
('carbon_monoxide_poisoning', 'Enclosed space combustion exposure; household members with similar headache; symptoms improve outdoors.', {'co_oximetry':'Elevated carboxyhemoglobin above exposure reference range.'}),
('influenza', 'Abrupt fever and myalgia; dry cough; influenza exposure.', {'respiratory_pcr':'Influenza A detected.'}),
]


def make_cases():
    from nova_agent.taxonomy import EXAM_CATALOG
    return [SyntheticCase(case_id='Expanded%02d' % i, chief_complaint=narrative,
        demographics={'age':40, 'sex':'female' if diagnosis in {'ovarian_torsion','pelvic_inflammatory_disease','hemorrhagic_ovarian_cyst'} else 'male'},
        ground_truth_diagnosis=diagnosis, category='expanded_development',
        answers={'associated_symptoms':narrative},
        exam_results={k:v for k,v in results.items() if k in EXAM_CATALOG},
        test_results={k:v for k,v in results.items() if k not in EXAM_CATALOG},
        default_answer='Unknown / not provided.', default_exam_result='Unknown / not provided.',
        default_test_result='Unknown / not provided.')
        for i,(diagnosis,narrative,results) in enumerate(VIGNETTES,1)]

EXPANDED_CASES = make_cases()
