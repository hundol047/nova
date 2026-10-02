# 680-entry candidate inventory (historical)

Current scope: [1,020 entries and saved evaluation history](CATALOG_1020_AND_LEARNING.md).
Counts below describe the earlier revision; current report files have since been updated.

This revision adds 408 MedlinePlus Genetics condition references to the previous 272-entry
inventory: **68 rule-supported entries + 204 health-topic references + 408 Genetics references
= 680 entries (2.5 times the previous inventory)**. Existing 68 rules and the original 204
reference records are unchanged. This is not 680 autonomous or clinically validated diagnoses.

## Source and selection

Source: MedlinePlus, National Library of Medicine. Official downloadable condition descriptions:
https://medlineplus.gov/download/ghr-summaries.xml

API documentation: https://medlineplus.gov/about/developers/geneticsdatafilesapi/
Public-domain reuse terms: https://medlineplus.gov/about/using/usingcontent/

Only `health-condition-summary` records with descriptions were eligible. Gene and chromosome
pages, treatment/procedure pages, and external database text were excluded. No patient data
is sent to the source. References are packaged offline with source URL, attribution, original
source review date (when supplied), and a SHA-256 integrity manifest. Source review dates do
not represent clinical review of this agent. A condition may itself involve chromosomes;
that is different from adding a chromosome information page as a disease.

The frozen selection contains 408 titles. To avoid alphabetic truncation, eligibility was
processed in stable SHA-256 name order, excluding normalized name/alias collisions against
existing rules, references and already selected additions. This is reproducible engineering
selection, **not a prevalence ranking, clinical prioritization or complete coverage standard**.
The new cohort emphasizes genetic/rare conditions. Broader conditions and their subtypes may
still be related; 680 counts catalog entries, not a standardized ontology of mutually exclusive
diseases. Exact-name deduplication does not establish semantic equivalence or independence.

Rebuild from a retained copy of the official XML (the source endpoint changes over time):

```bash
python scripts/import_genetics_candidates.py --xml /path/to/ghr-summaries.xml
python scripts/build_nova_submission.py
python -m nova_agent.knowledge.reference_catalog
```

The importer uses the committed explicit selection, not a live automatic selection. The raw
source hash and selected content are frozen in the manifest. Older 204 health-topic records
remain in their original bundle with their original hashes.

## Runtime behavior

All 612 reference entries remain `reference_only`, with autonomous diagnosis disabled.
Retrieval uses affirmed patient text and preserves the existing negation, family-history and
uncertainty filters. Reference snippets are kept separate from observed patient findings and
never enter deterministic disease scores. Results remain bounded to three excerpts by default
(maximum five, each at most 1,100 characters); reference volume does not enlarge the prompt limit.
Exact canonical title queries outrank broader alias mentions. Compiled alias patterns are cached
to avoid regex cache churn at this catalog size. Retrieval scores are not disease probabilities.

The existing LOW-confidence and finalization guards apply equally to new Genetics entries.
The runtime accepts only condition URLs matching the recorded condition identity and rejects
self-promotion, duplicate IDs, corrupt payloads, and wrong-page sources. Disable reference
retrieval with `NOVA_REFERENCE_CANDIDATES=0`; this never enables autonomous reference diagnosis.

## Verification and limits

All 1,022 unit tests passed, including title retrieval for every reference, duplicate identity
checks, source-scope integrity checks, and prevention of reference-only final diagnoses. The
standalone submission build and source synchronization checks also passed. Existing mock
regression retained 205/205 scored cases, with three additional unscored cases. Adversarial
checks, README metric consistency and the existing leakage scan passed.

See `evaluation/reference_catalog_results.json` for all 612 title lookups and both source
manifests. Title retrieval is a catalog/navigation test, **not diagnostic accuracy**.
See `evaluation/catalog_results.json` for the existing 205 scored mock cases plus three
unscored cases. The reference-only diagnostic accuracy field remains null.

No independent clinical cases or real-model calls were available for this revision. Enlarging
the retrieval pool can change the context seen by a real model, even when mock results are
unchanged. Thus real-world accuracy preservation is not established. New autonomous diagnoses
require condition-specific clinical review and independent evaluation before activation.
English source vocabulary also does not establish equivalent Korean-language performance.

## Added 408 condition references

