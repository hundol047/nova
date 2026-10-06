"""Round E development test cases (spec: fresh cases for the new architectural defect classes --
generic phrase false-positive matching, specific-vs-generic severity conflict, reproductive-age
vague emergency, multilingual routing, morphology negative controls, zero-evidence terminal
behavior, discriminator-priority behavior. This is a DEVELOPMENT set: MAY be iterated against, but
is explicitly NOT Blind v15 and never reused as/reworded into it. Distinct wording and disease
pairings from Blind v14's own cases (which covered PE, ectopic pregnancy, anaphylaxis, and a
Korean/Japanese ACS/appendicitis pairing) -- proves each fix generalizes rather than only patching
the specific cases that exposed it.
"""

from __future__ import annotations

from evaluation.cases import SyntheticCase

GENERALIZATION_DEV_CASES_ROUND_E = [
    # --- generic_phrase_false_positive_matching: GERD's "worse after meals" must not spuriously
    #     match unrelated "worse when I breathe" wording for a genuinely different diagnosis ---
    SyntheticCase(
        case_id="DevE01_PleuriticPainNotGERD", category="generic_phrase_false_positive_matching",
        chief_complaint="sharp chest pain that's worse when I take a deep breath, started after a long flight",
        demographics={"age": 54, "sex": "female"}, ground_truth_diagnosis="pulmonary_embolism",
        notes="Deliberately shares the generic relational word 'worse' with GERD's own typical_feature "
              "'worse after meals' (and 'chest pain'), but never mentions meals at all -- tests that the "
              "distinguishing-token gate (matching.py) doesn't let GERD win on generic overlap while PE's "
              "own genuine risk factor (long flight) and pleuritic quality carry the real diagnosis.",
        answers={"onset": "sudden, a few hours after landing", "associated_symptoms": "short of breath, heart racing",
                  "social_history": "just got off a 10-hour flight"},
        exam_results={"vital_signs": "BP 118/74, HR 112, RR 24, Temp 37.0, SpO2 91%",
                      "extremity_exam": "right calf mildly swollen and tender"},
        test_results={"d_dimer": "elevated D-dimer", "ct_chest_angio": "filling defect in the right pulmonary artery"},
    ),

    # --- specific_vs_generic_severity_conflict: PE (specific findings) must outrank sepsis (only
    #     shares generic deranged-vitals wording) -- a THIRD pairing distinct from the anaphylaxis-
    #     vs-sepsis and DKA-vs-sepsis pairings already covered by unit tests ---
    SyntheticCase(
        case_id="DevE02_MassivePEnotSepsis", category="specific_vs_generic_severity_conflict",
        chief_complaint="sudden severe shortness of breath and chest pain, feels like he might pass out",
        demographics={"age": 61, "sex": "male"}, ground_truth_diagnosis="pulmonary_embolism",
        notes="Deranged vitals (tachycardia, tachypnea, hypotension) alone are equally consistent with "
              "sepsis, but only PE has real disease-specific support here (pleuritic pain, recent surgery "
              "risk factor, confirmatory imaging) -- sepsis must not win purely on shared generic severity.",
        answers={"onset": "sudden, about 30 minutes ago", "character": "sharp, worse with breathing",
                  "past_medical_history": "hip replacement surgery six days ago", "associated_symptoms": "denies fever, denies chills"},
        exam_results={"vital_signs": "BP 86/54, HR 126, RR 30, Temp 36.9, SpO2 88%",
                      "extremity_exam": "left calf swollen and tender"},
        test_results={"d_dimer": "elevated D-dimer", "ct_chest_angio": "large filling defect in the main pulmonary artery"},
    ),

    # --- reproductive_age_vague_emergency: contextual ectopic-pregnancy activation, fresh wording
    #     distinct from Blind v14's own "stomach bug" framing ---
    SyntheticCase(
        case_id="DevE03_VagueReproductiveAgeEmergency", category="reproductive_age_vague_emergency",
        chief_complaint="just feel really off today, some discomfort low on my right side",
        demographics={"age": 27, "sex": "female"}, ground_truth_diagnosis="ectopic_pregnancy",
        notes="No explicit pregnancy/gynecologic language in the chief complaint at all -- relies on "
              "nova_agent/contextual_safety.py's contextual activation (reproductive-age + abdominal/"
              "pelvic symptoms) to even reach the candidate pool, then real objective evidence to confirm.",
        answers={"onset": "on and off since yesterday", "location": "lower right side of her belly",
                  "character": "crampy, comes and goes",
                  "associated_symptoms": "some light spotting, denies fever, denies vomiting",
                  "social_history": "sexually active, period is about seven weeks late",
                  "past_medical_history": "no significant past medical history"},
        exam_results={"abdominal_exam": "mild right lower quadrant tenderness, no rebound",
                      "vital_signs": "BP 100/62, HR 106, RR 16, Temp 36.8, SpO2 99%"},
        test_results={"beta_hcg": "positive beta-hCG", "pelvic_ultrasound": "no intrauterine pregnancy, right adnexal mass"},
    ),

    # --- multilingual_routing: fresh Korean+English pairing, distinct diagnosis from Blind v14's
    #     Korean ACS / Japanese appendicitis cases ---
    SyntheticCase(
        case_id="DevE04_KoreanMixedPyelonephritis", category="multilingual_routing",
        chief_complaint="열이 나고 오른쪽 옆구리가 아파요, started yesterday",
        demographics={"age": 32, "sex": "female"}, ground_truth_diagnosis="pyelonephritis",
        notes="Korean for 'have a fever and my right flank hurts' plus English onset -- fresh wording "
              "and a fresh diagnosis (pyelonephritis, not ACS/appendicitis) from Blind v14's own "
              "mixed-language cases, proving the multilingual concept layer generalizes.",
        answers={"associated_symptoms": "burning when urinating, chills",
                  "past_medical_history": "no significant past medical history"},
        exam_results={"vital_signs": "BP 106/66, HR 104, RR 18, Temp 38.8, SpO2 98%",
                      "costovertebral_tenderness": "positive on the right"},
        test_results={"urinalysis": "positive leukocyte esterase and nitrites"},
    ),

    # --- morphology_negative_control: exertional/exertion must still match; an unrelated word
    #     sharing the same first characters must not collide ---
    SyntheticCase(
        case_id="DevE05_ExertionalAnginaNegativeControl", category="morphology_negative_control",
        chief_complaint="tight chest discomfort that comes on with exertion, goes away with rest",
        demographics={"age": 62, "sex": "male"}, ground_truth_diagnosis="acute_coronary_syndrome",
        notes="Relies on the exertional/exertion irregular-pair override (matching.py's "
              "_IRREGULAR_STEM_OVERRIDES) still working correctly after this round removed the "
              "6-character truncation fallback that pair used to rely on.",
        answers={"onset": "started 40 minutes ago while climbing stairs, hasn't fully resolved",
                  "associated_symptoms": "sweaty, mild nausea", "past_medical_history": "high cholesterol, smoker"},
        exam_results={"vital_signs": "BP 146/90, HR 96, RR 18, Temp 36.9, SpO2 97%"},
        test_results={"ecg": "ST depression in the lateral leads", "troponin": "elevated troponin"},
    ),

    # --- zero_evidence_terminal_behavior: genuinely nothing matches -- must degrade safely, never
    #     scored for a single "right answer", and must carry the new forced/zero-evidence metadata ---
    SyntheticCase(
        case_id="DevE06_ZeroEvidenceTerminalBehavior", category="zero_evidence_terminal_behavior",
        scoring_expected=False,
        chief_complaint="hard to explain, just not myself the last little while",
        demographics={"age": 45, "sex": "male"}, ground_truth_diagnosis="tension_headache",
        notes="Every follow-up left unanswered (bland defaults throughout) -- checked only for safe, "
              "graceful termination (reaches a final answer before the turn budget runs out, never "
              "crashes) and that PatientState's new forced/zero-evidence diagnosis flags come out "
              "True, never for a single 'correct' diagnosis (scoring_expected=False).",
        answers={}, exam_results={}, test_results={},
    ),

    # --- discriminator_priority: a plausible critical diagnosis should get its own high-specificity
    #     confirmatory test prioritized well before generic/low-value workup ---
    SyntheticCase(
        case_id="DevE07_DiscriminatorPriorityMeningitis", category="discriminator_priority",
        chief_complaint="bad headache, neck feels stiff, and I've been running a fever",
        demographics={"age": 24, "sex": "male"}, ground_truth_diagnosis="meningitis",
        notes="Tests that the agent prioritizes meningitis's own high-value discriminators (meningeal "
              "signs exam, lumbar puncture) reasonably early rather than spending many turns on broad, "
              "low-specificity workup first, once a critical diagnosis is plausible.",
        answers={"onset": "started yesterday evening, worsening", "associated_symptoms": "bright lights bother him, denies rash"},
        exam_results={"meningeal_signs": "positive nuchal rigidity", "vital_signs": "BP 110/70, HR 104, RR 18, Temp 39.0, SpO2 98%"},
        test_results={"lumbar_puncture": "CSF pleocytosis, elevated protein"},
    ),
]
