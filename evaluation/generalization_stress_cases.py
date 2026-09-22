"""Targeted stress set (spec section 17-18, Phase 5): NOT another attempt to pad the generalization
count toward 50-100. A small, deliberately-aimed set of new, genuinely distinct cases that probe the
two root-cause patterns behind this repo's only two known generalization-v2 misses (elderly
polypharmacy hypoglycemia scored via medication-class + glucose evidence; migraine vs ischemic
stroke separation via lay-language aliases + an objective-negative-exam signal) -- from BOTH
directions. Half the cases below exercise the fix; the other half are deliberate negative controls
that check the fix does NOT overfire onto a superficially similar case whose real answer is
something else entirely (a hyperkalemic polypharmacy patient is not hypoglycemia just because
medications are involved; a headache with a true focal deficit is not migraine just because it also
has some throbbing/photophobia-like language).

Never a reworded duplicate of Weakness01_ElderlyPolypharmacyHypoglycemia or
Headache04_ReassuringMigraine (evaluation/generalization_cases_v2.py), and never built by copying
knowledge-base phrase text verbatim into the answer text just to force a pass -- each case is an
independent clinical vignette a person unfamiliar with this repo's KB wording would still write.

Run only AFTER the existing held-out and generalization-v2 suites both stay clean (spec section 18's
required evaluation order) -- this file is the fourth, additional check, not a replacement for either.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

GENERALIZATION_STRESS_CASES = [
    # --- Hypoglycemia, atypical symptoms, young adult (not the elderly-confusion presentation) ---
    SyntheticCase(
        case_id="Stress01_YoungAdultAtypicalHypoglycemia", category="atypical_presentation",
        chief_complaint="feeling jittery and my heart is racing", demographics={"age": 24, "sex": "male"},
        ground_truth_diagnosis="hypoglycemia",
        notes="Adrenergic/autonomic-predominant hypoglycemia in a young adult (jitteriness, "
              "tachycardia, hunger) rather than the neuroglycopenic confusion of the elderly "
              "polypharmacy case -- a genuinely different symptom cluster of the same disease, "
              "testing whether the medication-class + glucose-evidence fix generalizes beyond the "
              "one authored presentation rather than only pattern-matching its exact wording.",
        answers={
            "onset": "about twenty minutes ago, came on fast",
            "associated_symptoms": "shaky, sweaty, and really hungry all of a sudden, heart "
                                    "pounding; denies chest pain, denies fainting",
            "past_medical_history": "type 1 diabetes since childhood",
            "medication": "I use an insulin pump",
            "social_history": "went for a long run this morning and skipped breakfast after",
        },
        exam_results={"mental_status_exam": "anxious but oriented, appropriate",
                      "vital_signs": "BP 128/78, HR 112, RR 18, Temp 36.7, SpO2 99%"},
        test_results={"glucose_point_of_care": "48 mg/dL"},
    ),
    # --- Hypoglycemia with NO diabetes history at all (alcohol-related, still hypoglycemia) ---
    SyntheticCase(
        case_id="Stress02_NonDiabeticAlcoholicHypoglycemia", category="atypical_presentation",
        chief_complaint="found confused outside a bar", demographics={"age": 38, "sex": "male"},
        ground_truth_diagnosis="hypoglycemia",
        notes="Hypoglycemia with NO diabetes and NO glucose-lowering medication at all -- alcohol "
              "suppresses gluconeogenesis in a malnourished/fasting drinker, a well-known cause of "
              "hypoglycemia the medication-class fix must not be required for (the glucose number "
              "itself has to carry the case), checking the fix didn't accidentally make medication "
              "history a prerequisite for considering hypoglycemia.",
        answers={
            "onset": "unclear, found this way by a bystander about half an hour ago",
            "associated_symptoms": "confused, sweaty, trembling once he started coming around; "
                                    "denies slurred speech now, denies one-sided weakness",
            "past_medical_history": "none that his friend knows of, no diabetes",
            "social_history": "friend says he'd been drinking heavily for two days and barely eating",
        },
        exam_results={"mental_status_exam": "confused, diaphoretic, tremulous",
                      "vital_signs": "BP 108/68, HR 108, RR 16, Temp 35.9, SpO2 98%"},
        test_results={"glucose_point_of_care": "38 mg/dL"},
    ),
    # --- Stroke mimicking migraine: some migraine-like language, but a true focal deficit ---
    SyntheticCase(
        case_id="Stress03_StrokeMimickingMigraine", category="dangerous_mimic",
        chief_complaint="bad headache and my vision is off", demographics={"age": 58, "sex": "female"},
        ground_truth_diagnosis="ischemic_stroke",
        notes="Deliberately borrows SOME migraine-sounding language (throbbing quality, visual "
              "symptoms) but pairs it with a PERSISTENT focal deficit and a first-ever episode in a "
              "vascular-risk patient -- the reverse-direction check for the migraine/stroke fix: the "
              "new feature-local aliases and reassuring_if_present exam signal must never be broad "
              "enough to talk the agent OUT of stroke when real focal findings are present.",
        answers={
            "onset": "sudden, about ninety minutes ago, never had anything like it before",
            "character": "throbbing on the right side",
            "associated_symptoms": "my left hand feels weak and clumsy and words aren't coming out "
                                    "right; denies nausea, denies sensitivity to light",
            "past_medical_history": "hypertension, high cholesterol, smokes a pack a day",
            "family_history": "no migraines in the family",
        },
        exam_results={"neuro_exam": "left-sided facial droop and left hand grip weakness, mild "
                                     "expressive aphasia",
                      "vital_signs": "BP 172/98, HR 88, RR 16, Temp 36.9, SpO2 98%"},
        test_results={"ct_head": "acute infarct in the right MCA territory", "glucose_point_of_care": "104 mg/dL"},
    ),
    # --- Migraine with aura, distinct phrasing from Headache04 (visual field disturbance wording) ---
    SyntheticCase(
        case_id="Stress04_MigraineWithAura", category="conflicting_findings",
        chief_complaint="zigzag lines in my vision before a headache", demographics={"age": 26, "sex": "female"},
        ground_truth_diagnosis="migraine",
        notes="Classic visual-aura migraine described with different vocabulary than Headache04 "
              "('zigzag lines', 'blind spot' rather than 'shimmering lights') -- checks the "
              "feature-local aura alias generalizes to more than the one exact phrase it was "
              "written against, and that a genuinely reassuring exam still lets migraine win "
              "cleanly without the newly-added stroke logic dragging it down.",
        answers={
            "character": "pounding pain behind my left eye, comes on after the visual stuff clears up",
            "onset": "the zigzag lines started first, about twenty minutes before the headache "
                     "began, gradually",
            "associated_symptoms": "a blind spot in the middle of my vision that spread outward, "
                                    "then the zigzag lines, now light really bothers me and I feel "
                                    "queasy; denies weakness, denies trouble speaking, denies numbness",
            "past_medical_history": "gets these a few times a year, first one was in college",
            "family_history": "my sister has the same kind of headaches with visual symptoms",
        },
        exam_results={"neuro_exam": "no focal neurological deficit",
                      "vital_signs": "BP 112/70, HR 68, RR 14, Temp 36.7, SpO2 99%"},
        test_results={},
    ),
    # --- Stroke presenting primarily as headache (not weakness) ---
    SyntheticCase(
        case_id="Stress05_StrokeWithHeadache", category="atypical_presentation",
        chief_complaint="sudden headache and I can't see out of one side", demographics={"age": 71, "sex": "male"},
        ground_truth_diagnosis="ischemic_stroke",
        notes="Headache as the presenting complaint for a posterior-circulation stroke with a "
              "visual field cut -- distinct from Stress03 (which leads with weakness/aphasia) and "
              "from the classic sudden-severe-headache SAH pattern already covered elsewhere, "
              "testing the agent doesn't anchor on 'headache -> migraine or SAH' and miss stroke "
              "when the objective finding is a field cut rather than limb weakness.",
        answers={
            "onset": "sudden, about an hour ago",
            "character": "dull ache, not the worst headache of my life",
            "associated_symptoms": "I keep bumping into things on my left side and can't see "
                                    "anything there; denies nausea, denies neck stiffness",
            "past_medical_history": "atrial fibrillation, doesn't take his blood thinner regularly",
        },
        exam_results={"neuro_exam": "left homonymous hemianopia, otherwise grossly intact",
                      "vital_signs": "BP 156/90, HR 92 irregularly irregular, RR 16, Temp 36.8, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the right occipital lobe", "glucose_point_of_care": "112 mg/dL"},
    ),
    # --- Elderly new-onset headache that is genuinely dangerous, not migraine ---
    SyntheticCase(
        case_id="Stress06_ElderlyNewOnsetDangerousHeadache", category="elderly",
        chief_complaint="worst headache I've ever had", demographics={"age": 68, "sex": "female"},
        ground_truth_diagnosis="subarachnoid_hemorrhage",
        notes="Elderly patient, first headache of this kind ever (no migraine history, no family "
              "history of migraine) -- a negative control checking that age/headache alone never "
              "triggers the new migraine feature-local aliases, and that a true thunderclap/neck-"
              "stiffness presentation is still recognized correctly even though this session added "
              "new migraine-favoring matching logic.",
        answers={
            "onset": "sudden, like being hit in the head, thirty minutes ago",
            "character": "worst pain of my life, nothing like my usual tension headaches",
            "associated_symptoms": "neck feels stiff, vomited once, light really bothers me; "
                                    "denies visual aura, denies this happening before",
            "past_medical_history": "no history of migraines, hypertension",
            "family_history": "none that she knows of",
        },
        exam_results={"meningeal_signs": "positive nuchal rigidity",
                      "neuro_exam": "no focal neurological deficit",
                      "vital_signs": "BP 168/96, HR 92, RR 18, Temp 37.0, SpO2 98%"},
        test_results={"ct_head": "subarachnoid blood in the basal cisterns"},
    ),
    # --- Polypharmacy weakness that is NOT hypoglycemia (electrolyte disorder instead) ---
    SyntheticCase(
        case_id="Stress07_PolypharmacyWeaknessHyperkalemia", category="elderly_polypharmacy",
        chief_complaint="feeling weak all over", demographics={"age": 76, "sex": "male"},
        ground_truth_diagnosis="severe_electrolyte_disorder",
        notes="Another elderly polypharmacy weakness case, deliberately NOT hypoglycemia (ACE "
              "inhibitor + potassium-sparing diuretic driving hyperkalemia instead) -- the key "
              "negative control for the hypoglycemia fix: an elderly patient on multiple medications "
              "with weakness must not be reflexively scored toward hypoglycemia just because that "
              "combination of demographics now has stronger matching machinery behind it.",
        answers={
            "onset": "gradually over the past two days",
            "associated_symptoms": "just feel weak and tired, heart feels like it skips sometimes; "
                                    "denies sweating, denies shakiness, denies confusion",
            "past_medical_history": "chronic kidney disease, hypertension, no diabetes",
            "medication": "lisinopril and spironolactone",
        },
        exam_results={"mental_status_exam": "alert, oriented, not diaphoretic",
                      "cardiac_auscultation": "irregular rhythm noted",
                      "vital_signs": "BP 138/84, HR 52, RR 16, Temp 36.7, SpO2 98%"},
        test_results={"glucose_point_of_care": "96 mg/dL", "bmp": "potassium 7.1", "ecg": "peaked T waves"},
    ),
    # --- Weakness with a normal glucose result -- the hypoglycemia hypothesis must be excluded ---
    SyntheticCase(
        case_id="Stress08_NormalGlucoseWeaknessGIBleed", category="negative_finding_centric",
        chief_complaint="feeling weak", demographics={"age": 64, "sex": "female"},
        ground_truth_diagnosis="gi_bleeding",
        notes="Weakness plus a diabetes history and a glucose-lowering medication (the same surface "
              "features as the elderly-polypharmacy hypoglycemia case) but the point-of-care glucose "
              "comes back NORMAL and the real cause is a slow GI bleed -- tests that the new numeric "
              "glucose-evidence logic actually excludes hypoglycemia on a normal value rather than "
              "the medication-class alias alone dragging the diagnosis toward hypoglycemia regardless "
              "of the number.",
        answers={
            "onset": "gradually over about a week",
            "associated_symptoms": "lightheaded when I stand up, feel weak; my stools have looked "
                                    "dark; denies shakiness, denies sweating, denies chest pain",
            "past_medical_history": "type 2 diabetes, takes glipizide",
            "medication": "glipizide and daily aspirin for her heart",
        },
        exam_results={"abdominal_exam": "mild diffuse tenderness, no rebound or guarding",
                      "vital_signs": "BP 96/64, HR 110, RR 18, Temp 36.8, SpO2 97%"},
        test_results={"glucose_point_of_care": "132 mg/dL", "fecal_occult_blood": "positive",
                      "cbc": "low hemoglobin"},
    ),
]
