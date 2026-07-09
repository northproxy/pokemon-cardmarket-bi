# Stage 2: Cardmarket Product Catalog Foundation

## New Chat Starter Prompt

I want to continue my learning-focused Pokémon Cardmarket BI project.

Project name:

```text
pokemon-cardmarket-bi
```

Main goal:

Build a clean, documented data engineering / BI project around Pokémon Cardmarket price analysis, personal collection tracking, and future analytics signals.

Current status:

Stage 1 is completed.

I created and validated the first reference dataset:

```text
pokemon_tcg_sets
```

This table is based only on the official Pokémon TCG `en.json` source, not on Cardmarket mapping.

Stage 1 source:

```text
data/reference/pokemon_tcg/sets/en.json
```

Generated CSV:

```text
data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
```

Database table:

```text
public.pokemon_tcg_sets
```

Primary key:

```text
pokemon_tcg_set_id
```

Important Stage 1 decisions:

- `pokemon_tcg_sets` is my own local official Pokémon TCG sets reference table.
- It is not a raw copy of the source JSON.
- Cardmarket fields such as `id_expansion`, German names, slugs, source URLs, and mapping confidence are intentionally excluded from v1.
- Cardmarket mapping will be designed later through migrations or a separate mapping table.
- `secret_card_count` is normalized as `max(total_cards - printed_total, 0)`.
- Promo/special source anomalies are preserved and documented in `notes`.

Stage 1 validation result:

- CSV was generated successfully.
- Import into PostgreSQL / Supabase succeeded.
- No missing set IDs.
- No missing English names.
- No duplicate primary keys.
- No negative card count values.
- No missing `created_at` or `updated_at` values.
- Two source anomalies were detected and accepted:
  - `swshp` — SWSH Black Star Promos
  - `svp` — Scarlet & Violet Black Star Promos

Current focus:

I now want to start Stage 2:

```text
Cardmarket Product Catalog Foundation
```

The goal of Stage 2 is to build a clean normalized product catalog table from Cardmarket product catalog JSON files.

Important design decision:

Do not start Cardmarket ↔ Pokémon TCG set mapping yet.

Stage 2 is only about understanding and normalizing Cardmarket product catalog data into a clean table.

Expected source file for first inspection:

```text
data/raw/cardmarket/pokemon/product_catalogs/products_singles_6_2026-07-05.json
```

Possible later source:

```text
data/raw/cardmarket/pokemon/product_catalogs/products_nonsingles_6_2026-07-05.json
```

For now, start with singles only.

Target concept:

```text
Cardmarket product catalog JSON → inspection → normalized CSV → PostgreSQL table → SQL checks → documentation
```

Please help me step by step, practically, and do not overcomplicate the design.

First thing I want to do:

Create an inspection script for the Cardmarket `products_singles` JSON file before designing the SQL schema.

The inspection should help us discover:

- total number of products
- source JSON structure
- top-level fields
- example product rows
- common missing fields
- unique `idCategory` values
- unique `idExpansion` values
- candidate fields for a minimal v1 `cardmarket_products` table

Please continue from this context.

---

# Stage 2 Plan: Cardmarket Product Catalog Foundation

## 1. Purpose

Stage 2 creates the foundation for Cardmarket product data.

The project already has an official Pokémon TCG sets reference table:

```text
pokemon_tcg_sets
```

The next required layer is a clean Cardmarket product catalog table.

This table will later support:

- daily price snapshots
- personal collection tracking
- product-level analytics
- expansion mapping
- BI views
- future price trend signals

At this stage, the goal is not analytics yet. The goal is to create a reliable product foundation.

---

## 2. Important Scope Decision

Stage 2 does not design Cardmarket mapping yet.

Do not map:

```text
pokemon_tcg_sets.pokemon_tcg_set_id
```

to:

```text
Cardmarket idExpansion
```

in this stage.

That mapping is a later step.

Stage 2 only answers:

```text
What products exist in the Cardmarket catalog, and how should we store them cleanly?
```

---

## 3. Source Files

Start with one concrete Cardmarket product catalog file:

```text
data/raw/cardmarket/pokemon/product_catalogs/products_singles_6_2026-07-05.json
```

Later, the same approach can be extended to:

```text
data/raw/cardmarket/pokemon/product_catalogs/products_nonsingles_6_2026-07-05.json
```

For Stage 2 v1, use singles only.

Reason:

- singles are closest to card-level price analytics
- the data model is easier to understand
- it avoids mixing cards, sealed products, accessories, and non-card products too early

---

## 4. Planned Output

The main planned database table is:

```text
public.cardmarket_products
```

The generated CSV will likely be stored here:

```text
data/reference/cardmarket/products/cardmarket_products.csv
```

The exact schema should not be finalized before inspecting the JSON source.

---

## 5. Recommended Stage 2 Folder Structure

Add the following structure:

```text
pokemon-cardmarket-bi/
├── data/
│   └── reference/
│       └── cardmarket/
│           └── products/
│               ├── README.md
│               └── cardmarket_products.csv
│
├── docs/
│   └── inspection/
│       └── cardmarket_products_singles_structure.md
│
├── scripts/
│   ├── inspection/
│   │   └── inspect_cardmarket_products.py
│   └── reference/
│       └── load_cardmarket_products.py
│
└── sql/
    ├── schema/
    │   └── 01_cardmarket_products.sql
    ├── imports/
    │   └── import_cardmarket_products.sql
    └── checks/
        └── cardmarket_products_basic_check.sql
```

