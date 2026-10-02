# 1,020-entry candidate inventory and reusable evaluation archive (historical)

Current inventory and model status: [1,451 entries](CATALOG_1451_AND_MODEL.md). Counts below
describe the earlier revision; current report files have since been updated.

The previous 680 entries are preserved and 340 Genetics condition references are added:
**68 diagnostic rules + 204 health-topic references + 748 Genetics references = 1,020 entries**.
This is 1.5x candidate coverage, not 1,020 validated autonomous diagnoses or increased clinical
accuracy. All 952 reference candidates remain reference-only and ineligible for final diagnosis.

The added cohort comes from the same retained official MedlinePlus Genetics XML snapshot,
with its original source hash. Only condition descriptions/synonyms are imported. Gene pages,
chromosome information pages and external database text are excluded. Existing condition identities and descriptions are preserved; trailing source-title
whitespace is normalized (including one prior title). New selections use stable SHA-256 name ordering,
skipping normalized name/alias collisions against existing and newly selected entries. This
emphasizes genetic/rare conditions, not prevalence or clinical priority. Related subtypes may
still overlap semantically; entry counts are not a mutually exclusive clinical ontology.

Source: MedlinePlus, National Library of Medicine.
API documentation: https://medlineplus.gov/about/developers/geneticsdatafilesapi/
Reuse terms: https://medlineplus.gov/about/using/usingcontent/
No patient data is sent to MedlinePlus. The catalog is bundled offline.

## Saved evaluation data

`evaluation/learning_archive/` contains content-addressed, immutable JSON snapshots. Each
snapshot includes the full evaluated synthetic case, expected labels, observed final diagnosis,
pass/fail/unscored status, case-set hashes and the complete report. The previous 680-entry mock
report is archived before expansion, preserving 205 passes plus three unscored cases. The new
1,020-entry run creates another snapshot with its own catalog/source fingerprints.

`evaluation.catalog_regression` now archives every completed run automatically, including
failed runs. Identical payloads reuse the same file; changed results create new files. Writes
are atomic, and a conflicting/corrupt existing file is never overwritten. Incomplete runs do
not create a completed snapshot. No data is loaded by inference, and no training job is started.
The CLI accepts only built-in synthetic cases, not external patient data. Labels and case hashes
are checked, and pass counts are recomputed before saving.

All records have `training_eligible: false` and `clinical_validation: false`. Passed tuning/
expanded development cases receive a training-candidate review route; held-out/evaluation and
unscored data stay evaluation-only. This distinction prevents automatic test-set contamination
and treating mock success as clinical supervision. Failed cases are preserved to avoid a
success-only view of the system. A separately reviewed training export and independent test
set are still required for actual fine-tuning.

```bash
# Runs the complete mock gate and automatically writes an immutable snapshot.
python -m evaluation.catalog_regression --save-json evaluation/catalog_results.json

# Archive an existing complete report against unchanged built-in case definitions.
python -m evaluation.learning_archive --report evaluation/catalog_results.json
```

Snapshots committed in this PR are retained in Git history. Future local evaluation runs save
to the same directory by default. GitHub CI uploads snapshots as run-specific artifacts with
**90-day retention**, not permanent storage; retain needed future snapshots in version control
or a durable authorized store before expiry. Evaluation is triggered by the existing CI or the
commands above, not a continuously running background learner. The workflow changes take
effect only on branches containing them and are not proof a scheduled training service exists.

Source fingerprints now hash code and input knowledge rather than generated reports/archive
files, so accumulating results cannot by itself invalidate a real-model resume. Real-model
reports and clinical independence remain unverified in this revision.

## Verification

All 1,389 unit tests passed. Existing mock regression retained 205/205 scored cases,
with three additional unscored cases; both the prior and new snapshots preserve these
results. All 952 reference title lookups passed. These lookup results are not diagnostic
accuracy. Standalone build/source synchronization, adversarial checks, README metric
consistency and the existing leakage scan passed. No live model or independent clinical
validation was performed.

## New condition references

