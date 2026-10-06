"""Second Tier-2 structured-catalog expansion batch (5,000-diagnosis round).

Pushes the Tier-2 structured layer to >=1,500 real, named conditions. Same honesty rules and tuple
form as tier2_catalog_expansion.py: (id, name, category, urgency|None, icd10|None, [aliases]).
No fabricated discriminating tests/findings/thresholds; urgency left None when not well-established.

This batch covers common named subtypes and additional real entities across specialties (fractures,
poisonings, dermatoses, arrhythmia subtypes, GI/hepatobiliary variants, endocrine subtypes, etc.),
plus specific well-known named syndromes. De-dup against everything earlier is enforced by the merger.
"""

from __future__ import annotations

from typing import List

C = List[tuple]


def _mk(prefix: str, category: str, items: List[tuple]) -> C:
    out: C = []
    for slug, name, urgency, icd10, aliases in items:
        out.append((f"{prefix}_{slug}", name, category, urgency, icd10, aliases))
    return out


# Named genetic / inherited syndromes (real entities; ROUTINE unless clearly urgent).
GENETIC = _mk("gen", "genetics", [
    ("achondroplasia", "Achondroplasia", "ROUTINE", "Q77.4", []),
    ("osteogenesis_imperfecta", "Osteogenesis Imperfecta", "URGENT", "Q78.0", []),
    ("alport", "Alport Syndrome", "URGENT", "Q87.81", []),
    ("von_hippel_lindau", "Von Hippel-Lindau Disease", "URGENT", "Q85.83", []),
    ("tuberous_sclerosis", "Tuberous Sclerosis Complex", "URGENT", "Q85.1", []),
    ("neurofibromatosis2", "Neurofibromatosis Type 2", "URGENT", "Q85.02", []),
    ("hereditary_hemorrhagic_telangiectasia", "Hereditary Hemorrhagic Telangiectasia", "URGENT", "I78.0", ["osler-weber-rendu"]),
    ("alpha1_antitrypsin", "Alpha-1 Antitrypsin Deficiency", "URGENT", "E88.01", []),
    ("cystic_fibrosis_gen", "Cystic Fibrosis", "URGENT", "E84.9", []),
    ("duchenne", "Duchenne Muscular Dystrophy", "URGENT", "G71.01", []),
    ("becker_md", "Becker Muscular Dystrophy", "URGENT", "G71.02", []),
    ("myotonic_dystrophy", "Myotonic Dystrophy", "URGENT", "G71.11", []),
    ("spinal_muscular_atrophy", "Spinal Muscular Atrophy", "CRITICAL", "G12.0", ["sma"]),
    ("friedreich_ataxia", "Friedreich Ataxia", "URGENT", "G11.11", []),
    ("charcot_marie_tooth", "Charcot-Marie-Tooth Disease", "ROUTINE", "G60.0", ["cmt"]),
    ("hereditary_angioedema_gen", "Hereditary Angioedema", "CRITICAL", "D84.1", []),
    ("lynch_syndrome", "Lynch Syndrome", "URGENT", "Z15.09", ["hnpcc"]),
    ("familial_adenomatous_polyposis", "Familial Adenomatous Polyposis", "URGENT", "D12.6", ["fap"]),
    ("brca_syndrome", "Hereditary Breast-Ovarian Cancer Syndrome", "URGENT", "Z15.01", ["brca"]),
    ("li_fraumeni", "Li-Fraumeni Syndrome", "URGENT", "Z15.09", []),
    ("gilbert_syndrome", "Gilbert Syndrome", "ROUTINE", "E80.4", []),
    ("dubin_johnson", "Dubin-Johnson Syndrome", "ROUTINE", "E80.6", []),
    ("hereditary_pancreatitis", "Hereditary Pancreatitis", "URGENT", "K86.1", []),
    ("mccune_albright", "McCune-Albright Syndrome", "ROUTINE", "Q78.1", []),
])

