# Terminology snapshots (operator-supplied, NOT committed)

This directory is where an operator places **local, license-respecting** terminology snapshots so
N.O.V.A.'s Tier-3 ontology layer can name conditions beyond the curated Tier-1/Tier-2 catalog.

The repository ships **no** SNOMED CT / ICD-11 / ICD-10 content. These terminologies carry their own
licensing/attribution terms, so bundling them is not permitted. The providers
(`nova_agent/ontology/providers/`) read a snapshot **if and only if** the operator supplies one; if
a snapshot is absent, the provider yields **nothing** — it never fabricates concepts to inflate
coverage.

## Expected files (all optional)

| File            | System   | Provider              |
| --------------- | -------- | --------------------- |
| `snomed.json`   | SNOMEDCT | `providers/snomed.py` |
| `icd11.json`    | ICD11    | `providers/icd11.py`  |
| `icd10.json`    | ICD10    | `providers/icd10.py`  |

## Snapshot schema

```json
{
  "system": "SNOMEDCT",
  "concepts": [
    {
      "code": "74400008",
      "display": "Appendicitis",
      "aliases": ["appendicitis"],
      "semantic_type": "DISEASE",
      "parents": ["18526009"],
      "children": []
    }
  ]
}
```

`*.json` files here are **git-ignored** (see `.gitignore`) and must never be committed.
See `docs/ontology/TERMINOLOGY_PROVENANCE.md` for licensing guidance.