| Condition | Official source |
|---|---|
| 10q26 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/10q26-deletion-syndrome) |
| 15q11-q13 duplication syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/15q11-q13-duplication-syndrome) |
| 15q24 microdeletion | [MedlinePlus](https://medlineplus.gov/genetics/condition/15q24-microdeletion) |
| 16p11.2 duplication | [MedlinePlus](https://medlineplus.gov/genetics/condition/16p112-duplication) |
| 16p12.2 microdeletion | [MedlinePlus](https://medlineplus.gov/genetics/condition/16p122-microdeletion) |
| 17 alpha-hydroxylase/17,20-lyase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/17-alpha-hydroxylase-17-20-lyase-deficiency) |
| 17q12 duplication | [MedlinePlus](https://medlineplus.gov/genetics/condition/17q12-duplication) |
| 19p13.13 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/19p1313-deletion-syndrome) |
| 1q21.1 microduplication | [MedlinePlus](https://medlineplus.gov/genetics/condition/1q211-microduplication) |
| 2-hydroxyglutaric aciduria | [MedlinePlus](https://medlineplus.gov/genetics/condition/2-hydroxyglutaric-aciduria) |
| 22q11.2 deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/22q112-deletion-syndrome) |
| 3-beta-hydroxysteroid dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-beta-hydroxysteroid-dehydrogenase-deficiency) |
| 3-M syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/3-m-syndrome) |
| 46,XX testicular difference of sex development | [MedlinePlus](https://medlineplus.gov/genetics/condition/46xx-testicular-difference-of-sex-development) |
| 48,XXXY syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/48xxxy-syndrome) |
| 5-alpha reductase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/5-alpha-reductase-deficiency) |
| 7q11.23 duplication syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/7q1123-duplication-syndrome) |
| Aarskog-Scott syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/aarskog-scott-syndrome) |
| Acatalasemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/acatalasemia) |
| Aceruloplasminemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/aceruloplasminemia) |
| Achondroplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/achondroplasia) |
| Achromatopsia | [MedlinePlus](https://medlineplus.gov/genetics/condition/achromatopsia) |
| Acromicric dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/acromicric-dysplasia) |
| Actin-accumulation myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/actin-accumulation-myopathy) |
| Adenine phosphoribosyltransferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/adenine-phosphoribosyltransferase-deficiency) |
| Adenosine monophosphate deaminase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/adenosine-monophosphate-deaminase-deficiency) |
| Adolescent idiopathic scoliosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/adolescent-idiopathic-scoliosis) |
| Adult-onset leukoencephalopathy with axonal spheroids and pigmented glia | [MedlinePlus](https://medlineplus.gov/genetics/condition/adult-onset-leukoencephalopathy-with-axonal-spheroids-and-pigmented-glia) |
| Aicardi syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/aicardi-syndrome) |
| Aicardi-Goutières syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/aicardi-goutieres-syndrome) |
| ALG1-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/alg1-congenital-disorder-of-glycosylation) |
| Allan-Herndon-Dudley syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/allan-herndon-dudley-syndrome) |
| Alpha thalassemia X-linked intellectual disability syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpha-thalassemia-x-linked-intellectual-disability-syndrome) |
| Alpha-N-acetylgalactosaminidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/alpha-n-acetylgalactosaminidase-deficiency) |
| Alport syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/alport-syndrome) |
| Alström syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/alstrom-syndrome) |
| Amish lethal microcephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/amish-lethal-microcephaly) |
| Andermann syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/andermann-syndrome) |
| Anhidrotic ectodermal dysplasia with immune deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/anhidrotic-ectodermal-dysplasia-with-immune-deficiency) |
| Anophthalmia/Microphthalmia | [MedlinePlus](https://medlineplus.gov/genetics/condition/anophthalmia-microphthalmia) |
| Arginine vasopressin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/arginine-vasopressin-deficiency) |
| Arginine:glycine amidinotransferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/arginineglycine-amidinotransferase-deficiency) |
| Aromatase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/aromatase-deficiency) |
| Aromatase excess syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/aromatase-excess-syndrome) |
| Arts syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/arts-syndrome) |
| Aspartylglucosaminuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/aspartylglucosaminuria) |
| Asphyxiating thoracic dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/asphyxiating-thoracic-dystrophy) |
| Ataxia with oculomotor apraxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/ataxia-with-oculomotor-apraxia) |
| Ataxia with vitamin E deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/ataxia-with-vitamin-e-deficiency) |
| Atelosteogenesis type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/atelosteogenesis-type-2) |
| Au-Kline syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/au-kline-syndrome) |
| Auriculocondylar syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/auriculo-condylar-syndrome) |
| Autosomal dominant congenital stationary night blindness | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-congenital-stationary-night-blindness) |
| Autosomal dominant hyper-IgE syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-hyper-ige-syndrome) |
| Autosomal dominant hypocalcemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-hypocalcemia) |
| Autosomal dominant leukodystrophy with autonomic disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-leukodystrophy-with-autonomic-disease) |
| Autosomal dominant vitreoretinochoroidopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-dominant-vitreoretinochoroidopathy) |
| Autosomal recessive congenital methemoglobinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-congenital-methemoglobinemia) |
| Autosomal recessive hypotrichosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/autosomal-recessive-hypotrichosis) |
| Beckwith-Wiedemann syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/beckwith-wiedemann-syndrome) |
| Benign essential blepharospasm | [MedlinePlus](https://medlineplus.gov/genetics/condition/benign-essential-blepharospasm) |
| Benign recurrent intrahepatic cholestasis | [MedlinePlus](https://medlineplus.gov/genetics/condition/benign-recurrent-intrahepatic-cholestasis) |
| Bernard-Soulier syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/bernard-soulier-syndrome) |
| Beta-mannosidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/beta-mannosidosis) |
| Beta-propeller protein-associated neurodegeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/beta-propeller-protein-associated-neurodegeneration) |
| Beta-ureidopropionase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/beta-ureidopropionase-deficiency) |
| Blepharocheilodontic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/blepharocheilodontic-syndrome) |
| Brody myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/brody-myopathy) |
| Burn-McKeown syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/burn-mckeown-syndrome) |
| C3 glomerulopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/c3-glomerulopathy) |
| Campomelic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/campomelic-dysplasia) |
| Cap myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/cap-myopathy) |
| Carnitine palmitoyltransferase I deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/carnitine-palmitoyltransferase-i-deficiency) |
| Carpenter syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/carpenter-syndrome) |
| Cartilage-hair hypoplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/cartilage-hair-hypoplasia) |
| Catecholaminergic polymorphic ventricular tachycardia | [MedlinePlus](https://medlineplus.gov/genetics/condition/catecholaminergic-polymorphic-ventricular-tachycardia) |
| CATSPER1-related nonsyndromic male infertility | [MedlinePlus](https://medlineplus.gov/genetics/condition/catsper1-related-nonsyndromic-male-infertility) |
| Central precocious puberty | [MedlinePlus](https://medlineplus.gov/genetics/condition/central-precocious-puberty) |
| Cerebral autosomal dominant arteriopathy with subcortical infarcts and leukoencephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/cerebral-autosomal-dominant-arteriopathy-with-subcortical-infarcts-and-leukoencephalopathy) |
| Char syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/char-syndrome) |
| Charcot-Marie-Tooth disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/charcot-marie-tooth-disease) |
| Cherubism | [MedlinePlus](https://medlineplus.gov/genetics/condition/cherubism) |
| CHILD syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/child-syndrome) |
| Childhood myocerebrohepatopathy spectrum | [MedlinePlus](https://medlineplus.gov/genetics/condition/childhood-myocerebrohepatopathy-spectrum) |
| Chorea-acanthocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/chorea-acanthocytosis) |
| Choroideremia | [MedlinePlus](https://medlineplus.gov/genetics/condition/choroideremia) |
| Chronic granulomatous disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/chronic-granulomatous-disease) |
| CHST3-related skeletal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/chst3-related-skeletal-dysplasia) |
| CLN10 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln10-disease) |
| CLN11 disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/cln11-disease) |
| Cockayne syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cockayne-syndrome) |
| Coffin-Lowry syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/coffin-lowry-syndrome) |
| Cold-induced sweating syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cold-induced-sweating-syndrome) |
| Color vision deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/color-vision-deficiency) |
| Combined malonic and methylmalonic aciduria | [MedlinePlus](https://medlineplus.gov/genetics/condition/combined-malonic-and-methylmalonic-aciduria) |
| Common variable immune deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/common-variable-immune-deficiency) |
| Complement factor I deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/complement-factor-i-deficiency) |
| Congenital bilateral absence of the vas deferens | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-bilateral-absence-of-the-vas-deferens) |
| Congenital bile acid synthesis defect type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-bile-acid-synthesis-defect-type-2) |
| Congenital cataracts, facial dysmorphism, and neuropathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-cataracts-facial-dysmorphism-and-neuropathy) |
| Congenital central hypoventilation syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-central-hypoventilation-syndrome) |
| Congenital deafness with labyrinthine aplasia, microtia, and microdontia | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-deafness-with-labyrinthine-aplasia-microtia-and-microdontia) |
| Congenital diaphragmatic hernia | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-diaphragmatic-hernia) |
| Congenital generalized lipodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-generalized-lipodystrophy) |
| Congenital insensitivity to pain with anhidrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-insensitivity-to-pain-with-anhidrosis) |
| Congenital leptin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-leptin-deficiency) |
| Congenital mirror movement disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-mirror-movement-disorder) |
| Congenital plasminogen deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/congenital-plasminogen-deficiency) |
| Corticosteroid-binding globulin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/corticosteroid-binding-globulin-deficiency) |
| Corticosterone methyloxidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/corticosterone-methyloxidase-deficiency) |
| Costeff syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/costeff-syndrome) |
| Craniometaphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/craniometaphyseal-dysplasia) |
| Cri-du-chat syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/cri-du-chat-syndrome) |
| Crouzon syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/crouzon-syndrome) |
| Crouzon syndrome with acanthosis nigricans | [MedlinePlus](https://medlineplus.gov/genetics/condition/crouzon-syndrome-with-acanthosis-nigricans) |
| CUL3-related neurodevelopmental disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/cul3-related-neurodevelopmental-disorder) |
| Cytochrome P450 oxidoreductase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/cytochrome-p450-oxidoreductase-deficiency) |
| Danon disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/danon-disease) |
| Desmosterolosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/desmosterolosis) |
| Dihydropyrimidine dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/dihydropyrimidine-dehydrogenase-deficiency) |
| Dilated cardiomyopathy with ataxia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dilated-cardiomyopathy-with-ataxia-syndrome) |
| Distal hereditary motor neuropathy, type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/distal-hereditary-motor-neuropathy-type-ii) |
| Distal hereditary motor neuropathy, type V | [MedlinePlus](https://medlineplus.gov/genetics/condition/distal-hereditary-motor-neuropathy-type-v) |
| Distal myopathy 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/distal-myopathy-2) |
| DOCK8 immunodeficiency syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dock8-immunodeficiency-syndrome) |
| DOLK-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/dolk-congenital-disorder-of-glycosylation) |
| Donnai-Barrow syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/donnai-barrow-syndrome) |
| Dopamine beta-hydroxylase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/dopamine-beta-hydroxylase-deficiency) |
| Dopamine transporter deficiency syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/dopamine-transporter-deficiency-syndrome) |
| Duane-radial ray syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/duane-radial-ray-syndrome) |
| Dupuytren contracture | [MedlinePlus](https://medlineplus.gov/genetics/condition/dupuytren-contracture) |
| Dyserythropoietic anemia and thrombocytopenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/dyserythropoietic-anemia-and-thrombocytopenia) |
| Ehlers-Danlos syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ehlers-danlos-syndrome) |
| Emanuel syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/emanuel-syndrome) |
| Eosinophil peroxidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/eosinophil-peroxidase-deficiency) |
| Epidermolysis bullosa simplex | [MedlinePlus](https://medlineplus.gov/genetics/condition/epidermolysis-bullosa-simplex) |
| Epidermolytic hyperkeratosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/epidermolytic-hyperkeratosis) |
| Erythrokeratodermia variabilis et progressiva | [MedlinePlus](https://medlineplus.gov/genetics/condition/erythrokeratodermia-variabilis-et-progressiva) |
| Essential tremor | [MedlinePlus](https://medlineplus.gov/genetics/condition/essential-tremor) |
| Ethylmalonic encephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/ethylmalonic-encephalopathy) |
| Ewing sarcoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/ewing-sarcoma) |
| Familial acute myeloid leukemia with mutated CEBPA | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-acute-myeloid-leukemia-with-mutated-cebpa) |
| Familial candidiasis | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-candidiasis) |
| Familial encephalopathy with neuroserpin inclusion bodies | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-encephalopathy-with-neuroserpin-inclusion-bodies) |
| Familial glucocorticoid deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-glucocorticoid-deficiency) |
| Familial hemiplegic migraine | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-hemiplegic-migraine) |
| Familial hemophagocytic lymphohistiocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-hemophagocytic-lymphohistiocytosis) |
| Familial hypobetalipoproteinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-hypobetalipoproteinemia) |
| Familial isolated pituitary adenoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-isolated-pituitary-adenoma) |
| Familial lipoprotein lipase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-lipoprotein-lipase-deficiency) |
| Familial paroxysmal kinesigenic dyskinesia | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-paroxysmal-kinesigenic-dyskinesia) |
| Familial restrictive cardiomyopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/familial-restrictive-cardiomyopathy) |
| Floating-Harbor syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/floating-harbor-syndrome) |
| FOXP2-related speech and language disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/foxp2-related-speech-and-language-disorder) |
| Friedreich ataxia | [MedlinePlus](https://medlineplus.gov/genetics/condition/friedreich-ataxia) |
| Frontonasal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/frontonasal-dysplasia) |
| Fryns syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/fryns-syndrome) |
| Fumarase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/fumarase-deficiency) |
| Fundus albipunctatus | [MedlinePlus](https://medlineplus.gov/genetics/condition/fundus-albipunctatus) |
| Galactosemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/galactosemia) |
| Geleophysic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/geleophysic-dysplasia) |
| Generalized pustular psoriasis | [MedlinePlus](https://medlineplus.gov/genetics/condition/generalized-pustular-psoriasis) |
| Genetic epilepsy with febrile seizures plus | [MedlinePlus](https://medlineplus.gov/genetics/condition/genetic-epilepsy-with-febrile-seizures-plus) |
| Genitopatellar syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/genitopatellar-syndrome) |
| Ghosal hematodiaphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/ghosal-hematodiaphyseal-dysplasia) |
| Giant congenital melanocytic nevus | [MedlinePlus](https://medlineplus.gov/genetics/condition/giant-congenital-melanocytic-nevus) |
| Glanzmann thrombasthenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/glanzmann-thrombasthenia) |
| Glucose-galactose malabsorption | [MedlinePlus](https://medlineplus.gov/genetics/condition/glucose-galactose-malabsorption) |
| Glutathione synthetase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/glutathione-synthetase-deficiency) |
| Glycogen storage disease type IX | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-ix) |
| Glycogen storage disease type VI | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-vi) |
| Glycogen storage disease type VII | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycogen-storage-disease-type-vii) |
| Glycoprotein VI deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/glycoprotein-vi-deficiency) |
| GM3 synthase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/gm3-synthase-deficiency) |
| Gnathodiaphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/gnathodiaphyseal-dysplasia) |
| GNE myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/gne-myopathy) |
| Gordon Holmes syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/gordon-holmes-syndrome) |
| GRIN2B-related neurodevelopmental disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/grin2b-related-neurodevelopmental-disorder) |
| GRN-related frontotemporal lobar degeneration | [MedlinePlus](https://medlineplus.gov/genetics/condition/grn-related-frontotemporal-lobar-degeneration) |
| Guanidinoacetate methyltransferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/guanidinoacetate-methyltransferase-deficiency) |
| Hartsfield syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hartsfield-syndrome) |
| Head and neck squamous cell carcinoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/head-and-neck-squamous-cell-carcinoma) |
| Hennekam syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hennekam-syndrome) |
| Hepatic lipase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/hepatic-lipase-deficiency) |
| Hereditary fibrosing poikiloderma with tendon contractures, myopathy, and pulmonary fibrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-fibrosing-poikiloderma-with-tendon-contractures-myopathy-and-pulmonary-fibrosis) |
| Hereditary fructose intolerance | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-fructose-intolerance) |
| Hereditary hemorrhagic telangiectasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-hemorrhagic-telangiectasia) |
| Hereditary leiomyomatosis and renal cell cancer | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-leiomyomatosis-and-renal-cell-cancer) |
| Hereditary paraganglioma-pheochromocytoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-paraganglioma-pheochromocytoma) |
| Hereditary sensory and autonomic neuropathy type IE | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-sensory-and-autonomic-neuropathy-type-ie) |
| Hereditary xanthinuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/hereditary-xanthinuria) |
| Hirschsprung disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/hirschsprung-disease) |
| Histiocytosis-lymphadenopathy plus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/histiocytosis-lymphadenopathy-plus-syndrome) |
| Horizontal gaze palsy with progressive scoliosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/horizontal-gaze-palsy-with-progressive-scoliosis) |
| Hutchinson-Gilford progeria syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hutchinson-gilford-progeria-syndrome) |
| Hyperkalemic periodic paralysis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperkalemic-periodic-paralysis) |
| Hyperparathyroidism-jaw tumor syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperparathyroidism-jaw-tumor-syndrome) |
| Hyperphosphatemic familial tumoral calcinosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/hyperphosphatemic-familial-tumoral-calcinosis) |
| Hypochondroplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypochondroplasia) |
| Hypochromic microcytic anemia with iron overload | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypochromic-microcytic-anemia-with-iron-overload) |
| Hypohidrotic ectodermal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/hypohidrotic-ectodermal-dysplasia) |
| Hystrix-like ichthyosis with deafness | [MedlinePlus](https://medlineplus.gov/genetics/condition/hystrix-like-ichthyosis-with-deafness) |
| Idiopathic inflammatory myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/idiopathic-inflammatory-myopathy) |
| IMAGe syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/image-syndrome) |
| Imerslund-Gräsbeck syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/imerslund-grasbeck-syndrome) |
| Infantile-onset ascending hereditary spastic paralysis | [MedlinePlus](https://medlineplus.gov/genetics/condition/infantile-onset-ascending-hereditary-spastic-paralysis) |
| Intrahepatic cholestasis of pregnancy | [MedlinePlus](https://medlineplus.gov/genetics/condition/intrahepatic-cholestasis-of-pregnancy) |
| Intranuclear rod myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/intranuclear-rod-myopathy) |
| Isolated congenital asplenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-congenital-asplenia) |
| Isolated Duane retraction syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-duane-retraction-syndrome) |
| Isolated growth hormone deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-growth-hormone-deficiency) |
| Isolated hyperchlorhidrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-hyperchlorhidrosis) |
| Isolated lissencephaly sequence | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-lissencephaly-sequence) |
| Isolated Pierre Robin sequence | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-pierre-robin-sequence) |
| Isolated sulfite oxidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/isolated-sulfite-oxidase-deficiency) |
| Jervell and Lange-Nielsen syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/jervell-and-lange-nielsen-syndrome) |
| Juvenile myoclonic epilepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/juvenile-myoclonic-epilepsy) |
| Juvenile polyposis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/juvenile-polyposis-syndrome) |
| Keratitis-ichthyosis-deafness syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/keratitis-ichthyosis-deafness-syndrome) |
| Keratoconus | [MedlinePlus](https://medlineplus.gov/genetics/condition/keratoconus) |
| Kindler epidermolysis bullosa | [MedlinePlus](https://medlineplus.gov/genetics/condition/kindler-epidermolysis-bullosa) |
| Kleefstra syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kleefstra-syndrome) |
| Klinefelter syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/klinefelter-syndrome) |
| Knobloch syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/knobloch-syndrome) |
| Kuskokwim syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/kuskokwim-syndrome) |
| L1 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/l1-syndrome) |
| Lactate dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/lactate-dehydrogenase-deficiency) |
| Lamellar ichthyosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/lamellar-ichthyosis) |
| Langer mesomelic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/langer-mesomelic-dysplasia) |
| Langerhans cell histiocytosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/langerhans-cell-histiocytosis) |
| Laron syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/laron-syndrome) |
| Lateral meningocele syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lateral-meningocele-syndrome) |
| Leber hereditary optic neuropathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/leber-hereditary-optic-neuropathy) |
| Lennox-Gastaut syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lennox-gastaut-syndrome) |
| Long-chain 3-hydroxyacyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/long-chain-3-hydroxyacyl-coa-dehydrogenase-deficiency) |
| Lymphedema-distichiasis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/lymphedema-distichiasis-syndrome) |
| Macrozoospermia | [MedlinePlus](https://medlineplus.gov/genetics/condition/macrozoospermia) |
| Maffucci syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/maffucci-syndrome) |
| Majeed syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/majeed-syndrome) |
| Mandibuloacral dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/mandibuloacral-dysplasia) |
| Maturity-onset diabetes of the young | [MedlinePlus](https://medlineplus.gov/genetics/condition/maturity-onset-diabetes-of-the-young) |
| MECP2-related severe neonatal encephalopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/mecp2-related-severe-neonatal-encephalopathy) |
| Meesmann corneal dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/meesmann-corneal-dystrophy) |
| Megalencephalic leukoencephalopathy with subcortical cysts | [MedlinePlus](https://medlineplus.gov/genetics/condition/megalencephalic-leukoencephalopathy-with-subcortical-cysts) |
| Meier-Gorlin syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/meier-gorlin-syndrome) |
| Melnick-Needles syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/melnick-needles-syndrome) |
| Melorheostosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/melorheostosis) |
| Menkes syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/menkes-syndrome) |
| Metachromatic leukodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/metachromatic-leukodystrophy) |
| Metatropic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/metatropic-dysplasia) |
| Microcephalic osteodysplastic primordial dwarfism type II | [MedlinePlus](https://medlineplus.gov/genetics/condition/microcephalic-osteodysplastic-primordial-dwarfism-type-ii) |
| Microcephaly, seizures, and developmental delay | [MedlinePlus](https://medlineplus.gov/genetics/condition/microcephaly-seizures-and-developmental-delay) |
| Microvillus inclusion disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/microvillus-inclusion-disease) |
| Miller syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/miller-syndrome) |
| Milroy disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/milroy-disease) |
| Mitochondrial complex I deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-complex-i-deficiency) |
| Mitochondrial encephalomyopathy, lactic acidosis, and stroke-like episodes | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-encephalomyopathy-lactic-acidosis-and-stroke-like-episodes) |
| Mitochondrial neurogastrointestinal encephalopathy disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/mitochondrial-neurogastrointestinal-encephalopathy-disease) |
| Motion sickness | [MedlinePlus](https://medlineplus.gov/genetics/condition/motion-sickness) |
| Moyamoya disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/moyamoya-disease) |
| Mucolipidosis II alpha/beta | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucolipidosis-ii-alpha-beta) |
| Mucolipidosis III gamma | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucolipidosis-iii-gamma) |
| Mucolipidosis type IV | [MedlinePlus](https://medlineplus.gov/genetics/condition/mucolipidosis-type-iv) |
| Muenke syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/muenke-syndrome) |
| Multicentric osteolysis, nodulosis, and arthropathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/multicentric-osteolysis-nodulosis-and-arthropathy) |
| Multiminicore disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiminicore-disease) |
| Multiple familial trichoepithelioma | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-familial-trichoepithelioma) |
| Multiple system atrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/multiple-system-atrophy) |
| MUTYH-associated polyposis  | [MedlinePlus](https://medlineplus.gov/genetics/condition/mutyh-associated-polyposis) |
| MyD88 deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/myd88-deficiency) |
| Myoclonus-dystonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/myoclonus-dystonia) |
| Myosin storage myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/myosin-storage-myopathy) |
| Müllerian aplasia and hyperandrogenism | [MedlinePlus](https://medlineplus.gov/genetics/condition/mullerian-aplasia-and-hyperandrogenism) |
| Naegeli-Franceschetti-Jadassohn syndrome/dermatopathia pigmentosa reticularis | [MedlinePlus](https://medlineplus.gov/genetics/condition/naegeli-franceschetti-jadassohn-syndrome-dermatopathia-pigmentosa-reticularis) |
| Nearsightedness | [MedlinePlus](https://medlineplus.gov/genetics/condition/nearsightedness) |
| Nemaline myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/nemaline-myopathy) |
| Netherton syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/netherton-syndrome) |
| Neuroblastoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/neuroblastoma) |
| Neutral lipid storage disease with myopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/neutral-lipid-storage-disease-with-myopathy) |
| NGLY1-congenital disorder of deglycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/ngly1-congenital-disorder-of-deglycosylation) |
| Nicolaides-Baraitser syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/nicolaides-baraitser-syndrome) |
| Nonsyndromic congenital nail disorder 10 | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-congenital-nail-disorder-10) |
| Nonsyndromic dilated cardiomyopathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-dilated-cardiomyopathy) |
| Nonsyndromic hearing loss | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-hearing-loss) |
| Nonsyndromic holoprosencephaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/nonsyndromic-holoprosencephaly) |
| Noonan syndrome with multiple lentigines | [MedlinePlus](https://medlineplus.gov/genetics/condition/noonan-syndrome-with-multiple-lentigines) |
| Norrie disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/norrie-disease) |
| Oculofaciocardiodental syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/oculofaciocardiodental-syndrome) |
| Ollier disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/ollier-disease) |
| Omenn syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/omenn-syndrome) |
| Ophthalmo-acromelic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/ophthalmo-acromelic-syndrome) |
| Opioid addiction | [MedlinePlus](https://medlineplus.gov/genetics/condition/opioid-addiction) |
| Opitz G/BBB syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/opitz-g-bbb-syndrome) |
| Optic atrophy type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/optic-atrophy-type-1) |
| Osteogenesis imperfecta | [MedlinePlus](https://medlineplus.gov/genetics/condition/osteogenesis-imperfecta) |
| Osteopetrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/osteopetrosis) |
| Otospondylomegaepiphyseal dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/otospondylomegaepiphyseal-dysplasia) |
| Otulipenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/otulipenia) |
| Pachyonychia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/pachyonychia-congenita) |
| Pallister-Hall syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pallister-hall-syndrome) |
| Palmoplantar keratoderma with deafness | [MedlinePlus](https://medlineplus.gov/genetics/condition/palmoplantar-keratoderma-with-deafness) |
| Paramyotonia congenita | [MedlinePlus](https://medlineplus.gov/genetics/condition/paramyotonia-congenita) |
| Partington syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/partington-syndrome) |
| PDGFRB-associated chronic eosinophilic leukemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/pdgfrb-associated-chronic-eosinophilic-leukemia) |
| Pearson syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pearson-syndrome) |
| Pelizaeus-Merzbacher-like disease type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/pelizaeus-merzbacher-like-disease-type-1) |
| Pendred syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pendred-syndrome) |
| Peroxisomal acyl-CoA oxidase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/peroxisomal-acyl-coa-oxidase-deficiency) |
| Perry syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/perry-syndrome) |
| Persistent Müllerian duct syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/persistent-mullerian-duct-syndrome) |
| Peters anomaly | [MedlinePlus](https://medlineplus.gov/genetics/condition/peters-anomaly) |
| Peutz-Jeghers syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/peutz-jeghers-syndrome) |
| PGM3-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/pgm3-congenital-disorder-of-glycosylation) |
| Phosphoglycerate kinase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/phosphoglycerate-kinase-deficiency) |
| Poikiloderma with neutropenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/poikiloderma-with-neutropenia) |
| Pol III-related leukodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/pol-iii-related-leukodystrophy) |
| Polycystic kidney disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/polycystic-kidney-disease) |
| Polymicrogyria | [MedlinePlus](https://medlineplus.gov/genetics/condition/polymicrogyria) |
| Popliteal pterygium syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/popliteal-pterygium-syndrome) |
| Potassium-aggravated myotonia | [MedlinePlus](https://medlineplus.gov/genetics/condition/potassium-aggravated-myotonia) |
| Potocki-Lupski syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/potocki-lupski-syndrome) |
| Primary carnitine deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-carnitine-deficiency) |
| Primary hyperoxaluria | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-hyperoxaluria) |
| Primary myelofibrosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-myelofibrosis) |
| Primary spontaneous pneumothorax | [MedlinePlus](https://medlineplus.gov/genetics/condition/primary-spontaneous-pneumothorax) |
| Prion disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/prion-disease) |
| Progressive external ophthalmoplegia | [MedlinePlus](https://medlineplus.gov/genetics/condition/progressive-external-ophthalmoplegia) |
| Progressive osseous heteroplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/progressive-osseous-heteroplasia) |
| Protein S deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/protein-s-deficiency) |
| Prothrombin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/prothrombin-deficiency) |
| Proximal 18q deletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/proximal-18q-deletion-syndrome) |
| Pseudoachondroplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/pseudoachondroplasia) |
| Pseudohypoaldosteronism type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/pseudohypoaldosteronism-type-1) |
| Pseudoxanthoma elasticum | [MedlinePlus](https://medlineplus.gov/genetics/condition/pseudoxanthoma-elasticum) |
| Pulmonary veno-occlusive disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/pulmonary-veno-occlusive-disease) |
| PURA syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/pura-syndrome) |
| Pyle disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/pyle-disease) |
| Pyridoxine-dependent epilepsy | [MedlinePlus](https://medlineplus.gov/genetics/condition/pyridoxine-dependent-epilepsy) |
| Recombinant 8 syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/recombinant-8-syndrome) |
| Renal coloboma syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/renal-coloboma-syndrome) |
| Renal hypouricemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/renal-hypouricemia) |
| Restless legs syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/restless-legs-syndrome) |
| Retinoblastoma | [MedlinePlus](https://medlineplus.gov/genetics/condition/retinoblastoma) |
| Rett syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rett-syndrome) |
| Rhabdoid tumor predisposition syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rhabdoid-tumor-predisposition-syndrome) |
| Rubinstein-Taybi syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/rubinstein-taybi-syndrome) |
| SADDAN | [MedlinePlus](https://medlineplus.gov/genetics/condition/saddan) |
| Scalp-ear-nipple syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/scalp-ear-nipple-syndrome) |
| Schwartz-Jampel syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/schwartz-jampel-syndrome) |
| Seasonal affective disorder | [MedlinePlus](https://medlineplus.gov/genetics/condition/seasonal-affective-disorder) |
| Senior-Løken syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/senior-loken-syndrome) |
| Septo-optic dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/septo-optic-dysplasia) |
| Severe congenital neutropenia | [MedlinePlus](https://medlineplus.gov/genetics/condition/severe-congenital-neutropenia) |
| Sheldon-Hall syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sheldon-hall-syndrome) |
| Short QT syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/short-qt-syndrome) |
| Short-chain acyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/short-chain-acyl-coa-dehydrogenase-deficiency) |
| Short/branched chain acyl-CoA dehydrogenase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/short-branched-chain-acyl-coa-dehydrogenase-deficiency) |
| Shprintzen-Goldberg syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/shprintzen-goldberg-syndrome) |
| Sialuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/sialuria) |
| Sick sinus syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sick-sinus-syndrome) |
| SLC35A2-congenital disorder of glycosylation | [MedlinePlus](https://medlineplus.gov/genetics/condition/slc35a2-congenital-disorder-of-glycosylation) |
| SLC4A1-associated distal renal tubular acidosis | [MedlinePlus](https://medlineplus.gov/genetics/condition/slc4a1-associated-distal-renal-tubular-acidosis) |
| Small fiber neuropathy | [MedlinePlus](https://medlineplus.gov/genetics/condition/small-fiber-neuropathy) |
| Smith-Kingsmore syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/smith-kingsmore-syndrome) |
| Smith-Magenis syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/smith-magenis-syndrome) |
| SOST-related sclerosing bone dysplasia | [MedlinePlus](https://medlineplus.gov/genetics/condition/sost-related-sclerosing-bone-dysplasia) |
| Sotos syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sotos-syndrome) |
| Spastic paraplegia type 2 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-2) |
| Spastic paraplegia type 8 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spastic-paraplegia-type-8) |
| Spinal muscular atrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinal-muscular-atrophy) |
| Spinal muscular atrophy with respiratory distress type 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinal-muscular-atrophy-with-respiratory-distress-type-1) |
| Spinocerebellar ataxia type 6 | [MedlinePlus](https://medlineplus.gov/genetics/condition/spinocerebellar-ataxia-type-6) |
| STING-associated vasculopathy with onset in infancy | [MedlinePlus](https://medlineplus.gov/genetics/condition/sting-associated-vasculopathy-with-onset-in-infancy) |
| Stormorken syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/stormorken-syndrome) |
| Succinyl-CoA:3-ketoacid CoA transferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/succinyl-coa3-ketoacid-coa-transferase-deficiency) |
| SUCLA2-related mitochondrial DNA depletion syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/sucla2-related-mitochondrial-dna-depletion-syndrome) |
| Tay-Sachs disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/tay-sachs-disease) |
| Tetra-amelia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/tetra-amelia-syndrome) |
| Tetrasomy 18p | [MedlinePlus](https://medlineplus.gov/genetics/condition/tetrasomy-18p) |
| Thiamine-responsive megaloblastic anemia syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/thiamine-responsive-megaloblastic-anemia-syndrome) |
| Thiopurine S-methyltransferase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/thiopurine-s-methyltransferase-deficiency) |
| Thrombotic thrombocytopenic purpura | [MedlinePlus](https://medlineplus.gov/genetics/condition/thrombotic-thrombocytopenic-purpura) |
| Tibial muscular dystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/tibial-muscular-dystrophy) |
| Timothy syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/timothy-syndrome) |
| TK2-related mitochondrial DNA depletion syndrome, myopathic form | [MedlinePlus](https://medlineplus.gov/genetics/condition/tk2-related-mitochondrial-dna-depletion-syndrome-myopathic-form) |
| Townes-Brocks Syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/townes-brocks-syndrome) |
| Transcobalamin deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/transcobalamin-deficiency) |
| Trichohepatoenteric syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/trichohepatoenteric-syndrome) |
| Trichorhinophalangeal syndrome type I | [MedlinePlus](https://medlineplus.gov/genetics/condition/trichorhinophalangeal-syndrome-type-i) |
| Trimethylaminuria | [MedlinePlus](https://medlineplus.gov/genetics/condition/trimethylaminuria) |
| Triosephosphate isomerase deficiency | [MedlinePlus](https://medlineplus.gov/genetics/condition/triosephosphate-isomerase-deficiency) |
| Trisomy 13 | [MedlinePlus](https://medlineplus.gov/genetics/condition/trisomy-13) |
| TUBB4A-related leukodystrophy | [MedlinePlus](https://medlineplus.gov/genetics/condition/tubb4a-related-leukodystrophy) |
| Tuberous sclerosis complex | [MedlinePlus](https://medlineplus.gov/genetics/condition/tuberous-sclerosis-complex) |
| Tumor necrosis factor receptor-associated periodic syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/tumor-necrosis-factor-receptor-associated-periodic-syndrome) |
| Uncombable hair syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/uncombable-hair-syndrome) |
| VACTERL association | [MedlinePlus](https://medlineplus.gov/genetics/condition/vacterl-association) |
| Wagner syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/wagner-syndrome) |
| Waldenström macroglobulinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/waldenstrom-macroglobulinemia) |
| Warsaw breakage syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/warsaw-breakage-syndrome) |
| Williams syndrome | [MedlinePlus](https://medlineplus.gov/genetics/condition/williams-syndrome) |
| Wilson disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/wilson-disease) |
| X-linked acrogigantism | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-acrogigantism) |
| X-linked agammaglobulinemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-agammaglobulinemia) |
| X-linked chondrodysplasia punctata 1 | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-chondrodysplasia-punctata-1) |
| X-linked lymphoproliferative disease | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-lymphoproliferative-disease) |
| X-linked sideroblastic anemia | [MedlinePlus](https://medlineplus.gov/genetics/condition/x-linked-sideroblastic-anemia) |
| Xeroderma pigmentosum | [MedlinePlus](https://medlineplus.gov/genetics/condition/xeroderma-pigmentosum) |
