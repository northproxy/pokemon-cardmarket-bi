# Reference Data: Cardmarket Expansions and Pokémon TCG Sets

This folder contains reference datasets used to connect Cardmarket product data with official Pokémon TCG set metadata.

The goal of this reference layer is not only to store names of expansions, but to create a clean mapping between two different data worlds:

1. **Cardmarket expansions**
   Used by Cardmarket to group products, singles, and non-singles.

2. **Pokémon TCG sets**
   Official set metadata from the Pokémon TCG data project.

3. **Mapping layer**
   A controlled bridge between Cardmarket expansion IDs and Pokémon TCG set IDs.

This separation is intentional. A Cardmarket expansion and a Pokémon TCG set may look similar, but they are not guaranteed to be the same entity in every case.

---

## Why this reference layer exists

The main project tracks Pokémon product prices from Cardmarket and prepares the data for analytics and BI.

Cardmarket provides product and price data, but its expansion identifiers are Cardmarket-specific. Pokémon TCG set data provides additional metadata such as:

* official set ID;
* official set name;
* series / era;
* release date;
* printed card count;
* total card count;
* set logo;
* set symbol;
* legality information.

By connecting these sources, the project can answer better analytical questions, for example:

* Which series has the strongest long-term price growth?
* Do older sets behave differently from newer sets?
* Are sets with many secret cards more volatile?
* How does time since release affect sealed product prices?
* Which Cardmarket expansions could not be confidently mapped to official Pokémon TCG sets?

---

## Data sources

### 1. Cardmarket expansions

Local source file:

```text
data/reference/expansions.csv
```

This file contains the Cardmarket expansion reference dataset.

Cardmarket expansion IDs are the primary identifiers used by Cardmarket product data. These IDs are required for joining raw Cardmarket product catalogs and price guide data with expansion metadata.

Example fields:

```text
id_expansion
name_en
name_de
slug
series_en
series_de
release_date
card_count
source_url_en
source_url_de
is_active
notes
created_at
updated_at
```

This dataset is considered the main reference source for Cardmarket-specific expansion information.

---

### 2. Pokémon TCG sets

External source:

```text
PokemonTCG / pokemon-tcg-data / sets / en.json
```

Pinned source version:

```text
0af6250a22495e4a3e9f60ff45fc3fedc2e0563d
```

This JSON file contains official Pokémon TCG set metadata.

Example fields from the source:

```json
{
  "id": "swsh11",
  "name": "Lost Origin",
  "series": "Sword & Shield",
  "printedTotal": 196,
  "total": 217,
  "legalities": {
    "unlimited": "Legal",
    "standard": "Legal",
    "expanded": "Legal"
  },
  "ptcgoCode": "LOR",
  "releaseDate": "2022/09/09",
  "updatedAt": "2022/09/09 13:45:00",
  "images": {
    "symbol": "https://images.pokemontcg.io/swsh11/symbol.png",
    "logo": "https://images.pokemontcg.io/swsh11/logo.png"
  }
}
```

This source is not used as a replacement for Cardmarket expansion data. It is used as an enrichment source.

---

## Data model

The reference layer is split into three tables:

```text
cardmarket_expansions
pokemon_tcg_sets
expansion_set_mappings
```

This structure avoids forcing two different source systems into one table.

---

# 1. `cardmarket_expansions`

This table stores Cardmarket expansion metadata.

It is the source of truth for Cardmarket expansion identifiers.

## Purpose

Use this table when working with Cardmarket product catalogs, price guides, singles, non-singles, or any other Cardmarket-derived dataset.

## Primary key

```text
id_expansion
```

## Schema

| Field           |      Type |    Required | Description                                                                         |
| --------------- | --------: | ----------: | ----------------------------------------------------------------------------------- |
| `id_expansion`  |   integer |         yes | Cardmarket expansion identifier. Primary key.                                       |
| `name_en`       |      text |         yes | English expansion name.                                                             |
| `name_de`       |      text | recommended | German expansion name.                                                              |
| `slug`          |      text | recommended | Cardmarket URL slug, for example `Lost-Origin`.                                     |
| `series_en`     |      text |    optional | English Cardmarket series name, for example `Sword & Shield`.                       |
| `series_de`     |      text |    optional | German Cardmarket series name, for example `Schwert & Schild`.                      |
| `release_date`  |      date |    optional | Cardmarket or manually verified expansion release date in ISO format: `YYYY-MM-DD`. |
| `card_count`    |   integer |    optional | Number of cards listed for the expansion on Cardmarket.                             |
| `source_url_en` |      text | recommended | English Cardmarket expansion page.                                                  |
| `source_url_de` |      text | recommended | German Cardmarket expansion page.                                                   |
| `is_active`     |   boolean |         yes | Whether the expansion should be considered active in the reference dataset.         |
| `notes`         |      text |    optional | Manual notes about mapping, uncertainty, source, or corrections.                    |
| `created_at`    | timestamp |         yes | Row creation timestamp in the database.                                             |
| `updated_at`    | timestamp |         yes | Last update timestamp in the database.                                              |

