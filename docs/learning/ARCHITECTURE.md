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



## 5,000-diagnosis retrieval architecture (PHASE 1)

To reason over a ≥ 5,000 searchable disease universe **without** becoming a naive 5,000-way
classifier, `learning/` adds a staged retrieval-and-rerank pipeline. Every stage can only **add**
or **re-order** candidates within the immutable priority `Safety Guard > ML Ranker > LLM`; no stage
may silently drop a critical/must-not-miss condition.

```
   patient query
        │
        ▼
  ┌───────────────┐   embedding + lexical + code fusion over the full catalog
  │ 1. RETRIEVAL  │   learning/retrieval/ → Top-100..200 candidates
  └──────┬────────┘   (feature-hash embeddings; torch-optional richer encoder)
         ▼
  ┌───────────────┐   multi-specialty activation (bands HIGH/MED/LOW), additive-only boost;
  │ 2. ROUTER     │   low-confidence → global fallback. A router MISS can NEVER remove a
  └──────┬────────┘   candidate — boost() only raises scores. learning/routing/
         ▼
  ┌───────────────┐   deterministic must-not-miss recall: re-inserts critical conditions
  │ 3. SAFETY     │   (e.g. ACS/PE/dissection for chest pain) even if 1&2 missed them.
  └──────┬────────┘   assert_no_critical_dropped() guards the invariant. learning/safety_recall.py
         ▼
  ┌───────────────┐   deep clinical reranker Top-100 → keep ~25; safety_mandatory candidates
  │ 4. RERANKER   │   are ALWAYS retained regardless of score. Real torch BCE path +
  └──────┬────────┘   deterministic fallback. learning/rerank/
         ▼
  ┌───────────────┐   the LLM receives ONLY the narrowed bundle (≤ 26) + evidence /
  │ 5. LLM        │   contradictions / missing data / must-not-miss list — never the full 5,000.
  └──────┬────────┘   Novel LLM dx → normalize → canonical or UNMAPPED_LLM_DIAGNOSIS.
         ▼
   open-world outcome: KNOWN_CONDITION / POSSIBLE_UNMAPPED_CONDITION /
   INSUFFICIENT_INFORMATION / UNKNOWN_PRESENTATION (OOD reduces confidence).
```

### Modules (retrieval pipeline)

| Module | Role |
| ------ | ---- |
| `retrieval/embedding.py` | Deterministic feature-hash embedding (`EMBED_DIM=256`), cosine sim; torch-free. |
| `retrieval/disease_encoder.py` | Encodes a catalog concept to a `DiseaseFeatures` vector (duck-typed on the catalog). |
| `retrieval/patient_encoder.py` | Encodes a `PatientQuery` (symptoms/history/labs/imaging) to the same space. |
| `retrieval/index.py` | `DiseaseIndex` — build-once, cached, memoized `get_default_index()`; no per-request rebuild. |
| `retrieval/retriever.py` | `Retriever` — embedding + lexical + code fusion, per-stage latency, `RetrievedItem.sources`. |
| `retrieval/metrics.py` | `recall_at_k`, `critical_recall_at_k`, `critical_miss_rate`. |
| `retrieval/eval_synthetic.py` | Synthetic labeled eval set (REAL clinical recall = `NOT VERIFIED`). |
| `routing/router.py` | `SpecialtyRouter` — multi-specialty bands, global fallback, additive-only `boost()`. |
| `safety_recall.py` | `apply_safety_recall` adds missing critical conditions; `assert_no_critical_dropped`. |
| `rerank/reranker.py` | `Reranker` keep≈25; `safety_mandatory` always retained; `Reranker.load` compat-guarded. |
| `rerank/model_torch.py` `train_reranker.py` `checkpoint.py` | Real torch BCE training + per-component checkpoint + ontology-version compatibility guard. |
| `pipeline.py` | `FiveKPipeline` orchestrates 1→5; LLM bundle ≤ 26; lexical-grounding UNKNOWN guard. |
| `baseline.py` | `MultiMetricGate` (PROMOTE/SHADOW/REJECT) — see `MODEL_LIFECYCLE.md`. |
| `error_taxonomy.py` | `classify_miss` + `CoverageGapQueue` (human review, no auto KB edit). |
| `resilience.py` | `safe_call` degradation + `decide_rare_mode` (no crash on missing ML/ontology/LLM). |

### Dependency-free by default

The entire retrieval/router/rerank/pipeline/gate path runs and is **tested without torch** using
deterministic feature-hash embeddings and scorers. A richer torch encoder/reranker is loaded only
when torch is present. Consequently the torch training path is `IMPLEMENTED_BUT_NOT_EXECUTED` in a
torch-free environment and is honestly reported as **NOT VERIFIED** there — never as a clinical
claim.

### Measured (synthetic catalog, this environment)

recall@50/100/200 = 1.0, recall@20 = 0.996, critical_recall@100 = 1.0,
critical_miss_rate@100 = 0.0; index build ≈ 0.2 s over 5,651 concepts, query ≈ 72 ms. These are
**synthetic-catalog mechanics numbers only** — see
`docs/evaluation/FIVE_THOUSAND_DISEASE_COMPARISON.md`.

### Isolation (unchanged)

`learning/` — including the retrieval pipeline — is **never** imported by `nova_agent/`,
`competition/`, or `submission/`. The retrieval index/retriever accept a catalog object by
duck-typing; they do not import the reasoning engine. The submission declares **no** torch and no
external terminology dependency.