| Condition | Source |
|---|---|
| 16p11.2 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/16p112-deletion-syndrome) |
| 1p36 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/1p36-deletion-syndrome) |
| 21-hydroxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/21-hydroxylase-deficiency) |
| 3-hydroxyacyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-hydroxyacyl-coa-dehydrogenase-deficiency) |
| 3-methylcrotonyl-CoA carboxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-methylcrotonyl-coa-carboxylase-deficiency) |
| 3p deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/3p-deletion-syndrome) |
| 3q29 microdeletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/3q29-microdeletion-syndrome) |
| 47,XYY syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/47xyy-syndrome) |
| 49,XXXXY syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/49xxxxy-syndrome) |
| 8p11 myeloproliferative syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/8p11-myeloproliferative-syndrome) |
| ACAD9 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/acad9-deficiency) |
| Acrocallosal syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/acrocallosal-syndrome) |
| Action myoclonus–renal failure syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/action-myoclonus-renal-failure-syndrome) |
| Adenylosuccinate lyase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/adenylosuccinate-lyase-deficiency) |
| Adermatoglyphia | [MedlinePlus](https://medlineplus.gov/genetics/condition/adermatoglyphia) |
| ADNP syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/adnp-syndrome) |
| African iron overload | [MedlinePlus](https://medlineplus.gov/genetics/condition/african-iron-overload) |
| Alagille syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/alagille-syndrome) |
| Alexander disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/alexander-disease) |
| ALG12-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/alg12-congenital-disorder-of-glycosylation) |
| Alkaptonuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/alkaptonuria) |
| Allergic asthma | [MedlinePlus](https://medlineplus.gov/genetics/condition/allergic-asthma) |
| Alopecia areata | [MedlinePlus](https://medlineplus.gov/genetics/condition/alopecia-areata) |
| Alpers-Huttenlocher syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpers-huttenlocher-syndrome) |
| Alpha thalassemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpha-thalassemia) |
| Alpha-methylacyl-CoA racemase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpha-methylacyl-coa-racemase-deficiency) |
| Alternating hemiplegia of childhood | [MedlinePlus](https://medlineplus.gov/genetics/condition/alternating-hemiplegia-of-childhood) |
| Aminoacylase 1 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/aminoacylase-1-deficiency) |
| Angelman syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/angelman-syndrome) |
| Ankyloblepharon-ectodermal defects-cleft lip/palate syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ankyloblepharon-ectodermal-defects-cleft-lip-palate-syndrome) |
| Anophthalmia/microphthalmia-esophageal atresia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/anophthalmia-microphthalmia-esophageal-atresia-syndrome) |
| Antiphospholipid syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/antiphospholipid-syndrome) |
| Ataxia neuropathy spectrum | [MedlinePlus](https://medlineplus.gov/genetics/condition/ataxia-neuropathy-spectrum) |
| Atelosteogenesis type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/atelosteogenesis-type-1) |
| Atopic dermatitis | [MedlinePlus](https://medlineplus.gov/genetics/condition/atopic-dermatitis) |
| Atypical hemolytic-uremic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/atypical-hemolytic-uremic-syndrome) |
| Autoimmune polyendocrinopathy-candidiasis-ectodermal dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/autoimmune-polyendocrinopathy-candidiasis-ectodermal-dystrophy) |
| Autosomal dominant optic atrophy and cataract | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-optic-atrophy-and-cataract) |
| Autosomal dominant sleep-related hypermotor epilepsy  | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-sleep-related-hypermotor-epilepsy) |
| Autosomal recessive cerebellar ataxia type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-cerebellar-ataxia-type-1) |
| Autosomal recessive congenital stationary night blindness | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-congenital-stationary-night-blindness) |
| Autosomal recessive spastic ataxia of Charlevoix-Saguenay | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-spastic-ataxia-of-charlevoix-saguenay) |
| Bannayan-Riley-Ruvalcaba syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bannayan-riley-ruvalcaba-syndrome) |
| Bare lymphocyte syndrome type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/bare-lymphocyte-syndrome-type-i) |
| Bart-Pumphrey syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bart-pumphrey-syndrome) |
| Beare-Stevenson cutis gyrata syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/beare-stevenson-cutis-gyrata-syndrome) |
| Benign familial neonatal seizures | [MedlinePlus](https://medlineplus.gov/genetics/condition/benign-familial-neonatal-seizures) |
| Bietti crystalline dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/bietti-crystalline-dystrophy) |
| Biotin-thiamine-responsive basal ganglia disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/biotin-thiamine-responsive-basal-ganglia-disease) |
| Biotinidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/biotinidase-deficiency) |
| Björnstad syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bjornstad-syndrome) |
| Blau syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/blau-syndrome) |
| Bloom syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bloom-syndrome) |
| Branchiootorenal/branchiootic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/branchiootorenal-branchiootic-syndrome) |
| Caffey disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/caffey-disease) |
| Camurati-Engelmann disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/camurati-engelmann-disease) |
| Canavan disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/canavan-disease) |
| Carbamoyl phosphate synthetase I deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/carbamoyl-phosphate-synthetase-i-deficiency) |
| Carbonic anhydrase VA deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/carbonic-anhydrase-va-deficiency) |
| Carney complex | [MedlinePlus](https://medlineplus.gov/genetics/condition/carney-complex) |
| Caudal regression syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/caudal-regression-syndrome) |
| Central core disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/central-core-disease) |
| Childhood absence epilepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/childhood-absence-epilepsy) |
| CHMP2B-related frontotemporal dementia | [MedlinePlus](https://medlineplus.gov/genetics/condition/chmp2b-related-frontotemporal-dementia) |
| Christianson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/christianson-syndrome) |
| CLN2 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln2-disease) |
| CLN7 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln7-disease) |
| CLN8 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln8-disease) |
| Clopidogrel resistance | [MedlinePlus](https://medlineplus.gov/genetics/condition/clopidogrel-resistance) |
| CLPB deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/clpb-deficiency) |
| Coffin-Siris syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/coffin-siris-syndrome) |
| Cole disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cole-disease) |
| Combined oxidative phosphorylation deficiency 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/combined-oxidative-phosphorylation-deficiency-1) |
| Congenital afibrinogenemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-afibrinogenemia) |
| Congenital anomalies of kidney and urinary tract | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-anomalies-of-kidney-and-urinary-tract) |
| Congenital fiber-type disproportion | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-fiber-type-disproportion) |
| Congenital fibrosis of the extraocular muscles | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-fibrosis-of-the-extraocular-muscles) |
| Congenital hepatic fibrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-hepatic-fibrosis) |
| Congenital stromal corneal dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-stromal-corneal-dystrophy) |
| Cornelia de Lange syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cornelia-de-lange-syndrome) |
| Craniofrontonasal syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/craniofrontonasal-syndrome) |
| Crigler-Najjar syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/crigler-najjar-syndrome) |
| Cutis laxa | [MedlinePlus](https://medlineplus.gov/genetics/condition/cutis-laxa) |
| Cytochrome c oxidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/cytochrome-c-oxidase-deficiency) |
| Dandy-Walker malformation | [MedlinePlus](https://medlineplus.gov/genetics/condition/dandy-walker-malformation) |
| Deafness and myopia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/deafness-and-myopia-syndrome) |
| Dentatorubral-pallidoluysian atrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/dentatorubral-pallidoluysian-atrophy) |
| Dentinogenesis imperfecta | [MedlinePlus](https://medlineplus.gov/genetics/condition/dentinogenesis-imperfecta) |
| Deoxyguanosine kinase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/deoxyguanosine-kinase-deficiency) |
| Dihydrolipoamide dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/dihydrolipoamide-dehydrogenase-deficiency) |
| DLG4-related synaptopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/dlg4-related-synaptopathy) |
| DNMT3A overgrowth syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dnmt3a-overgrowth-syndrome) |
| DOORS syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/doors-syndrome) |
| Dopa-responsive dystonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/dopa-responsive-dystonia) |
| Duchenne and Becker muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/duchenne-and-becker-muscular-dystrophy) |
| Dyskeratosis congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/dyskeratosis-congenita) |
| Dystonia 16 | [MedlinePlus](https://medlineplus.gov/genetics/condition/dystonia-16) |
| Early-onset myopathy with fatal cardiomyopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/early-onset-myopathy-with-fatal-cardiomyopathy) |
| Emery-Dreifuss muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/emery-dreifuss-muscular-dystrophy) |
| Enlarged parietal foramina | [MedlinePlus](https://medlineplus.gov/genetics/condition/enlarged-parietal-foramina) |
| Epidermolysis bullosa with pyloric atresia | [MedlinePlus](https://medlineplus.gov/genetics/condition/epidermolysis-bullosa-with-pyloric-atresia) |
| Epilepsy of infancy with migrating focal seizures  | [MedlinePlus](https://medlineplus.gov/genetics/condition/epilepsy-of-infancy-with-migrating-focal-seizures) |
| Episodic ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/episodic-ataxia) |
| Esophageal atresia/tracheoesophageal fistula | [MedlinePlus](https://medlineplus.gov/genetics/condition/esophageal-atresia-tracheoesophageal-fistula) |
| Factor XI deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-xi-deficiency) |
| Familial erythrocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-erythrocytosis) |
| Familial hyperaldosteronism | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-hyperaldosteronism) |
| Familial hypertrophic cardiomyopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-hypertrophic-cardiomyopathy) |
| Familial male-limited precocious puberty | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-male-limited-precocious-puberty) |
| Familial Mediterranean fever | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-mediterranean-fever) |
| Familial partial lipodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-partial-lipodystrophy) |
| Familial porencephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-porencephaly) |
| Familial thoracic aortic aneurysm and dissection | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-thoracic-aortic-aneurysm-and-dissection) |
| Farsightedness | [MedlinePlus](https://medlineplus.gov/genetics/condition/farsightedness) |
| FBXL4-related encephalomyopathic mitochondrial DNA depletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fbxl4-related-encephalomyopathic-mitochondrial-dna-depletion-syndrome) |
| Fibronectin glomerulopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/fibronectin-glomerulopathy) |
| FOXG1 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/foxg1-syndrome) |
| Fragile XE syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fragile-xe-syndrome) |
| Freeman-Sheldon syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/freeman-sheldon-syndrome) |
| Frontometaphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/frontometaphyseal-dysplasia) |
| Frontotemporal dementia with parkinsonism-17 | [MedlinePlus](https://medlineplus.gov/genetics/condition/frontotemporal-dementia-with-parkinsonism-17) |
| Fuchs endothelial dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/fuchs-endothelial-dystrophy) |
| Fucosidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/fucosidosis) |
| Gastrointestinal stromal tumor | [MedlinePlus](https://medlineplus.gov/genetics/condition/gastrointestinal-stromal-tumor) |
| Gaucher disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/gaucher-disease) |
| Glucose phosphate isomerase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/glucose-phosphate-isomerase-deficiency) |
| GLUT1 deficiency syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/glut1-deficiency-syndrome) |
| Glutamate formiminotransferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/glutamate-formiminotransferase-deficiency) |
| Glycogen storage disease type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-i) |
| Glycogen storage disease type III | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-iii) |
| Glycogen storage disease type IV | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-iv) |
| Glycogen storage disease type V | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-v) |
| GM1 gangliosidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/gm1-gangliosidosis) |
| Gorlin syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gorlin-syndrome) |
| Gorlin-Chaudhry-Moss syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gorlin-chaudhry-moss-syndrome) |
| Gout | [MedlinePlus](https://medlineplus.gov/genetics/condition/gout) |
| Griscelli syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/griscelli-syndrome) |
| Hand-foot-genital syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hand-foot-genital-syndrome) |
| Hartnup disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/hartnup-disease) |
| Hashimoto's disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/hashimotos-disease) |
| Hepatic veno-occlusive disease with immunodeficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/hepatic-veno-occlusive-disease-with-immunodeficiency) |
| Hereditary angioedema | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-angioedema) |
| Hereditary angiopathy with nephropathy, aneurysms, and muscle cramps syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-angiopathy-with-nephropathy-aneurysms-and-muscle-cramps-syndrome) |
| Hereditary antithrombin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-antithrombin-deficiency) |
| Hereditary cerebral amyloid angiopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-cerebral-amyloid-angiopathy) |
| Hereditary hyperekplexia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-hyperekplexia) |
| Hereditary multiple osteochondromas | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-multiple-osteochondromas) |
| Hereditary neuralgic amyotrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-neuralgic-amyotrophy) |
| Hereditary sensory and autonomic neuropathy type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-sensory-and-autonomic-neuropathy-type-ii) |
| Hereditary sensory and autonomic neuropathy type V | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-sensory-and-autonomic-neuropathy-type-v) |
| Hereditary sensory neuropathy type IA | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-sensory-neuropathy-type-ia) |
| Hereditary spherocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-spherocytosis) |
| Histidinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/histidinemia) |
| Holt-Oram syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/holt-oram-syndrome) |
| Huntington's disease-like | [MedlinePlus](https://medlineplus.gov/genetics/condition/huntingtons-disease-like) |
| Hyaline fibromatosis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyaline-fibromatosis-syndrome) |
| Hyperlysinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperlysinemia) |
| Hypermethioninemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypermethioninemia) |
| Hypokalemic periodic paralysis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypokalemic-periodic-paralysis) |
| Hypomyelination and congenital cataract | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypomyelination-and-congenital-cataract) |
| Ichthyosis with confetti | [MedlinePlus](https://medlineplus.gov/genetics/condition/ichthyosis-with-confetti) |
| Idiopathic infantile hypercalcemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/idiopathic-infantile-hypercalcemia) |
| Immune thrombocytopenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/immune-thrombocytopenia) |
| Inclusion body myopathy with early-onset Paget disease and frontotemporal dementia | [MedlinePlus](https://medlineplus.gov/genetics/condition/inclusion-body-myopathy-with-early-onset-paget-disease-and-frontotemporal-dementia) |
| Infantile-onset spinocerebellar ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/infantile-onset-spinocerebellar-ataxia) |
| Inherited thyroxine-binding globulin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/inherited-thyroxine-binding-globulin-deficiency) |
| Intervertebral disc disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/intervertebral-disc-disease) |
| Intestinal pseudo-obstruction | [MedlinePlus](https://medlineplus.gov/genetics/condition/intestinal-pseudo-obstruction) |
| IRAK-4 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/irak-4-deficiency) |
| Isolated ectopia lentis | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-ectopia-lentis) |
| Isolated hyperCKemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-hyperckemia) |
| Isovaleric acidemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/isovaleric-acidemia) |
| Jackson-Weiss syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/jackson-weiss-syndrome) |
| Jansen-de Vries syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/jansen-de-vries-syndrome) |
| Juvenile primary lateral sclerosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/juvenile-primary-lateral-sclerosis) |
| Kallmann syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kallmann-syndrome) |
| KCNK9 imprinting syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kcnk9-imprinting-syndrome) |
| Keratoderma with woolly hair | [MedlinePlus](https://medlineplus.gov/genetics/condition/keratoderma-with-woolly-hair) |
| Klippel-Feil syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/klippel-feil-syndrome) |
| Klippel-Trenaunay syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/klippel-trenaunay-syndrome) |
| Lafora progressive myoclonus epilepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/lafora-progressive-myoclonus-epilepsy) |
| Laing distal myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/laing-distal-myopathy) |
| LAMA2-related muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/lama2-related-muscular-dystrophy) |
| Laryngo-onycho-cutaneous syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/laryngo-onycho-cutaneous-syndrome) |
| Leber congenital amaurosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/leber-congenital-amaurosis) |
| Lesch-Nyhan syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lesch-nyhan-syndrome) |
| Leukoencephalopathy with brainstem and spinal cord involvement and lactate elevation | [MedlinePlus](https://medlineplus.gov/genetics/condition/leukoencephalopathy-with-brainstem-and-spinal-cord-involvement-and-lactate-elevation) |
| Leukoencephalopathy with thalamus and brainstem involvement and high lactate | [MedlinePlus](https://medlineplus.gov/genetics/condition/leukoencephalopathy-with-thalamus-and-brainstem-involvement-and-high-lactate) |
| Liebenberg syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/liebenberg-syndrome) |
| Lipoid proteinosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/lipoid-proteinosis) |
| Lynch syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lynch-syndrome) |
| Lysinuric protein intolerance | [MedlinePlus](https://medlineplus.gov/genetics/condition/lysinuric-protein-intolerance) |
| Mabry syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mabry-syndrome) |
| Mal de Meleda | [MedlinePlus](https://medlineplus.gov/genetics/condition/mal-de-meleda) |
| Malignant hyperthermia | [MedlinePlus](https://medlineplus.gov/genetics/condition/malignant-hyperthermia) |
| Malonyl-CoA decarboxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/malonyl-coa-decarboxylase-deficiency) |
| Mandibulofacial dysostosis with microcephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/mandibulofacial-dysostosis-with-microcephaly) |
| Manitoba oculotrichoanal syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/manitoba-oculotrichoanal-syndrome) |
| Maple syrup urine disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/maple-syrup-urine-disease) |
| Marinesco-Sjögren syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/marinesco-sjogren-syndrome) |
| MBD5-associated neurodevelopmental disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/mbd5-associated-neurodevelopmental-disorder) |
| MDA5 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mda5-deficiency) |
| Meckel syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/meckel-syndrome) |
| MECP2 duplication syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mecp2-duplication-syndrome) |
| Medium-chain acyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/medium-chain-acyl-coa-dehydrogenase-deficiency) |
| Medullary cystic kidney disease type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/medullary-cystic-kidney-disease-type-1) |
| Megacystis-microcolon-intestinal hypoperistalsis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/megacystis-microcolon-intestinal-hypoperistalsis-syndrome) |
| Meige disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/meige-disease) |
| Methemoglobinemia, beta-globin type | [MedlinePlus](https://medlineplus.gov/genetics/condition/methemoglobinemia-beta-globin-type) |
| Methylmalonic acidemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/methylmalonic-acidemia) |
| Mevalonate kinase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mevalonate-kinase-deficiency) |
| Microphthalmia with linear skin defects syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/microphthalmia-with-linear-skin-defects-syndrome) |
| Mitochondrial complex III deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-complex-iii-deficiency) |
| Mitochondrial complex V deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-complex-v-deficiency) |
| Mitochondrial trifunctional protein deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-trifunctional-protein-deficiency) |
| Molybdenum cofactor deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/molybdenum-cofactor-deficiency) |
| Monilethrix | [MedlinePlus](https://medlineplus.gov/genetics/condition/monilethrix) |
| Mucopolysaccharidosis type III | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-iii) |
| Mucopolysaccharidosis type VI | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-vi) |
| Mucopolysaccharidosis type VII | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-vii) |
| Multiple epiphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-epiphyseal-dysplasia) |
| Multiple pterygium syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-pterygium-syndrome) |
| MYH9-related disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/myh9-related-disorder) |
| Myoclonic epilepsy myopathy sensory ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/myoclonic-epilepsy-myopathy-sensory-ataxia) |
| Myoclonic epilepsy with ragged-red fibers | [MedlinePlus](https://medlineplus.gov/genetics/condition/myoclonic-epilepsy-with-ragged-red-fibers) |
| Myofibrillar myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/myofibrillar-myopathy) |
| Myostatin-related muscle hypertrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/myostatin-related-muscle-hypertrophy) |
| Myotonia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/myotonia-congenita) |
| Myotonic dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/myotonic-dystrophy) |
| N-acetylglutamate synthase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/n-acetylglutamate-synthase-deficiency) |
| Nephronophthisis | [MedlinePlus](https://medlineplus.gov/genetics/condition/nephronophthisis) |
| Neurodevelopmental disorder with or without anomalies of the brain, eye, or heart | [MedlinePlus](https://medlineplus.gov/genetics/condition/neurodevelopmental-disorder-with-or-without-anomalies-of-the-brain-eye-or-heart) |
| Neuroferritinopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/neuroferritinopathy) |
| Nijmegen breakage syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/nijmegen-breakage-syndrome) |
| Nonketotic hyperglycinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonketotic-hyperglycinemia) |
| Nonsyndromic aplasia cutis congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-aplasia-cutis-congenita) |
| Nonsyndromic paraganglioma | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-paraganglioma) |
| North American Indian childhood cirrhosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/north-american-indian-childhood-cirrhosis) |
| Ochoa syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ochoa-syndrome) |
| Oculocutaneous albinism | [MedlinePlus](https://medlineplus.gov/genetics/condition/oculocutaneous-albinism) |
| Osteoglophonic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/osteoglophonic-dysplasia) |
| Osteoporosis-pseudoglioma syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/osteoporosis-pseudoglioma-syndrome) |
| Otopalatodigital syndrome type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/otopalatodigital-syndrome-type-2) |
| Pallister-Killian mosaic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pallister-killian-mosaic-syndrome) |
| Paroxysmal nocturnal hemoglobinuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/paroxysmal-nocturnal-hemoglobinuria) |
| Periventricular heterotopia | [MedlinePlus](https://medlineplus.gov/genetics/condition/periventricular-heterotopia) |
| Peters plus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/peters-plus-syndrome) |
| Pfeiffer syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pfeiffer-syndrome) |
| Phenylketonuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/phenylketonuria) |
| Phosphoglycerate dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/phosphoglycerate-dehydrogenase-deficiency) |
| Piebaldism | [MedlinePlus](https://medlineplus.gov/genetics/condition/piebaldism) |
| PLCG2-associated antibody deficiency and immune dysregulation | [MedlinePlus](https://medlineplus.gov/genetics/condition/plcg2-associated-antibody-deficiency-and-immune-dysregulation) |
| PMM2-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/pmm2-congenital-disorder-of-glycosylation) |
| Poland syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/poland-syndrome) |
| Polycythemia vera | [MedlinePlus](https://medlineplus.gov/genetics/condition/polycythemia-vera) |
| PPM-X syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ppm-x-syndrome) |
| Primary sclerosing cholangitis | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-sclerosing-cholangitis) |
| Progressive myoclonic epilepsy type 1  | [MedlinePlus](https://medlineplus.gov/genetics/condition/progressive-myoclonic-epilepsy-type-1) |
| Proopiomelanocortin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/proopiomelanocortin-deficiency) |
| Propionic acidemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/propionic-acidemia) |
| Prothrombin thrombophilia | [MedlinePlus](https://medlineplus.gov/genetics/condition/prothrombin-thrombophilia) |
| Pyridoxal phosphate-responsive seizures | [MedlinePlus](https://medlineplus.gov/genetics/condition/pyridoxal-phosphate-responsive-seizures) |
| Pyruvate dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/pyruvate-dehydrogenase-deficiency) |
| RAB18 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/rab18-deficiency) |
| Rabson-Mendenhall syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rabson-mendenhall-syndrome) |
| RAPADILINO syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rapadilino-syndrome) |
| Rapid-onset dystonia parkinsonism | [MedlinePlus](https://medlineplus.gov/genetics/condition/rapid-onset-dystonia-parkinsonism) |
| REN-related kidney disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/ren-related-kidney-disease) |
| Renal tubular dysgenesis | [MedlinePlus](https://medlineplus.gov/genetics/condition/renal-tubular-dysgenesis) |
| Retroperitoneal fibrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/retroperitoneal-fibrosis) |
| Rhizomelic chondrodysplasia punctata | [MedlinePlus](https://medlineplus.gov/genetics/condition/rhizomelic-chondrodysplasia-punctata) |
| Riboflavin transporter deficiency neuronopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/riboflavin-transporter-deficiency-neuronopathy) |
| Ring chromosome 14 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ring-chromosome-14-syndrome) |
| Ring chromosome 20 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ring-chromosome-20-syndrome) |
| Robinow syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/robinow-syndrome) |
| Romano-Ward syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/romano-ward-syndrome) |
| Rotor syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rotor-syndrome) |
| RRM2B-related mitochondrial DNA depletion syndrome, encephalomyopathic form with renal tubulopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/rrm2b-related-mitochondrial-dna-depletion-syndrome-encephalomyopathic-form-with-renal-tubulopathy) |
| SATB2-associated syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/satb2-associated-syndrome) |
| Schinzel-Giedion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/schinzel-giedion-syndrome) |
| SCN8A-related epilepsy with encephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/scn8a-related-epilepsy-with-encephalopathy) |
| Sepiapterin reductase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/sepiapterin-reductase-deficiency) |
| SETBP1 haploinsufficiency disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/setbp1-haploinsufficiency-disorder) |
| Simpson-Golabi-Behmel syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/simpson-golabi-behmel-syndrome) |
| Sitosterolemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/sitosterolemia) |
| Sjögren-Larsson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sjogren-larsson-syndrome) |
| Smith-Lemli-Opitz syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/smith-lemli-opitz-syndrome) |
| Snijders Blok-Campeau syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/snijders-blok-campeau-syndrome) |
| Snyder-Robinson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/snyder-robinson-syndrome) |
| Spastic paraplegia type 11 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-11) |
| Spastic paraplegia type 31 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-31) |
| Spastic paraplegia type 49 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-49) |
| Spinal muscular atrophy with lower extremity predominance | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinal-muscular-atrophy-with-lower-extremity-predominance) |
| Spinal muscular atrophy with progressive myoclonic epilepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinal-muscular-atrophy-with-progressive-myoclonic-epilepsy) |
| Spinocerebellar ataxia type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinocerebellar-ataxia-type-1) |
| Spinocerebellar ataxia type 3 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinocerebellar-ataxia-type-3) |
| Spondylocarpotarsal synostosis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondylocarpotarsal-synostosis-syndrome) |
| Spondylothoracic dysostosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondylothoracic-dysostosis) |
| Stargardt macular degeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/stargardt-macular-degeneration) |
| Stüve-Wiedemann syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/stuve-wiedemann-syndrome) |
| SUCLG1-related mitochondrial DNA depletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/suclg1-related-mitochondrial-dna-depletion-syndrome) |
| Sudden infant death with dysgenesis of the testes syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sudden-infant-death-with-dysgenesis-of-the-testes-syndrome) |
| Surfactant dysfunction | [MedlinePlus](https://medlineplus.gov/genetics/condition/surfactant-dysfunction) |
| T-cell immunodeficiency, congenital alopecia, and nail dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/t-cell-immunodeficiency-congenital-alopecia-and-nail-dystrophy) |
| Tarsal-carpal coalition syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/tarsal-carpal-coalition-syndrome) |
| Transthyretin amyloidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/transthyretin-amyloidosis) |
| Treacher Collins syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/treacher-collins-syndrome) |
| Triple A syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/triple-a-syndrome) |
| Trisomy 18 | [MedlinePlus](https://medlineplus.gov/genetics/condition/trisomy-18) |
| TRNT1 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/trnt1-deficiency) |
| Troyer syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/troyer-syndrome) |
| Tubular aggregate myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/tubular-aggregate-myopathy) |
| Type A insulin resistance syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/type-a-insulin-resistance-syndrome) |
| Tyrosinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/tyrosinemia) |
| Van der Woude syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/van-der-woude-syndrome) |
| Very long-chain acyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/very-long-chain-acyl-coa-dehydrogenase-deficiency) |
| Vibratory urticaria | [MedlinePlus](https://medlineplus.gov/genetics/condition/vibratory-urticaria) |
| Vici syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/vici-syndrome) |
| WAGR syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wagr-syndrome) |
| Weaver syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/weaver-syndrome) |
| Weill-Marchesani syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/weill-marchesani-syndrome) |
| Weissenbacher-Zweymüller syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/weissenbacher-zweymuller-syndrome) |
| Wiskott-Aldrich syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wiskott-aldrich-syndrome) |
| Wolf-Hirschhorn syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wolf-hirschhorn-syndrome) |
| Wolff-Parkinson-White syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wolff-parkinson-white-syndrome) |
| Wolfram syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wolfram-syndrome) |
| X-linked adrenoleukodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-adrenoleukodystrophy) |
| X-linked cardiac valvular dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-cardiac-valvular-dysplasia) |
| X-linked chondrodysplasia punctata 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-chondrodysplasia-punctata-2) |
| X-linked congenital stationary night blindness | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-congenital-stationary-night-blindness) |
| X-linked creatine deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-creatine-deficiency) |
| X-linked dystonia-parkinsonism | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-dystonia-parkinsonism) |
| X-linked infantile nystagmus | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-infantile-nystagmus) |
| X-linked myotubular myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-myotubular-myopathy) |
| X-linked sideroblastic anemia and ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-sideroblastic-anemia-and-ataxia) |
| Xia-Gibbs syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/xia-gibbs-syndrome) |
| Y chromosome infertility | [MedlinePlus](https://medlineplus.gov/genetics/condition/y-chromosome-infertility) |
| Yao syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/yao-syndrome) |
| ZAP70-related severe combined immunodeficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/zap70-related-severe-combined-immunodeficiency) |
| Zellweger spectrum disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/zellweger-spectrum-disorder) |
