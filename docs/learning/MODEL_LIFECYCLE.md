# Model Lifecycle

How a ranker model goes from a dataset snapshot to (optionally) production — always through an
explicit, gated, human-controlled path. No model ever self-promotes.

## States (`learning/registry.py`)

```
   register ──▶ SHADOW ──promote(gated)──▶ PRODUCTION
                  │                             │
                  │                             ├─ rollback ──▶ previous PRODUCTION
                  └─ promote blocked ──▶ REJECTED
   (superseded production) ──▶ ARCHIVED
```

- **SHADOW** — evaluated alongside production, **not used for decisions**. Every newly registered
  model starts here.
- **PRODUCTION** — the currently-served model. There is exactly one.
- **ARCHIVED** — a previously-production model, kept for rollback/audit.
- **REJECTED** — failed the promotion gate.

## Training (`learning/train.py`)

1. Load an **immutable snapshot** (`--snapshot`).
2. Assert no forbidden (NOVA/LLM) label survived (defense in depth).
3. Split **patient-level** or **temporal**; abort on any patient leakage across folds.
4. Fit OOD detector (+ calibrator later) on the **training fold only**.
5. If torch is absent: validate data prep + split integrity and **skip** neural training (expected
   outside the learning environment). If present: train, evaluate, and `register(...)` as **SHADOW**.

Training is **offline and batch**. `continual.assert_offline_training()` is a tripwire: setting
`NOVA_ONLINE_TRAINING=true` makes training routines refuse to run. There is no per-patient/online
update path.

## Promotion gate (`registry.PromotionGate`)

A SHADOW model may be promoted **only if** it clears safety-critical criteria versus the current
production model:

- `critical_recall >= 0.99` (must not miss critical/red-flag conditions), and
- **zero tolerance** for `critical_recall` regression vs production.

If the gate fails, `promote()` marks the candidate `REJECTED` and raises — production is untouched.

## Rollback

`rollback()` restores the previous production version from history and archives the current one. It
is instant and does not require retraining.

## No self-modifying production

The served model is a static, versioned artifact. It is never mutated in place; changes happen only
by promoting a new SHADOW model through the gate. Every production change is recorded in the
registry with its dataset snapshot id and metrics.



## Multi-metric promotion gate for the 5,000-diagnosis candidate (`learning/baseline.py`)

The 516/1,280-concept bundled architecture is the **BASELINE**; the ≥ 5,000-searchable retrieval
architecture is the **CANDIDATE**. Promotion of the candidate is governed by a configurable
**multi-metric** gate (`MultiMetricGate`) — a single top-1 improvement is **never** sufficient.

`MultiMetricGate.compare(baseline: MetricSet, candidate: MetricSet)` returns one of three
decisions:

- **PROMOTE** — the candidate clears every floor and regresses no protected metric.
- **SHADOW** — the candidate is safe but not clearly better (e.g. improves top-1 only, or a
  specialty/subgroup shows a non-catastrophic dip) → runs in shadow, clinical output unchanged.
- **REJECT** — the candidate violates a hard safety floor or regresses a protected metric.

Gate criteria (all enforced, not just top-1):

| Criterion | Rule |
| --------- | ---- |
| Critical recall floor | `critical_recall >= 0.99` (absolute floor). |
| Critical recall regression | **zero tolerance** vs baseline → REJECT on any drop. |
| Critical miss rate | `critical_miss_rate <= 0.01`. |
| Top-3 / Top-5 regression | material regression → REJECT. |
| Specialty / subgroup | catastrophic regression in any specialty/subgroup → REJECT; mild → SHADOW. |
| Top-1-only improvement | cannot PROMOTE by itself → SHADOW. |

The metric set (`MetricSet`) carries Top-1/3/5/10, Recall@K, Critical Recall@5/20/100,
Critical Miss, OOD, calibration, and latency. `scripts/compare_5000_baseline.py` computes these for
BASELINE vs CANDIDATE on the synthetic eval set and prints the gate decision (see
`docs/evaluation/FIVE_THOUSAND_DISEASE_COMPARISON.md`).

## Shadow deployment (clinical output unchanged)

The candidate retrieval architecture is introduced in **shadow** via the existing
`GovernedMLRuntime` shadow mode: the pipeline is executed and its ordering **logged**, but the
clinician-facing `action`/`differential` is **not changed**. Shadow data (PHI-free) is captured for
later gate evaluation. Only a human-approved PROMOTE (clearing the multi-metric gate) makes the
candidate authoritative.
