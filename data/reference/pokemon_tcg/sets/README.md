# Pokémon TCG Sets Reference Import Process

This document describes the process for creating the first version of the `pokemon_tcg_sets` reference dataset.

The goal is to transform the Pokémon TCG sets JSON file into a clean CSV file, import it into PostgreSQL / Supabase, and validate the result with SQL checks.

This stage intentionally does **not** include Cardmarket mapping.

---

## Process Overview

The `pokemon_tcg_sets` dataset is built in four steps:

1. Store the source JSON file in the project.
2. Run a Python script to convert the JSON file into a normalized CSV file.
3. Import the CSV file into the PostgreSQL / Supabase table.
4. Run SQL checks to validate the imported data.

---

## 1. Source File Location

The source file is stored here:

```text
data/reference/pokemon_tcg/sets/en.json
```

The file contains Pokémon TCG set metadata such as:

- set ID
- set name
- series name
- release date
- printed card count
- total card count
- legalities
- image URLs
- source update timestamp

The pinned upstream source used for this dataset is:

```text
https://github.com/PokemonTCG/pokemon-tcg-data/blob/0af6250a22495e4a3e9f60ff45fc3fedc2e0563d/sets/en.json
```

---

## 2. CSV Generation

The source JSON file is converted into a clean CSV file using:

```text
scripts/reference/load_pokemon_tcg_sets.py
```

Run the script from the project root:

```powershell
python scripts/reference/load_pokemon_tcg_sets.py
```

Or with a specific Python installation:

```powershell
C:/python3810/python.exe scripts/reference/load_pokemon_tcg_sets.py
```

The script reads:

```text
data/reference/pokemon_tcg/sets/en.json
```

And creates:

```text
data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
```

---

## 3. Transformation Logic

The Python script performs the following transformations:

| Source JSON Field | CSV Field |
|---|---|
| `id` | `pokemon_tcg_set_id` |
| `name` | `name_en` |
| `series` | `series_en` |
| `ptcgoCode` | `ptcgo_code` |
| `releaseDate` | `release_date` |
| `printedTotal` | `printed_total` |
| `total` | `total_cards` |
| derived from `total` and `printedTotal` | `secret_card_count` |
| `legalities` | `legalities` |
| `images.symbol` | `symbol_url` |
| `images.logo` | `logo_url` |
| `updatedAt` | `source_updated_at` |

The script also adds local project fields:

| Field | Default Value |
|---|---|
| `is_active` | `true` |
| `notes` | empty string, unless a source anomaly is detected |

The fields `created_at` and `updated_at` are not included in the CSV. They are generated automatically by the database.

---

## 4. Date Normalization

The source JSON uses dates in this format:

```text
YYYY/MM/DD
```

Example:

```text
2022/09/09
```

The CSV stores dates in ISO format:

```text
YYYY-MM-DD
```

Example:

```text
2022-09-09
```

This makes dates easier to sort, filter, and use in SQL queries.

The source update timestamp is also normalized from:

```text
YYYY/MM/DD HH:MM:SS
```

to:

```text
YYYY-MM-DD HH:MM:SS
```

---

## 5. Secret Card Count

The `secret_card_count` field is calculated during CSV generation.

For regular sets, the logical formula is:

```text
secret_card_count = total_cards - printed_total
```

Example:

```text
217 - 196 = 21
```

However, some promo or special sets in the source data may have `total_cards` lower than `printed_total`.

To keep the analytical field safe and non-negative, the loader uses:

```text
secret_card_count = max(total_cards - printed_total, 0)
```

If either `printed_total` or `total_cards` is missing, `secret_card_count` remains empty.

When `total_cards < printed_total`, the row is still imported, `secret_card_count` is normalized to `0`, and the reason is stored in the `notes` field.

---

## 6. Database Schema

The PostgreSQL / Supabase table is defined in:

```text
sql/schema/00_pokemon_tcg_sets.sql
```

This file creates the table:

```text
public.pokemon_tcg_sets
```

The table uses:

```text
pokemon_tcg_set_id
```

as the primary key.

Example IDs:

```text
base1
swsh11
sv03
```

The schema includes:

- basic data quality constraints
- indexes for common filters
- automatic `updated_at` trigger

The schema does **not** enforce `total_cards >= printed_total`, because some valid source rows do not follow that rule.

---

## 7. Importing the CSV