This mirrors the successful Stage 1 structure.

---

## 6. Step-by-Step Plan

## Step 2.1 — Inspect the Cardmarket Product Catalog

Create:

```text
scripts/inspection/inspect_cardmarket_products.py
```

The script should read:

```text
data/raw/cardmarket/pokemon/product_catalogs/products_singles_6_2026-07-05.json
```

The script should output an inspection report to:

```text
docs/inspection/cardmarket_products_singles_structure.md
```

The report should include:

- source file path
- inspection timestamp
- total number of product records
- detected JSON root type
- top-level fields
- data types per field
- number of missing/null values per field
- sample rows
- unique `idCategory` values
- unique `idExpansion` count
- first 20 `idExpansion` examples
- possible v1 table fields
- warnings or source anomalies

Purpose:

```text
Do not guess the schema. Inspect the source first.
```

---

## Step 2.2 — Decide Minimal v1 Fields

After inspection, decide a minimal table structure.

Possible candidate fields:

```text
id_product
name_en
id_category
id_expansion
image_url
is_active_in_catalog
source_file
source_snapshot_date
created_at
updated_at
```

Only keep fields that exist clearly and consistently in the source.

Avoid adding derived or uncertain fields too early.

---

## Step 2.3 — Create Product Loader Script

Create:

```text
scripts/reference/load_cardmarket_products.py
```

Purpose:

```text
Cardmarket products_singles JSON → normalized CSV
```

Expected output:

```text
data/reference/cardmarket/products/cardmarket_products.csv
```

The loader should:

- read one source JSON file
- normalize source field names to snake_case
- keep Cardmarket product IDs unchanged
- preserve `idExpansion` as `id_expansion`
- preserve `idCategory` as `id_category`
- add source metadata
- write a clean CSV

The loader should not:

- download data
- import directly into Supabase
- map to Pokémon TCG sets
- enrich with German names
- calculate prices
- create BI signals

---

## Step 2.4 — Create SQL Schema

Create:

```text
sql/schema/01_cardmarket_products.sql
```

The table should probably be:

```text
public.cardmarket_products
```

Expected design principles:

- `id_product` is the primary key
- `id_expansion` is stored, but not mapped yet
- `id_category` is stored for filtering and validation
- source metadata is stored for traceability
- `created_at` and `updated_at` are handled by the database
- constraints should be safe, not overly strict

Do not add a foreign key to `pokemon_tcg_sets` in this stage.

---

## Step 2.5 — Create Import SQL

Create:

```text
sql/imports/import_cardmarket_products.sql
```

This file should document import options:

- Supabase Table Editor CSV import
- local PostgreSQL `COPY`
- `psql \copy`
- future staging/upsert approach

For v1, manual Supabase CSV import is acceptable.

---

## Step 2.6 — Create Basic SQL Checks

Create:

```text
sql/checks/cardmarket_products_basic_check.sql
```

Checks should include:

- total row count
- missing product IDs
- duplicate product IDs
- missing product names
- missing `id_expansion`
- missing `id_category`
- products by category
- products by expansion
- sample products
- source file distribution
- created_at / updated_at check

Avoid checks that assume mapping already exists.

---

## Step 2.7 — Import Into Supabase

Recommended first import method:

```text
Supabase Table Editor CSV import
```

Import:

```text
data/reference/cardmarket/products/cardmarket_products.csv
```

into:

```text
public.cardmarket_products
```

After import, run:

```text
sql/checks/cardmarket_products_basic_check.sql
```

---

## Step 2.8 — Document the Dataset

Create:

```text
data/reference/cardmarket/products/README.md
```

The README should document:

- purpose of the dataset
- source file
- transformation logic
- field mapping
- known limitations
- import process
- validation result
- why mapping is intentionally postponed

Keep it practical and short.

---

## 7. What Not to Do in Stage 2

Do not add yet:

- Cardmarket ↔ Pokémon TCG set mapping
- German expansion names
- Cardmarket expansion slugs
- Cardmarket expansion URL reference table
- BI dashboards
- price trend signals
- personal collection tracking
- automated GitHub Actions
- complex staging/upsert logic
- nonsingles support unless singles are stable first

---

## 8. Stage 2 Definition of Done

Stage 2 v1 is done when:

- the source Cardmarket singles JSON structure has been inspected
- inspection report exists in `docs/inspection/`
- normalized `cardmarket_products.csv` exists
- `public.cardmarket_products` table exists
- CSV import into PostgreSQL / Supabase succeeds
- basic SQL checks pass
- known anomalies are documented
- dataset README exists
- changes are committed to Git

---

## 9. Suggested Git Commit

After Stage 2 is completed:

```bash
git add data/reference/cardmarket/products/README.md
git add data/reference/cardmarket/products/cardmarket_products.csv
git add docs/inspection/cardmarket_products_singles_structure.md
git add scripts/inspection/inspect_cardmarket_products.py
git add scripts/reference/load_cardmarket_products.py
git add sql/schema/01_cardmarket_products.sql
git add sql/imports/import_cardmarket_products.sql
git add sql/checks/cardmarket_products_basic_check.sql

git commit -m "Add Cardmarket products reference foundation"
```

---

## 10. Recommended First Task in the New Chat

Start with:

```text
Create Stage 2 inspection script for Cardmarket products_singles JSON.
```

The first file to build should be:

```text
scripts/inspection/inspect_cardmarket_products.py
```

This keeps the project disciplined:

```text
inspect first → design second → transform third → import fourth → validate fifth
```
