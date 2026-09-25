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
as **absent** — we never fabricate detail to inflate the count.

## Current coverage (regenerate to refresh)

Run:

```bash
python scripts/report_disease_coverage.py          # human-readable
python scripts/report_disease_coverage.py --json    # machine-readable
```

At the time of writing the bundled catalog contains:

- **516 concepts total** = **34 Tier-1 deep** + **482 Tier-2 structured** + **0 Tier-3** (no
  terminology snapshot bundled — see `TERMINOLOGY_PROVENANCE.md`). `coverage_target_met=true`
  (bundled ≥ 500).
- **33 specialty categories** spanning cardiovascular, vascular, pulmonary, neurology, GI,
  hepatology, nephrology, urology, endocrine/metabolic, genetics/congenital, infectious,
  hematology, oncology, rheumatology, immunology, allergy, dermatology, psychiatric, toxicology,
  environmental, obstetric, gynecology, pediatric, ENT, ophthalmology, orthopedics, trauma
  (balanced, no single specialty dominates).
- **478 concepts carry an ICD-10 anchor**; **0 duplicate concept ids**; **0 NOT_CURATED** in the
  bundled set (every bundled concept has at least name + aliases + category).

The catalog is generated deterministically from `scripts/build_tier2_catalog.py`
(+ `scripts/tier2_catalog_extra.py`); re-run to regenerate. Installing an operator terminology
snapshot (via `scripts/import_terminology.py`) adds Tier-3 concepts on top, raising the searchable
universe without adding any curated clinical claims.

> Honest framing: N.O.V.A. is **not** a "5,000-disease classifier." It is a **broad,
> ontology-backed retrieval + high-precision clinical reranker + LLM reasoner + deterministic safety
> guard + open-world UNKNOWN/OOD detector**. Coverage numbers describe what is *searchable*, not a
> claim of diagnostic accuracy on all of them.

## Open-world outcomes

Every retrieval resolves to one of four first-class outcomes (`nova_agent/open_world.py`):

- `KNOWN_CONDITION` — confident match to a curated (Tier-1/2) concept.
- `POSSIBLE_UNMAPPED_CONDITION` — candidates exist but only weakly / Tier-3-only → *possible*.
- `INSUFFICIENT_INFORMATION` — too little signal to retrieve responsibly → gather more.
- `UNKNOWN_PRESENTATION` — nothing plausible matched → explicitly outside known coverage.

An LLM's free-text diagnosis is normalized to a canonical concept when confident, else preserved
verbatim as `UNMAPPED_LLM_DIAGNOSIS` — it is **never** coerced into a nearby known disease.
