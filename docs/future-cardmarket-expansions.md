# Expansion Reference Data

## Purpose

The `expansions` reference layer exists to translate Cardmarket's internal Pokémon `idExpansion` values into human-readable expansion metadata.

Cardmarket product catalog files contain an `idExpansion` field for each product. This field is useful as a stable technical identifier, but it is not enough for analysis, reporting, or collection tracking because a value such as `5093` does not explain the actual expansion name.

For example:

| id_expansion | name_en | name_de |
|---:|---|---|
| 5093 | Lost Origin | Verlorener Ursprung |

The goal of this layer is to make product and price data easier to analyze without modifying the original raw files.

---

## Design Principle

The original Cardmarket files must remain raw and unchanged.

The project does not write English or German expansion names directly into `products_singles_6.json`, `products_nonsingles_6.json`, or daily price guide files. Instead, expansion metadata is stored in a separate curated reference table.

This keeps the project architecture clean:

```text
raw Cardmarket product catalog
        ↓
products table
        ↓ products.id_expansion
expansions reference table
        ↓
BI-ready enriched views
```

This follows a common data engineering pattern:

| Layer | Purpose |
|---|---|
| Raw data | Store original source files exactly as downloaded. |
| Reference data | Store manually reviewed lookup tables and metadata. |
| Database tables | Store normalized entities used by the application. |
| Views | Create BI-ready joined datasets. |

---

## Why This Is a Separate Table

Expansion metadata should live in its own table because one expansion can contain hundreds of products.

A bad approach would be to duplicate expansion names in every product row:

```text
products.expansion_name_en
products.expansion_name_de
```

The preferred approach is:

```text
products.id_expansion → expansions.id_expansion
```

Benefits:

1. No duplicated expansion names across thousands of product rows.
2. One correction updates the expansion name everywhere.
3. The table can later include more metadata such as release date, series, logo URL, symbol URL, or external IDs.
4. BI reports can filter products by expansion, series, or release date.
5. The raw Cardmarket archive stays untouched.

---

## Main Files

The expansion reference layer uses the following files:

```text
data/reference/
├── expansions.csv
├── expansions_seed.csv
└── README.md
```

### `data/reference/expansions.csv`

This is the final curated reference file.

It is the source of truth for the `expansions` database table.

Example:

```csv
id_expansion,name_en,name_de,slug,series_en,series_de,release_date,card_count,source_url_en,source_url_de,is_active,notes
5093,Lost Origin,Verlorener Ursprung,Lost-Origin,Sword & Shield,Schwert & Schild,2022-09-09,266,https://www.cardmarket.com/en/Pokemon/Expansions/Lost-Origin,https://www.cardmarket.com/de/Pokemon/Expansions/Lost-Origin,true,Initial manually verified example.
```

### `data/reference/expansions_seed.csv`

This is a generated working file.

It is created from Cardmarket product catalog files and lists all detected `idExpansion` values. It helps identify which expansions are missing from the curated reference table.

This file can be regenerated and should not be treated as the final source of truth.

---

## Database Table

The main table is:

```text
expansions
```

Recommended schema:

```sql
CREATE TABLE IF NOT EXISTS expansions (
    id_expansion INTEGER PRIMARY KEY,

    name_en TEXT NOT NULL,
    name_de TEXT,

    slug TEXT,
    series_en TEXT,
    series_de TEXT,

    release_date DATE,
    card_count INTEGER,

    source_url_en TEXT,
    source_url_de TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

SQLite uses a compatible version stored in:

```text
sql/schema/01_expansions_sqlite.sql
```

PostgreSQL/Supabase uses:

```text
sql/schema/01_expansions.sql
```

---

## Field Definitions

| Field | Type | Required | Description |
|---|---:|---:|---|
| `id_expansion` | integer | yes | Cardmarket expansion identifier. Primary key. |
| `name_en` | text | yes | English expansion name. |
| `name_de` | text | recommended | German expansion name. |
| `slug` | text | recommended | Cardmarket URL slug, for example `Lost-Origin`. |
| `series_en` | text | optional | English series name, for example `Sword & Shield`. |
| `series_de` | text | optional | German series name, for example `Schwert & Schild`. |
| `release_date` | date | optional | Expansion release date in ISO format: `YYYY-MM-DD`. |
| `card_count` | integer | optional | Number of cards listed for the expansion. |
| `source_url_en` | text | recommended | English Cardmarket expansion page. |
| `source_url_de` | text | recommended | German Cardmarket expansion page. |
| `is_active` | boolean | yes | Whether the expansion should be considered active in the reference dataset. |
| `notes` | text | optional | Manual notes about mapping, uncertainty, source, or corrections. |
| `created_at` | timestamp | yes | Row creation timestamp in the database. |
| `updated_at` | timestamp | yes | Last update timestamp in the database. |

---

## Relationship with Products

The products table should store only the Cardmarket expansion ID:

```sql
id_expansion INTEGER REFERENCES expansions(id_expansion)
```

Products should not duplicate `name_en`, `name_de`, `series_en`, or `release_date`.

The relationship is:

```text
products.id_expansion → expansions.id_expansion
```

Example join:

```sql
SELECT
    p.id_product,
    p.product_name,
    p.id_expansion,
    e.name_en AS expansion_name_en,
    e.name_de AS expansion_name_de,
    e.series_en,
    e.series_de,
    e.release_date
FROM products p
LEFT JOIN expansions e
    ON p.id_expansion = e.id_expansion;
```

---

## BI View

The project includes the view:

```text
sql/views/vw_products_enriched.sql
```

Purpose:

```text
products + expansions = analysis-ready product catalog
```

The view adds expansion metadata to each product row without changing the underlying `products` table.

Typical BI fields:

| Field | Meaning |
|---|---|
| `id_product` | Cardmarket product ID. |
| `product_name` | Product/card name. |
| `id_expansion` | Cardmarket expansion ID. |
| `expansion_name_en` | English expansion name. |
| `expansion_name_de` | German expansion name. |
| `series_en` | English series name. |
| `series_de` | German series name. |
| `expansion_release_date` | Expansion release date. |

---

## Scripts

Expansion-related scripts live in:

```text
scripts/reference/
├── extract_expansions_seed.py
├── validate_expansions_reference.py
└── load_expansions.py
```

### `extract_expansions_seed.py`

Creates a seed file with all unique `idExpansion` values found in product catalog JSON files.

Default input:

```text
data/raw/cardmarket/pokemon/product_catalogs/
```

Default output:

```text
data/reference/expansions_seed.csv
```

Run:

```bash
python scripts/reference/extract_expansions_seed.py
```

Optional explicit input:

```bash
python scripts/reference/extract_expansions_seed.py \
  --input-file data/raw/cardmarket/pokemon/product_catalogs/products_singles_6_2026-07-15.json \
  --input-file data/raw/cardmarket/pokemon/product_catalogs/products_nonsingles_6_2026-07-15.json
