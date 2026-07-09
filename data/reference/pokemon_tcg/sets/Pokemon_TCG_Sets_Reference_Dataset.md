# Pokémon TCG Sets Reference Dataset

This folder contains the first version of the Pokémon TCG sets reference dataset for the `pokemon-cardmarket-bi` project.

The goal of this dataset is to provide a clean, stable, and beginner-friendly reference table of official Pokémon TCG sets before working with Cardmarket products, prices, and BI analytics.

## Purpose

The `pokemon_tcg_sets` dataset answers a simple question:

> Which official Pokémon TCG set are we talking about?

This dataset is used as a reference layer for Pokémon set metadata such as set name, series, release date, card counts, legalities, and image URLs.

At this stage, this dataset does **not** try to solve Cardmarket expansion mapping. Cardmarket-specific fields such as expansion IDs, German names, slugs, and Cardmarket URLs will be added later when the mapping logic is designed.

## Source

The first version of this dataset is based on the Pokémon TCG sets JSON file:

```text
data/reference/pokemon_tcg/sets/en.json
```

Original upstream source:

```text
https://github.com/PokemonTCG/pokemon-tcg-data/blob/0af6250a22495e4a3e9f60ff45fc3fedc2e0563d/sets/en.json
```

Example source object:

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

## Dataset Scope

This dataset stores official Pokémon TCG set metadata.

It includes:

* set identifier
* English set name
* English series name
* Pokémon TCG Online / Live code
* release date
* printed card count
* total card count
* calculated secret card count
* legality information
* symbol image URL
* logo image URL
* source update timestamp
* local metadata fields

It intentionally does **not** include Cardmarket mapping fields in version 1.

## Table Name

```text
pokemon_tcg_sets
```

## Primary Key

```text
pokemon_tcg_set_id
```

This field comes from the `id` field in the Pokémon TCG source JSON.

Examples:

```text
base1
swsh11
sv03
```

The Pokémon TCG set ID is used as the primary key because the first version of this table is based only on the Pokémon TCG source data.

## Field List

| Field                |      Type | Required | Description                                                        |
| -------------------- | --------: | -------: | ------------------------------------------------------------------ |
| `pokemon_tcg_set_id` |      text |      yes | Unique Pokémon TCG set identifier. Primary key. Example: `swsh11`. |
| `name_en`            |      text |      yes | English set name. Example: `Lost Origin`.                          |
| `series_en`          |      text | optional | English series name. Example: `Sword & Shield`.                    |
| `ptcgo_code`         |      text | optional | Pokémon TCG Online / Live code. Example: `LOR`.                    |
| `release_date`       |      date | optional | Set release date in ISO format: `YYYY-MM-DD`.                      |
| `printed_total`      |   integer | optional | Official printed card count, excluding secret cards.               |
| `total_cards`        |   integer | optional | Official total card count, including secret cards.                 |
| `secret_card_count`  |   integer | optional | Derived value: `total_cards - printed_total`.                      |
| `legalities`         |     jsonb | optional | Raw legality object from the source JSON.                          |
| `symbol_url`         |      text | optional | URL of the set symbol image.                                       |
| `logo_url`           |      text | optional | URL of the set logo image.                                         |
| `source_updated_at`  | timestamp | optional | Update timestamp from the source JSON.                             |
| `is_active`          |   boolean |      yes | Whether the set is active in the local reference dataset.          |
| `notes`              |      text | optional | Manual notes about the set or future mapping decisions.            |
| `created_at`         | timestamp |      yes | Row creation timestamp in the local database.                      |
| `updated_at`         | timestamp |      yes | Last row update timestamp in the local database.                   |

## Field Mapping from Source JSON

| Source JSON Field      | Local Table Field    |
| ---------------------- | -------------------- |
| `id`                   | `pokemon_tcg_set_id` |
| `name`                 | `name_en`            |
| `series`               | `series_en`          |
| `ptcgoCode`            | `ptcgo_code`         |
| `releaseDate`          | `release_date`       |
| `printedTotal`         | `printed_total`      |
| `total`                | `total_cards`        |
| `total - printedTotal` | `secret_card_count`  |
| `legalities`           | `legalities`         |
| `images.symbol`        | `symbol_url`         |
| `images.logo`          | `logo_url`           |
| `updatedAt`            | `source_updated_at`  |

## Data Transformation Rules

### Date Format

The source uses dates like:

```text
2022/09/09
```

The local dataset stores dates as:

```text
2022-09-09
```

### Timestamp Format

The source uses timestamps like:

```text
2022/09/09 13:45:00
```

The local dataset stores them as database timestamps.

### Secret Card Count

`secret_card_count` is calculated during the import process:

```text
secret_card_count = total_cards - printed_total
```

Example:

```text
217 - 196 = 21
```

If either value is missing, `secret_card_count` should be left empty.

### Legalities

The `legalities` object is stored as raw JSON.

Example:

```json
{
  "unlimited": "Legal",
  "standard": "Legal",
  "expanded": "Legal"
}
```

For version 1, this object is not split into separate columns.

## Version 1 Design Decision

Version 1 is intentionally simple.

The table only contains Pokémon TCG source fields and basic local metadata.

The following Cardmarket-related fields are intentionally excluded for now:

```text
id_expansion
name_de
slug
source_url_en
source_url_de
card_count
pokemon_tcg_match_status
pokemon_tcg_match_method
pokemon_tcg_match_confidence
pokemon_tcg_match_notes
```

These fields will be considered later when the project starts working on Cardmarket expansion mapping.

## Why Cardmarket Mapping Is Excluded for Now

Cardmarket and Pokémon TCG do not always use the same identifiers, naming conventions, grouping logic, or language variants.

Adding Cardmarket fields too early would make the first reference table harder to understand and maintain.

The current goal is to create a reliable base table first. Mapping to Cardmarket can be handled later through either:

* additional fields in this table, or
* a separate mapping table.

The decision will be made after inspecting Cardmarket expansion data.

## Recommended File Location

```text
data/reference/pokemon_tcg/sets/en.json
```

Recommended output CSV location:

```text
data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
```

Recommended schema location:

```text
database/schema/pokemon_tcg_sets.sql
```

Recommended import script location:

```text
scripts/reference/load_pokemon_tcg_sets.py
```

## Recommended Folder Structure

```text
pokemon-cardmarket-bi/
├── data/
│   └── reference/
│       └── pokemon_tcg/
│           └── sets/
│               ├── en.json
│               ├── pokemon_tcg_sets.csv
│               └── README.md
├── scripts/
│   └── reference/
│       └── load_pokemon_tcg_sets.py
└── database/
    └── schema/
        └── pokemon_tcg_sets.sql
```

## Future Improvements

Possible future improvements:

* add Cardmarket expansion identifiers
* add German set names
* add Cardmarket slugs
* add Cardmarket source URLs
* add manual review status
* add mapping confidence
* add mapping notes
* create a separate Cardmarket mapping table
* validate set names across multiple sources
* track source file version or source commit hash

These improvements are intentionally postponed until the base Pokémon TCG reference table is working.

## Summary

`pokemon_tcg_sets` is the first clean reference table in the `pokemon-cardmarket-bi` project.

It provides a stable list of official Pokémon TCG sets and prepares the project for later work with Cardmarket product data, price history, and BI analytics.

Version 1 focuses on simplicity, clarity, and reliable source-based metadata.
