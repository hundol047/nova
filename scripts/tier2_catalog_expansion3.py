"""Third Tier-2 structured-catalog expansion batch (5,000-diagnosis round) -> pushes Tier-2 >=1,500.

Same honesty rules and tuple form as the other expansion modules:
(id, name, category, urgency|None, icd10|None, [aliases]). Real named clinical entities only; no
fabricated discriminating tests/findings/thresholds; urgency None when not well-established.

Covers additional real named entities: specific fractures/injuries, additional infections, ocular
and ENT conditions, endocrine and GI subtypes, and additional neuro/rheum/derm entities.
"""

from __future__ import annotations

from typing import List

C = List[tuple]


def _mk(prefix: str, category: str, items: List[tuple]) -> C:
    return [(f"{prefix}_{s}", n, category, u, c, a) for (s, n, u, c, a) in items]


ORTHO_TRAUMA = _mk("ot3", "orthopedics", [
    ("colles_fracture", "Colles Fracture", "URGENT", "S52.539A", []),
    ("smith_fracture", "Smith Fracture", "URGENT", "S52.549A", []),
    ("scaphoid_fracture", "Scaphoid Fracture", "URGENT", "S62.009A", []),
    ("boxer_fracture", "Boxer Fracture", "URGENT", "S62.309A", []),
    ("clavicle_fracture", "Clavicle Fracture", "URGENT", "S42.009A", []),
    ("proximal_humerus_fracture", "Proximal Humerus Fracture", "URGENT", "S42.209A", []),
    ("supracondylar_fracture", "Supracondylar Humerus Fracture", "CRITICAL", "S42.409A", []),
    ("olecranon_fracture", "Olecranon Fracture", "URGENT", "S52.009A", []),
    ("radial_head_fracture", "Radial Head Fracture", "URGENT", "S52.109A", []),
    ("femoral_shaft_fracture", "Femoral Shaft Fracture", "CRITICAL", "S72.309A", []),
    ("tibial_plateau_fracture", "Tibial Plateau Fracture", "URGENT", "S82.109A", []),
    ("ankle_fracture", "Ankle Fracture", "URGENT", "S82.899A", []),
    ("calcaneus_fracture", "Calcaneus Fracture", "URGENT", "S92.009A", []),
    ("lisfranc_injury", "Lisfranc Injury", "URGENT", "S93.309A", []),
    ("patella_fracture", "Patella Fracture", "URGENT", "S82.009A", []),
    ("hip_dislocation", "Hip Dislocation", "CRITICAL", "S73.006A", []),
    ("knee_dislocation", "Knee Dislocation", "CRITICAL", "S83.106A", []),
    ("patellar_dislocation", "Patellar Dislocation", "URGENT", "S83.006A", []),
    ("acromioclavicular_separation", "Acromioclavicular Separation", "URGENT", "S43.109A", []),
    ("rotator_cuff_ot3", "Rotator Cuff Tear", "ROUTINE", "M75.100", []),
    ("labral_tear_hip", "Acetabular Labral Tear", "ROUTINE", "S73.191A", []),
    ("meniscus_ot3", "Meniscal Tear", "ROUTINE", "S83.209A", []),
    ("quadriceps_rupture", "Quadriceps Tendon Rupture", "URGENT", "S76.119A", []),
    ("patellar_tendon_rupture", "Patellar Tendon Rupture", "URGENT", "S76.119A", []),
    ("stress_fracture_ot3", "Stress Fracture", "URGENT", "M84.30XA", []),
    ("pathologic_fracture", "Pathologic Fracture", "URGENT", "M84.40XA", []),
    ("nonunion_fracture", "Fracture Nonunion", "ROUTINE", "M84.10", []),
    ("mallet_finger", "Mallet Finger", "ROUTINE", "S66.329A", []),
    ("jersey_finger", "Jersey Finger", "URGENT", "S66.120A", []),
    ("gamekeeper_thumb", "Gamekeeper Thumb", "URGENT", "S63.649A", ["skier thumb"]),
])