```

### `validate_expansions_reference.py`

Checks whether every `idExpansion` used in product catalogs exists in `expansions.csv`.

Run:

```bash
python scripts/reference/validate_expansions_reference.py
```

If a new Cardmarket expansion appears and is missing from the curated file, the script reports it:

```text
Missing expansions in data/reference/expansions.csv:
- 5301
- 5302
```

This is intentional. It tells the maintainer to update the reference table.

### `load_expansions.py`

Loads `data/reference/expansions.csv` into the local SQLite database.

Default database:

```text
db/local/pokemon_cardmarket_bi.db
```

Run:

```bash
python scripts/reference/load_expansions.py
```

---

## SQL Checks

Expansion checks live in:

```text
sql/checks/
├── missing_expansions_check.sql
└── products_without_expansion_reference_check.sql
```

### `missing_expansions_check.sql`

Returns distinct expansion IDs that exist in `products` but are missing from `expansions`.

### `products_without_expansion_reference_check.sql`

Returns product rows that cannot be enriched with expansion metadata.

These checks are useful after loading new product catalogs.

---

## Update Logic

The reference table should be updated when new Cardmarket product catalogs introduce new `idExpansion` values.

Recommended flow:

```text
1. Download latest product catalogs.
2. Run extract_expansions_seed.py.
3. Compare detected idExpansion values with expansions.csv.
4. Add missing English/German names and metadata manually.
5. Run validate_expansions_reference.py.
6. Load expansions.csv into the database.
7. Use vw_products_enriched for analysis.
```

---

## Why Manual Enrichment Is Acceptable

This project intentionally keeps expansion metadata curated instead of fully automated.

Reasons:

1. Pokémon expansions are released infrequently.
2. English/German names need to be correct for BI and UI use.
3. Cardmarket product files expose `idExpansion`, but not necessarily a complete localized expansion reference table.
4. Manual review prevents incorrect slug/name matching.
5. The reference table remains small and easy to maintain.

The automation detects missing IDs. The human reviewer confirms names and metadata.

This is a good MVP trade-off.

---

## Source Strategy

Primary key source:

```text
Cardmarket product catalog → idExpansion
```

Primary metadata source:

```text
Cardmarket expansion pages
```

Example:

| Language | URL |
|---|---|
| English | `https://www.cardmarket.com/en/Pokemon/Expansions/Lost-Origin` |
| German | `https://www.cardmarket.com/de/Pokemon/Expansions/Lost-Origin` |

External sources such as TCGdex or Bulbapedia may be used later for validation or enrichment, but they should not replace Cardmarket `idExpansion` as the project key.

---

## GitHub Actions

The project includes an optional workflow:

```text
.github/workflows/expansions-reference-check.yml
```

It runs:

1. Unit tests for the reference file.
2. Expansion coverage validation if product catalog JSON files exist in the repository.

This workflow is useful for pull requests that change `expansions.csv`, product catalog samples, or reference scripts.

For the main scheduled pipeline, expansion validation can also be added to:

```text
.github/workflows/product-catalog-twice-monthly.yml
```

Recommended order:

```text
1. Download product catalogs.
2. Validate product catalog structure.
3. Extract expansion seed.
4. Validate expansions reference coverage.
5. Stop the workflow if new idExpansion values are missing.
```

---

## Placement Summary

Add these files:

```text
data/reference/expansions.csv
data/reference/expansions_seed.csv
data/reference/README.md

sql/schema/01_expansions.sql
sql/schema/01_expansions_sqlite.sql

sql/views/vw_products_enriched.sql
sql/views/vw_products_enriched_sqlite.sql

sql/checks/missing_expansions_check.sql
sql/checks/products_without_expansion_reference_check.sql

scripts/reference/extract_expansions_seed.py
scripts/reference/validate_expansions_reference.py
scripts/reference/load_expansions.py

tests/test_expansions_reference.py

.github/workflows/expansions-reference-check.yml

docs/expansion.md
```

---

## Important Naming Decision

The Cardmarket source field is called:

```text
idExpansion
```

Inside the project database and CSV files, the normalized name should be:

```text
id_expansion
```

Reason:

1. SQL and Python are easier to read with snake_case.
2. It is consistent with names like `id_product`, `id_category`, and `created_at`.
3. The raw field name is still preserved in raw archived files.

Mapping rule:

```text
raw.idExpansion → database.id_expansion
```

---

## Current MVP Decision

For the MVP, the expansion reference layer is:

```text
semi-automated detection + manually curated metadata
```

Automation is responsible for:

```text
finding all unique idExpansion values
detecting missing mappings
loading the curated table
supporting CI validation
```

Manual review is responsible for:

```text
English name
German name
Cardmarket slug
series name
release date
card count
source URLs
```

This is the cleanest balance between reliability, simplicity, and portfolio-quality data modeling.
