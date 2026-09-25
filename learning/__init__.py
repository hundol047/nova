"""N.O.V.A. learning subsystem (vNext PART B) — OPTIONAL, off the critical path.

This package holds the deep-learning candidate RANKER and its data pipeline. It is deliberately a
TOP-LEVEL package, NOT part of nova_agent/, and is NEVER included in the competition submission.

Hard invariants (enforced structurally + in tests):
  - torch is OPTIONAL. Import of this package must NOT require torch. Training/inference code that
    needs torch imports it lazily and raises a clear error if it is missing (see _torch.py).
  - The ranker NEVER auto-confirms a diagnosis. It only RE-ORDERS an already-safety-vetted
    candidate list and attaches calibrated scores. Safety Guard > ML Ranker > LLM (priority order).
    A ranker output can never promote a candidate the safety layer excluded, nor suppress a
    red-flag/critical candidate.
  - No calibrated percentage is emitted unless a fitted calibrator is present (see calibration.py).
  - A NOVA prediction is NEVER used as a training label (see labels.py / continual pipeline).

Nothing here is imported by nova_agent at runtime; the reasoning engine works fully without it.
"""

__all__ = [
    "schemas",
    "ranker",
    "encoder",
    "ood",
    "calibration",
]