## Notes

`cardmarket_expansions` should not contain Pokémon TCG API fields directly.

For example, the table should not be expanded with fields such as:

```text
pokemon_tcg_set_id
pokemon_tcg_logo_url
pokemon_tcg_legalities
```

Those fields belong either to `pokemon_tcg_sets` or to the mapping table.

---

# 2. `pokemon_tcg_sets`

This table stores official Pokémon TCG set metadata imported from `sets/en.json`.

## Purpose

Use this table to enrich Cardmarket expansion data with official set metadata.

This table is useful for:

* BI filtering by series;
* calculating age of a set;
* comparing price behavior by release period;
* showing set logos and symbols in a future UI;
* checking whether Cardmarket expansion names match official Pokémon TCG names.

## Primary key

```text
pokemon_tcg_set_id
```

Example:

```text
swsh11
```

## Schema

| Field                |      Type |    Required | Source field    | Description                                                     |
| -------------------- | --------: | ----------: | --------------- | --------------------------------------------------------------- |
| `pokemon_tcg_set_id` |      text |         yes | `id`            | Official Pokémon TCG set ID, for example `swsh11`. Primary key. |
| `name`               |      text |         yes | `name`          | Official English set name, for example `Lost Origin`.           |
| `series`             |      text | recommended | `series`        | Official series / era name, for example `Sword & Shield`.       |
| `printed_total`      |   integer |    optional | `printedTotal`  | Number of cards in the printed main set.                        |
| `total_cards`        |   integer |    optional | `total`         | Total number of cards, including secret cards.                  |
| `secret_card_count`  |   integer |    optional | derived         | Derived value: `total_cards - printed_total`.                   |
| `ptcgo_code`         |      text |    optional | `ptcgoCode`     | Pokémon TCG Online code, for example `LOR`.                     |
| `release_date`       |      date | recommended | `releaseDate`   | Official Pokémon TCG release date, converted to `YYYY-MM-DD`.   |
| `source_updated_at`  | timestamp |    optional | `updatedAt`     | Timestamp from the source file.                                 |
| `legalities_json`    |      json |    optional | `legalities`    | Raw legality object from the source.                            |
| `symbol_url`         |      text |    optional | `images.symbol` | URL of the set symbol image.                                    |
| `logo_url`           |      text |    optional | `images.logo`   | URL of the set logo image.                                      |
| `source_file`        |      text | recommended | internal        | Source file name, for example `sets/en.json`.                   |
| `source_commit`      |      text | recommended | internal        | Git commit hash used for the import.                            |
| `created_at`         | timestamp |         yes | internal        | Row creation timestamp in the database.                         |
| `updated_at`         | timestamp |         yes | internal        | Last update timestamp in the database.                          |

## Derived fields

### `secret_card_count`

```text
secret_card_count = total_cards - printed_total
```

Example:

```text
Lost Origin:
total_cards = 217
printed_total = 196
secret_card_count = 21
```

This is useful for later analytics because sets with more secret or extra cards may behave differently in price development.

---

# 3. `expansion_set_mappings`

This table connects Cardmarket expansions with Pokémon TCG sets.

## Purpose

This is the most important table in the reference model.

It makes the relationship between Cardmarket and Pokémon TCG data explicit, reviewable, and auditable.

A mapping table is necessary because names may differ between sources.

Example:

```text
Cardmarket:
Lost Origin

Pokémon TCG:
Lost Origin
```

This looks easy.

But other cases may be less clear:

```text
Cardmarket:
Sword & Shield - Lost Origin

Pokémon TCG:
Lost Origin
```

Or:

```text
Cardmarket:
Promos / special products / language-specific expansion names

Pokémon TCG:
No direct one-to-one set match
```

