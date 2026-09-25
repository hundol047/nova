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



## vNext completion: real training loop, checkpoints, governed runtime

The learning subsystem is now end-to-end (all torch-optional; torch is imported lazily and is
**never** a submission or core-runtime dependency):

- **Training** (`learning/train.py`): a real loop — DataLoader-style batching over candidate sets,
  cross-entropy ranking loss, Adam, gradient clipping, per-epoch validation, early stopping,
  best-checkpoint tracking, metric logging (top-k / MRR / critical recall), deterministic seeding
  (`learning/seed.py`). Without torch it runs data-prep + split-integrity validation and reports
  `IMPLEMENTED_BUT_NOT_EXECUTED` (never a clinical-performance claim).
- **Checkpoints** (`learning/checkpoint.py`): weights + a JSON metadata sidecar (model_version,
  input_dim, hidden, dropout, feature_version, schema_version, model_arch, dataset_version,
  code_sha, metrics, created_at). `check_compatibility()` refuses a checkpoint whose
  feature_version / input_dim / schema_version / model_arch does not match the running code —
  **before** touching weights. `TorchRanker.load()` is the compatibility-guarded factory.
- **Governed runtime** (`learning/runtime.py`): `GovernedMLRuntime` consults the ranker under
  strict governance — `disabled` (default), `shadow` (audit only, clinical output unchanged),
  `active` (reorder only, Safety Guard applied after, OOD falls back to deterministic,
  `_merge_preserving` guarantees ML never drops a deterministic candidate). Invariant:
  **Safety Guard > ML Ranker > LLM**.
- **Backend integration** (`backend/app/services/nova_service.py`): `_consult_ml_shadow()` is a
  fail-safe hook after `agent.decide()`; in shadow mode it audits the ML ordering and never changes
  `action`/`differential`. Config gates: `NOVA_ML_RANKER_ENABLED` (default false),
  `NOVA_ML_SHADOW_MODE` (default true), `NOVA_ML_MODEL_PATH`.
- **Retraining lifecycle** (`learning/retrain.py`): `train` (→ SHADOW, never auto-promote) /
  `promote` (requires `--approved-by` **and** the safety gate) / `rollback` / `status`.

**REAL PATIENT TRAINING = NOT VERIFIED**: this repository has no real hospital patient data;
synthetic runs validate the pipeline mechanics only and are never presented as clinical performance.
