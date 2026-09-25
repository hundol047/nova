# Learning Data Governance

Rules governing what data may enter the learning pipeline and how it is protected. These are
enforced in code (`learning/continual.py`, `learning/labels.py`, `learning/deidentify.py`,
`learning/dataset.py`) and asserted in `tests/test_learning_pipeline.py`.

## 1. Capture is opt-in and off by default

Nothing is recorded unless `NOVA_LEARNING_ENABLED=true`. Default is **false**. When disabled,
`continual.capture_record()` raises `LearningDisabledError` — no clinical outcome is stored.

## 2. De-identification at capture

Before a record is built:

- **Direct identifiers are stripped** (name, MRN, SSN, phone, email, address, DOB, device/IP, …).
- The patient id is replaced with a **non-reversible HMAC pseudonym** (`pt_…`). With
  `NOVA_DEID_SECRET` set, the pseudonym is stable across runs (needed for patient-level splitting);
  without it, pseudonyms are per-run only.
- Feature snapshots are **allow-listed clinical signal only** (age bucket, vitals, symptom/lab
  flags); identifier keys are defensively stripped from them too.

There are **no PHI columns** in `clinical_learning_cases` (migration 0003).

## 3. A NOVA prediction is NEVER a training label

The outcome store keeps `nova_top_concept_id` (what NOVA thought) **separate** from
`label_concept_id` (the truth). A row becomes **training-eligible only** when a
clinician/coded/pathology outcome is attached and `label_status = ADJUDICATED`. `LabelSource`
values `NOVA_PREDICTION` and `LLM_SUGGESTION` are **forbidden** as labels — enforced at capture, at
dataset build, and by a DB `CHECK` constraint. This prevents the model from learning to agree with
itself.

## 4. Coverage-gap analytics are PHI-free

`UNKNOWN_PRESENTATION` / `POSSIBLE_UNMAPPED_CONDITION` outcomes are logged as `coverage_gap_events`
using a **salted, non-reversible fingerprint** of the query terms — the raw text is never stored.
Aggregated fingerprints show *where* to expand the catalog without retaining patient data.

The 5,000-diagnosis pipeline's `CoverageGapQueue` (`learning/error_taxonomy.py`) obeys the same
rule: it stores only PHI-free descriptors and is a **human-review queue only** — it **never**
auto-edits the knowledge base or auto-adds a disease concept. Expanding the disease universe is
always a deliberate, reviewed curation action. See `CONTINUAL_LEARNING.md` for the error taxonomy.

## 5. Immutable dataset snapshots

Training reads from **content-hashed, immutable** JSONL snapshots (`learning/dataset.py`). A
snapshot is never edited in place; a new build produces a new snapshot id, and re-building an
existing id refuses to overwrite. This makes every trained model reproducible from a named dataset.

## 6. What leaves the system

Nothing is sent to any third party. There are no external terminology or telemetry calls in the
learning path. Model artifacts and dataset snapshots stay on operator-controlled storage.