The project should not silently assume that equal or similar names always mean the same thing.

## Primary key

Recommended composite key:

```text
id_expansion + pokemon_tcg_set_id
```

Alternatively, the table may use a technical surrogate key:

```text
id_mapping
```

For this project, the composite key is enough unless many-to-many mapping becomes complex.

## Schema

| Field                |      Type |    Required | Description                                                                   |
| -------------------- | --------: | ----------: | ----------------------------------------------------------------------------- |
| `id_expansion`       |   integer |         yes | Cardmarket expansion ID. Foreign key to `cardmarket_expansions.id_expansion`. |
| `pokemon_tcg_set_id` |      text |         yes | Pokémon TCG set ID. Foreign key to `pokemon_tcg_sets.pokemon_tcg_set_id`.     |
| `match_status`       |      text |         yes | Mapping status.                                                               |
| `match_method`       |      text | recommended | Method used to create the mapping.                                            |
| `match_confidence`   |   decimal | recommended | Confidence score from `0.00` to `1.00`.                                       |
| `is_primary_mapping` |   boolean |         yes | Whether this is the primary mapping for this Cardmarket expansion.            |
| `needs_review`       |   boolean |         yes | Whether the mapping should be manually checked.                               |
| `notes`              |      text |    optional | Manual notes about the mapping decision.                                      |
| `created_at`         | timestamp |         yes | Row creation timestamp in the database.                                       |
| `updated_at`         | timestamp |         yes | Last update timestamp in the database.                                        |

---

## Mapping statuses

Allowed values for `match_status`:

| Value            | Meaning                                                               |
| ---------------- | --------------------------------------------------------------------- |
| `matched`        | The Cardmarket expansion is confidently matched to a Pokémon TCG set. |
| `manual_review`  | A possible match exists, but it requires manual verification.         |
| `unmatched`      | No suitable Pokémon TCG set was found.                                |
| `not_applicable` | The Cardmarket expansion does not represent a normal Pokémon TCG set. |

---

## Mapping methods

Allowed values for `match_method`:

| Value             | Meaning                                                          |
| ----------------- | ---------------------------------------------------------------- |
| `exact_name`      | Exact name match.                                                |
| `normalized_name` | Match after cleaning punctuation, casing, prefixes, or suffixes. |
| `slug`            | Match based on Cardmarket URL slug.                              |
| `code`            | Match based on known set code, for example `LOR`.                |
| `date_name_combo` | Match based on name similarity and release date proximity.       |
| `manual`          | Manually verified mapping.                                       |
| `none`            | No match method available.                                       |

---

## Match confidence

`match_confidence` should be a decimal value between `0.00` and `1.00`.

Recommended interpretation:

|         Range | Meaning                                                        |
| ------------: | -------------------------------------------------------------- |
|        `1.00` | Manually verified or exact reliable match.                     |
| `0.90 - 0.99` | Very strong automated match.                                   |
| `0.70 - 0.89` | Probable match, but should be reviewed.                        |
| `0.40 - 0.69` | Weak match. Manual review required.                            |
| `0.00 - 0.39` | Not reliable. Should not be used for analytics without review. |

---

## Example mapping

```text
Cardmarket expansion:
id_expansion = 12345
name_en = Lost Origin

Pokémon TCG set:
pokemon_tcg_set_id = swsh11
name = Lost Origin
series = Sword & Shield

Mapping:
id_expansion = 12345
pokemon_tcg_set_id = swsh11
match_status = matched
match_method = exact_name
match_confidence = 1.00
is_primary_mapping = true
needs_review = false
```

---

# Relationship diagram

```text
cardmarket_expansions
        |
        | id_expansion
        |
        v
expansion_set_mappings
        ^
        | pokemon_tcg_set_id
        |
pokemon_tcg_sets
```

Or as a logical model:

```text
Cardmarket Expansion  <-- mapping -->  Pokémon TCG Set
```

---

# Why not use one big table?

A single table would be easier at the beginning, but it would mix different concepts:

```text
Cardmarket expansion fields
+
Pokémon TCG official set fields
+
mapping quality fields
```

That would make the data harder to understand and maintain.

The three-table model is better because:

* each source keeps its own identity;
* source-specific fields remain clean;
* mapping decisions are auditable;
* uncertain matches can be reviewed;
* future data sources can be added more easily;
* BI queries can use only verified mappings.