# Arrhythmia / conduction subtypes + cardiomyopathy variants (real entities).
CARDIO2 = _mk("cd2", "cardiovascular", [
    ("brugada", "Brugada Syndrome", "CRITICAL", "I49.8", []),
    ("catecholaminergic_vt", "Catecholaminergic Polymorphic VT", "CRITICAL", "I47.2", ["cpvt"]),
    ("short_qt", "Short QT Syndrome", "URGENT", "I45.81", []),
    ("arvc", "Arrhythmogenic Right Ventricular Cardiomyopathy", "URGENT", "I42.8", ["arvc"]),
    ("lqt_acquired", "Acquired Long QT Syndrome", "URGENT", "I45.81", []),
    ("multifocal_atrial_tachycardia", "Multifocal Atrial Tachycardia", "URGENT", "I47.1", ["mat"]),
    ("junctional_rhythm", "Junctional Rhythm", "URGENT", "I49.8", []),
    ("second_degree_av_mobitz1", "Second-Degree AV Block Mobitz I", "URGENT", "I44.1", ["wenckebach"]),
    ("second_degree_av_mobitz2", "Second-Degree AV Block Mobitz II", "CRITICAL", "I44.1", []),
    ("sinus_arrest", "Sinus Arrest", "CRITICAL", "I49.5", []),
    ("torsades", "Torsades de Pointes", "CRITICAL", "I47.2", []),
    ("accelerated_idioventricular", "Accelerated Idioventricular Rhythm", "URGENT", "I49.8", []),
    ("chronic_stable_ihd", "Chronic Ischemic Heart Disease", "ROUTINE", "I25.9", []),
    ("ischemic_cardiomyopathy", "Ischemic Cardiomyopathy", "URGENT", "I25.5", []),
    ("peripartum_cardiomyopathy", "Peripartum Cardiomyopathy", "CRITICAL", "O90.3", []),
    ("high_output_failure", "High-Output Heart Failure", "URGENT", "I50.9", []),
    ("right_heart_failure", "Right Heart Failure", "URGENT", "I50.810", []),
    ("papillary_muscle_rupture", "Papillary Muscle Rupture", "CRITICAL", "I23.5", []),
    ("ventricular_septal_rupture", "Post-MI Ventricular Septal Rupture", "CRITICAL", "I23.2", []),
    ("free_wall_rupture", "Myocardial Free Wall Rupture", "CRITICAL", "I23.3", []),
    ("dresslers", "Dressler Syndrome", "URGENT", "I24.1", ["post-mi pericarditis"]),
    ("septic_emboli", "Septic Emboli", "CRITICAL", "I76", []),
    ("paradoxical_embolism", "Paradoxical Embolism", "CRITICAL", "I74.9", []),
])

