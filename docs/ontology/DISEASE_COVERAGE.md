# N.O.V.A. Disease Coverage

N.O.V.A. reasons over a **tiered disease universe**, not a fixed list. Coverage numbers below are
**reported from the actual catalog** by `scripts/report_disease_coverage.py`, never aspirational.

> N.O.V.A. does **not** claim to diagnose "all diseases" or achieve "100% diagnostic accuracy." It
> provides a **broad, ontology-backed differential diagnosis** with explicit uncertainty. Conditions
> outside its curated knowledge are surfaced as *possible* or *unknown*, never forced into a label.

## Tiers

| Tier | Meaning | Reasoning support |
| ---- | ------- | ----------------- |
| **Tier-1 (deep)** | The 34 hand-authored profiles with discriminating questions/exams/tests, confirmatory findings, red flags. | Full deterministic reasoning (unchanged from prior releases). |
| **Tier-2 (structured)** | Broad curated conditions across specialties: name, aliases (EN + KR), category, urgency hint, ICD-10 anchor. | Searchable + rankable candidate; generic workup guidance only. |
| **Tier-3 (ontology-only)** | A concept known only from an operator-supplied terminology snapshot (SNOMED/ICD). | Retrievable as a *named possibility*; **no curated clinical claims**. |

A concept the catalog cannot curate is marked **`NOT_CURATED`** and its clinical fields are treated
as **absent** — we never fabricate detail to inflate the count. The count-honesty rule is explicit:
*정확도를 희생해서 숫자를 맞추지 않는다* — we never fabricate clinical detail to hit a coverage number.

## Current coverage (regenerate to refresh)

Run:

```bash
python scripts/report_disease_coverage.py          # human-readable
python scripts/report_disease_coverage.py --json    # machine-readable
```

There are **two distinct numbers**, reported separately and honestly:

### 1. Bundled (shipped in-repo, no snapshot required)

- **1,280 bundled concepts** = **34 Tier-1 deep** + **1,246 Tier-2 structured** + **0 Tier-3**.
- `coverage_target_met=true` (bundled ≥ 500). `searchable_target_met=false` **on the bundle alone**
  — the ≥ 5,000 searchable universe requires the Tier-3 snapshot (below).
- **0 duplicate concept ids**; every bundled concept has at least name + aliases + category.
- **~35 specialty categories** spanning cardiovascular, vascular, pulmonary, neurology, GI,
  hepatology, nephrology, urology, endocrine/metabolic, genetics/congenital, infectious,
  hematology, oncology, rheumatology, immunology, allergy, dermatology, psychiatric, toxicology,
  environmental, obstetric, gynecology, pediatric, ENT, ophthalmology, orthopedics, trauma
  (balanced, no single specialty dominates).

### 2. Full searchable universe (with reproducible Tier-3 snapshot)

- **5,651 total searchable** = **34 Tier-1 deep** + **1,246 Tier-2 structured** + **4,371 Tier-3
  ontology-only**. `searchable_target_met=true` (≥ 5,000).
- The Tier-3 layer is added by an **operator-supplied terminology snapshot**. The repo ships a
  **non-restricted synthetic snapshot generator** (`scripts/build_tier3_synthetic_snapshot.py`) so
  the ≥ 5,000 universe is **reproducible in CI/tests without shipping any licensed content**:

  ```bash
  python scripts/build_tier3_synthetic_snapshot.py --target 4200
  ```

  The generated `nova_agent/ontology/snapshots/custom.json` is **gitignored** (never committed).
  Real SNOMED/ICD content is license-restricted and is loaded only from an operator's local
  snapshot at runtime — see `TERMINOLOGY_PROVENANCE.md`.

The bundled catalog is generated deterministically from `scripts/build_tier2_catalog.py`
(which merges `scripts/tier2_catalog_expansion{,2,3}.py`); re-run to regenerate. Installing a
terminology snapshot adds Tier-3 concepts on top, raising the searchable universe **without adding
any curated clinical claims** (every Tier-3 concept is `NOT_CURATED`).

> **Historical snapshot:** an earlier release documented a **516-concept** bundle (34 Tier-1 + 482
> Tier-2, 0 Tier-3). The Tier-2 layer has since been expanded to 1,246 curated conditions; the
> historical 516 figure is retained only for provenance and no longer reflects the current catalog.

> Honest framing: N.O.V.A. is **not** a "5,000-disease classifier" and does **not** perform a naive
> 5,000-way classification. It is a **broad, ontology-backed retrieval → multi-specialty router →
> deterministic safety-recall → high-precision clinical reranker → narrowed LLM reasoner →
> open-world UNKNOWN/OOD detector**. Coverage numbers describe what is *searchable*, not a claim of
> diagnostic accuracy on all of them. See `docs/learning/ARCHITECTURE.md` for the retrieval pipeline
> and `docs/evaluation/FIVE_THOUSAND_DISEASE_COMPARISON.md` for baseline-vs-candidate metrics.

## Open-world outcomes

Every retrieval resolves to one of four first-class outcomes (`nova_agent/open_world.py`):

- `KNOWN_CONDITION` — confident match to a curated (Tier-1/2) concept.
- `POSSIBLE_UNMAPPED_CONDITION` — candidates exist but only weakly / Tier-3-only → *possible*.
- `INSUFFICIENT_INFORMATION` — too little signal to retrieve responsibly → gather more.
- `UNKNOWN_PRESENTATION` — nothing plausible matched → explicitly outside known coverage.

An LLM's free-text diagnosis is normalized to a canonical concept when confident, else preserved
verbatim as `UNMAPPED_LLM_DIAGNOSIS` — it is **never** coerced into a nearby known disease.