This also demonstrates proper data engineering thinking: external systems should be joined through controlled mapping logic, not through blind name matching.

---

# Data flow

## Step 1: Load Cardmarket expansions

Input:

```text
data/reference/expansions.csv
```

Output table:

```text
cardmarket_expansions
```

Expected behavior:

* load all Cardmarket expansion rows;
* preserve `id_expansion`;
* keep inactive rows if they are historically relevant;
* do not delete old expansions only because they are no longer actively used;
* use `is_active` to control whether the row should be used in current workflows.

---

## Step 2: Load Pokémon TCG sets

Input:

```text
data/reference/pokemon_tcg/sets/en.json
```

Output table:

```text
pokemon_tcg_sets
```

Expected behavior:

* parse JSON;
* convert `releaseDate` from `YYYY/MM/DD` to `YYYY-MM-DD`;
* convert `updatedAt` to timestamp;
* flatten image URLs into `symbol_url` and `logo_url`;
* store `legalities` as raw JSON;
* calculate `secret_card_count`;
* store source metadata such as file name and commit hash.

---

## Step 3: Generate candidate mappings

Input tables:

```text
cardmarket_expansions
pokemon_tcg_sets
```

Output table:

```text
expansion_set_mappings
```

Candidate mapping logic may use:

* exact English name match;
* normalized English name match;
* slug similarity;
* series comparison;
* release date proximity;
* known Pokémon TCG code;
* manual correction rules.

---

## Step 4: Review uncertain mappings

Mappings with low confidence or unclear status should be marked as:

```text
manual_review
```

These rows should not be trusted blindly in BI views.

Recommended rule:

```text
Only mappings with match_status = 'matched'
and match_confidence >= 0.90
should be used in default analytics views.
```

---

# Normalization rules

Before comparing names, the pipeline may normalize strings.

Recommended normalization:

* convert to lowercase;
* trim whitespace;
* replace multiple spaces with one space;
* remove punctuation where safe;
* normalize ampersands;
* remove common prefixes such as `Sword & Shield -` only in matching logic, not in stored source data;
* keep the original source values unchanged.

Example:

```text
Sword & Shield - Lost Origin
lost origin
Lost-Origin
```

May all point to the same candidate, but the original values must remain unchanged in the source tables.

---

# Update strategy

## Cardmarket expansions

`expansions.csv` is maintained as a local reference file.

Updates may happen when:

* new Cardmarket expansions appear;
* German or English names are corrected;
* source URLs are added;
* release dates are verified;
* mapping notes are improved;
* inactive or special cases are identified.

Rows should not be physically deleted without a reason. Use:

```text
is_active = false
```

when an expansion should no longer be used by default.

---

## Pokémon TCG sets

`sets/en.json` should be imported from a pinned source version.

The source commit should be stored during import.

This makes the dataset reproducible. If the external source changes later, the project can still explain which version was used.

Recommended metadata fields:

```text
source_file
source_commit
created_at
updated_at
```

---

## Mapping table

The mapping table should be treated as curated data.

Automated matching can generate candidates, but manual review should be possible.

Manual decisions should be preserved in:

```text
notes
match_method = manual
match_confidence = 1.00
needs_review = false
```

---

# Recommended database constraints

## `cardmarket_expansions`

Recommended constraints:

```sql
PRIMARY KEY (id_expansion);
```

```sql
CHECK (is_active IN (true, false));
```

Optional:

```sql
UNIQUE (slug);
```

Only use a unique slug if the dataset proves that slugs are stable and unique.

---

## `pokemon_tcg_sets`

Recommended constraints:

```sql
PRIMARY KEY (pokemon_tcg_set_id);
```

```sql
CHECK (printed_total IS NULL OR printed_total >= 0);
```

```sql
CHECK (total_cards IS NULL OR total_cards >= 0);
```

```sql
CHECK (
  secret_card_count IS NULL
  OR secret_card_count >= 0
);
```

---

## `expansion_set_mappings`

Recommended constraints:

```sql
PRIMARY KEY (id_expansion, pokemon_tcg_set_id);
```

```sql
FOREIGN KEY (id_expansion)
REFERENCES cardmarket_expansions(id_expansion);
```

```sql
FOREIGN KEY (pokemon_tcg_set_id)
REFERENCES pokemon_tcg_sets(pokemon_tcg_set_id);
```

