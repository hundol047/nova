# 1,451 candidate entries and selected local model

Added the remaining 431 non-overlapping condition candidates from the retained MedlinePlus
Genetics source. **68 diagnostic rules + 204 health-topic references + 1,179 Genetics references
= 1,451 total entries.** The prior 1,020 entries are preserved. All 1,383 references remain
reference-only: no new autonomous diagnoses, clinical validation or measured accuracy gains.

Source: MedlinePlus, National Library of Medicine. Selection uses the same official frozen XML,
condition-only scope and normalized-name/alias collision exclusion described in
[the 1,020-entry revision](CATALOG_1020_AND_LEARNING.md). The remaining 126 Genetics source
conditions were excluded due to name/alias collisions under this selection procedure; no claim
of a complete or mutually exclusive disease ontology is made. Broad conditions and subtypes
may overlap semantically. English vocabulary does not establish Korean-language parity.

## Model choice and actual status

Selected **Qwen3 4B Instruct via local Ollama**, avoiding a required paid hosted API account.
Model page: https://ollama.com/library/qwen3:4b-instruct
Local installation: https://docs.ollama.com/linux
Local API compatibility: https://docs.ollama.com/api/openai-compatibility

The available executor has approximately 9.7 GiB RAM and no detected NVIDIA GPU. Ollama 0.35.0
was downloaded and its executable verified. The official model pull failed when resolving its
blob redirect host with a network-unreachable error. The temporary server was stopped. The
saved `evaluation/local_model_integration.json` therefore records failed integration, missing
weights and no training; **no real model response was obtained and no persistent server runs**.
This is not a model-quality result. Neither the website nor production provider was changed.

`config/nova_local_model.json` and `scripts/local_model.py` preserve the selected configuration
and provide a repeatable real-response check. The helper accepts only loopback HTTP endpoints,
clears API credentials for local calls, and records success only after actual response/schema
validation without fallback. Missing connections cannot pass as mock success. The default
agent provider remains mock until explicitly configured for an available local server.

On a machine where the model can be downloaded, install Ollama using its official instructions,
start the Ollama app/service (or `ollama serve` in a separate terminal), then run:

```powershell
ollama pull qwen3:4b-instruct
python scripts/local_model.py --smoke --save-json local-model-check.json
```

The helper configures only its own process. To use the same model in other NOVA commands in
PowerShell, set the environment in that terminal:

```powershell
$env:NOVA_LLM_PROVIDER = "local"
$env:NOVA_LLM_MODEL = "qwen3:4b-instruct"
$env:NOVA_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:NOVA_LLM_TIMEOUT_SECONDS = "180"
$env:NOVA_LLM_MAX_RETRIES = "0"
$env:NOVA_LLM_API_KEY = ""
$env:NO_PROXY = "localhost,127.0.0.1,::1"
python scripts/smoke_real_llm.py
```

Passing one smoke turn demonstrates connectivity and structured output only. Full independent
case evaluation remains required. Ollama serves models; installing or pulling a model does not
fine-tune it. No automatic training was started. Existing synthetic archives remain segregated
from test data with training eligibility false. Actual fine-tuning needs reviewed training data,
a separate held-out evaluation and an appropriate training backend/hardware. No training or
clinical approval is inferred from the selected model's capabilities or publisher description.

## Verification

All 1,826 unit tests passed. Existing mock regression retained 205/205 scored cases plus
three unscored cases, and the new snapshot was archived. All 1,383 reference title lookups
passed (lookup, not diagnostic accuracy). Standalone build/source synchronization, adversarial
checks, README metric consistency and the existing leakage scan passed. The real-model
integration check failed as recorded above; it is not counted as a passing test or evaluation.

## Added 431 condition references

