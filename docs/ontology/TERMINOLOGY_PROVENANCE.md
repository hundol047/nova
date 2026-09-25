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

| File | System |
| ---- | ------ |
| `snomed.json` | SNOMED CT |
| `icd11.json` | ICD-11 |
| `icd10.json` | ICD-10 / ICD-10-CM |

Snapshot files are **git-ignored** and never committed. If a snapshot is absent, the provider
**yields nothing** — it never fabricates concepts. See `snapshots/README.md` for the schema.

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