The generated CSV can be imported into the database using one of the following methods.

### Option A: Supabase Table Editor

For the first version, the simplest method is to use the Supabase web interface:

1. Open Supabase.
2. Go to the `pokemon_tcg_sets` table.
3. Use the CSV import feature.
4. Select:

```text
data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
```

5. Confirm that the CSV columns match the table columns.
6. Import the file.

The CSV does not contain `created_at` and `updated_at`. This is expected because the database fills these fields automatically.

### Option B: SQL / psql Import

A helper SQL file is stored here:

```text
sql/imports/import_pokemon_tcg_sets.sql
```

This file documents possible import approaches using `COPY`, `\copy`, or a temporary staging table with `ON CONFLICT` upsert logic.

For v1, manual Supabase CSV import is enough.

---

## 8. Data Validation

After importing the CSV into the database, run:

```text
sql/checks/pokemon_tcg_sets_basic_check.sql
```

This file contains basic validation queries.

The checks include:

- total row count
- active / inactive row count
- missing Pokémon TCG set IDs
- missing English names
- duplicate set IDs
- card count consistency
- secret card count calculation
- negative numeric values
- source anomalies where `total_cards < printed_total`
- missing release dates
- missing series names
- missing PTCGO codes
- series overview
- latest sets by release date
- example lookup for `Lost Origin`
- metadata check for `created_at` and `updated_at`

Some checks are expected to return rows. For example, older or special sets may not have a `ptcgo_code`.

Rows where `total_cards < printed_total` are also allowed. They are treated as source anomalies, not failed imports.

---

## 9. Recommended Execution Order

The recommended order for building this dataset is:

```text
1. Place source file:
   data/reference/pokemon_tcg/sets/en.json

2. Run Python transformation script:
   scripts/reference/load_pokemon_tcg_sets.py

3. Confirm generated CSV:
   data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv

4. Create database table:
   sql/schema/00_pokemon_tcg_sets.sql

5. Import CSV into database:
   Supabase Table Editor or sql/imports/import_pokemon_tcg_sets.sql

6. Run validation checks:
   sql/checks/pokemon_tcg_sets_basic_check.sql
```

---

## 10. Files Used in This Process

```text
data/reference/pokemon_tcg/sets/en.json
data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
data/reference/pokemon_tcg/sets/README.md
scripts/reference/load_pokemon_tcg_sets.py
sql/schema/00_pokemon_tcg_sets.sql
sql/imports/import_pokemon_tcg_sets.sql
sql/checks/pokemon_tcg_sets_basic_check.sql
```

---

## 11. What This Process Does Not Do Yet

This process does not yet:

- download Pokémon TCG data automatically
- import data directly into Supabase from Python
- map Pokémon TCG sets to Cardmarket expansions
- add Cardmarket expansion IDs
- add German set names
- add Cardmarket slugs
- validate against Cardmarket product catalogs
- create BI views

These steps are intentionally postponed.

The current goal is only to create a clean and reliable Pokémon TCG sets reference table.

---

## Known Source Anomalies

Some promo or special sets in the upstream Pokémon TCG source may have `total_cards` lower than `printed_total`.

This table does not reject those rows because they are valid source records. Instead, the loader normalizes:

```text
secret_card_count = max(total_cards - printed_total, 0)
```

When this happens, the reason is stored in the `notes` field.

---

## Validation Result

The first import into `public.pokemon_tcg_sets` completed successfully.

Validation checks confirmed:

- no missing set IDs
- no missing English names
- no duplicate primary keys
- no negative card count values
- no missing `created_at` or `updated_at` values

Two source-data anomalies were detected:

| pokemon_tcg_set_id | name_en | printed_total | total_cards |
|---|---|---:|---:|
| `swshp` | SWSH Black Star Promos | 307 | 304 |
| `svp` | Scarlet & Violet Black Star Promos | 102 | 75 |

These rows are allowed because they are valid records from the upstream source.

For these cases, `secret_card_count` is normalized to `0`, and the reason is stored in the `notes` field.

---

## Summary

The `pokemon_tcg_sets` process creates the first reference dataset for the project.

It starts with the pinned Pokémon TCG `en.json` file, transforms it into a clean CSV, imports it into PostgreSQL / Supabase, and validates the result with SQL checks.

This gives the project a stable foundation before adding Cardmarket products, prices, mappings, and analytics.
