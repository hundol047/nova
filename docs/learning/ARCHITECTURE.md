# Learning Subsystem Architecture

The `learning/` package is N.O.V.A.'s **optional** deep-learning candidate ranker and its data
pipeline. It is deliberately **isolated** from the reasoning engine and the competition submission.

## Where it sits (and does not)

```
                 ┌─────────────────────────────────────────────┐
   patient  ───▶ │  nova_agent/  (deterministic reasoning)      │
   input         │   ├─ clinical_presentation / differential    │
                 │   ├─ ontology/ (DiseaseCatalog, open_world)   │
                 │   └─ safety_validator  ◀── SAFETY GUARD       │
                 └───────────────┬─────────────────────────────┘
                                 │ safety-vetted candidate list
                                 ▼
                 ┌─────────────────────────────────────────────┐
   OPTIONAL ───▶ │  learning/  (ranker)                         │
                 │   re-orders + attaches calibrated scores      │
                 │   NEVER auto-confirms, NEVER resurrects an    │
                 │   excluded candidate, NEVER outranks a        │
                 │   critical/red-flag candidate                 │
                 └───────────────┬─────────────────────────────┘
                                 ▼
                       clinician-facing differential
```

**Priority invariant:** `Safety Guard > ML Ranker > LLM`. The ranker only informs *ordering* of an
already-safety-vetted list; the deterministic safety layer always has the final say.

## Modules

| Module | Role |
| ------ | ---- |
| `schemas.py` | Dataclasses: `RankerInput/Output`, `CandidateFeature`, `TrainingExample`, `LabelSource`. |
| `encoder.py` | Deterministic, torch-free feature encoder (numeric + hashed flag bag; stable dim). |
| `ranker.py` | `LinearRanker` — always-available fallback that enforces the safety ordering. |
| `model_torch.py` | `TorchRanker` — neural backend, loaded **only** if torch is installed. |
| `ood.py` | Distance-to-centroid out-of-distribution detector; flags low-trust cases. |
| `calibration.py` | Isotonic (PAV) calibrator; returns `None` until fitted → no fake percentages. |
| `labels.py` | Enforces a NOVA/LLM prediction can never be a training label. |
| `deidentify.py` | Strip direct identifiers + HMAC pseudonymize for patient-level splitting. |
| `splits.py` | Patient-level **and** temporal splits (no patient straddles the cutoff). |
| `dataset.py` | Immutable, content-hashed dataset snapshots. |
| `registry.py` | Model registry: shadow → gated promotion → rollback. |
| `evaluate.py` | Metrics incl. `critical_recall` (the promotion gate). |
| `monitoring.py` | PHI-free drift/OOD/disagreement counters. |
| `continual.py` | Continual-learning governance (capture gating, offline-only tripwire). |
| `coverage_gap.py` | PHI-free coverage-gap analytics. |

## torch is OPTIONAL

Importing `learning` never requires torch. Only the neural train/inference path needs it
(`_torch.require_torch()` raises a clear message if missing). torch lives **only** in
`backend/requirements-learning.txt` — never in the core runtime or the submission.

## Isolation guarantees (enforced by tests)

- `learning/` never imports `evaluation/` (no training on blind/held-out data).
- `nova_agent/` and `submission/` never import `torch` or `learning`.
- `submission/` excludes the `learning` package and declares no torch dependency.

See `tests/test_learning_eval_isolation.py` and `scripts/verify_local_release.py`
(`learning_isolation`).