| Condition | Official source |
|---|---|
| 15q13.3 microdeletion | [MedlinePlus](https://medlineplus.gov/genetics/condition/15q133-microdeletion) |
| 17-beta hydroxysteroid dehydrogenase 3 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/17-beta-hydroxysteroid-dehydrogenase-3-deficiency) |
| 17q12 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/17q12-deletion-syndrome) |
| 1q21.1 microdeletion | [MedlinePlus](https://medlineplus.gov/genetics/condition/1q211-microdeletion) |
| 22q11.2 duplication | [MedlinePlus](https://medlineplus.gov/genetics/condition/22q112-duplication) |
| 22q13.3 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/22q133-deletion-syndrome) |
| 2q37 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/2q37-deletion-syndrome) |
| 3-hydroxy-3-methylglutaryl-CoA lyase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-hydroxy-3-methylglutaryl-coa-lyase-deficiency) |
| 3-methylglutaconyl-CoA hydratase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-methylglutaconyl-coa-hydratase-deficiency) |
| 3MC syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/3mc-syndrome) |
| 3q29 microduplication syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/3q29-microduplication-syndrome) |
| 48,XXYY syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/48xxyy-syndrome) |
| 5q minus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/5q-minus-syndrome) |
| 5q31.3 microdeletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/5q313-microdeletion-syndrome) |
| 6q24-related transient neonatal diabetes mellitus | [MedlinePlus](https://medlineplus.gov/genetics/condition/6q24-related-transient-neonatal-diabetes-mellitus) |
| 9q22.3 microdeletion | [MedlinePlus](https://medlineplus.gov/genetics/condition/9q223-microdeletion) |
| Abdominal wall defect | [MedlinePlus](https://medlineplus.gov/genetics/condition/abdominal-wall-defect) |
| Achondrogenesis | [MedlinePlus](https://medlineplus.gov/genetics/condition/achondrogenesis) |
| Activated PI3K-delta syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/activated-pi3k-delta-syndrome) |
| Acute necrotizing encephalopathy type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/acute-necrotizing-encephalopathy-type-1) |
| Acute promyelocytic leukemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/acute-promyelocytic-leukemia) |
| Adams-Oliver syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/adams-oliver-syndrome) |
| ADCY5-related dyskinesia | [MedlinePlus](https://medlineplus.gov/genetics/condition/adcy5-related-dyskinesia) |
| Adenosine deaminase 2 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/adenosine-deaminase-2-deficiency) |
| Adenosine deaminase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/adenosine-deaminase-deficiency) |
| Adiposis dolorosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/adiposis-dolorosa) |
| Adult polyglucosan body disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/adult-polyglucosan-body-disease) |
| Age-related hearing loss | [MedlinePlus](https://medlineplus.gov/genetics/condition/age-related-hearing-loss) |
| Aldosterone-producing adenoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/aldosterone-producing-adenoma) |
| ALG6-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/alg6-congenital-disorder-of-glycosylation) |
| Alpha-mannosidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpha-mannosidosis) |
| Alveolar capillary dysplasia with misalignment of pulmonary veins | [MedlinePlus](https://medlineplus.gov/genetics/condition/alveolar-capillary-dysplasia-with-misalignment-of-pulmonary-veins) |
| Amelogenesis imperfecta | [MedlinePlus](https://medlineplus.gov/genetics/condition/amelogenesis-imperfecta) |
| Androgenetic alopecia | [MedlinePlus](https://medlineplus.gov/genetics/condition/androgenetic-alopecia) |
| Anencephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/anencephaly) |
| Aniridia | [MedlinePlus](https://medlineplus.gov/genetics/condition/aniridia) |
| Ankyrin-B syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ankyrin-b-syndrome) |
| Anonychia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/anonychia-congenita) |
| Apert syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/apert-syndrome) |
| Arginase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/arginase-deficiency) |
| Arginine vasopressin resistance | [MedlinePlus](https://medlineplus.gov/genetics/condition/arginine-vasopressin-resistance) |
| Argininosuccinic aciduria | [MedlinePlus](https://medlineplus.gov/genetics/condition/argininosuccinic-aciduria) |
| Aromatic l-amino acid decarboxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/aromatic-l-amino-acid-decarboxylase-deficiency) |
| Arterial tortuosity syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/arterial-tortuosity-syndrome) |
| Asparagine synthetase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/asparagine-synthetase-deficiency) |
| Ataxia-pancytopenia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ataxia-pancytopenia-syndrome) |
| Ataxia-telangiectasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/ataxia-telangiectasia) |
| Atelosteogenesis type 3 | [MedlinePlus](https://medlineplus.gov/genetics/condition/atelosteogenesis-type-3) |
| Autoimmune Addison disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/autoimmune-addison-disease) |
| Autoimmune lymphoproliferative syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/autoimmune-lymphoproliferative-syndrome) |
| Autosomal dominant cerebellar ataxia, deafness, and narcolepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-cerebellar-ataxia-deafness-and-narcolepsy) |
| Autosomal dominant epilepsy with auditory features | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-epilepsy-with-auditory-features) |
| Autosomal dominant tubulointerstitial kidney disease-UMOD | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-tubulointerstitial-kidney-disease-umod) |
| Autosomal recessive axonal neuropathy with neuromyotonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-axonal-neuropathy-with-neuromyotonia) |
| Autosomal recessive primary microcephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-primary-microcephaly) |
| Axenfeld-Rieger syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/axenfeld-rieger-syndrome) |
| Baller-Gerold syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/baller-gerold-syndrome) |
| BAP1 tumor predisposition syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bap1-tumor-predisposition-syndrome) |
| Baraitser-Winter syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/baraitser-winter-syndrome) |
| Bardet-Biedl syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bardet-biedl-syndrome) |
| Bare lymphocyte syndrome type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/bare-lymphocyte-syndrome-type-ii) |
| Bartter syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bartter-syndrome) |
| Birt-Hogg-Dubé syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/birt-hogg-dube-syndrome) |
| Blepharophimosis, ptosis, and epicanthus inversus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/blepharophimosis-ptosis-and-epicanthus-inversus-syndrome) |
| Boomerang dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/boomerang-dysplasia) |
| Bosma arhinia microphthalmia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bosma-arhinia-microphthalmia-syndrome) |
| Boucher-Neuhäuser syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/boucher-neuhauser-syndrome) |
| Bowen-Conradi syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bowen-conradi-syndrome) |
| Bradyopsia | [MedlinePlus](https://medlineplus.gov/genetics/condition/bradyopsia) |
| Brain-lung-thyroid syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/brain-lung-thyroid-syndrome) |
| Branchio-oculo-facial syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/branchio-oculo-facial-syndrome) |
| Brugada syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/brugada-syndrome) |
| Cantú syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cantu-syndrome) |
| Capillary malformation-arteriovenous malformation syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/capillary-malformation-arteriovenous-malformation-syndrome) |
| Cardiofaciocutaneous syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cardiofaciocutaneous-syndrome) |
| Carnitine palmitoyltransferase II deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/carnitine-palmitoyltransferase-ii-deficiency) |
| Carnitine-acylcarnitine translocase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/carnitine-acylcarnitine-translocase-deficiency) |
| CASK-related intellectual disability | [MedlinePlus](https://medlineplus.gov/genetics/condition/cask-related-intellectual-disability) |
| CAV3-related distal myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/cav3-related-distal-myopathy) |
| CDKL5 deficiency disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/cdkl5-deficiency-disorder) |
| Cerebral autosomal recessive arteriopathy with subcortical infarcts and leukoencephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/cerebral-autosomal-recessive-arteriopathy-with-subcortical-infarcts-and-leukoencephalopathy) |
| Cerebral cavernous malformation | [MedlinePlus](https://medlineplus.gov/genetics/condition/cerebral-cavernous-malformation) |
| Cerebral folate transport deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/cerebral-folate-transport-deficiency) |
| Cerebrotendinous xanthomatosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/cerebrotendinous-xanthomatosis) |
| Chanarin-Dorfman syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/chanarin-dorfman-syndrome) |
| Channelopathy-associated congenital insensitivity to pain | [MedlinePlus](https://medlineplus.gov/genetics/condition/channelopathy-associated-congenital-insensitivity-to-pain) |
| CHARGE syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/charge-syndrome) |
| CHD2 myoclonic encephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/chd2-myoclonic-encephalopathy) |
| Chediak-Higashi syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/chediak-higashi-syndrome) |
| CHOPS syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/chops-syndrome) |
| Chordoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/chordoma) |
| Chronic atrial and intestinal dysrhythmia | [MedlinePlus](https://medlineplus.gov/genetics/condition/chronic-atrial-and-intestinal-dysrhythmia) |
| Chylomicron retention disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/chylomicron-retention-disease) |
| Citrullinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/citrullinemia) |
| CLCN2-related leukoencephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/clcn2-related-leukoencephalopathy) |
| Cleidocranial dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/cleidocranial-dysplasia) |
| CLN1 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln1-disease) |
| CLN3 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln3-disease) |
| CLN4 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln4-disease) |
| CLN6 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln6-disease) |
| Clouston syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/clouston-syndrome) |
| Coats plus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/coats-plus-syndrome) |
| COG5-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/cog5-congenital-disorder-of-glycosylation) |
| Cohen syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cohen-syndrome) |
| COL4A1-related brain small-vessel disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/col4a1-related-brain-small-vessel-disease) |
| Collagen VI-related dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/collagen-vi-related-myopathy) |
| Coloboma | [MedlinePlus](https://medlineplus.gov/genetics/condition/coloboma) |
| Combined pituitary hormone deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/combined-pituitary-hormone-deficiency) |
| Complement component 2 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/complement-component-2-deficiency) |
| Complement component 8 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/complement-component-8-deficiency) |
| Complete LCAT deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/complete-lcat-deficiency) |
| Complete plasminogen activator inhibitor 1 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/complete-plasminogen-activator-inhibitor-1-deficiency) |
| Congenital adrenal hyperplasia due to 11-beta-hydroxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-adrenal-hyperplasia-due-to-11-beta-hydroxylase-deficiency) |
| Congenital bile acid synthesis defect type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-bile-acid-synthesis-defect-type-1) |
| Congenital contractural arachnodactyly | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-contractural-arachnodactyly) |
| Congenital dyserythropoietic anemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-dyserythropoietic-anemia) |
| Congenital hyperinsulinism | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-hyperinsulinism) |
| Congenital hypothyroidism | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-hypothyroidism) |
| Congenital myasthenic syndromes | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-myasthenic-syndrome) |
| Congenital nephrotic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-nephrotic-syndrome) |
| Congenital sucrase-isomaltase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-sucrase-isomaltase-deficiency) |
| Constitutional mismatch repair deficiency syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/constitutional-mismatch-repair-deficiency-syndrome) |
| Core binding factor acute myeloid leukemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/core-binding-factor-acute-myeloid-leukemia) |
| Costello syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/costello-syndrome) |
| Craniofacial microsomia | [MedlinePlus](https://medlineplus.gov/genetics/condition/craniofacial-microsomia) |
| Craniofacial-deafness-hand syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/craniofacial-deafness-hand-syndrome) |
| Critical congenital heart disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/critical-congenital-heart-disease) |
| Cryptogenic cirrhosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/cryptogenic-cirrhosis) |
| Cyclic neutropenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/cyclic-neutropenia) |
| Cyclic vomiting syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cyclic-vomiting-syndrome) |
| Cystinosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/cystinosis) |
| Cystinuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/cystinuria) |
| Cytogenetically normal acute myeloid leukemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/cytogenetically-normal-acute-myeloid-leukemia) |
| D-bifunctional protein deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/d-bifunctional-protein-deficiency) |
| Darier disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/darier-disease) |
| Deafness-dystonia-optic neuronopathy syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/deafness-dystonia-optic-neuronopathy-syndrome) |
| Deafness-infertility syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/deafness-infertility-syndrome) |
| Dent disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/dent-disease) |
| Denys-Drash syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/denys-drash-syndrome) |
| Dermatofibrosarcoma protuberans | [MedlinePlus](https://medlineplus.gov/genetics/condition/dermatofibrosarcoma-protuberans) |
| Desmoid tumor | [MedlinePlus](https://medlineplus.gov/genetics/condition/desmoid-tumor) |
| Developmental and epileptic encephalopathy 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/developmental-and-epileptic-encephalopathy-1) |
| Diamond-Blackfan anemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/diamond-blackfan-anemia) |
| Diastrophic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/diastrophic-dysplasia) |
| DICER1 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dicer1-syndrome) |
| Distal arthrogryposis type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/distal-arthrogryposis-type-1) |
| Donohue syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/donohue-syndrome) |
| Dubin-Johnson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dubin-johnson-syndrome) |
| Dysequilibrium syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dysequilibrium-syndrome) |
| Dystonia 6 | [MedlinePlus](https://medlineplus.gov/genetics/condition/dystonia-6) |
| Dystrophic epidermolysis bullosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/dystrophic-epidermolysis-bullosa) |
| Early-onset glaucoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/early-onset-glaucoma) |
| Early-onset isolated dystonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/early-onset-isolated-dystonia) |
| Ellis-van Creveld syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ellis-van-creveld-syndrome) |
| Encephalocraniocutaneous lipomatosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/encephalocraniocutaneous-lipomatosis) |
| Epidermal nevus | [MedlinePlus](https://medlineplus.gov/genetics/condition/epidermal-nevus) |
| Epilepsy-aphasia spectrum | [MedlinePlus](https://medlineplus.gov/genetics/condition/epilepsy-aphasia-spectrum) |
| Erdheim-Chester disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/erdheim-chester-disease) |
| Erythromelalgia | [MedlinePlus](https://medlineplus.gov/genetics/condition/erythromelalgia) |
| Essential pentosuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/essential-pentosuria) |
| Essential thrombocythemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/essential-thrombocythemia) |
| Fabry disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/fabry-disease) |
| Facioscapulohumeral muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/facioscapulohumeral-muscular-dystrophy) |
| Factor V deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-v-deficiency) |
| Factor V Leiden thrombophilia | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-v-leiden-thrombophilia) |
| Factor VII deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-vii-deficiency) |
| Factor X deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-x-deficiency) |
| Factor XIII deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/factor-xiii-deficiency) |
| Familial adenomatous polyposis | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-adenomatous-polyposis) |
| Familial atrial fibrillation | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-atrial-fibrillation) |
| Familial dysautonomia | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-dysautonomia) |
| Familial exudative vitreoretinopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-exudative-vitreoretinopathy) |
| Familial focal epilepsy with variable foci | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-focal-epilepsy-with-variable-foci) |
| Familial isolated hyperparathyroidism | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-isolated-hyperparathyroidism) |
| Familial paroxysmal nonkinesigenic dyskinesia | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-paroxysmal-nonkinesigenic-dyskinesia) |
| Familial pityriasis rubra pilaris | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-pityriasis-rubra-pilaris) |
| Farber lipogranulomatosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/farber-lipogranulomatosis) |
| Fatty acid hydroxylase-associated neurodegeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/fatty-acid-hydroxylase-associated-neurodegeneration) |
| Feingold syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/feingold-syndrome) |
| FG syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fg-syndrome) |
| Fibrochondrogenesis | [MedlinePlus](https://medlineplus.gov/genetics/condition/fibrochondrogenesis) |
| Fish-eye disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/fish-eye-disease) |
| Focal dermal hypoplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/focal-dermal-hypoplasia) |
| Fragile X syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fragile-x-syndrome) |
| Fragile X-associated primary ovarian insufficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/fragile-x-associated-primary-ovarian-insufficiency) |
| Fragile X-associated tremor/ataxia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fragile-x-associated-tremor-ataxia-syndrome) |
| Frasier syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/frasier-syndrome) |
| Free sialic acid storage disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/free-sialic-acid-storage-disorder) |
| Fukuyama congenital muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/fukuyama-congenital-muscular-dystrophy) |
| GABA-transaminase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/gaba-transaminase-deficiency) |
| Galactosialidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/galactosialidosis) |
| Generalized arterial calcification of infancy | [MedlinePlus](https://medlineplus.gov/genetics/condition/generalized-arterial-calcification-of-infancy) |
| Gestational diabetes | [MedlinePlus](https://medlineplus.gov/genetics/condition/gestational-diabetes) |
| Giant axonal neuropathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/giant-axonal-neuropathy) |
| Gilbert syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gilbert-syndrome) |
| Gillespie syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gillespie-syndrome) |
| Globozoospermia | [MedlinePlus](https://medlineplus.gov/genetics/condition/globozoospermia) |
| Glutaric acidemia type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/glutaric-acidemia-type-i) |
| Glutaric acidemia type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/glutaric-acidemia-type-ii) |
| Glycogen storage disease type 0 | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-0) |
| GM2 activator deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/gm2-activator-deficiency) |
| GRACILE syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gracile-syndrome) |
| Grange syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/grange-syndrome) |
| Graves' disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/graves-disease) |
| Greenberg dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/greenberg-dysplasia) |
| Greig cephalopolysyndactyly syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/greig-cephalopolysyndactyly-syndrome) |
| Gyrate atrophy of the choroid and retina | [MedlinePlus](https://medlineplus.gov/genetics/condition/gyrate-atrophy-of-the-choroid-and-retina) |
| Hailey-Hailey disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/hailey-hailey-disease) |
| Hajdu-Cheney syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hajdu-cheney-syndrome) |
| Harlequin ichthyosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/harlequin-ichthyosis) |
| Hereditary diffuse gastric cancer | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-diffuse-gastric-cancer) |
| Hereditary folate malabsorption | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-folate-malabsorption) |
| Hereditary myopathy with early respiratory failure | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-myopathy-with-early-respiratory-failure) |
| Hereditary pancreatitis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-pancreatitis) |
| Heterotaxy syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/heterotaxy-syndrome) |
| HIVEP2-related intellectual disability | [MedlinePlus](https://medlineplus.gov/genetics/condition/hivep2-related-intellectual-disability) |
| Holocarboxylase synthetase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/holocarboxylase-synthetase-deficiency) |
| Homocystinuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/homocystinuria) |
| Horner syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/horner-syndrome) |
| HSD10 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/hsd10-disease) |
| Hyperferritinemia-cataract syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperferritinemia-cataract-syndrome) |
| Hypermanganesemia with dystonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypermanganesemia-with-dystonia) |
| Hyperprolinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperprolinemia) |
| Hypomagnesemia with secondary hypocalcemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypomagnesemia-with-secondary-hypocalcemia) |
| Hypomyelination with brainstem and spinal cord involvement and leg spasticity | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypomyelination-with-brainstem-and-spinal-cord-involvement-and-leg-spasticity) |
| Hypophosphatasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypophosphatasia) |
| Immune dysregulation, polyendocrinopathy, enteropathy, X-linked syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/immune-dysregulation-polyendocrinopathy-enteropathy-x-linked-syndrome) |
| Incontinentia pigmenti | [MedlinePlus](https://medlineplus.gov/genetics/condition/incontinentia-pigmenti) |
| Infantile neuroaxonal dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/infantile-neuroaxonal-dystrophy) |
| Iron-refractory iron deficiency anemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/iron-refractory-iron-deficiency-anemia) |
| Isobutyryl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/isobutyryl-coa-dehydrogenase-deficiency) |
| Jacobsen syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/jacobsen-syndrome) |
| JAK3-deficient severe combined immunodeficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/jak3-deficient-severe-combined-immunodeficiency) |
| Joubert syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/joubert-syndrome) |
| Junctional epidermolysis bullosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/junctional-epidermolysis-bullosa) |
| Juvenile Paget disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/juvenile-paget-disease) |
| Juvenile primary osteoporosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/juvenile-primary-osteoporosis) |
| Kabuki syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kabuki-syndrome) |
| Kaufman oculocerebrofacial syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kaufman-oculocerebrofacial-syndrome) |
| KBG syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kbg-syndrome) |
| Kearns-Sayre syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kearns-sayre-syndrome) |
| Kniest dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/kniest-dysplasia) |
| Koolen-de Vries syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/koolen-de-vries-syndrome) |
| Krabbe disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/krabbe-disease) |
| Lacrimo-auriculo-dento-digital syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lacrimo-auriculo-dento-digital-syndrome) |
| Larsen syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/larsen-syndrome) |
| Lattice corneal dystrophy type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/lattice-corneal-dystrophy-type-i) |
| Lattice corneal dystrophy type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/lattice-corneal-dystrophy-type-ii) |
| Left ventricular noncompaction | [MedlinePlus](https://medlineplus.gov/genetics/condition/left-ventricular-noncompaction) |
| Legius syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/legius-syndrome) |
| Leigh syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/leigh-syndrome) |
| Leprosy | [MedlinePlus](https://medlineplus.gov/genetics/condition/leprosy) |
| Leptin receptor deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/leptin-receptor-deficiency) |
| Leukocyte adhesion deficiency type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/leukocyte-adhesion-deficiency-type-1) |
| Leukoencephalopathy with vanishing white matter | [MedlinePlus](https://medlineplus.gov/genetics/condition/leukoencephalopathy-with-vanishing-white-matter) |
| Li-Fraumeni syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/li-fraumeni-syndrome) |
| Liddle syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/liddle-syndrome) |
| Limb-girdle muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/limb-girdle-muscular-dystrophy) |
| LMNA-related congenital muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/lmna-related-congenital-muscular-dystrophy) |
| Loeys-Dietz syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/loeys-dietz-syndrome) |
| Lowe syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lowe-syndrome) |
| Lymphangioleiomyomatosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/lymphangioleiomyomatosis) |
| Lysosomal acid lipase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/lysosomal-acid-lipase-deficiency) |
| Léri-Weill dyschondrosteosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/leri-weill-dyschondrosteosis) |
| Mainzer-Saldino syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mainzer-saldino-syndrome) |
| Mannose-binding lectin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mannose-binding-lectin-deficiency) |
| Marfan syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/marfan-syndrome) |
| Maternally inherited diabetes and deafness | [MedlinePlus](https://medlineplus.gov/genetics/condition/maternally-inherited-diabetes-and-deafness) |
| Mayer-Rokitansky-Küster-Hauser syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mayer-rokitansky-kuster-hauser-syndrome) |
| McCune-Albright syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mccune-albright-syndrome) |
| McLeod neuroacanthocytosis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mcleod-neuroacanthocytosis-syndrome) |
| MED13L syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/med13l-syndrome) |
| Megalencephaly-capillary malformation syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/megalencephaly-capillary-malformation-syndrome) |
| Megalencephaly-polymicrogyria-polydactyly-hydrocephalus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/megalencephaly-polymicrogyria-polydactyly-hydrocephalus-syndrome) |
| MEGDEL syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/megdel-syndrome) |
| Metabolic dysfunction-associated steatotic liver disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/metabolic-dysfunction-associated-steatotic-liver-disease) |
| Methylmalonic acidemia with homocystinuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/methylmalonic-acidemia-with-homocystinuria) |
| Microcephaly-capillary malformation syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/microcephaly-capillary-malformation-syndrome) |
| Mitochondrial membrane protein-associated neurodegeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-membrane-protein-associated-neurodegeneration) |
| Moebius syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/moebius-syndrome) |
| Monoamine oxidase A deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/monoamine-oxidase-a-deficiency) |
| Mosaic variegated aneuploidy syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mosaic-variegated-aneuploidy-syndrome) |
| Mowat-Wilson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mowat-wilson-syndrome) |
| MPV17-related hepatocerebral mitochondrial DNA depletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/mpv17-related-hepatocerebral-mitochondrial-dna-depletion-syndrome) |
| Mucopolysaccharidosis type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-i) |
| Mucopolysaccharidosis type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-ii) |
| Mucopolysaccharidosis type IV | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucopolysaccharidosis-type-iv) |
| Multiple cutaneous and mucosal venous malformations | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-cutaneous-and-mucosal-venous-malformations) |
| Multiple endocrine neoplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-endocrine-neoplasia) |
| Multiple mitochondrial dysfunctions syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-mitochondrial-dysfunctions-syndrome) |
| Multiple sulfatase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-sulfatase-deficiency) |
| Mycosis fungoides | [MedlinePlus](https://medlineplus.gov/genetics/condition/mycosis-fungoides) |
| Myhre syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/myhre-syndrome) |
| Myopathy with deficiency of iron-sulfur cluster assembly enzyme | [MedlinePlus](https://medlineplus.gov/genetics/condition/myopathy-with-deficiency-of-iron-sulfur-cluster-assembly-enzyme) |
| Nager syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/nager-syndrome) |
| Nail-patella syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/nail-patella-syndrome) |
| Nakajo-Nishimura syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/nakajo-nishimura-syndrome) |
| Narcolepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/narcolepsy) |
| Neurofibromatosis type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/neurofibromatosis-type-1) |
| Neurofibromatosis type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/neurofibromatosis-type-2) |
| Neuromyelitis optica | [MedlinePlus](https://medlineplus.gov/genetics/condition/neuromyelitis-optica) |
| Neuropathy, ataxia, and retinitis pigmentosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/neuropathy-ataxia-and-retinitis-pigmentosa) |
| Niemann-Pick disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/niemann-pick-disease) |
| Nonbullous congenital ichthyosiform erythroderma | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonbullous-congenital-ichthyosiform-erythroderma) |
| Obstructive sleep apnea | [MedlinePlus](https://medlineplus.gov/genetics/condition/obstructive-sleep-apnea) |
| Oculodentodigital dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/oculodentodigital-dysplasia) |
| Oculopharyngeal muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/oculopharyngeal-muscular-dystrophy) |
| Ohdo syndrome, Maat-Kievit-Brunner type | [MedlinePlus](https://medlineplus.gov/genetics/condition/ohdo-syndrome-maat-kievit-brunner-type) |
| Ohdo syndrome, Say-Barber-Biesecker-Young-Simpson variant | [MedlinePlus](https://medlineplus.gov/genetics/condition/ohdo-syndrome-say-barber-biesecker-young-simpson-variant) |
| Oral-facial-digital syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/oral-facial-digital-syndrome) |
| PACS1 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pacs1-syndrome) |
| Pantothenate kinase-associated neurodegeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/pantothenate-kinase-associated-neurodegeneration) |
| Parathyroid cancer | [MedlinePlus](https://medlineplus.gov/genetics/condition/parathyroid-cancer) |
| Parkes Weber syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/parkes-weber-syndrome) |
| Paroxysmal extreme pain disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/paroxysmal-extreme-pain-disorder) |
| PDGFRA-associated chronic eosinophilic leukemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/pdgfra-associated-chronic-eosinophilic-leukemia) |
| Peeling skin syndrome 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/peeling-skin-syndrome-2) |
| Pelizaeus-Merzbacher disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/pelizaeus-merzbacher-disease) |
| Permanent neonatal diabetes mellitus | [MedlinePlus](https://medlineplus.gov/genetics/condition/permanent-neonatal-diabetes-mellitus) |
| Perrault syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/perrault-syndrome) |
| Phosphoglycerate mutase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/phosphoglycerate-mutase-deficiency) |
| Phosphoribosylpyrophosphate synthetase superactivity | [MedlinePlus](https://medlineplus.gov/genetics/condition/phosphoribosylpyrophosphate-synthetase-superactivity) |
| Pilomatricoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/pilomatricoma) |
| Platyspondylic dysplasia, Torrance type | [MedlinePlus](https://medlineplus.gov/genetics/condition/platyspondylic-dysplasia-torrance-type) |
| Polycystic lipomembranous osteodysplasia with sclerosing leukoencephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/polycystic-lipomembranous-osteodysplasia-with-sclerosing-leukoencephalopathy) |
| Pontocerebellar hypoplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/pontocerebellar-hypoplasia) |
| Potocki-Shaffer syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/potocki-shaffer-syndrome) |
| PPP2R5D-related intellectual disability | [MedlinePlus](https://medlineplus.gov/genetics/condition/ppp2r5d-related-intellectual-disability) |
| Prader-Willi syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/prader-willi-syndrome) |
| Preeclampsia | [MedlinePlus](https://medlineplus.gov/genetics/condition/preeclampsia) |
| Prekallikrein deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/prekallikrein-deficiency) |
| PRICKLE1-related progressive myoclonus epilepsy with ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/prickle1-related-progressive-myoclonus-epilepsy-with-ataxia) |
| Primary ciliary dyskinesia | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-ciliary-dyskinesia) |
| Primary coenzyme Q10 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-coenzyme-q10-deficiency) |
| Primary familial brain calcification | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-familial-brain-calcification) |
| Primary localized cutaneous amyloidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-localized-cutaneous-amyloidosis) |
| Primary macronodular adrenal hyperplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-macronodular-adrenal-hyperplasia) |
| Progressive familial heart block | [MedlinePlus](https://medlineplus.gov/genetics/condition/progressive-familial-heart-block) |
| Progressive pseudorheumatoid dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/progressive-pseudorheumatoid-dysplasia) |
| Prolidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/prolidase-deficiency) |
| Protein C deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/protein-c-deficiency) |
| Proteus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/proteus-syndrome) |
| Pseudocholinesterase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/pseudocholinesterase-deficiency) |
| Pseudohypoaldosteronism type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/pseudohypoaldosteronism-type-2) |
| Purine nucleoside phosphorylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/purine-nucleoside-phosphorylase-deficiency) |
| Pyruvate carboxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/pyruvate-carboxylase-deficiency) |
| Recurrent hydatidiform mole | [MedlinePlus](https://medlineplus.gov/genetics/condition/recurrent-hydatidiform-mole) |
| Refsum disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/refsum-disease) |
| Renal tubular acidosis with deafness | [MedlinePlus](https://medlineplus.gov/genetics/condition/renal-tubular-acidosis-with-deafness) |
| Renpenning syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/renpenning-syndrome) |
| Retinal arterial macroaneurysm with supravalvular pulmonic stenosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/retinal-arterial-macroaneurysm-with-supravalvular-pulmonic-stenosis) |
| Retinitis pigmentosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/retinitis-pigmentosa) |
| Rigid spine muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/rigid-spine-muscular-dystrophy) |
| Rippling muscle disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/rippling-muscle-disease) |
| RNAse T2-deficient leukoencephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/rnase-t2-deficient-leukoencephalopathy) |
| Roberts syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/roberts-syndrome) |
| Saethre-Chotzen syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/saethre-chotzen-syndrome) |
| Sandhoff disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/sandhoff-disease) |
| Saul-Wilson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/saul-wilson-syndrome) |
| Schimke immuno-osseous dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/schimke-immuno-osseous-dysplasia) |
| Schizoaffective disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/schizoaffective-disorder) |
| Schwannomatosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/schwannomatosis) |
| Short stature, hyperextensibility, hernia, ocular depression, Rieger anomaly, and teething delay | [MedlinePlus](https://medlineplus.gov/genetics/condition/short-stature-hyperextensibility-hernia-ocular-depression-rieger-anomaly-and-teething-delay) |
| Sialidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/sialidosis) |
| Silver syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/silver-syndrome) |
| Spastic paraplegia type 15 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-15) |
| Spastic paraplegia type 3A | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-3a) |
| Spastic paraplegia type 4 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-4) |
| Spastic paraplegia type 5A | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-5a) |
| Spastic paraplegia type 7 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-7) |
| Spina bifida | [MedlinePlus](https://medlineplus.gov/genetics/condition/spina-bifida) |
| Spinal and bulbar muscular atrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinal-and-bulbar-muscular-atrophy) |
| Spinocerebellar ataxia type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinocerebellar-ataxia-type-2) |
| Spinocerebellar ataxia type 36 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinocerebellar-ataxia-type-36) |
| Spondyloenchondrodysplasia with immune dysregulation | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondyloenchondrodysplasia-with-immune-dysregulation) |
| Spondyloepiphyseal dysplasia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondyloepiphyseal-dysplasia-congenita) |
| Spondyloepiphyseal dysplasia with marked metaphyseal changes | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondyloepiphyseal-dysplasia-with-marked-metaphyseal-changes) |
| Spondyloepiphyseal dysplasia with metatarsal shortening | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondyloepiphyseal-dysplasia-with-metatarsal-shortening) |
| Spondyloperipheral dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/spondyloperipheral-dysplasia) |
| Sporadic hemiplegic migraine | [MedlinePlus](https://medlineplus.gov/genetics/condition/sporadic-hemiplegic-migraine) |
| STAC3 disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/stac3-disorder) |
| Steatocystoma multiplex | [MedlinePlus](https://medlineplus.gov/genetics/condition/steatocystoma-multiplex) |
| Stevens-Johnson syndrome/toxic epidermal necrolysis | [MedlinePlus](https://medlineplus.gov/genetics/condition/stevens-johnson-syndrome-toxic-epidermal-necrolysis) |
| Stickler syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/stickler-syndrome) |
| STXBP1 encephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/stxbp1-encephalopathy) |
| Subcortical band heterotopia | [MedlinePlus](https://medlineplus.gov/genetics/condition/subcortical-band-heterotopia) |
| Succinic semialdehyde dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/succinic-semialdehyde-dehydrogenase-deficiency) |
| Supravalvular aortic stenosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/supravalvular-aortic-stenosis) |
| Swyer syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/swyer-syndrome) |
| SYNGAP1-related intellectual disability | [MedlinePlus](https://medlineplus.gov/genetics/condition/syngap1-related-intellectual-disability) |
| Systemic mastocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/systemic-mastocytosis) |
| Sézary syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sezary-syndrome) |
| Tangier disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/tangier-disease) |
| Task-specific focal dystonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/task-specific-focal-dystonia) |
| Tetrahydrobiopterin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/tetrahydrobiopterin-deficiency) |
| Thanatophoric dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/thanatophoric-dysplasia) |
| Thrombocytopenia-absent radius syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/thrombocytopenia-absent-radius-syndrome) |
| Tietz syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/tietz-syndrome) |
| Trichothiodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/trichothiodystrophy) |
| Trisomy X | [MedlinePlus](https://medlineplus.gov/genetics/condition/trisomy-x) |
| Tyrosine hydroxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/tyrosine-hydroxylase-deficiency) |
| UNC80 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/unc80-deficiency) |
| Usher syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/usher-syndrome) |
| UV-sensitive syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/uv-sensitive-syndrome) |
| VEXAS syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/vexas-syndrome) |
| Vitamin D-dependent rickets | [MedlinePlus](https://medlineplus.gov/genetics/condition/vitamin-d-dependent-rickets) |
| Vitelliform macular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/vitelliform-macular-dystrophy) |
| Vohwinkel syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/vohwinkel-syndrome) |
| Von Hippel-Lindau syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/von-hippel-lindau-syndrome) |
| Von Willebrand disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/von-willebrand-disease) |
| Waardenburg syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/waardenburg-syndrome) |
| Walker-Warburg syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/walker-warburg-syndrome) |
| Warfarin resistance | [MedlinePlus](https://medlineplus.gov/genetics/condition/warfarin-resistance) |
| Warfarin sensitivity | [MedlinePlus](https://medlineplus.gov/genetics/condition/warfarin-sensitivity) |
| Weyers acrofacial dysostosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/weyers-acrofacial-dysostosis) |
| White sponge nevus | [MedlinePlus](https://medlineplus.gov/genetics/condition/white-sponge-nevus) |
| White-Sutton syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/white-sutton-syndrome) |
| Wilms tumor | [MedlinePlus](https://medlineplus.gov/genetics/condition/wilms-tumor) |
| Winchester syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/winchester-syndrome) |
| X-linked adrenal hypoplasia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-adrenal-hypoplasia-congenita) |
| X-linked dilated cardiomyopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-dilated-cardiomyopathy) |
| X-linked hyper IgM syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-hyper-igm-syndrome) |
| X-linked hypophosphatemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-hypophosphatemia) |
| X-linked immunodeficiency with magnesium defect, Epstein-Barr virus infection, and neoplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-immunodeficiency-with-magnesium-defect-epstein-barr-virus-infection-and-neoplasia) |
| X-linked infantile spinal muscular atrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-infantile-spinal-muscular-atrophy) |
| X-linked intellectual disability, Siderius type | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-intellectual-disability-siderius-type) |
| X-linked juvenile retinoschisis | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-juvenile-retinoschisis) |
| X-linked severe combined immunodeficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-severe-combined-immunodeficiency) |
| X-linked spondyloepiphyseal dysplasia tarda | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-spondyloepiphyseal-dysplasia-tarda) |
| X-linked thrombocytopenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-thrombocytopenia) |
| Yuan-Harel-Lupski syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/yuan-harel-lupski-syndrome) |
