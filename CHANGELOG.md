# Changelog

## 2026-10-03
- Fix mixed comma-list assertion scope and current-exam reassurance matching.
- Preserve multilingual feature aliases previously overwritten by duplicate dictionary keys.
- Add evidence-semantics regressions and retain reproducible synthetic replay artifacts.
- All-case synthetic mock Top-1: 180/191 (94.24%); 97% all-case target remains unmet.

### Laboratory trend follow-up
- Parse measured trend endpoints with existing unit and numeric conflict guards.
- Reject hypothetical/predicted laboratory clauses as current observations.
- Synthetic mock final-answer accuracy: 181/191 (94.76%); 100% remains unmet.

Safety follow-up: [observed flags and tradeoffs](docs/evaluation/safety_flags_2026_10_03/README.md). Synthetic critical-case final flags: 71/97 to 84/97; exact dangerous target answers unchanged at 90/97. Not clinical sensitivity.

Added 24 source-informed synthetic safety snapshots and fixed historical/family symptoms triggering current safety flags. [Evidence and limitations](docs/evaluation/source_safety_2026_10_03/README.md).

ICD-11 2026 reference registration: [18,375 ordinary categories plus separately classified functioning/extension codes](docs/ontology/ICD11_2026_REFERENCE.md). Offline reference only; diagnostic coverage and accuracy are unchanged.

## 2026-10-03 — specific current signs remain safety-relevant

- Fixed missed bleeding/focal neurological safety flags when language routing misses a tag or a candidate originated only from the safety net. Added scoped speech-deficit aliases.
- Evaluated two 400-input synthetic cohorts before and after: warning misses 22→15 and 19→13, without increasing noncritical warning counts. Exact diagnosis agreement remained 95.75% and 96.75%; no diagnostic-accuracy improvement claimed.
- Rejected broader evidence and cold-sweat alias attempts because they increased warnings on noncritical cases. Regression: 633 passed, 1 skipped; pre-existing API TestClient issue excluded.
- Evidence and limitations: `docs/evaluation/safety_cycle2/RESULTS.md` and `README.md`. No training, clinical validation or deployment.
