# 5,000-Diagnosis Architecture: Baseline vs Candidate

This document records the **BASELINE vs CANDIDATE** comparison for the 5,000-searchable-diagnosis
retrieval architecture (PHASE 1) and the governance decision the promotion gate would enforce.

> **Honesty banner — read first.** Every number below is measured on a **synthetic labeled eval
> set** built from the (synthetic Tier-3) catalog. It validates the **retrieval/rerank plumbing at
> scale**, not clinical performance. **REAL clinical superiority is NOT VERIFIED** — this repository
> has no real hospital patient data, and this environment has no torch/pydantic/network, so the
> torch reranker training path is `IMPLEMENTED_BUT_NOT_EXECUTED` and the FastAPI/Blind runs are
> deferred to CI. We never present synthetic mechanics numbers as diagnostic accuracy, and we never
> fabricate detail to hit a number (*정확도를 희생해서 숫자를 맞추지 않는다*).

## Definitions

| Arm | What it is |
| --- | ---------- |
| **BASELINE** | Lexical-only retrieval over the catalog (no embedding index fusion). Represents the pre-PHASE-1 shipped behavior. |
| **CANDIDATE** | The ≥ 5,000-searchable architecture: embedding + lexical + code fusion over the full index → multi-specialty router → deterministic safety-recall → deep reranker → narrowed LLM → open-world outcome. |

Both arms are measured on the **same** synthetic eval set with the same seed
(`scripts/compare_5000_baseline.py --json`, `--n 250 --seed 13`).

## Coverage under test

| Layer | Count |
| ----- | ----- |
| Tier-1 deep (hand-authored) | 34 |
| Tier-2 structured (curated) | 1,246 |
| Tier-3 ontology-only (synthetic snapshot) | 4,371 |
| **Total searchable** | **5,651** (`searchable_target_met = true`, ≥ 5,000) |
| Duplicate concept ids | 0 |

(Regenerate with `python scripts/build_tier3_synthetic_snapshot.py --target 4200` then
`python scripts/report_disease_coverage.py`.)

## Measured metrics (synthetic, n=250, seed=13)

| Metric | BASELINE | CANDIDATE |
| ------ | -------- | --------- |
| top_1 | 0.984 | 0.988 |
| top_3 | 1.000 | 1.000 |
| top_5 | 1.000 | 1.000 |
| top_10 | 1.000 | 1.000 |
| recall@20 | 1.000 | 1.000 |
| recall@50 | 1.000 | 1.000 |
| recall@100 | 1.000 | 1.000 |
| critical_recall@5 | 1.000 | 1.000 |
| critical_recall@20 | 1.000 | 1.000 |
| critical_recall@100 | 1.000 | 1.000 |
| critical_miss_rate@100 | 0.000 | 0.000 |
| per-specialty recall@100 | 1.0 across all specialties | 1.0 across all specialties |

Additional retrieval measurements (from `learning/retrieval/eval_synthetic.py`): recall@200 = 1.0,
recall@20 = 0.996 on a larger draw; index build ≈ 0.2 s over 5,651 concepts; query ≈ 72 ms.

## Gate decision

`learning/baseline.MultiMetricGate.compare(baseline, candidate)` →

```
decision: PROMOTE
reasons: ['all gate criteria satisfied']
```

The candidate clears every safety floor (critical_recall ≥ 0.99, critical_miss_rate ≤ 0.01), shows
**no regression** on critical recall or top-3/top-5, and shows **no catastrophic specialty/subgroup
regression**; it also does not rely on a top-1-only improvement. On these **synthetic** metrics the
gate would PROMOTE. In a real deployment the same gate runs on adjudicated clinical data and the
candidate begins in **shadow** (clinical output unchanged) until a human approves promotion — see
`docs/learning/MODEL_LIFECYCLE.md`.

## Why the numbers are near-ceiling (and what that does / does not mean)

The synthetic eval builder derives each query from a known concept's own features, so retrieval
recall is expected to be near-perfect — this confirms the **plumbing** (indexing, fusion, ranking,
safety-recall re-insertion, narrowing) works end-to-end over 5,651 concepts without dropping
critical conditions. It is **not** evidence of clinical accuracy. The discriminating clinical work
(disambiguating mimics, weighing contradictions, ordering the differential) is validated separately
by the frozen **Blind v11** benchmark (24 cases incl. retrieval-miss and router-miss traps), which
requires pydantic and is therefore **NOT VERIFIED in this environment** and deferred to CI.

## Reproduce

```bash
python scripts/build_tier3_synthetic_snapshot.py --target 4200   # regenerate Tier-3 (gitignored)
python scripts/report_disease_coverage.py --json                 # confirm >= 5,000 searchable
python scripts/compare_5000_baseline.py --json                   # baseline vs candidate + gate
```
