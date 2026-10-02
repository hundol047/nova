# 3,628 candidate entries: scope and readiness

The requested 2.5-fold inventory is ceil(1,451 × 2.5) = **3,628**, an addition of **2,177**.
There are still **68 scored rule entries**. The **3,560 reference-only entries** comprise
204 MedlinePlus health topics, 1,179 MedlinePlus Genetics conditions and 2,177 Orphanet disorders.
This expands retrieval coverage, not the number of clinically validated diagnoses.

## Source and selection

Source: [Orphanet July 2026 nomenclature pack](https://www.orphacode.org/pack-nomenclature/),
`ORPHAnomenclature_en_2026.xml`, extracted 2026-06-23 07:28:38.
Attribution: Orphadata / Orphanet © INSERM. July 2026.
License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
English definitions were selected, HTML removed and whitespace normalized. Each runtime
entry and retrieved prompt retains attribution, an original source link and the license link.

Only Active records at the Disorder classification level, typed Disease, Clinical syndrome
or Malformation syndrome, with an English definition were eligible (5,311 source records).
Groups, subtypes, inactive/historical entities and definition-free records were excluded.
Frozen SHA256 name ordering provided reproducible engineering selection, not clinical priority.
Normalized names and aliases do not overlap the previous inventory or each other; this does
not prove the absence of conceptual or subtype overlap between different terminologies.

The complete additions are in
[`selection.txt`](../nova_agent/knowledge/orphanet_candidates/selection.txt), with definitions,
identifiers and source links in [`catalog.json`](../nova_agent/knowledge/orphanet_candidates/catalog.json).
The manifest records source, selection and catalog checksums. Reproduce with:

```sh
python scripts/import_orphanet_candidates.py --xml /path/to/ORPHAnomenclature_en_2026.xml
```

## Behavior and validation limits

Exact canonical-title queries use a navigation lookup so punctuation and words such as
“without” in a disease name do not erase the identity. Clinical narrative queries retain
negation, family-history, tentative and historical filtering. Title resolution is not
patient diagnosis. References stay LOW confidence and cannot authorize a final diagnosis.
Reference definitions never become patient findings or modify existing rule scores.

All 4,069 automated tests passed. Title lookup and provenance checks cover all 3,560 references. The saved mock regression
covers the existing 205 scored cases (plus three unscored cases), not the newly added disorders.
See the machine-readable reports in `evaluation/` for executed results. Passed synthetic
cases are archived with source fingerprints; none are automatically used for training.

**Clinical accuracy is unknown, including the prior 99% target.** No independent adjudicated
clinical dataset or real-model responses are available. The prior potassium parser improvement
(20/43 to 43/43 development probes) is not clinical diagnostic accuracy. Ollama model weights
remain unavailable in this environment; no persistent model service or retraining is running.
