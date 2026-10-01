# 272-entry reference and diagnostic-rule inventory

**This revision does not enable 272 autonomous diagnoses.** It preserves the existing 68
rule-supported entries and adds 204 sourced reference candidates for differential exploration.
No clinically validated accuracy claim exists for either group. Unverified candidates cannot
be promoted by an LLM confidence band or by changing a catalog flag.

| Capability | Count | Validation status |
|---|---:|---|
| Existing rule-supported entries | 68 | Internal synthetic/mock regressions only |
| Added MedlinePlus reference candidates | 204 | Source/title lookup checked; diagnostic accuracy unmeasured |
| Total entries | 272 | A combined inventory, not 272 validated diagnoses |
| Independently clinically validated entries | 0 | External cases and live model evaluation still required |

## Source and import

Source: MedlinePlus, National Library of Medicine. Public-domain **health-topic summaries**
from the October 1, 2026 XML export are included, with titles, aliases, topic IDs, links and
attribution. This import excludes A.D.A.M. encyclopedia content, drug monographs and images.
See [MedlinePlus XML](https://medlineplus.gov/xml.html) and
[reuse terms](https://medlineplus.gov/about/using/usingcontent/).

The selected titles are explicitly listed in `nova_agent/knowledge/reference_candidates/selection.txt`.
They span infectious, neurologic, endocrine, hematologic, autoimmune, oncologic and other
conditions. They do not duplicate a canonical name or alias in the existing rule catalog.
Selection is an engineering scope choice, not a prevalence ranking or clinical coverage standard.

`manifest.json` records the official export URL, generation timestamp, SHA-256 of the uncompressed
XML, selected-title hash and generated catalog hash. The selected content is packaged offline;
no patient observations are sent to MedlinePlus. Re-importing requires the retained source XML
(the publisher rotates downloadable export versions):

```bash
python scripts/import_medline_candidates.py --xml /path/to/mplus_topics_2026-10-01.xml --source-url https://medlineplus.gov/xml/mplus_topics_compressed_2026-10-01.zip
python -m nova_agent.knowledge.reference_catalog
```

## Runtime behavior and guards

Affirmed observations retrieve at most three relevant references using lexical BM25 ranking.
Each includes its source, attribution and `reference_only` status. Nonspecific single-token,
negated, family-history and tentative queries are filtered conservatively. Each excerpt is
bounded to 1,100 characters. Lexical ranking is not a diagnostic probability and can retrieve
irrelevant material; English topic vocabulary does not establish broad Korean language support.

References are stored separately from patient observations and never enter `all_findings_text`
or deterministic disease scores. The model prompt labels them as educational context, not
patient evidence. An introduced reference candidate stays LOW confidence and cannot bypass
final-diagnosis validation. The turn-limit path also refuses to combine a deterministic key
with a different LLM-proposed disease name, fixing a separate consistency bug.

`NOVA_REFERENCE_CANDIDATES=0` disables added reference retrieval. It does not enable unvalidated
candidates for autonomous diagnosis. Corrupt catalogs, foreign/encyclopedia source URLs and
self-promoting metadata are rejected. The real-model runner hashes the reference catalog and
configuration to prevent resuming results under silently changed source context.

## Validation and unfinished work

This revision passed 604 unit tests and standalone submission/source-sync checks. The existing
mock regression gate passed all 205 scored cases, with three additional unscored cases.

`evaluation/reference_catalog_results.json` reports 204 title lookups and provenance checks.
**This is not 204 diagnostic test cases or evidence of new-disease accuracy.**
`evaluation/catalog_results.json` reports the unchanged, existing 205 scored synthetic cases
and three additional unscored cases, with the 68/204 split and new-disease accuracy explicitly null.

Before any new condition becomes autonomous, it needs reviewed disease-specific evidence and
exclusions, valid examinations/test mappings, independent positive/negative/near-neighbor and
atypical cases, and live-model evaluation against the frozen baseline. The source library alone
cannot supply those missing labels or establish non-inferiority. No API key or independently
adjudicated new-condition case set was available for this revision. Thus the user's requested
fourfold expansion of **verified diagnostic ability** remains incomplete; only the reference
inventory has reached fourfold size.

## Added reference candidates

| Candidate | Source topic |
|---|---|
| Acne | [MedlinePlus 124](https://medlineplus.gov/acne.html) |
| Acoustic Neuroma | [MedlinePlus 1624](https://medlineplus.gov/acousticneuroma.html) |
| Acute Lymphocytic Leukemia | [MedlinePlus 1437](https://medlineplus.gov/acutelymphocyticleukemia.html) |
| Acute Myeloid Leukemia | [MedlinePlus 5622](https://medlineplus.gov/acutemyeloidleukemia.html) |
| Addison Disease | [MedlinePlus 1233](https://medlineplus.gov/addisondisease.html) |
| Adhesions | [MedlinePlus 3920](https://medlineplus.gov/adhesions.html) |
| Alcohol Use Disorder (AUD) | [MedlinePlus 120](https://medlineplus.gov/alcoholusedisorderaud.html) |
| Alpha-1 Antitrypsin Deficiency | [MedlinePlus 1692](https://medlineplus.gov/alpha1antitrypsindeficiency.html) |
| Alzheimer's Disease | [MedlinePlus 22](https://medlineplus.gov/alzheimersdisease.html) |
| Amyloidosis | [MedlinePlus 5273](https://medlineplus.gov/amyloidosis.html) |
| Amyotrophic Lateral Sclerosis | [MedlinePlus 135](https://medlineplus.gov/amyotrophiclateralsclerosis.html) |
| Anal Cancer | [MedlinePlus 3791](https://medlineplus.gov/analcancer.html) |
| Ankylosing Spondylitis | [MedlinePlus 143](https://medlineplus.gov/ankylosingspondylitis.html) |
| Aortic Aneurysm | [MedlinePlus 4931](https://medlineplus.gov/aorticaneurysm.html) |
| Aplastic Anemia | [MedlinePlus 5955](https://medlineplus.gov/aplasticanemia.html) |
| Arteriovenous Malformations | [MedlinePlus 4553](https://medlineplus.gov/arteriovenousmalformations.html) |
| Aspergillosis | [MedlinePlus 5628](https://medlineplus.gov/aspergillosis.html) |
| Atherosclerosis | [MedlinePlus 5400](https://medlineplus.gov/atherosclerosis.html) |
| Athlete's Foot | [MedlinePlus 151](https://medlineplus.gov/athletesfoot.html) |
| Attention Deficit Hyperactivity Disorder | [MedlinePlus 152](https://medlineplus.gov/attentiondeficithyperactivitydisorder.html) |
| Autism Spectrum Disorder | [MedlinePlus 153](https://medlineplus.gov/autismspectrumdisorder.html) |
| Behcet's Syndrome | [MedlinePlus 1084](https://medlineplus.gov/behcetssyndrome.html) |
| Bell's Palsy | [MedlinePlus 1219](https://medlineplus.gov/bellspalsy.html) |
| Bile Duct Cancer | [MedlinePlus 5905](https://medlineplus.gov/bileductcancer.html) |
| Bipolar Disorder | [MedlinePlus 600](https://medlineplus.gov/bipolardisorder.html) |
| Bladder Cancer | [MedlinePlus 163](https://medlineplus.gov/bladdercancer.html) |
| Bone Cancer | [MedlinePlus 169](https://medlineplus.gov/bonecancer.html) |
| Botulism | [MedlinePlus 1557](https://medlineplus.gov/botulism.html) |
| Brain Aneurysm | [MedlinePlus 4926](https://medlineplus.gov/brainaneurysm.html) |
| Brain Tumors | [MedlinePlus 173](https://medlineplus.gov/braintumors.html) |
| Breast Cancer | [MedlinePlus 3](https://medlineplus.gov/breastcancer.html) |
| Bursitis | [MedlinePlus 1230](https://medlineplus.gov/bursitis.html) |
| C. diff Infections | [MedlinePlus 4617](https://medlineplus.gov/cdiffinfections.html) |
| Campylobacter Infections | [MedlinePlus 6046](https://medlineplus.gov/campylobacterinfections.html) |
| Cardiomyopathy | [MedlinePlus 3754](https://medlineplus.gov/cardiomyopathy.html) |
| Carotid Artery Disease | [MedlinePlus 4063](https://medlineplus.gov/carotidarterydisease.html) |
| Carpal Tunnel Syndrome | [MedlinePlus 179](https://medlineplus.gov/carpaltunnelsyndrome.html) |
| Cat Scratch Disease | [MedlinePlus 4320](https://medlineplus.gov/catscratchdisease.html) |
| Cataract | [MedlinePlus 116](https://medlineplus.gov/cataract.html) |
| Celiac Disease | [MedlinePlus 897](https://medlineplus.gov/celiacdisease.html) |
| Cerebral Palsy | [MedlinePlus 180](https://medlineplus.gov/cerebralpalsy.html) |
| Cervical Cancer | [MedlinePlus 111](https://medlineplus.gov/cervicalcancer.html) |
| Chickenpox | [MedlinePlus 182](https://medlineplus.gov/chickenpox.html) |
| Chikungunya | [MedlinePlus 6345](https://medlineplus.gov/chikungunya.html) |
| Chlamydia Infections | [MedlinePlus 1307](https://medlineplus.gov/chlamydiainfections.html) |
| Cholera | [MedlinePlus 5709](https://medlineplus.gov/cholera.html) |
| Chronic Kidney Disease | [MedlinePlus 5987](https://medlineplus.gov/chronickidneydisease.html) |
| Chronic Lymphocytic Leukemia | [MedlinePlus 87](https://medlineplus.gov/chroniclymphocyticleukemia.html) |
| Chronic Myeloid Leukemia | [MedlinePlus 5624](https://medlineplus.gov/chronicmyeloidleukemia.html) |
| Cirrhosis | [MedlinePlus 190](https://medlineplus.gov/cirrhosis.html) |
| Colonic Polyps | [MedlinePlus 3134](https://medlineplus.gov/colonicpolyps.html) |
| Colorectal Cancer | [MedlinePlus 88](https://medlineplus.gov/colorectalcancer.html) |
| Complex Regional Pain Syndrome | [MedlinePlus 382](https://medlineplus.gov/complexregionalpainsyndrome.html) |
| Concussion | [MedlinePlus 4867](https://medlineplus.gov/concussion.html) |
| Congenital Heart Defects | [MedlinePlus 198](https://medlineplus.gov/congenitalheartdefects.html) |
| Coronary Artery Disease | [MedlinePlus 1276](https://medlineplus.gov/coronaryarterydisease.html) |
| COVID-19 (Coronavirus Disease 2019) | [MedlinePlus 3181](https://medlineplus.gov/covid19coronavirusdisease2019.html) |
| Creutzfeldt-Jakob Disease | [MedlinePlus 1242](https://medlineplus.gov/creutzfeldtjakobdisease.html) |
| Crohn's Disease | [MedlinePlus 119](https://medlineplus.gov/crohnsdisease.html) |
| Croup | [MedlinePlus 6292](https://medlineplus.gov/croup.html) |
| Cryptosporidiosis | [MedlinePlus 1591](https://medlineplus.gov/cryptosporidiosis.html) |
| Cushing's Syndrome | [MedlinePlus 4318](https://medlineplus.gov/cushingssyndrome.html) |
| Cystic Fibrosis | [MedlinePlus 203](https://medlineplus.gov/cysticfibrosis.html) |
| Cytomegalovirus Infections | [MedlinePlus 3980](https://medlineplus.gov/cytomegalovirusinfections.html) |
| Dengue | [MedlinePlus 3104](https://medlineplus.gov/dengue.html) |
| Depression | [MedlinePlus 113](https://medlineplus.gov/depression.html) |
| Diabetes Insipidus | [MedlinePlus 3046](https://medlineplus.gov/diabetesinsipidus.html) |
| Diabetes Type 1 | [MedlinePlus 1339](https://medlineplus.gov/diabetestype1.html) |
| Diabetes Type 2 | [MedlinePlus 5930](https://medlineplus.gov/diabetestype2.html) |
| Diphtheria | [MedlinePlus 1512](https://medlineplus.gov/diphtheria.html) |
| Down Syndrome | [MedlinePlus 217](https://medlineplus.gov/downsyndrome.html) |
| Dystonia | [MedlinePlus 1252](https://medlineplus.gov/dystonia.html) |
| Ebola | [MedlinePlus 6202](https://medlineplus.gov/ebola.html) |
| Eczema | [MedlinePlus 1215](https://medlineplus.gov/eczema.html) |
| Encephalitis | [MedlinePlus 241](https://medlineplus.gov/encephalitis.html) |
| Endocarditis | [MedlinePlus 4316](https://medlineplus.gov/endocarditis.html) |
| Endometriosis | [MedlinePlus 243](https://medlineplus.gov/endometriosis.html) |
| Enlarged Prostate (BPH) | [MedlinePlus 6196](https://medlineplus.gov/enlargedprostatebph.html) |
| Eosinophilic Esophagitis | [MedlinePlus 6967](https://medlineplus.gov/eosinophilicesophagitis.html) |
| Epilepsy | [MedlinePlus 244](https://medlineplus.gov/epilepsy.html) |
| Esophageal Cancer | [MedlinePlus 245](https://medlineplus.gov/esophagealcancer.html) |
| Fibromyalgia | [MedlinePlus 32](https://medlineplus.gov/fibromyalgia.html) |
| Fifth Disease | [MedlinePlus 1609](https://medlineplus.gov/fifthdisease.html) |
| G6PD Deficiency | [MedlinePlus 6155](https://medlineplus.gov/g6pddeficiency.html) |
| Gallbladder Cancer | [MedlinePlus 4645](https://medlineplus.gov/gallbladdercancer.html) |
| Gallstones | [MedlinePlus 4643](https://medlineplus.gov/gallstones.html) |
| Genital Herpes | [MedlinePlus 5863](https://medlineplus.gov/genitalherpes.html) |
| Genital Warts | [MedlinePlus 4322](https://medlineplus.gov/genitalwarts.html) |
| Giant Cell Arteritis | [MedlinePlus 5615](https://medlineplus.gov/giantcellarteritis.html) |
| Giardia Infections | [MedlinePlus 1258](https://medlineplus.gov/giardiainfections.html) |
| Glaucoma | [MedlinePlus 42](https://medlineplus.gov/glaucoma.html) |
| Gonorrhea | [MedlinePlus 3019](https://medlineplus.gov/gonorrhea.html) |
| Granulomatosis with Polyangiitis | [MedlinePlus 1447](https://medlineplus.gov/granulomatosiswithpolyangiitis.html) |
| Guillain-Barre Syndrome | [MedlinePlus 1234](https://medlineplus.gov/guillainbarresyndrome.html) |
| Hantavirus Infections | [MedlinePlus 3217](https://medlineplus.gov/hantavirusinfections.html) |
| Hay Fever | [MedlinePlus 4746](https://medlineplus.gov/hayfever.html) |
| Head and Neck Cancer | [MedlinePlus 330](https://medlineplus.gov/headandneckcancer.html) |
| Hemochromatosis | [MedlinePlus 1220](https://medlineplus.gov/hemochromatosis.html) |
| Hemophilia | [MedlinePlus 3115](https://medlineplus.gov/hemophilia.html) |
| Hemorrhoids | [MedlinePlus 1226](https://medlineplus.gov/hemorrhoids.html) |
| Hepatitis A | [MedlinePlus 1686](https://medlineplus.gov/hepatitisa.html) |
| Hepatitis B | [MedlinePlus 1687](https://medlineplus.gov/hepatitisb.html) |
| Hepatitis C | [MedlinePlus 1286](https://medlineplus.gov/hepatitisc.html) |
| Hernia | [MedlinePlus 283](https://medlineplus.gov/hernia.html) |
| Herniated Disk | [MedlinePlus 284](https://medlineplus.gov/herniateddisk.html) |
| Hiatal Hernia | [MedlinePlus 4370](https://medlineplus.gov/hiatalhernia.html) |
| Hidradenitis Suppurativa | [MedlinePlus 4363](https://medlineplus.gov/hidradenitissuppurativa.html) |
| High Blood Pressure | [MedlinePlus 34](https://medlineplus.gov/highbloodpressure.html) |
| Histoplasmosis | [MedlinePlus 5632](https://medlineplus.gov/histoplasmosis.html) |
| HIV | [MedlinePlus 1](https://medlineplus.gov/hiv.html) |
| Hodgkin Lymphoma | [MedlinePlus 1262](https://medlineplus.gov/hodgkinlymphoma.html) |
| Huntington's Disease | [MedlinePlus 1218](https://medlineplus.gov/huntingtonsdisease.html) |
| Hydrocephalus | [MedlinePlus 607](https://medlineplus.gov/hydrocephalus.html) |
| Impetigo | [MedlinePlus 1253](https://medlineplus.gov/impetigo.html) |
| Infectious Mononucleosis | [MedlinePlus 298](https://medlineplus.gov/infectiousmononucleosis.html) |
| Insomnia | [MedlinePlus 6055](https://medlineplus.gov/insomnia.html) |
| Interstitial Cystitis | [MedlinePlus 1274](https://medlineplus.gov/interstitialcystitis.html) |
| Irritable Bowel Syndrome | [MedlinePlus 614](https://medlineplus.gov/irritablebowelsyndrome.html) |
| Juvenile Arthritis | [MedlinePlus 1292](https://medlineplus.gov/juvenilearthritis.html) |
| Kawasaki Disease | [MedlinePlus 4921](https://medlineplus.gov/kawasakidisease.html) |
| Kidney Cancer | [MedlinePlus 301](https://medlineplus.gov/kidneycancer.html) |
| Lactose Intolerance | [MedlinePlus 898](https://medlineplus.gov/lactoseintolerance.html) |
| Lead Poisoning | [MedlinePlus 608](https://medlineplus.gov/leadpoisoning.html) |
| Legionnaires' Disease | [MedlinePlus 1526](https://medlineplus.gov/legionnairesdisease.html) |
| Lewy Body Dementia | [MedlinePlus 4070](https://medlineplus.gov/lewybodydementia.html) |
| Listeria Infections | [MedlinePlus 1241](https://medlineplus.gov/listeriainfections.html) |
| Liver Cancer | [MedlinePlus 309](https://medlineplus.gov/livercancer.html) |
| Lung Cancer | [MedlinePlus 86](https://medlineplus.gov/lungcancer.html) |
| Lupus | [MedlinePlus 82](https://medlineplus.gov/lupus.html) |
| Lyme Disease | [MedlinePlus 84](https://medlineplus.gov/lymedisease.html) |
| Lymphedema | [MedlinePlus 4610](https://medlineplus.gov/lymphedema.html) |
| Macular Degeneration | [MedlinePlus 313](https://medlineplus.gov/maculardegeneration.html) |
| Malaria | [MedlinePlus 315](https://medlineplus.gov/malaria.html) |
| Measles | [MedlinePlus 318](https://medlineplus.gov/measles.html) |
| Melanoma | [MedlinePlus 321](https://medlineplus.gov/melanoma.html) |
| Meniere's Disease | [MedlinePlus 1674](https://medlineplus.gov/menieresdisease.html) |
| Mesothelioma | [MedlinePlus 4014](https://medlineplus.gov/mesothelioma.html) |
| Mitral Valve Prolapse | [MedlinePlus 1605](https://medlineplus.gov/mitralvalveprolapse.html) |
| Mpox | [MedlinePlus 3229](https://medlineplus.gov/mpox.html) |
| Multiple Myeloma | [MedlinePlus 332](https://medlineplus.gov/multiplemyeloma.html) |
| Multiple Sclerosis | [MedlinePlus 83](https://medlineplus.gov/multiplesclerosis.html) |
| Mumps | [MedlinePlus 334](https://medlineplus.gov/mumps.html) |
| Myasthenia Gravis | [MedlinePlus 336](https://medlineplus.gov/myastheniagravis.html) |
| Myelodysplastic Syndromes | [MedlinePlus 5550](https://medlineplus.gov/myelodysplasticsyndromes.html) |
| Myositis | [MedlinePlus 1617](https://medlineplus.gov/myositis.html) |
| Norovirus Infections | [MedlinePlus 6103](https://medlineplus.gov/norovirusinfections.html) |
| Obsessive-Compulsive Disorder | [MedlinePlus 471](https://medlineplus.gov/obsessivecompulsivedisorder.html) |
| Osteoarthritis | [MedlinePlus 1250](https://medlineplus.gov/osteoarthritis.html) |
| Osteonecrosis | [MedlinePlus 1647](https://medlineplus.gov/osteonecrosis.html) |
| Osteoporosis | [MedlinePlus 37](https://medlineplus.gov/osteoporosis.html) |
| Ovarian Cancer | [MedlinePlus 348](https://medlineplus.gov/ovariancancer.html) |
| Paget's Disease of Bone | [MedlinePlus 1607](https://medlineplus.gov/pagetsdiseaseofbone.html) |
| Pancreatic Cancer | [MedlinePlus 469](https://medlineplus.gov/pancreaticcancer.html) |
| Parkinson's Disease | [MedlinePlus 85](https://medlineplus.gov/parkinsonsdisease.html) |
| Pemphigus | [MedlinePlus 4948](https://medlineplus.gov/pemphigus.html) |
| Peptic Ulcer | [MedlinePlus 357](https://medlineplus.gov/pepticulcer.html) |
| Peripheral Arterial Disease | [MedlinePlus 4083](https://medlineplus.gov/peripheralarterialdisease.html) |
| Pituitary Tumors | [MedlinePlus 5328](https://medlineplus.gov/pituitarytumors.html) |
| Polycystic Ovary Syndrome | [MedlinePlus 5912](https://medlineplus.gov/polycysticovarysyndrome.html) |
| Polymyalgia Rheumatica | [MedlinePlus 1382](https://medlineplus.gov/polymyalgiarheumatica.html) |
| Porphyria | [MedlinePlus 1249](https://medlineplus.gov/porphyria.html) |
| Post-Traumatic Stress Disorder | [MedlinePlus 367](https://medlineplus.gov/posttraumaticstressdisorder.html) |
| Prostate Cancer | [MedlinePlus 112](https://medlineplus.gov/prostatecancer.html) |
| Psoriasis | [MedlinePlus 373](https://medlineplus.gov/psoriasis.html) |
| Psoriatic Arthritis | [MedlinePlus 6159](https://medlineplus.gov/psoriaticarthritis.html) |
| Pulmonary Fibrosis | [MedlinePlus 378](https://medlineplus.gov/pulmonaryfibrosis.html) |
| Pulmonary Hypertension | [MedlinePlus 3634](https://medlineplus.gov/pulmonaryhypertension.html) |
| Rabies | [MedlinePlus 523](https://medlineplus.gov/rabies.html) |
| Raynaud Phenomenon | [MedlinePlus 381](https://medlineplus.gov/raynaudphenomenon.html) |
| Retinal Detachment | [MedlinePlus 6141](https://medlineplus.gov/retinaldetachment.html) |
| Rheumatoid Arthritis | [MedlinePlus 1232](https://medlineplus.gov/rheumatoidarthritis.html) |
| Rickets | [MedlinePlus 3898](https://medlineplus.gov/rickets.html) |
| Rosacea | [MedlinePlus 1247](https://medlineplus.gov/rosacea.html) |
| Rubella | [MedlinePlus 387](https://medlineplus.gov/rubella.html) |
| Salmonella Infections | [MedlinePlus 1213](https://medlineplus.gov/salmonellainfections.html) |
| Sarcoidosis | [MedlinePlus 389](https://medlineplus.gov/sarcoidosis.html) |
| Scabies | [MedlinePlus 1254](https://medlineplus.gov/scabies.html) |
| Schizophrenia | [MedlinePlus 392](https://medlineplus.gov/schizophrenia.html) |
| Scleroderma | [MedlinePlus 394](https://medlineplus.gov/scleroderma.html) |
| Sickle Cell Disease | [MedlinePlus 402](https://medlineplus.gov/sicklecelldisease.html) |
| Sinusitis | [MedlinePlus 404](https://medlineplus.gov/sinusitis.html) |
| Sjogren's Syndrome | [MedlinePlus 918](https://medlineplus.gov/sjogrenssyndrome.html) |
| Sleep Apnea | [MedlinePlus 2784](https://medlineplus.gov/sleepapnea.html) |
| Spinal Stenosis | [MedlinePlus 412](https://medlineplus.gov/spinalstenosis.html) |
| Stomach Cancer | [MedlinePlus 419](https://medlineplus.gov/stomachcancer.html) |
| Syphilis | [MedlinePlus 3017](https://medlineplus.gov/syphilis.html) |
| Testicular Cancer | [MedlinePlus 434](https://medlineplus.gov/testicularcancer.html) |
| Tetanus | [MedlinePlus 435](https://medlineplus.gov/tetanus.html) |
| Thalassemia | [MedlinePlus 4239](https://medlineplus.gov/thalassemia.html) |
| Thyroid Cancer | [MedlinePlus 438](https://medlineplus.gov/thyroidcancer.html) |
| Tonsillitis | [MedlinePlus 6440](https://medlineplus.gov/tonsillitis.html) |
| Tourette Syndrome | [MedlinePlus 442](https://medlineplus.gov/tourettesyndrome.html) |
| Toxoplasmosis | [MedlinePlus 1214](https://medlineplus.gov/toxoplasmosis.html) |
| Trichomoniasis | [MedlinePlus 4325](https://medlineplus.gov/trichomoniasis.html) |
| Trigeminal Neuralgia | [MedlinePlus 2729](https://medlineplus.gov/trigeminalneuralgia.html) |
| Tuberculosis | [MedlinePlus 41](https://medlineplus.gov/tuberculosis.html) |
| Ulcerative Colitis | [MedlinePlus 446](https://medlineplus.gov/ulcerativecolitis.html) |
| Uterine Cancer | [MedlinePlus 449](https://medlineplus.gov/uterinecancer.html) |
| Uterine Fibroids | [MedlinePlus 1222](https://medlineplus.gov/uterinefibroids.html) |
| Valley Fever | [MedlinePlus 5634](https://medlineplus.gov/valleyfever.html) |
| Vitiligo | [MedlinePlus 1306](https://medlineplus.gov/vitiligo.html) |
| West Nile Virus | [MedlinePlus 1377](https://medlineplus.gov/westnilevirus.html) |
| Whooping Cough | [MedlinePlus 461](https://medlineplus.gov/whoopingcough.html) |
| Zika Virus | [MedlinePlus 6342](https://medlineplus.gov/zikavirus.html) |
