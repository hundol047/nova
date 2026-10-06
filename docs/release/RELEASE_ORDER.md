# Release order (why the verification record no longer chases its own hash)

Three kinds of file take part in a local pre-guide release. Only the first kind is hashed into the
shipped archive; the other two POINT AT it. Keeping that direction one-way is what removes the circularity
that made `test_current_runtime_exact_archive_and_commit` and the inventory test fail after every runtime edit.

| Kind | Examples | Changes the archive? |
| --- | --- | --- |
| Runtime (shipped) | `nova_agent/**`, `competition/**`, `submission/run.py`, `submission/requirements.txt` | yes |
| Mirror / archive | `submission/nova_agent/**`, `submission/competition/**`, `submission/submission.zip` | derived from runtime |
| Evidence (not shipped) | `artifacts/compliance_hardening/clinical_asset_inventory.json`, `artifacts/verification/*`, `artifacts/**/regressions.json`, test reports | no |

## Order (each step may only read what came before it)

1. **Freeze the runtime** and commit it. Any later runtime edit restarts the list.
2. `python scripts/build_nova_submission.py` -- rebuilds the mirror and the ZIP. The build is reproducible
   (fixed ZIP timestamps/permissions, sorted entries, manifest time = `SOURCE_DATE_EPOCH` or the HEAD
   committer time), so rebuilding unchanged sources yields the identical SHA-256. Commit the mirror.
3. `python scripts/refresh_runtime_inventory.py` -- refreshes inventory hashes and adds UNRESOLVED entries for
   new files; it never raises an authorship/licence/permission status. `--check` fails if stale.
4. Run the evaluations and the full test suite against that exact commit.
5. `python scripts/record_open_data_release.py --runtime <commit>` (v16 recorder; v17 for this integration) --
   binds the recorded hashes to the commit and copies the ZIP into `artifacts/verification/`. It asserts that
   every recorded hash equals the working-tree bytes AND `git show <commit>:<file>`.
6. Commit the evidence. Nothing in step 3-6 is inside the archive, so none of it can change a runtime hash.

`python scripts/validate_submission_zip.py` (step 2 or 6) unpacks the ZIP into an empty directory and checks
the packaging rules with an isolated interpreter; it never needs the repository.

What this does NOT do: it does not establish official-interface compatibility, real-model behaviour or
source/licence clearance. Those stay `NOT VERIFIED` / `UNRESOLVED` and keep `official_submission_allowed` false.
