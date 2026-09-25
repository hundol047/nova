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

- **174 concepts total** = **34 Tier-1 deep** + **140 Tier-2 structured** + **0 Tier-3** (no
  terminology snapshot bundled — see `TERMINOLOGY_PROVENANCE.md`).
- **18 specialty categories** (cardiovascular, pulmonary, GI, neuro, endocrine/metabolic,
  genitourinary/renal, infectious, heme/onc, rheum/msk, psychiatric, toxicology, environmental,
  dermatology, ENT, ophthalmology, obstetric, pediatric, plus the core categories).
- **136 concepts carry an ICD-10 anchor**; **0 duplicate concept ids**.

Installing an operator terminology snapshot adds Tier-3 concepts on top (potentially thousands),
raising the searchable universe without adding any curated clinical claims.

## Open-world outcomes

Every retrieval resolves to one of four first-class outcomes (`nova_agent/open_world.py`):

- `KNOWN_CONDITION` — confident match to a curated (Tier-1/2) concept.
- `POSSIBLE_UNMAPPED_CONDITION` — candidates exist but only weakly / Tier-3-only → *possible*.
- `INSUFFICIENT_INFORMATION` — too little signal to retrieve responsibly → gather more.
- `UNKNOWN_PRESENTATION` — nothing plausible matched → explicitly outside known coverage.

An LLM's free-text diagnosis is normalized to a canonical concept when confident, else preserved
verbatim as `UNMAPPED_LLM_DIAGNOSIS` — it is **never** coerced into a nearby known disease.
