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