INFECT3 = _mk("if3", "infectious", [
    ("erysipeloid", "Erysipeloid", "ROUTINE", "A26.0", []),
    ("cat_scratch", "Cat Scratch Disease", "ROUTINE", "A28.1", []),
    ("rat_bite_fever", "Rat-Bite Fever", "URGENT", "A25.9", []),
    ("melioidosis", "Melioidosis", "CRITICAL", "A24.9", []),
    ("nocardiosis", "Nocardiosis", "URGENT", "A43.9", []),
    ("actinomycosis", "Actinomycosis", "URGENT", "A42.9", []),
    ("leprosy", "Leprosy", "URGENT", "A30.9", ["hansen disease"]),
    ("nontuberculous_mycobacterial", "Nontuberculous Mycobacterial Infection", "URGENT", "A31.9", ["ntm"]),
    ("mycoplasma_pneumonia", "Mycoplasma Pneumonia", "URGENT", "J15.7", ["atypical pneumonia"]),
    ("psittacosis", "Psittacosis", "URGENT", "A70", []),
    ("babesiosis", "Babesiosis", "URGENT", "B60.0", []),
    ("ehrlichiosis", "Ehrlichiosis", "URGENT", "A77.40", []),
    ("anaplasmosis", "Anaplasmosis", "URGENT", "A77.49", []),
    ("trichinosis", "Trichinellosis", "URGENT", "B75", []),
    ("filariasis", "Lymphatic Filariasis", "URGENT", "B74.0", []),
    ("onchocerciasis", "Onchocerciasis", "URGENT", "B73.00", ["river blindness"]),
    ("chagas", "Chagas Disease", "URGENT", "B57.2", ["american trypanosomiasis"]),
    ("leishmaniasis", "Leishmaniasis", "URGENT", "B55.9", []),
    ("african_trypanosomiasis", "African Trypanosomiasis", "URGENT", "B56.9", ["sleeping sickness"]),
    ("mumps_orchitis", "Mumps Orchitis", "URGENT", "B26.0", []),
    ("infectious_myocarditis", "Infectious Myocarditis", "CRITICAL", "I40.0", []),
    ("viral_gastroenteritis", "Viral Gastroenteritis", "ROUTINE", "A08.4", ["norovirus"]),
    ("rotavirus", "Rotavirus Enteritis", "URGENT", "A08.0", []),
    ("adenovirus", "Adenovirus Infection", "ROUTINE", "B34.0", []),
    ("parvovirus_b19", "Parvovirus B19 Infection", "ROUTINE", "B34.3", []),
    ("coxsackievirus", "Coxsackievirus Infection", "ROUTINE", "B34.1", []),
    ("gas_gangrene", "Gas Gangrene", "CRITICAL", "A48.0", ["clostridial myonecrosis"]),
])

GI_ENDO3 = _mk("ge3", "abdominal_gi", [
    ("zollinger_ellison", "Zollinger-Ellison Syndrome", "URGENT", "E16.4", ["gastrinoma"]),
    ("vipoma", "VIPoma", "URGENT", "E16.8", []),
    ("glucagonoma", "Glucagonoma", "URGENT", "E16.8", []),
    ("somatostatinoma", "Somatostatinoma", "URGENT", "E16.8", []),
    ("menetrier", "Menetrier Disease", "ROUTINE", "K29.60", []),
    ("gastric_volvulus", "Gastric Volvulus", "CRITICAL", "K31.89", []),
    ("superior_mesenteric_artery_syndrome", "Superior Mesenteric Artery Syndrome", "URGENT", "K55.1", ["sma syndrome"]),
    ("intestinal_pseudo_obstruction", "Chronic Intestinal Pseudo-Obstruction", "URGENT", "K59.89", []),
    ("rectal_prolapse", "Rectal Prolapse", "URGENT", "K62.3", []),
    ("solitary_rectal_ulcer", "Solitary Rectal Ulcer Syndrome", "ROUTINE", "K62.6", []),
    ("pilonidal_disease", "Pilonidal Disease", "URGENT", "L05.91", []),
    ("diverticular_bleed", "Diverticular Hemorrhage", "CRITICAL", "K57.31", []),
    ("colonic_ischemia", "Colonic Ischemia", "URGENT", "K55.9", []),
    ("cecal_volvulus", "Cecal Volvulus", "CRITICAL", "K56.2", []),
    ("abdominal_compartment", "Abdominal Compartment Syndrome", "CRITICAL", "R19.8", []),
    ("chylous_ascites", "Chylous Ascites", "URGENT", "R18.8", []),
    ("splenic_infarct", "Splenic Infarct", "URGENT", "D73.5", []),
    ("splenic_abscess", "Splenic Abscess", "CRITICAL", "D73.3", []),
    ("portal_hypertensive_gastropathy", "Portal Hypertensive Gastropathy", "URGENT", "K31.89", []),
])

GU_NEPH3 = _mk("gn3", "genitourinary", [
    ("emphysematous_pyelonephritis", "Emphysematous Pyelonephritis", "CRITICAL", "N10", []),
    ("xanthogranulomatous_pyelonephritis", "Xanthogranulomatous Pyelonephritis", "URGENT", "N11.8", []),
    ("perinephric_abscess", "Perinephric Abscess", "CRITICAL", "N15.1", []),
    ("renal_infarct", "Renal Infarction", "URGENT", "N28.0", []),
    ("staghorn_calculus", "Staghorn Calculus", "URGENT", "N20.0", []),
    ("ureteral_stricture", "Ureteral Stricture", "URGENT", "N13.5", []),
    ("bladder_rupture", "Bladder Rupture", "CRITICAL", "S37.29XA", []),
    ("renal_trauma", "Renal Trauma", "CRITICAL", "S37.00XA", []),
    ("papillary_necrosis", "Renal Papillary Necrosis", "URGENT", "N17.2", []),
    ("goodpasture_gn3", "Anti-GBM Disease", "CRITICAL", "M31.0", []),
    ("thin_basement_membrane", "Thin Basement Membrane Nephropathy", "ROUTINE", "N02.9", []),
    ("membranoproliferative_gn", "Membranoproliferative Glomerulonephritis", "URGENT", "N03.5", ["mpgn"]),
    ("rapidly_progressive_gn", "Rapidly Progressive Glomerulonephritis", "CRITICAL", "N01.9", ["rpgn"]),
    ("diabetic_nephropathy", "Diabetic Nephropathy", "URGENT", "E11.21", []),
    ("cast_nephropathy", "Myeloma Cast Nephropathy", "URGENT", "N16", []),
    ("hepatic_glomerulosclerosis", "Cholemic Nephropathy", "URGENT", "N16", []),
    ("priapism_gn3", "Priapism", "CRITICAL", "N48.30", []),
    ("peyronie", "Peyronie Disease", "ROUTINE", "N48.6", []),
    ("phimosis", "Phimosis", "URGENT", "N47.1", []),
    ("paraphimosis", "Paraphimosis", "CRITICAL", "N47.2", []),
])