# Poisoning / toxicology subtypes (real agents).
TOX2 = _mk("tx2", "toxicology", [
    ("aspirin_toxicity", "Aspirin (Salicylate) Toxicity", "CRITICAL", "T39.011A", []),
    ("acetaminophen_tox2", "Acetaminophen Toxicity", "CRITICAL", "T39.1X1A", []),
    ("nsaid_toxicity", "NSAID Overdose", "URGENT", "T39.391A", []),
    ("warfarin_toxicity", "Warfarin Toxicity", "CRITICAL", "T45.511A", []),
    ("insulin_overdose", "Insulin Overdose", "CRITICAL", "T38.3X1A", []),
    ("sulfonylurea_overdose", "Sulfonylurea Overdose", "CRITICAL", "T38.3X1A", []),
    ("antifreeze", "Ethylene Glycol Poisoning", "CRITICAL", "T52.8X1A", []),
    ("methanol_tox2", "Methanol Poisoning", "CRITICAL", "T51.1X1A", []),
    ("isopropanol", "Isopropanol Poisoning", "URGENT", "T51.2X1A", []),
    ("lead_poisoning", "Lead Poisoning", "URGENT", "T56.0X1A", ["plumbism"]),
    ("mercury_poisoning", "Mercury Poisoning", "URGENT", "T56.1X1A", []),
    ("arsenic_poisoning", "Arsenic Poisoning", "CRITICAL", "T57.0X1A", []),
    ("cyanide_tox2", "Cyanide Poisoning", "CRITICAL", "T57.3X1A", []),
    ("carbon_monoxide_tox2", "Carbon Monoxide Poisoning", "CRITICAL", "T58.91XA", []),
    ("hydrogen_sulfide", "Hydrogen Sulfide Poisoning", "CRITICAL", "T59.6X1A", []),
    ("organophosphate_tox2", "Organophosphate Poisoning", "CRITICAL", "T60.0X1A", []),
    ("caustic_ingestion", "Caustic Ingestion", "CRITICAL", "T54.91XA", []),
    ("digoxin_tox2", "Digoxin Toxicity", "CRITICAL", "T46.0X1A", []),
    ("lithium_tox2", "Lithium Toxicity", "URGENT", "T43.591A", []),
    ("theophylline_toxicity", "Theophylline Toxicity", "CRITICAL", "T48.6X1A", []),
    ("beta_blocker_tox2", "Beta-Blocker Overdose", "CRITICAL", "T44.7X1A", []),
    ("ccb_tox2", "Calcium Channel Blocker Overdose", "CRITICAL", "T46.1X1A", []),
    ("cocaine_toxicity", "Cocaine Toxicity", "CRITICAL", "T40.5X1A", []),
    ("amphetamine_toxicity", "Amphetamine Toxicity", "CRITICAL", "T43.601A", []),
    ("mushroom_poisoning", "Mushroom Poisoning", "CRITICAL", "T62.0X1A", []),
    ("scombroid", "Scombroid Poisoning", "URGENT", "T61.1X1A", []),
    ("ciguatera", "Ciguatera Poisoning", "URGENT", "T61.0X1A", []),
    ("serotonin_tox2", "Serotonin Syndrome", "CRITICAL", "T43.225A", []),
    ("nms_tox2", "Neuroleptic Malignant Syndrome", "CRITICAL", "G21.0", []),
    ("malignant_hyperthermia", "Malignant Hyperthermia", "CRITICAL", "T88.3XXA", []),
    ("anticholinergic_toxicity", "Anticholinergic Toxidrome", "URGENT", "T44.3X1A", []),
    ("cholinergic_toxidrome", "Cholinergic Toxidrome", "CRITICAL", "T44.0X1A", []),
    ("sympathomimetic_toxidrome", "Sympathomimetic Toxidrome", "URGENT", "T50.901A", []),
    ("opioid_toxidrome", "Opioid Toxidrome", "CRITICAL", "T40.2X1A", []),
    ("sedative_toxidrome", "Sedative-Hypnotic Toxidrome", "URGENT", "T42.71XA", []),
])

# GI / hepatobiliary additional real entities.
GI2 = _mk("gi2", "abdominal_gi", [
    ("eosinophilic_gastroenteritis", "Eosinophilic Gastroenteritis", "ROUTINE", "K52.81", []),
    ("whipple_disease", "Whipple Disease", "URGENT", "K90.81", []),
    ("tropical_sprue", "Tropical Sprue", "URGENT", "K90.1", []),
    ("bacterial_overgrowth", "Small Intestinal Bacterial Overgrowth", "ROUTINE", "K90.4", ["sibo"]),
    ("bile_acid_diarrhea", "Bile Acid Diarrhea", "ROUTINE", "K90.49", []),
    ("collagenous_colitis", "Collagenous Colitis", "ROUTINE", "K52.832", []),
    ("lymphocytic_colitis", "Lymphocytic Colitis", "ROUTINE", "K52.831", []),
    ("radiation_enteritis", "Radiation Enteritis", "URGENT", "K52.0", []),
    ("pneumatosis_intestinalis", "Pneumatosis Intestinalis", "URGENT", "K63.89", []),
    ("ogilvie_syndrome", "Ogilvie Syndrome", "URGENT", "K59.81", ["acute colonic pseudo-obstruction"]),
    ("dieulafoy_lesion", "Dieulafoy Lesion", "CRITICAL", "K31.89", []),
    ("gastric_outlet_obstruction", "Gastric Outlet Obstruction", "URGENT", "K31.1", []),
    ("bezoar", "Gastric Bezoar", "URGENT", "T18.2XXA", []),
    ("cholangitis_recurrent", "Recurrent Pyogenic Cholangitis", "CRITICAL", "K83.09", []),
    ("gallstone_ileus", "Gallstone Ileus", "CRITICAL", "K56.3", []),
    ("mirizzi_syndrome", "Mirizzi Syndrome", "URGENT", "K83.1", []),
    ("sphincter_oddi", "Sphincter of Oddi Dysfunction", "ROUTINE", "K83.4", []),
    ("hepatic_vein_thrombosis", "Budd-Chiari Syndrome", "CRITICAL", "I82.0", ["budd-chiari"]),
    ("hepatorenal_syndrome", "Hepatorenal Syndrome", "CRITICAL", "K76.7", []),
    ("hepatopulmonary_syndrome", "Hepatopulmonary Syndrome", "URGENT", "K76.81", []),
    ("nonalcoholic_steatohepatitis", "Nonalcoholic Steatohepatitis", "ROUTINE", "K75.81", ["nash"]),
    ("hemobilia", "Hemobilia", "CRITICAL", "K83.8", []),
    ("gastric_antral_vascular_ectasia", "Gastric Antral Vascular Ectasia", "URGENT", "K31.819", ["gave"]),
    ("caroli_disease", "Caroli Disease", "URGENT", "Q44.5", []),
])

