# Recorded-signal neural training readiness — 2026-10-03

Status: **input pipeline improved; clinical model training NOT EXECUTED; runtime NOT activated**.
This repository already contained an optional MLP ranker and batch trainer. The current diagnostic
engine's reported mock-dialogue scores do not measure that neural model.

## Changed now

Previously, training generated three per-candidate signals from an example-ID/concept-ID hash,
while inference consumes evidence/retrieval/prior scores. That was a prototype contract, not
medical evidence. The hash fallback has been removed. Training rows now require recorded
`candidate_signals`, in exactly this order: `[base_evidence_score, retrieval_score, prior]`.
The label selects the loss target only; it is never used to construct these input scores.
Changing example ID or label cannot change input features.

Finite numeric values, exact feature dimension, unique candidate IDs, and complete signal coverage
are required. Invalid rows abort preparation rather than silently disappearing from evaluation.
Immutable snapshot manifests and SHA-256 are checked before training. Checkpoint schema is now
`sched.v2`; old pseudo-feature checkpoints are intentionally incompatible and require retraining,
not relabeling their metadata. Legacy snapshots remain readable but cannot train without recorded
signals. Capture signals before learning the outcome; schema validation cannot prove that provenance.

Validation metrics used for early stopping are now printed as validation, not independent test.
The existing trainer still does NOT implement a separately adjudicated independent final clinical
test cohort. Its qualitative critical-label heuristic, calibration and promotion gates need review
before any clinical model activation. No automatic promotion or clinical accuracy claim is made here.

## Data required next

Provide a legally usable, de-identified dataset with documented origin and independently verified
outcomes. Label-source enums alone are not proof of expert review. Record review evidence and
usage rights outside patient-facing runtime. NOVA/LLM predictions remain forbidden training labels
under this project's policy. Existing simulation output is not converted to clinician-confirmed data.

Each raw record already accepted by `learning.dataset.build_snapshot` now additionally needs:

```json
{
  "candidate_ids": ["concept_a", "concept_b"],
  "candidate_signals": {
    "concept_a": [1.2, 0.3, 0.1],
    "concept_b": [0.4, 0.5, 0.2]
  }
}
```

This snippet is a schema illustration, not a clinical training row. It does not contain required
patient/encounter fields or any label. Keep all encounters for one patient and related synthetic
source families in a single split; exact feature/ID tests alone do not detect every near-duplicate.

After approved data preparation and PyTorch installation, the existing offline entrypoint is:

```
python -m learning.train --snapshot /path/to/dataset_VERSION.jsonl --output-dir /path/to/research-models
```

This command has NOT been run on clinical data. A valid training run requires more than passing
schema checks. Freeze separate train/validation/independent-test data before clinical use, evaluate
safety/non-regression/calibration, and retain expert review before deployment.

## Competition constraints checked

Official source checked 2026-10-03: https://nova.snubhai.org/rules/
Preliminary fixed `openai/gpt-oss-20b` fine-tuning and loading its weight adapters are prohibited.
Each case must call the designated LLM; external inference APIs are prohibited. CPU/RAM auxiliary
components are allowed subject to runtime restrictions, but this change does not integrate or
certify the experimental ranker for the competition. No fixed-LLM weight or adapter was changed.
Finals have different model rules; do not assume preliminary and final permissions are identical.

## Verification and remaining blockers

New checks cover training/inference feature agreement, label/ID invariance, malformed/nonfinite
scores, schema dimensions, snapshot round-trip and tampering. Unit test records are synthetic;
their label strings do not represent real clinician adjudication. PyTorch training smoke test is
skipped in this environment because PyTorch is absent. Full regression results are in
`recorded_signals_regression.txt`; API TestClient remains explicitly excluded due to its existing blocker.

No reviewed clinical training dataset has been supplied for this work. No new weights, no clinical
accuracy result, no deployment, and no self-learning from live patient data were produced.