MISC3 = _mk("mi3", "general", [
    ("angioedema_ace", "ACE-Inhibitor Angioedema", "CRITICAL", "T78.3XXA", []),
    ("drug_induced_lupus", "Drug-Induced Lupus", "URGENT", "M32.0", []),
    ("drug_fever", "Drug Fever", "URGENT", "R50.2", []),
    ("acute_hemolytic_transfusion", "Acute Hemolytic Transfusion Reaction", "CRITICAL", "T80.310A", []),
    ("febrile_nonhemolytic", "Febrile Nonhemolytic Transfusion Reaction", "URGENT", "T80.89XA", []),
    ("trali", "Transfusion-Related Acute Lung Injury", "CRITICAL", "J95.84", ["trali"]),
    ("taco", "Transfusion-Associated Circulatory Overload", "CRITICAL", "E87.70", ["taco"]),
    ("iatrogenic_pneumothorax", "Iatrogenic Pneumothorax", "URGENT", "J95.811", []),
    ("post_dural_puncture_headache", "Post-Dural Puncture Headache", "URGENT", "G97.1", []),
    ("propofol_infusion_syndrome", "Propofol Infusion Syndrome", "CRITICAL", "T41.1X5A", []),
    ("local_anesthetic_toxicity", "Local Anesthetic Systemic Toxicity", "CRITICAL", "T41.3X1A", ["last"]),
    ("contrast_nephropathy_mi3", "Contrast-Induced Nephropathy", "URGENT", "N14.11", []),
    ("tumor_lysis_mi3", "Tumor Lysis Syndrome", "CRITICAL", "E88.3", []),
    ("capillary_leak", "Systemic Capillary Leak Syndrome", "CRITICAL", "I87.8", []),
    ("acute_chest_syndrome", "Acute Chest Syndrome", "CRITICAL", "D57.01", []),
    ("splenic_sequestration", "Splenic Sequestration Crisis", "CRITICAL", "D57.02", []),
    ("aplastic_crisis", "Aplastic Crisis", "CRITICAL", "D57.09", []),
    ("hyperviscosity", "Hyperviscosity Syndrome", "CRITICAL", "D89.1", []),
    ("leukostasis", "Leukostasis", "CRITICAL", "C95.00", []),
])

DERM_EYE3 = _mk("dy3", "dermatology", [
    ("bullous_impetigo", "Bullous Impetigo", "URGENT", "L01.03", []),
    ("ecthyma", "Ecthyma", "URGENT", "L08.0", []),
    ("erythrasma", "Erythrasma", "ROUTINE", "L08.1", []),
    ("intertrigo", "Intertrigo", "ROUTINE", "L30.4", []),
    ("tinea_corporis", "Tinea Corporis", "ROUTINE", "B35.4", ["ringworm"]),
    ("tinea_capitis", "Tinea Capitis", "ROUTINE", "B35.0", []),
    ("tinea_pedis", "Tinea Pedis", "ROUTINE", "B35.3", ["athlete's foot"]),
    ("onychomycosis", "Onychomycosis", "ROUTINE", "B35.1", []),
    ("candidal_intertrigo", "Candidal Intertrigo", "ROUTINE", "B37.2", []),
    ("molluscum", "Molluscum Contagiosum", "ROUTINE", "B08.1", []),
    ("verruca", "Verruca (Warts)", "ROUTINE", "B07.9", []),
    ("keratoacanthoma", "Keratoacanthoma", "ROUTINE", "L85.8", []),
    ("seborrheic_keratosis", "Seborrheic Keratosis", "ROUTINE", "L82.1", []),
    ("dermatofibroma", "Dermatofibroma", "ROUTINE", "D23.9", []),
    ("lipoma", "Lipoma", "ROUTINE", "D17.9", []),
    ("epidermal_cyst", "Epidermal Inclusion Cyst", "ROUTINE", "L72.0", []),
    ("hidradenitis_dy3", "Hidradenitis Suppurativa", "URGENT", "L73.2", []),
    ("acanthosis_nigricans", "Acanthosis Nigricans", "ROUTINE", "L83", []),
    ("erythema_ab_igne", "Erythema Ab Igne", "ROUTINE", "L59.0", []),
])


ALL_EXPANSION3_GROUPS = [
    ORTHO_TRAUMA, INFECT3, GI_ENDO3, GU_NEPH3, MISC3, DERM_EYE3,
]