# Endocrine / renal / electrolyte additional entities.
ENDO_RENAL2 = _mk("er2", "endocrine_metabolic", [
    ("subclinical_hypothyroid", "Subclinical Hypothyroidism", "ROUTINE", "E03.9", []),
    ("subclinical_hyperthyroid", "Subclinical Hyperthyroidism", "ROUTINE", "E05.90", []),
    ("euthyroid_sick", "Euthyroid Sick Syndrome", "URGENT", "E07.81", []),
    ("thyroid_cancer_papillary", "Papillary Thyroid Carcinoma", "URGENT", "C73", []),
    ("thyroid_cancer_medullary", "Medullary Thyroid Carcinoma", "URGENT", "C73", []),
    ("hungry_bone", "Hungry Bone Syndrome", "URGENT", "E83.51", []),
    ("tertiary_hyperparathyroid", "Tertiary Hyperparathyroidism", "URGENT", "E21.1", []),
    ("secondary_hyperparathyroid", "Secondary Hyperparathyroidism", "ROUTINE", "E21.1", []),
    ("prolactinoma", "Prolactinoma", "ROUTINE", "D35.2", []),
    ("acromegaly_er2", "Acromegaly", "ROUTINE", "E22.0", []),
    ("sheehan_syndrome", "Sheehan Syndrome", "URGENT", "E23.0", []),
    ("central_diabetes_insipidus", "Central Diabetes Insipidus", "URGENT", "E23.2", []),
    ("nephrogenic_di", "Nephrogenic Diabetes Insipidus", "URGENT", "N25.1", []),
    ("pseudohypoparathyroidism", "Pseudohypoparathyroidism", "ROUTINE", "E20.1", []),
    ("gitelman", "Gitelman Syndrome", "URGENT", "N25.89", []),
    ("bartter", "Bartter Syndrome", "URGENT", "N25.89", []),
    ("liddle", "Liddle Syndrome", "URGENT", "I15.8", []),
    ("fanconi_syndrome", "Fanconi Syndrome", "URGENT", "E72.09", []),
    ("distal_rta", "Distal Renal Tubular Acidosis", "URGENT", "N25.89", ["type 1 rta"]),
    ("proximal_rta", "Proximal Renal Tubular Acidosis", "URGENT", "N25.89", ["type 2 rta"]),
    ("type4_rta", "Type 4 Renal Tubular Acidosis", "URGENT", "N25.89", []),
    ("tumor_induced_osteomalacia", "Tumor-Induced Osteomalacia", "URGENT", "M83.8", []),
    ("milk_alkali", "Milk-Alkali Syndrome", "URGENT", "E83.52", []),
])

