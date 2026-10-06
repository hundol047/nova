# Round M evidence map

Authoritative current evidence: `final_summary.json`, `failure_analysis.json`, `final/traces.tar.xz`,
`final_regressions.json`, `pytest_summary.json`, `package_audit.json` and verification v12.

`baseline_before_fixes/` and `pre_normalizer_fix/` are SUPERSEDED diagnostic work records.
Their original accuracy metrics used a defective embedded-acronym matcher; never use them as
current or official accuracy claims. `development_change_comparison.json` re-scores saved initial
predictions under the corrected matcher solely for a descriptive efficiency/accuracy comparison.

Existing blind_v19_integrity.json/leakage_v19.txt are historical authoring/leakage records,
not an execution attempt or performance result. v19 remains unexecuted and reference-only.

No private patient/evaluation data is included. All case/answer traces are synthetic development
material and are excluded from the submission candidate ZIP.
