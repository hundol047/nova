# Controlled provenance recovery and replacement

Current decision: **BLOCKED for official submission**, not a conclusion that internally
authored material is inherently license-invalid. No clinical asset has been removed or replaced.

`artifacts/compliance_hardening/clinical_asset_inventory.json` inventories 72 existing
source/data/document assets and three absent optional terminology snapshots. Each existing
asset has its actual SHA256, Git history evidence and an individual decision E with recovery
routes A/B/C. Commit dates/authors are explicitly not generation dates/clinical authors.
Rights, original authorship, medical validation and clinician review are separate fields.

1. Recover original records: original author, source/version, source rights, exact generation
   model/version/prompt/code/output, and actual reviewer records. Repository metadata cannot
   substitute for missing evidence. `knowledge/PROVENANCE.md` asserts internal heuristic
   authorship but does not identify a rights holder or provide clinician approval.
2. If team-original authorship can be substantiated, obtain an actual holder's permission
   for research publication, redistribution and modification. Do not infer this from the
   team name, Git author, or permission to commit code. Team ownership does not establish
   medical correctness, and historical AI content must not be relabelled to clear the gate.
3. Stage replacements outside `nova_agent/` and the ZIP. Verify exact source bytes, version,
   applicable terms and attribution before transformation. Prefer deterministic extraction
   with recorded input/output hashes and source-controlled transformation code. Unknown
   coding-assistant model identity cannot satisfy external-LLM label reproducibility.
4. Review field-level clinical applicability, retain coverage, and compare the same permitted
   development sets before/after. Require no safety regression and report accuracy, tests,
   turns and every changed result. Only then consider promotion and fresh runtime verification.

The legitimate available Git object history contains MedlinePlus and Orphanet manifests for
different catalogs. Their preserved records are in `recovered_history.json`. They do not
prove the origin of this branch's current features and have not been retroactively cited as such.
MedlinePlus's publisher terms and XML description were inspected on 2026-10-05. The candidate
record in `replacement_source_candidates.json` specifies the allowed sections and exclusions.
Government hosting is not blanket permission: A.D.A.M., drug monographs, images and external
linked pages have separate rights. No Orphanet license clearance is inferred from its old manifest.

This pass generated engineering code/metadata, not new medical facts or clinical labels.
Existing diagnosis coverage and all clinical scoring/retrieval/stop files remain byte-identical.