# Rheumatology / autoimmune / vasculitis additional entities.
RHEUM2 = _mk("rh2", "rheumatology", [
    ("microscopic_polyangiitis", "Microscopic Polyangiitis", "URGENT", "M31.7", []),
    ("eosinophilic_granulomatosis", "Eosinophilic Granulomatosis with Polyangiitis", "URGENT", "M30.1", ["churg-strauss"]),
    ("henoch_schonlein_rh", "IgA Vasculitis", "URGENT", "D69.0", ["henoch-schonlein purpura"]),
    ("cryoglobulinemic_vasculitis", "Cryoglobulinemic Vasculitis", "URGENT", "D89.1", []),
    ("kawasaki_rh", "Kawasaki Disease", "URGENT", "M30.3", []),
    ("relapsing_polychondritis", "Relapsing Polychondritis", "URGENT", "M94.1", []),
    ("mixed_connective_tissue", "Mixed Connective Tissue Disease", "URGENT", "M35.1", ["mctd"]),
    ("undifferentiated_connective_tissue", "Undifferentiated Connective Tissue Disease", "ROUTINE", "M35.9", []),
    ("adult_onset_stills", "Adult-Onset Still Disease", "URGENT", "M06.1", []),
    ("igg4_disease", "IgG4-Related Disease", "URGENT", "M35.9", []),
    ("sarcoid_arthropathy", "Sarcoid Arthropathy", "ROUTINE", "D86.86", []),
    ("enteropathic_arthritis", "Enteropathic Arthritis", "ROUTINE", "M07.60", []),
    ("crest_syndrome", "Limited Systemic Sclerosis (CREST)", "URGENT", "M34.1", ["crest"]),
    ("eosinophilic_fasciitis", "Eosinophilic Fasciitis", "URGENT", "M35.4", []),
    ("antisynthetase", "Antisynthetase Syndrome", "URGENT", "M33.10", []),
    ("inclusion_body_myositis", "Inclusion Body Myositis", "ROUTINE", "G72.41", []),
    ("felty_syndrome", "Felty Syndrome", "URGENT", "M05.00", []),
    ("caplan_syndrome", "Caplan Syndrome", "URGENT", "J99", []),
])

# Pulmonary / sleep / occupational additional entities.
PULM2 = _mk("pu2", "pulmonary", [
    ("central_sleep_apnea", "Central Sleep Apnea", "URGENT", "G47.31", []),
    ("obesity_hypoventilation", "Obesity Hypoventilation Syndrome", "URGENT", "E66.2", []),
    ("primary_ciliary_dyskinesia", "Primary Ciliary Dyskinesia", "URGENT", "Q34.8", []),
    ("alpha1_lung", "Alpha-1 Antitrypsin Emphysema", "URGENT", "J43.9", []),
    ("lymphangioleiomyomatosis", "Lymphangioleiomyomatosis", "URGENT", "J84.81", ["lam"]),
    ("pulmonary_langerhans", "Pulmonary Langerhans Cell Histiocytosis", "URGENT", "J84.82", []),
    ("cryptogenic_organizing_pneumonia", "Cryptogenic Organizing Pneumonia", "URGENT", "J84.116", ["cop"]),
    ("acute_interstitial_pneumonia", "Acute Interstitial Pneumonia", "CRITICAL", "J84.114", []),
    ("nonspecific_interstitial", "Nonspecific Interstitial Pneumonia", "URGENT", "J84.113", ["nsip"]),
    ("diffuse_alveolar_hemorrhage", "Diffuse Alveolar Hemorrhage", "CRITICAL", "R04.89", []),
    ("goodpasture", "Goodpasture Syndrome", "CRITICAL", "M31.0", ["anti-gbm disease"]),
    ("bronchiectasis_pu2", "Bronchiectasis", "URGENT", "J47.9", []),
    ("allergic_bronchopulmonary_aspergillosis", "Allergic Bronchopulmonary Aspergillosis", "URGENT", "B44.81", ["abpa"]),
    ("tracheobronchomalacia", "Tracheobronchomalacia", "URGENT", "J98.09", []),
    ("pulmonary_sequestration", "Pulmonary Sequestration", "URGENT", "Q33.2", []),
    ("catamenial_pneumothorax", "Catamenial Pneumothorax", "URGENT", "J93.9", []),
    ("re_expansion_edema", "Re-Expansion Pulmonary Edema", "CRITICAL", "J81.0", []),
    ("negative_pressure_edema", "Negative Pressure Pulmonary Edema", "CRITICAL", "J81.0", []),
])

