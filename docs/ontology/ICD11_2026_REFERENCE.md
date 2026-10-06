# ICD-11 2026-01 reference registration

Downloaded the English official WHO simple-tabulation archive, checked its release header,
and registered every chapter, block and coded category in an offline reference SQLite store.
Original source rows, codes, titles (including table indentation), URIs and hierarchy fields are
retained unchanged. Added NOVA metadata identifies reference-only status and lack of clinical
validation. No translations, crosswalks or new clinical rules were generated.

| Official table entries | Count |
|---|---:|
| Coded categories outside chapters X and V | 18,375 |
| Functioning chapter V categories | 130 |
| Extension chapter X categories | 17,159 |
| All coded categories | 35,664 |
| Chapters and blocks | 28 + 1,360 |
| All registered classification rows | 37,052 |

18,375 is not a count of distinct diseases: it includes other health-classification categories.
The previously cited ~17,000 is WHO's approximate category count, not a fixed import limit.
Do not add these counts to existing NOVA diagnoses as if all were unique diseases.

## Use

The installed reference database is `nova_agent/ontology/snapshots/icd11_reference_2026.sqlite`.
It is separate from the default candidate registry; the runtime remains 34 deep profiles and
1,246 supplementary concepts. Registered reference entries are not validated diagnostic skills.
The submission mirror contains the lookup module; installing the optional reference database in
that environment is a separate operator action. No deployment or runtime network dependency.

```sh
python -m nova_agent.ontology.icd11_reference 1A00
python -m nova_agent.ontology.icd11_reference "Cholera"
python -m nova_agent.ontology.icd11_reference "severity" --kind extension
python scripts/import_icd11_reference.py --archive WHO-ICD11-2026.zip --output nova_agent/ontology/snapshots/icd11_reference_2026.sqlite --report import-report.json
```

The importer refuses to overwrite an existing installation, validates official workbook fields,
retains duplicate-free codes, and checks SQLite integrity before atomic installation.
The lookup uses parameterized literal matching and includes original URI, release, attribution
and non-validated status. `openpyxl` is needed only for import; lookup uses Python's sqlite3.

## Provenance and verification

- Source: https://icdcdn.who.int/static/releasefiles/2026-01/SimpleTabulation-ICD-11-MMS-en.zip
- Official browser: https://icd.who.int/browse/2026-01/mms/en
- Terms: https://icd.who.int/en/docs/ICD11-license.pdf
- International Classification of Diseases, Eleventh Revision (ICD-11), World Health Organization
  (WHO) 2019. https://icd.who.int/browse11. CC BY-ND 3.0 IGO. No WHO endorsement of NOVA.

`icd11_2026_import.json` records source hash and counts. `icd11_2026_checks.json` records equality
of all 37,052 imported original rows to the workbook, no duplicate/missing codes, database integrity,
exact-code lookup and unchanged runtime catalog size. Importer unit tests use synthetic fixtures.
WHO data and the generated database are intentionally not committed under the repository's
operator-supplied terminology policy. A separate downloadable bundle retains source, database,
license and attribution for restoration. The importer and reports are committed.

## Regression and restore

Full non-API suite before the packaging exclusion: 617 passed, 1 skipped. The pre-existing
API TestClient initialization issue remains unresolved; the API file was explicitly excluded.
The packaging exclusion additionally prevents local reference databases and journals from being
copied into competition submissions. Focused importer/packaging/safety checks: 40 passed
(`icd11_2026_focused.txt`). The source-sync check explicitly excludes operator databases and
separately asserts that no SQLite database or journal is present in the submission.

To restore the downloadable bundle, copy `icd11_reference_2026.sqlite` into
`nova_agent/ontology/snapshots/`. The default diagnostic registry intentionally ignores this SQLite
file. The package retains the original WHO ZIP and license PDF; source labels are English.
