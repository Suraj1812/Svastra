# Svastra+ Local Terminology Database Bundle

This folder contains the source data and SQLite SQL scripts required to rebuild
the local Svastra+ terminology database on a developer machine.

Svastra+ uses strict local device storage for privacy and security. This
terminology database is reference data only. It does not contain PHI. The
PostOffice API remains the cloud component for Canonical Event Payload exchange;
PostOffice is not the runtime terminology store.

## Files to Share

Share these files with engineers:

| File | Purpose |
| --- | --- |
| `svp_entry_terms.json` | Human-facing selectable terms with `conceptId`, `term`, and `tag`. |
| `ide_drug_catalog_transformed.json` | Medication catalog with drug concept, ingredients, dose form concept, prescription text, and administration text. |
| `doseform_unitdose_mapping.json` | Dose-form/unit-dose option source data. |
| `allergy_causative_pairs.json` | Allergy concept to causative-agent concept relationships. |
| `substance_ancestors.json` | Substance subtype/equivalence ancestry relationships. |
| `01_create_schema.sql` | Drops and creates the SQLite schema. |
| `02_load_json.sql` | Loads the JSON files into SQLite and creates indexes/FTS. |
| `03_query_examples.sql` | Query examples for autocomplete, UI routing, dose-unit lookup, and allergy checks. |
| `README.md` | Developer instructions. |
| `MANIFEST.json` | Version, checksums, expected counts, and known caveats. |

The generated SQLite database file does not need to be shared if developers are
expected to rebuild locally. If a prebuilt database is shared, use the generated
file name `svp_terminology.sqlite` or another versioned name documented in
`MANIFEST.json`.

## Required Tooling

Use the SQLite command-line shell with JSON1 and FTS5 support. The scripts use:

- `json_each`
- `json_extract`
- `readfile`
- FTS5
- generated columns

The `readfile()` function is available in the standard SQLite CLI builds, but
is not always available through language bindings unless explicitly registered.

## Build

From the folder containing the JSON files and SQL scripts:

```powershell
sqlite3 svp_terminology.sqlite ".read 01_create_schema.sql" ".read 02_load_json.sql"
```

On macOS/Linux:

```bash
sqlite3 svp_terminology.sqlite ".read 01_create_schema.sql" ".read 02_load_json.sql"
```

Expected result from the current data set is approximately a 516 MB SQLite
database.

## Runtime Use

The Svastra+ application should open the database read-only.

Recommended configuration:

```text
SVASTRA_TERMINOLOGY_DB=./data/terminology/svp_terminology.sqlite
```

Recommended Python connection:

```python
import sqlite3

conn = sqlite3.connect(
    "file:./data/terminology/svp_terminology.sqlite?mode=ro&immutable=1",
    uri=True,
)
```

Use `immutable=1` only when the deployed database file will never be modified in
place.

## Application Contract

Humans work with `term`.

The system works with `concept_id` / `conceptId`.

The UI should:

1. Search terms by characters typed by the user.
2. Present autocomplete/autosuggest options filtered by tag.
3. Store the selected `conceptId`.
4. Use the selected tag to decide which controls to show.
5. Persist canonical clinical structures by concept ID, not by display term.

## Main Tables

| Table | Description |
| --- | --- |
| `concepts` | Unique concept IDs used by the terminology bundle. |
| `terms` | Human-readable terms and synonyms. |
| `tags` | UI and clinical classification tags. |
| `concept_tags` | Concept-to-tag classification. |
| `term_tags` | Term-to-tag classification. |
| `terms_fts` | FTS5 index for fast autocomplete/autosuggest. |
| `drug_catalog` | Medication catalog rows. |
| `drug_ingredients` | Medication-to-ingredient concept relationships. |
| `allergy_causative_agents` | Allergy concept to causative-agent concept relationships. |
| `substance_ancestors` | Substance ancestor/equivalence relationships. |
| `dose_forms` | Dose-form concepts from the unit-dose mapping file. |
| `unit_doses` | Unit-dose concepts and display terms. |
| `doseform_unit_options` | Dose-form to allowed unit-dose options. |

## Allergy Check

The allergy check is true when any ingredient of a medication is equivalent to,
or a subtype of, any causative agent linked to any selected drug allergy.

Use these tables:

- `drug_ingredients`
- `allergy_causative_agents`
- `substance_ancestors`

See `03_query_examples.sql` for both boolean and explanatory allergy-check
queries.

## Autocomplete and Autosuggest

Use `terms_fts` for fast token-prefix search:

```sql
WHERE terms_fts MATCH (:query_prefix || '*')
```

Use the contains fallback query in `03_query_examples.sql` only when the UI must
match characters inside a term. Contains search is less index-friendly than FTS
prefix search.

## Dose-Form and Unit-Dose Caveat

The current `doseform_unitdose_mapping.json` loads correctly into:

- `dose_forms`
- `unit_doses`
- `doseform_unit_options`

However, the current drug catalog field `dose_form_conceptId` does not directly
match the `formConceptId` values in `doseform_unitdose_mapping.json`.

Validation result for the current files:

```text
drug_catalog.dose_form_concept_id direct matches to dose_forms.form_concept_id: 0
```

This means medication-to-unit-dose suggestions need one additional data bridge:

- either add a matching unit-of-presentation/form concept ID to each drug row,
- or provide a crosswalk from drug catalog `dose_form_conceptId` to
  `doseform_unitdose_mapping.formConceptId`.

Until that crosswalk exists, the database can store both datasets but cannot
reliably infer unit-dose options for a selected medication.

## Expected Counts

After a successful rebuild from the current source JSON files:

```text
source_files                 5
concepts               345,504
terms                  646,849
tags                        24
concept_tags           361,692
term_tags              678,844
drug_catalog            93,603
drug_ingredients       124,110
dose_forms                  50
unit_doses                  41
doseform_unit_options       52
allergy_causative_agents 1,039
substance_ancestors  2,053,938
terms_fts             646,849
```

## Verification

Use checksums in `MANIFEST.json` to verify received files.

PowerShell:

```powershell
Get-FileHash .\svp_entry_terms.json -Algorithm SHA256
```

Python:

```python
import hashlib
from pathlib import Path

path = Path("svp_entry_terms.json")
print(hashlib.sha256(path.read_bytes()).hexdigest())
```

## Recommended Bundle Name

```text
svastra_terminology_bundle_v20260625.zip
```

Do not hardcode developer-machine paths such as `D:\...` in application code.
Use configuration or an environment variable such as `SVASTRA_TERMINOLOGY_DB`.
