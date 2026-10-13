# DDXPlus v2 diagnostic replay cohort

Source: [DDXPlus English v2](https://doi.org/10.6084/m9.figshare.22687585.v2), obtained from the [N.O.V.A. public benchmark bundle](https://nova.snubhai.org/downloads/nova-benchmarks-2026.zip). The original bundle SHA-256 is recorded in `manifest.json` and verified before extraction. License: CC BY 4.0, retained in `LICENSE.txt`.

Attribution: Arsene Fansi Tchango, Rishab Goel, Zhi Wen, Julien Martel, Joumana Ghosn. *DDXPlus: A New Dataset For Automatic Medical Diagnosis.* NeurIPS 2022 Datasets and Benchmarks Track; arXiv:2205.09148.

Changes: `scripts/evaluate_external_ddxplus.py` selects 2,000 original synthetic records with distinct complete evidence-code configurations. It retains the original train/validate/test partition and uses per-condition quotas, producing 1,200 development, 400 validation and 400 holdout records across 49 conditions. Duplicate evidence configurations are excluded across all partitions even if age, sex, initial complaint or diagnosis differs. Selection uses no agent predictions. Original labels and evidence codes are unchanged; unnecessary source columns are omitted. Original question/answer metadata is retained unchanged.

Replay: positive binary and supplied categorical questionnaire answers enter the existing patient-state interface. No unreported negatives, exams, laboratory values or patient dialogue are generated. A small grammar conversion removes the leading question frame to attach a bare yes to its original topic. Compound questions stay compound. This conversion is an engineering approximation, not independently medically adjudicated. Gold diagnosis and source severity never enter the diagnostic engine.

This is an external synthetic diagnostic replay, not 2,000 real patients, not Korean conversational testing, and not an official N.O.V.A. score. It cannot measure information acquisition, communication, triage or real Doctor-model behavior. Runtime tuning against its holdout is prohibited. Evaluation files are excluded from the submission archive.