# Neuro additional real entities.
NEURO2 = _mk("nu2", "neuro", [
    ("posterior_reversible_encephalopathy", "Posterior Reversible Encephalopathy Syndrome", "CRITICAL", "I67.83", ["pres"]),
    ("reversible_cerebral_vasoconstriction", "Reversible Cerebral Vasoconstriction Syndrome", "CRITICAL", "I67.841", ["rcvs"]),
    ("central_pontine_myelinolysis", "Osmotic Demyelination Syndrome", "CRITICAL", "G37.2", ["central pontine myelinolysis"]),
    ("anti_nmda_encephalitis", "Anti-NMDA Receptor Encephalitis", "CRITICAL", "G04.81", []),
    ("limbic_encephalitis", "Autoimmune Limbic Encephalitis", "CRITICAL", "G04.81", []),
    ("creutzfeldt_jakob", "Creutzfeldt-Jakob Disease", "URGENT", "A81.00", ["cjd"]),
    ("progressive_multifocal", "Progressive Multifocal Leukoencephalopathy", "CRITICAL", "A81.2", ["pml"]),
    ("subacute_combined_degeneration", "Subacute Combined Degeneration", "URGENT", "E53.8", []),
    ("lambert_eaton", "Lambert-Eaton Myasthenic Syndrome", "URGENT", "G70.81", ["lems"]),
    ("miller_fisher", "Miller Fisher Syndrome", "CRITICAL", "G61.0", []),
    ("chronic_subdural", "Chronic Subdural Hematoma", "URGENT", "I62.03", []),
    ("carotid_cavernous_fistula", "Carotid-Cavernous Fistula", "URGENT", "I77.0", []),
    ("dural_venous_thrombosis", "Dural Venous Sinus Thrombosis", "CRITICAL", "I67.6", []),
    ("spontaneous_intracranial_hypotension", "Spontaneous Intracranial Hypotension", "URGENT", "G96.0", []),
    ("occipital_neuralgia", "Occipital Neuralgia", "ROUTINE", "M54.81", []),
    ("meralgia_paresthetica", "Meralgia Paresthetica", "ROUTINE", "G57.10", []),
    ("tarsal_tunnel", "Tarsal Tunnel Syndrome", "ROUTINE", "G57.50", []),
    ("thoracic_outlet", "Thoracic Outlet Syndrome", "URGENT", "G54.0", []),
    ("stiff_person", "Stiff Person Syndrome", "URGENT", "G25.82", []),
    ("neuroleptic_dystonia", "Acute Dystonic Reaction", "URGENT", "G24.02", []),
    ("akathisia", "Drug-Induced Akathisia", "URGENT", "G25.71", []),
    ("tardive_dyskinesia", "Tardive Dyskinesia", "ROUTINE", "G24.01", []),
])

# Dermatology additional real entities.
DERM2 = _mk("de2", "dermatology", [
    ("bullous_pemphigoid_de2", "Bullous Pemphigoid", "URGENT", "L12.0", []),
    ("pemphigus_foliaceus", "Pemphigus Foliaceus", "URGENT", "L10.2", []),
    ("linear_iga", "Linear IgA Bullous Dermatosis", "URGENT", "L13.8", []),
    ("staph_scalded_skin", "Staphylococcal Scalded Skin Syndrome", "CRITICAL", "L00", ["ssss"]),
    ("acute_generalized_pustulosis", "Acute Generalized Exanthematous Pustulosis", "URGENT", "L27.0", ["agep"]),
    ("sweet_syndrome", "Sweet Syndrome", "URGENT", "L98.2", []),
    ("pyoderma_gangrenosum", "Pyoderma Gangrenosum", "URGENT", "L88", []),
    ("necrolytic_migratory", "Necrolytic Migratory Erythema", "URGENT", "L53.8", []),
    ("calciphylaxis", "Calciphylaxis", "CRITICAL", "E83.59", []),
    ("cutaneous_lupus", "Cutaneous Lupus Erythematosus", "ROUTINE", "L93.0", []),
    ("morphea", "Morphea (Localized Scleroderma)", "ROUTINE", "L94.0", []),
    ("granuloma_annulare", "Granuloma Annulare", "ROUTINE", "L92.0", []),
    ("lichen_sclerosus", "Lichen Sclerosus", "ROUTINE", "L90.0", []),
    ("erythrodermic_psoriasis", "Erythrodermic Psoriasis", "CRITICAL", "L40.8", []),
    ("pustular_psoriasis", "Generalized Pustular Psoriasis", "CRITICAL", "L40.1", []),
    ("bacterial_purpura_fulminans", "Purpura Fulminans", "CRITICAL", "D65", []),
    ("erythema_multiforme_de2", "Erythema Multiforme Major", "URGENT", "L51.1", []),
    ("cutaneous_t_cell_lymphoma", "Cutaneous T-Cell Lymphoma", "URGENT", "C84.A0", []),
])

