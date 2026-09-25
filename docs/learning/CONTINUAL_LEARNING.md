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
