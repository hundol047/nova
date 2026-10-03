# Continual Learning

How N.O.V.A. can *improve over time* from real clinical outcomes — safely, offline, and opt-in.
This ties together the outcome store (backend migration 0003), governance (`learning/continual.py`),
the data pipeline (`learning/dataset.py`, `splits.py`), and the model lifecycle (`registry.py`).

## The loop (all offline, all gated)

```
  1. CAPTURE (opt-in)          clinician outcome ──▶ clinical_learning_cases (de-identified)
                               NOVA prediction stored SEPARATELY, never as a label
  2. ADJUDICATE                clinician/coded/pathology label attached ──▶ label_status=ADJUDICATED
  3. SNAPSHOT (offline)        immutable, content-hashed dataset from ADJUDICATED rows only
  4. SPLIT                     patient-level AND/OR temporal (no leakage)
  5. TRAIN (offline)           SHADOW model + OOD + calibrator (torch env only)
  6. EVALUATE                  critical_recall, top-k, MRR on held-out fold
  7. PROMOTE (human, gated)    only if safety gate clears; else REJECTED
  8. MONITOR                   PHI-free drift/OOD/shadow-disagreement; humans decide rollback
```

Nothing in this loop runs automatically end-to-end. Capture is off by default; promotion is an
explicit human action; there is no online/per-patient training.

## Guardrails (why this is safe)

| Risk | Guardrail |
| ---- | --------- |
| Model learns to agree with itself | NOVA/LLM prediction can **never** be a label (`labels.py`, DB CHECK). |
| PHI leakage into training data | De-identify + pseudonymize at capture; no PHI columns; allow-listed features. |
| Data leakage inflating metrics | Patient-level + temporal splits; abort on cross-fold patient overlap. |
| Training on the evaluation set | `learning/` may not import `evaluation/` (static test). |
| Silent capture | `NOVA_LEARNING_ENABLED=false` default; capture raises when disabled. |
| Runaway self-modification | Offline-only tripwire; shadow→gated-promote→rollback; single production artifact. |
| Over-confident scores | No calibrated probability shown unless a calibrator is fitted; OOD flags low-trust. |
| Missing a critical condition | Ranker floats critical/red-flag to the top band; promotion gate requires critical_recall ≥ 0.99. |

## What "improvement" means here

The ranker learns to **order** the differential better from adjudicated outcomes. It does **not**
expand the disease universe on its own (that is curation of the ontology/Tier-2 catalog, informed by
PHI-free coverage-gap analytics), and it **never** turns a low-confidence guess into a confirmed
diagnosis. The deterministic safety layer remains authoritative at all times.



## Error taxonomy & coverage-gap queue (`learning/error_taxonomy.py`)

Continual improvement of the 5,000-diagnosis pipeline is driven by **classified misses**, not by
tuning to any evaluation case. Every miss on the held-out / shadow data is categorized by
`classify_miss(...)` into exactly one class so remediation targets the right stage:

| Miss class | Meaning | Typical remediation (human, offline) |
| ---------- | ------- | ------------------------------------ |
| `RETRIEVAL` | Correct dx never entered the Top-K candidate pool. | Improve embedding/lexical/code fusion or index coverage. |
| `RANKING` | Dx was retrieved but the reranker placed it too low. | Reranker training data / features. |
| `REASONING` | Dx was in the narrowed bundle but the LLM/logic chose wrong. | Reasoning prompts / evidence assembly. |
| `PIPELINE_INTEGRATION` | Dx lost between stages (an integration defect). | Fix the stage hand-off. |
| `COVERAGE_GAP` | The dx is **not in the catalog at all**. | Route to the coverage-gap queue for **human curation**. |
| `NO_MISS` | Correct — no action. | — |

`COVERAGE_GAP` items are appended to a **`CoverageGapQueue`** for **human review only**. The queue
**never** auto-edits the knowledge base or auto-adds a concept — expanding the disease universe is
always a deliberate, reviewed curation step (consistent with the "improvement" definition above).
The queue stores PHI-free descriptors only.

## Rare-disease mode & failure-mode resilience (`learning/resilience.py`)

- `decide_rare_mode(...)` widens retrieval / lowers thresholds for likely rare presentations so a
  long-tail (Tier-3) condition can still surface as a *possibility* rather than being crowded out —
  without ever forcing a low-confidence label.
- `safe_call(...)` wraps each pipeline stage so that when a component is **unavailable or
  corrupt** — ML backend missing, retrieval index absent, ontology snapshot missing, LLM
  unreachable, an **incompatible checkpoint**, or a **corrupt snapshot** — the pipeline **degrades
  gracefully and does not crash**. It falls back to the deterministic path and records a
  `DegradationReport`; the Safety Guard remains authoritative throughout.