# Pediatric additional real entities.
PEDS2 = _mk("pd2", "pediatric", [
    ("bronchiolitis_pd2", "Bronchiolitis", "URGENT", "J21.9", []),
    ("epiglottitis_pd2", "Pediatric Epiglottitis", "CRITICAL", "J05.10", []),
    ("bacterial_tracheitis", "Bacterial Tracheitis", "CRITICAL", "J04.10", []),
    ("retropharyngeal_peds", "Retropharyngeal Abscess", "CRITICAL", "J39.0", []),
    ("intussusception_pd2", "Intussusception", "CRITICAL", "K56.1", []),
    ("malrotation_volvulus", "Midgut Volvulus", "CRITICAL", "Q43.1", []),
    ("necrotizing_enterocolitis", "Necrotizing Enterocolitis", "CRITICAL", "P77.9", ["nec"]),
    ("hirschsprung_pd2", "Hirschsprung Disease", "URGENT", "Q43.1", []),
    ("juvenile_dermatomyositis", "Juvenile Dermatomyositis", "URGENT", "M33.00", []),
    ("mis_c", "Multisystem Inflammatory Syndrome in Children", "CRITICAL", "M35.81", ["mis-c"]),
    ("slipped_capital_femoral", "Slipped Capital Femoral Epiphysis", "URGENT", "M93.003", ["scfe"]),
    ("legg_calve_perthes", "Legg-Calve-Perthes Disease", "URGENT", "M91.10", []),
    ("transient_synovitis", "Transient Synovitis of the Hip", "ROUTINE", "M67.30", []),
    ("osgood_schlatter", "Osgood-Schlatter Disease", "ROUTINE", "M92.50", []),
    ("nursemaid_elbow", "Radial Head Subluxation", "URGENT", "S53.032A", ["nursemaid elbow"]),
    ("febrile_seizure_pd2", "Febrile Seizure", "URGENT", "R56.00", []),
    ("infantile_spasms", "Infantile Spasms", "CRITICAL", "G40.821", ["west syndrome"]),
    ("reye_syndrome", "Reye Syndrome", "CRITICAL", "G93.7", []),
    ("rheumatic_fever_pd2", "Acute Rheumatic Fever", "URGENT", "I00", []),
    ("scarlet_fever_pd2", "Scarlet Fever", "URGENT", "A38.9", []),
    ("roseola", "Roseola Infantum", "ROUTINE", "B08.20", []),
    ("fifth_disease", "Erythema Infectiosum", "ROUTINE", "B08.3", ["fifth disease"]),
    ("pertussis_pd2", "Pertussis", "URGENT", "A37.90", []),
])

# Obstetric / gynecologic additional real entities.
OBGYN2 = _mk("og2", "obstetric", [
    ("ectopic_pregnancy_og2", "Ectopic Pregnancy", "CRITICAL", "O00.90", []),
    ("molar_pregnancy", "Hydatidiform Mole", "URGENT", "O01.9", []),
    ("septic_abortion", "Septic Abortion", "CRITICAL", "O08.0", []),
    ("uterine_rupture", "Uterine Rupture", "CRITICAL", "O71.1", []),
    ("cord_prolapse", "Umbilical Cord Prolapse", "CRITICAL", "O69.0XX0", []),
    ("shoulder_dystocia", "Shoulder Dystocia", "CRITICAL", "O66.0", []),
    ("retained_placenta", "Retained Placenta", "URGENT", "O73.0", []),
    ("endometritis_postpartum", "Postpartum Endometritis", "URGENT", "O85", []),
    ("preterm_premature_rupture", "Preterm Premature Rupture of Membranes", "URGENT", "O42.90", ["pprom"]),
    ("intrahepatic_cholestasis", "Intrahepatic Cholestasis of Pregnancy", "URGENT", "O26.611", []),
    ("gestational_hypertension", "Gestational Hypertension", "URGENT", "O13.9", []),
    ("acute_fatty_liver_pregnancy", "Acute Fatty Liver of Pregnancy", "CRITICAL", "O26.61", []),
    ("ovarian_hyperstimulation", "Ovarian Hyperstimulation Syndrome", "URGENT", "N98.1", ["ohss"]),
    ("asherman", "Asherman Syndrome", "ROUTINE", "N85.6", []),
    ("premature_ovarian_insufficiency", "Premature Ovarian Insufficiency", "ROUTINE", "E28.310", []),
    ("vulvodynia", "Vulvodynia", "ROUTINE", "N94.819", []),
    ("lichen_sclerosus_vulvar", "Vulvar Lichen Sclerosus", "ROUTINE", "L90.0", []),
])

