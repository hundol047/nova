"""Round D development test cases (spec: NEW cases -- distinct wording from Blind v13, wider
diagnosis spread, and explicitly NOT Blind v14 -- built to exercise the four architectural defect
classes this round's chief_complaint.py taxonomy audit / specificity-precedence / morphology
normalizer / zero-evidence-fallback fixes address). This is a DEVELOPMENT set: used locally while
building and regression-checking those fixes, never frozen, never reused as (or reworded into)
Blind v14, and never hand-tuned against by adjusting a fix until a specific case here passes --
each case is an independent clinical vignette, not derived from any blind-set case's wording.

One case per required category:
  - unrouted_common_complaint: a common presentation whose wording previously matched no
    chief-complaint routing tag at all (closed by the systematic Tier-1 taxonomy audit).
  - morphological_variant: relies on the conservative suffix-stripping normalizer (a KB alias in
    one grammatical form, the patient's own wording in another).
  - generic_vs_specific_conflict: both a generic umbrella symptom word and a more specific,
    clinically-decisive alternative are present in the same sentence -- the specific one must win.
  - zero_evidence_presentation: genuinely nothing (no symptom/risk/objective signal at all) --
    checked for graceful UNKNOWN_PRESENTATION handling, never scored for a single "right answer".
  - multi_concept_complaint: two distinct, co-occurring routing concepts in one presentation.
  - lay_language_complaint: pure colloquial phrasing, no clinical terminology anywhere.
  - objective_evidence_after_vague_complaint: the presenting sentence alone routes to nothing
    diagnostically decisive; a later objective lab/imaging result is what actually carries the case.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

GENERALIZATION_DEV_CASES_ROUND_D = [
    # --- unrouted_common_complaint: gastroenteritis via the new "diarrhea" routing tag ---
    SyntheticCase(
        case_id="Dev01_UnroutedDiarrheaGastroenteritis", category="unrouted_common_complaint",
        chief_complaint="I can't stop running to the bathroom, it's all watery",
        demographics={"age": 27, "sex": "female"},
        ground_truth_diagnosis="gastroenteritis",
        notes="Presenting complaint is pure diarrhea with no mention of the word 'abdominal' or "
              "'pain' at all -- before this round's taxonomy audit, 'diarrhea' had no chief-"
              "complaint routing tag of its own, so a presentation like this (no accompanying "
              "abdominal-pain language) could fail to route to anything. Distinct wording and a "
              "distinct disease from the existing gastroenteritis case in "
              "generalization_cases_v2.py's TravelersGastroenteritis vignette.",
        answers={
            "onset": "since last night, maybe 12 hours now",
            "associated_symptoms": "watery stool maybe eight times today, some queasy stomach; "
                                    "denies blood in stool, denies high fever, denies severe pain",
            "social_history": "ate at a new food truck two days ago",
        },
        exam_results={"abdominal_exam": "mild diffuse tenderness, no rebound, no guarding, "
                                         "no rigidity",
                      "vital_signs": "BP 112/70, HR 92, RR 16, Temp 37.4, SpO2 99%"},
        test_results={},
    ),
    # --- morphological_variant: "spins"/"faint" (spin/spinning, faint/fainting stem family) ---
    SyntheticCase(
        case_id="Dev02_MorphologyOrthostaticSpinning", category="morphological_variant",
        chief_complaint="everything spins when I stand up too fast, feels like I might faint",
        demographics={"age": 71, "sex": "male"},
        ground_truth_diagnosis="orthostatic_hypotension",
        notes="The KB's orthostatic_hypotension entry describes 'lightheadedness on standing' -- "
              "this case deliberately uses 'spins'/'faint' (relying on the conservative morphology "
              "normalizer's spin<->spinning and faint<->fainting stemming, not exact KB wording) "
              "and improves promptly on sitting, distinguishing it from BPPV (positional, not "
              "standing-triggered) and from true cardiac syncope (no palpitations, no chest pain).",
        answers={
            "onset": "happens every time he stands up quickly from a chair",
            "relieving": "gets better within a few seconds if he sits back down",
            "associated_symptoms": "just the spinning feeling and almost fainting; denies chest "
                                    "pain, denies palpitations before the episodes, denies slurred "
                                    "speech, denies focal weakness",
            "medication": "takes a water pill for blood pressure",
            "social_history": "hasn't been drinking much water this week",
        },
        exam_results={"vital_signs": "BP 96/60 standing, 128/78 sitting, HR 86, RR 16, Temp 36.7, SpO2 98%",
                      "neuro_exam": "no focal neurological deficit"},
        test_results={},
    ),
    # --- generic_vs_specific_conflict: generic "weakness" wording alongside a genuine focal deficit ---
    SyntheticCase(
        case_id="Dev03_GenericWeaknessMaskingFocalStroke", category="generic_vs_specific_conflict",
        chief_complaint="just feeling really weak all over since this morning",
        demographics={"age": 66, "sex": "female"},
        ground_truth_diagnosis="ischemic_stroke",
        notes="Opens with the same generic 'weakness' language a benign fatigue/dehydration case "
              "would use, but the follow-up reveals a genuine FOCAL deficit (one-sided arm "
              "weakness plus a drooping mouth) -- the specific focal_weakness signal must take "
              "precedence over the generic umbrella tag rather than being diluted by it (spec: a "
              "generic alias must never shadow/steal a presentation from a more specific concept "
              "when real specific evidence exists). Distinct wording from the existing focal-"
              "weakness stroke cases in this repo's held-out/generalization sets.",
        answers={
            "onset": "sudden, noticed it about 40 minutes ago",
            "associated_symptoms": "her right arm feels weak and heavy and won't cooperate, and "
                                    "the right side of her mouth is drooping; denies headache, "
                                    "denies chest pain, denies loss of consciousness",
            "past_medical_history": "atrial fibrillation, hypertension",
            "medication": "supposed to take a blood thinner but missed the last few doses",
        },
        exam_results={"neuro_exam": "right facial droop, right arm drift, mild dysarthria",
                      "vital_signs": "BP 172/96, HR 90 irregularly irregular, RR 16, Temp 36.8, SpO2 97%"},
        test_results={"ct_head": "acute infarct in the left MCA territory",
                      "glucose_point_of_care": "104 mg/dL"},
    ),
    # --- zero_evidence_presentation: genuinely nothing matches anything ---
    SyntheticCase(
        case_id="Dev04_ZeroEvidenceVagueMalaise", category="zero_evidence_presentation",
        scoring_expected=False,
        chief_complaint="I just don't feel like myself lately, hard to explain",
        demographics={"age": 33, "sex": "male"},
        ground_truth_diagnosis="tension_headache",
        notes="No single right answer here by design -- every follow-up question is left "
              "unanswered (falls to the bland default_answer/default_exam_result/"
              "default_test_result for everything), so no symptom, risk, medication, history, "
              "imaging, or objective evidence ever matches anything at all. Checked only for safe, "
              "graceful handling (reaches SOME final diagnosis before the turn budget runs out, "
              "never crashes, never critical-misses) -- never for a single 'correct' diagnosis, "
              "since a genuinely zero-evidence presentation has none. The ground_truth_diagnosis "
              "field is a nominal placeholder only (scoring_expected=False means it is never "
              "compared against the agent's output).",
        answers={},
        exam_results={},
        test_results={},
    ),
    # --- multi_concept_complaint: two distinct, co-occurring routing concepts (neck_stiffness + fever) ---
    SyntheticCase(
        case_id="Dev05_MultiConceptFeverNeckStiffness", category="multi_concept_complaint",
        chief_complaint="bad headache, my neck feels stiff, and I've been running a fever since this morning",
        demographics={"age": 22, "sex": "female"},
        ground_truth_diagnosis="meningitis",
        notes="Deliberately names three concurrent concepts (headache, the new neck_stiffness "
              "routing tag, fever) in a single sentence -- tests multi-concept extraction pulling "
              "in all three rather than only the first-matched or highest-scoring single tag, so "
              "meningitis (tagged under all three) is reachable even though no ONE concept alone "
              "is decisive.",
        answers={
            "onset": "started yesterday evening, getting worse",
            "associated_symptoms": "bright lights bother her eyes and she felt a bit confused "
                                    "talking to her roommate; denies rash, denies recent travel",
            "past_medical_history": "no significant past medical history",
        },
        exam_results={"meningeal_signs": "positive nuchal rigidity, positive Kernig's sign",
                      "vital_signs": "BP 108/68, HR 108, RR 20, Temp 39.1, SpO2 97%",
                      "mental_status_exam": "mildly confused, oriented to person only"},
        test_results={"lumbar_puncture": "CSF pleocytosis, elevated protein",
                      "blood_culture": "pending"},
    ),
    # --- lay_language_complaint: pure colloquial phrasing, no clinical terms at all ---
    SyntheticCase(
        case_id="Dev06_LayLanguagePEAfterFlight", category="lay_language_complaint",
        chief_complaint="can't catch my breath and there was blood when I spit after coughing",
        demographics={"age": 52, "sex": "male"},
        ground_truth_diagnosis="pulmonary_embolism",
        notes="Every clinical concept is expressed in pure lay phrasing -- 'can't catch my breath' "
              "(dyspnea), 'blood when I spit after coughing' (hemoptysis, via the tightened "
              "2-content-word blood-anchored alias this round's own false-positive fix left in "
              "place), 'sharp pain that gets worse when I breathe in' (pleuritic chest pain), "
              "'long flight' (immobilization risk factor) -- never the KB's own clinical wording.",
        answers={
            "onset": "sudden, about two hours ago",
            "character": "sharp pain that gets worse when I breathe in",
            "associated_symptoms": "coughing up a little blood when I spit, heart feels like it's "
                                    "racing; denies leg pain, denies fever",
            "social_history": "just got off a 14-hour flight yesterday",
        },
        exam_results={"vital_signs": "BP 116/74, HR 118, RR 26, Temp 37.0, SpO2 89%",
                      "lung_auscultation": "clear bilaterally",
                      "extremity_exam": "mild right calf swelling"},
        test_results={"d_dimer": "elevated D-dimer", "ct_chest_angio": "filling defect in the right pulmonary artery"},
    ),
    # --- objective_evidence_after_vague_complaint: the presenting sentence alone routes to nothing decisive ---
    SyntheticCase(
        case_id="Dev07_VagueComplaintHypoglycemiaOnLabs", category="objective_evidence_after_vague_complaint",
        chief_complaint="I feel spacey and slow to answer things, hard to put my finger on it",
        demographics={"age": 74, "sex": "male"},
        ground_truth_diagnosis="hypoglycemia",
        notes="The presenting chief complaint itself ('spacey and slow to answer') is deliberately "
              "vague and names no clinical concept at all; altered_mental_status routing only "
              "arrives one turn later via the associated_symptoms answer, and the diagnosis only "
              "becomes DECISIVE once the objective point-of-care glucose result is elicited -- "
              "exercising candidate_generator.py's numeric-glucose objective_finding pool path "
              "end-to-end (not just a routing label), on top of ordinary symptom-based routing "
              "rather than instead of it. Deliberately distinct medication class (sulfonylurea, "
              "not insulin), demographic, trigger, and symptom wording from this repo's other "
              "hypoglycemia cases (Weakness01's elderly-polypharmacy confusion, Stress01's "
              "young-adult adrenergic presentation, Stress02's non-diabetic alcoholic presentation).",
        answers={
            "onset": "family noticed it about an hour ago, came on gradually",
            "associated_symptoms": "a little trembly, and his family says he seems confused, "
                                    "slow to respond to questions; denies chest pain, denies "
                                    "palpitations, denies focal weakness",
            "past_medical_history": "type 2 diabetes",
            "medication": "started glipizide last week, missed lunch today",
        },
        exam_results={"mental_status_exam": "somnolent but arousable, slow to answer, oriented to person only",
                      "vital_signs": "BP 128/78, HR 96, RR 16, Temp 36.6, SpO2 98%",
                      "neuro_exam": "no focal neurological deficit"},
        test_results={"glucose_point_of_care": "41 mg/dL"},
    ),
]