```sql
CHECK (
  match_status IN (
    'matched',
    'manual_review',
    'unmatched',
    'not_applicable'
  )
);
```

```sql
CHECK (
  match_method IN (
    'exact_name',
    'normalized_name',
    'slug',
    'code',
    'date_name_combo',
    'manual',
    'none'
  )
);
```

```sql
CHECK (
  match_confidence IS NULL
  OR (
    match_confidence >= 0.00
    AND match_confidence <= 1.00
  )
);
```

Recommended business rule:

```text
There should be only one primary mapping per Cardmarket expansion.
```

In PostgreSQL, this can be enforced with a partial unique index:

```sql
CREATE UNIQUE INDEX unique_primary_mapping_per_expansion
ON expansion_set_mappings (id_expansion)
WHERE is_primary_mapping = true;
```

---

# How this reference layer supports BI

Once the mapping is available, Cardmarket price data can be enriched with Pokémon TCG set metadata.

Example analytical joins:

```text
price_snapshots
  -> products
  -> cardmarket_expansions
  -> expansion_set_mappings
  -> pokemon_tcg_sets
```

This allows BI views to include:

* Cardmarket expansion name;
* Pokémon TCG official set name;
* series;
* release date;
* months since release;
* printed card count;
* total card count;
* secret card count;
* set logo;
* set symbol.

---

# Example BI fields

After joining the tables, the analytical model can expose fields such as:

| Field                  | Meaning                                       |
| ---------------------- | --------------------------------------------- |
| `id_expansion`         | Cardmarket expansion ID.                      |
| `expansion_name_en`    | Cardmarket English expansion name.            |
| `pokemon_tcg_set_id`   | Official Pokémon TCG set ID.                  |
| `official_set_name`    | Pokémon TCG set name.                         |
| `series`               | Official series / era.                        |
| `release_date`         | Official or preferred release date.           |
| `months_since_release` | Age of the set in months.                     |
| `printed_total`        | Number of printed cards in the main set.      |
| `total_cards`          | Total number of cards including secret cards. |
| `secret_card_count`    | Number of extra / secret cards.               |
| `mapping_confidence`   | Confidence level of the source mapping.       |

---

# Important design principle

This project should not pretend that data from different sources is automatically clean.

The reference layer exists because real-world data is messy:

* names differ;
* slugs differ;
* release dates may not always match;
* some Cardmarket expansions may not have a direct Pokémon TCG set equivalent;
* some mappings may require manual review.

The mapping table makes this uncertainty visible instead of hiding it.

That is the main reason for using three tables.

---

# Current recommended folder structure

```text
data/
└── reference/
    ├── README.md
    ├── expansions.csv
    ├── pokemon_tcg/
    │   └── sets/
    │       └── en.json
    └── mappings/
        └── expansion_set_mappings.csv
```

Recommended meaning:

| Path                                                 | Purpose                                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------- |
| `data/reference/README.md`                           | Documentation for the reference layer.                              |
| `data/reference/expansions.csv`                      | Local Cardmarket expansion reference file.                          |
| `data/reference/pokemon_tcg/sets/en.json`            | Raw Pokémon TCG set metadata.                                       |
| `data/reference/mappings/expansion_set_mappings.csv` | Curated mapping between Cardmarket expansions and Pokémon TCG sets. |

---

# Recommended implementation order

1. Keep `expansions.csv` as the source file for `cardmarket_expansions`.
2. Add the Pokémon TCG `sets/en.json` file under `data/reference/pokemon_tcg/sets/`.
3. Create a loader for `pokemon_tcg_sets`.
4. Create a first automatic mapping script.
5. Export uncertain mappings for manual review.
6. Save reviewed mappings into `expansion_set_mappings.csv`.
7. Load all three tables into the database.
8. Use only trusted mappings in default BI views.

---

# Summary

The reference layer uses three tables:

```text
cardmarket_expansions
pokemon_tcg_sets
expansion_set_mappings
```

This design keeps Cardmarket data, Pokémon TCG data, and mapping decisions separate.

That separation is important because it makes the project:

* easier to debug;
* easier to document;
* safer for analytics;
* better suited for future automation;
* more convincing as a data engineering portfolio project.

The key rule is:

```text
Cardmarket expansion ≠ Pokémon TCG set
```

They should be connected through a reviewed mapping layer, not merged blindly by name.