# Ophthalmology / ENT additional real entities.
EYE_ENT2 = _mk("ee2", "ophthalmology", [
    ("giant_cell_arteritis_eye", "Arteritic Anterior Ischemic Optic Neuropathy", "CRITICAL", "H47.011", ["aaion"]),
    ("nonarteritic_ischemic_optic", "Nonarteritic Anterior Ischemic Optic Neuropathy", "URGENT", "H47.012", ["naion"]),
    ("hyphema", "Traumatic Hyphema", "URGENT", "H21.00", []),
    ("globe_rupture", "Globe Rupture", "CRITICAL", "S05.30XA", []),
    ("retrobulbar_hemorrhage", "Retrobulbar Hemorrhage", "CRITICAL", "H05.239", []),
    ("thyroid_eye_disease", "Thyroid Eye Disease", "URGENT", "H06.2X9", ["graves ophthalmopathy"]),
    ("chemical_burn_eye", "Ocular Chemical Burn", "CRITICAL", "T26.60XA", []),
    ("uveitis_anterior", "Anterior Uveitis", "URGENT", "H20.00", ["iritis"]),
    ("posterior_uveitis", "Posterior Uveitis", "URGENT", "H30.90", []),
    ("optic_neuritis_ee2", "Optic Neuritis", "URGENT", "H46.9", []),
    ("mucormycosis", "Rhino-Orbital-Cerebral Mucormycosis", "CRITICAL", "B46.5", []),
    ("malignant_otitis_externa", "Malignant Otitis Externa", "CRITICAL", "H60.20", []),
    ("sudden_hearing_ee2", "Sudden Sensorineural Hearing Loss", "URGENT", "H91.20", []),
    ("nasal_septal_hematoma", "Nasal Septal Hematoma", "URGENT", "S00.30XA", []),
    ("angioedema_airway", "Airway Angioedema", "CRITICAL", "T78.3XXA", []),
    ("foreign_body_airway", "Airway Foreign Body", "CRITICAL", "T17.900A", []),
])

# Environmental / miscellaneous real entities.
ENV2 = _mk("ev2", "environmental", [
    ("heat_exhaustion", "Heat Exhaustion", "URGENT", "T67.5XXA", []),
    ("heat_cramps", "Heat Cramps", "ROUTINE", "T67.2XXA", []),
    ("acute_mountain_sickness", "Acute Mountain Sickness", "URGENT", "T70.29XA", ["ams"]),
    ("high_altitude_cerebral_edema", "High-Altitude Cerebral Edema", "CRITICAL", "T70.29XA", ["hace"]),
    ("radiation_sickness", "Acute Radiation Syndrome", "CRITICAL", "T66.XXXA", []),
    ("caisson_disease", "Decompression Sickness", "CRITICAL", "T70.3XXA", []),
    ("marine_envenomation", "Marine Envenomation", "URGENT", "T63.591A", []),
    ("scorpion_sting", "Scorpion Envenomation", "URGENT", "T63.2X1A", []),
    ("spider_bite", "Spider Bite Envenomation", "URGENT", "T63.3", []),
    ("hymenoptera_sting", "Hymenoptera Sting Reaction", "URGENT", "T63.441A", []),
    ("frostnip", "Frostnip", "ROUTINE", "T33.90", []),
    ("chilblains", "Chilblains (Pernio)", "ROUTINE", "T69.1XXA", []),
    ("trench_foot", "Immersion Foot (Trench Foot)", "URGENT", "T69.0XXA", []),
])


ALL_EXPANSION2_GROUPS = [
    GENETIC, CARDIO2, TOX2, GI2, ENDO_RENAL2, RHEUM2, PULM2, NEURO2, DERM2,
    PEDS2, OBGYN2, EYE_ENT2, ENV2,
]
