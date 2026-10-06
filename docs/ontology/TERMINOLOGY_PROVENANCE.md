# Terminology Provenance & Licensing

N.O.V.A.'s ontology layer can map and name conditions using standard medical terminologies
(SNOMED CT, ICD-11, ICD-10). This document records **where terminology content comes from** and the
**licensing rules** the implementation respects.

## The repository ships terminology-free

We bundle **no** SNOMED CT, ICD-11, or proprietary ICD-10 content. Reasons:

- **SNOMED CT** is licensed (SNOMED International / national release centres). Redistribution
  requires an affiliate licence.
- **ICD-11** (WHO) carries its own licence and attribution terms.
- Even where a code system is freely redistributable (e.g. ICD-10-CM is US public domain), we keep
  the repo terminology-free so the operator controls versioning and provenance.

## How terminology is supplied (operator-provided, local, offline)

Providers under `nova_agent/ontology/providers/` read a **local snapshot** the operator places at
`nova_agent/ontology/snapshots/<system>.json`:

| File | System | Provider |
| ---- | ------ | -------- |
| `snomed.json` | SNOMED CT | `SnomedProvider` |
| `icd11.json` | ICD-11 | `Icd11Provider` |
| `icd10.json` | ICD-10 / ICD-10-CM | `Icd10Provider` |
| `custom.json` | Operator / hospital-local terminology | `CustomProvider` |

The **`custom`** system (imported with `--source custom` or `--source hospital`, both normalized to
a `CUSTOM` code system) lets an operator load a **hospital-local terminology map** — codes and
concepts a site maintains internally that do not fit a standard release. It is treated identically
to any other Tier-3 source: searchable, `NOT_CURATED`, no fabricated clinical claims.

Snapshot files are **git-ignored** and never committed. If a snapshot is absent, the provider
**yields nothing** — it never fabricates concepts. See `snapshots/README.md` for the schema.

### Reproducible synthetic Tier-3 snapshot (for CI / tests only)

Because real SNOMED/ICD content cannot be committed, the repo ships a **non-restricted synthetic
generator** so the ≥ 5,000 searchable universe is reproducible without any licensed data:

```bash
python scripts/build_tier3_synthetic_snapshot.py --target 4200
```

This writes a `NOVASYNTH`-system snapshot to `nova_agent/ontology/snapshots/custom.json` (also
git-ignored). The synthetic concepts are **clearly non-clinical placeholders** used only to
exercise retrieval/router/rerank at scale and to make coverage/tests reproducible — they are
**never** presented as real diagnoses and are all `NOT_CURATED`. In a real deployment the operator
replaces this with a licensed snapshot.

## No runtime network calls

The ontology layer **never** calls an external terminology API at runtime. All lookups are served
from the local snapshot (or not at all). This keeps the system deployable in an air-gapped hospital
environment and avoids sending any query to a third party.

## The bundled ICD-10 anchors on Tier-2 concepts

Tier-2 catalog entries (`nova_agent/knowledge/tier2_catalog.json`) may carry an **ICD-10 code as a
convenience anchor**. These are widely-published category codes used only to aid mapping/search.
The operator's Tier-3 terminology snapshot remains the **authoritative** source for coding; the
anchors are clearly labelled `system: "ICD10"` and are not represented as an official code release.

## Attribution

When an operator loads a licensed terminology snapshot, they are responsible for complying with that
terminology's licence and attribution requirements in their deployment.



## Importing an operator terminology snapshot (Tier-3)

The repository ships **no** SNOMED CT / ICD-11 / ICD-10 content. An operator with a valid licence
converts their export into a local Tier-3 snapshot using the import CLI:

```bash
python scripts/import_terminology.py \
  --source snomed --input /path/to/export.json \
  --output nova_agent/ontology/snapshots/snomed.json      # or icd11 / icd10
```

Supported input formats: `json`, `csv`, `tsv`, and a normalized `rf2`-derived export (not raw RF2
release files). The importer validates and reports (dropping invalid rows): duplicate concept id,
missing preferred name, inactive concept, invalid hierarchy reference, cyclic hierarchy, unknown
code system, malformed synonym. Use `--dry-run --report report.json` to validate without writing.

Supported `--source` values: `snomed`, `icd11`, `icd10`, and `custom` / `hospital` (the last two
map to the `CUSTOM` code system for hospital-local terminology).

Runtime behavior:
- With a snapshot present, Tier-3 concepts become **searchable named possibilities** with
  synonym/code/hierarchy support — never treated as deeply-curated clinical evidence
  (`curation_status = NOT_CURATED`).
- With **no** snapshot, the ontology layer **degrades gracefully** to the bundled catalog
  (34 Tier-1 + 1,246 Tier-2 = 1,280 concepts, Tier-3 count = 0). No network call is ever made at
  runtime — all lookups are local.

Snapshot files live under `nova_agent/ontology/snapshots/*.json` and are **git-ignored** so
licensed content is never committed.

## Competition submission

The competition submission (`submission/`) declares **only `pydantic`** as a runtime dependency —
no torch, no terminology packages — and makes **no external terminology API calls**. The optional
`learning/` package and any Tier-3 snapshot are hospital-deployment concerns, excluded from the
submission artifact.
