# README / Documentation Structure

## Document Version

```text
Version: 0.5
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial README / documentation structure |
| 0.2 | 2026-07-04 | Fixed `01-final-mvp-scope.md` → `01-mvp-scope.md` everywhere, aligned the repository tree with `06-github-repository-structure.md` (single source of truth), synced the MVP analytics signal list with `09-analytics-signal-definitions.md` (removed `sealed_growth`, added `missing_price_data`), added a Known Limitations section referencing `03-data-dictionary.md`, referenced the falsifiable success criteria from `01-mvp-scope.md`, and added this version header, based on architecture review |
| 0.3 | 2026-07-04 | `06-github-repository-structure.md` added `LICENSE` (MIT) to its tree, so this document's tree now genuinely matches it — closing the drift that existed between the two trees in earlier drafts |
| 0.4 | 2026-07-05 | Added `11-local-environment-setup.md` to both repo-tree copies, both doc index tables, and the reading order — also caught and fixed both tree copies missing `db/backups/`, which `06` had already added but this document hadn't picked up (the exact kind of drift this doc's tree note warns against) |
| 0.5 | 2026-07-14 | Renamed field-name references from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `estimatedMarketValue` → `estimated_market_value`), matching the project-wide database naming decision in `02-data-model.md` v0.5 / `03-data-dictionary.md` v0.5. Only the small number of field mentions in the README draft's prose changed — no CSV/import column headers appear in this document, so nothing here intersects with the camelCase exception documented in `08-collection-import-flow.md`. |

## Purpose

This document defines the recommended documentation structure for the Pokémon Cardmarket BI project.

The goal is to make the GitHub repository easy to understand for:

```text
recruiters
data analysts
BI developers
data engineers
technical reviewers
future contributors
```

The documentation should show that this is not just a script project.

It is a small but realistic data engineering and BI portfolio project with:

```text
automated data collection
raw data archiving
normalized database design
collection import logic
valuation logic
analytics signals
clear MVP boundaries
future roadmap
```

---

## Documentation Strategy

The project should use a simple documentation structure:

```text
README.md
docs/
  01-mvp-scope.md
  02-data-model.md
  03-data-dictionary.md
  04-etl-pipeline-design.md
  05-raw-archive-strategy.md
  06-github-repository-structure.md
  07-github-actions-logic.md
  08-collection-import-flow.md
  09-analytics-signal-definitions.md
  10-readme-documentation-structure.md
  11-local-environment-setup.md
```

The `README.md` should be the entry point.

The `docs/` folder should contain deeper project documentation.

Each doc in `docs/` carries its own `Document Version` and `Changelog` header, this one included — so a reviewer can tell at a glance whether any given doc reflects the latest resolved decisions.

---

## Main README Role

The root `README.md` should answer the most important questions quickly:

```text
What is this project?
Why does it exist?
What problem does it solve?
What data does it use?
What does the MVP include?
How is the project structured?
Where can I read more?
```

The README should not contain every technical detail.

Instead, it should summarize the project and link to the detailed documentation files.

---

## Recommended Repository Structure

The repository tree below matches `06-github-repository-structure.md` exactly, which is the single source of truth for the repository layout. This document does not redefine it — repeating a slightly different tree here would create the same kind of drift the project has already had to resolve between other document pairs.

```text
pokemon-cardmarket-bi/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
│
├── docs/
│   ├── 01-mvp-scope.md
│   ├── 02-data-model.md
│   ├── 03-data-dictionary.md
│   ├── 04-etl-pipeline-design.md
│   ├── 05-raw-archive-strategy.md
│   ├── 06-github-repository-structure.md
│   ├── 07-github-actions-logic.md
│   ├── 08-collection-import-flow.md
│   ├── 09-analytics-signal-definitions.md
│   ├── 10-readme-documentation-structure.md
│   └── 11-local-environment-setup.md
│
├── data/
│   ├── sample/
│   └── import_templates/
│
├── db/
│   └── backups/
│
├── sql/
│   ├── schema/
│   ├── views/
│   └── checks/
│
├── src/
│   ├── config/
│   ├── ingestion/
│   ├── transform/
│   ├── load/
│   ├── collection/
│   ├── analytics/
│   └── utils/
│
├── tests/
│
└── .github/
    └── workflows/
```

An earlier draft of this document used a different tree (`scripts/` instead of `src/`, a `workflows/README.md`, no `tests/` or `.env.example`) that conflicted with doc 06. That version has been replaced with the one above.

---

## Important Note About Raw Data

The repository should not store full raw Cardmarket archive files if they become large or are downloaded automatically over time.

Instead, raw archive files should be stored externally, for example on the user's own server via FTP.

The repository can include small sample files only:

```text
data/sample/
```

Example:

```text
data/sample/price_guide_6_sample.json
data/sample/products_singles_6_sample.json
data/sample/products_nonsingles_6_sample.json
```

Collection import templates live separately, in `data/import_templates/` (see `06-github-repository-structure.md`):

```text
data/import_templates/collection_import_template.csv
```

The sample and template files should be small enough to be GitHub-friendly.

---

# README.md Recommended Structure

The root README should follow this structure:

```text
1. Project title
2. Short project description
3. Problem statement
4. MVP scope
5. Data sources
6. High-level architecture
7. Core database tables
8. Collection valuation logic
9. Analytics signals
10. Known limitations
11. Repository structure
12. Documentation index
13. Current status
14. Roadmap
15. What this project demonstrates
16. Disclaimer
```

This adds a dedicated "Known limitations" section (10) that did not exist in the earlier draft — see that section below for why it matters enough to earn its own place rather than being folded into the disclaimer.

---

# 1. Project Title

Recommended title:

```text
Pokémon Cardmarket BI Tracker
```

Alternative title:

```text
Pokémon Cardmarket Price & Collection Analytics
```

The title should be clear and searchable.

---

# 2. Short Project Description

Recommended README text:

```text
Pokémon Cardmarket BI Tracker is a learning-focused data engineering and BI portfolio project for tracking Pokémon product prices and personal collection value using official Cardmarket downloadable JSON files.

The project stores daily price snapshots, archives raw data, normalizes product and price information, supports personal collection imports, and defines BI-friendly analytics signals for market and collection analysis.
```

---

# 3. Problem Statement

Recommended README text:

```text
Pokémon collectors often want to understand how product prices change over time, but daily price guide files are only snapshots. Without saving these snapshots regularly, historical price data is lost.

This project solves that problem by building a simple data pipeline that downloads, archives, validates, and stores daily Cardmarket price guide data. It also connects that data to a personal collection table so collection value can be tracked over time.
```

---

# 4. MVP Scope

Recommended README text:

```text
The MVP focuses on building a realistic foundation:

- automated daily price guide collection
- twice-monthly product catalog collection
- raw JSON archiving
- normalized database tables
- personal collection import through CSV/Excel staging
- basic collection valuation
- simple analytics signals
- BI-ready views
- clear project documentation
```

Out of scope for the MVP:

```text
- full web application
- Selenium/browser scraping
- automatic seller price updates
- machine learning
- price prediction
- real-time alerts
- mobile app
```

---

# 5. Data Sources

Recommended README text:

```text
The project uses official downloadable Cardmarket JSON files for Pokémon:

- products_singles_6.json
- products_nonsingles_6.json
- price_guide_6.json
```

Main relationship key:

```text
id_product
```

Important source rule:

```text
The daily price guide is a snapshot, not a ready-made historical dataset. Historical price data is created by saving snapshots every day.
```

---

# 6. High-Level Architecture

Recommended README text:

```text
Cardmarket JSON files
→ scheduled download
→ raw archive
→ validation
→ normalization
→ database tables
→ BI views
→ collection valuation / analytics signals
```

Recommended simple diagram:

```text
                  ┌──────────────────────────┐
                  │ Cardmarket JSON downloads │
                  └─────────────┬────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ Raw archive               │
                  │ dated JSON snapshots      │
                  └─────────────┬────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ Validation & normalization│
                  └─────────────┬────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ Database tables           │
                  │ products, price snapshots │
                  └─────────────┬────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ BI views & analytics      │
                  └──────────────────────────┘
```

---

# 7. Core Database Tables

Recommended README text:

```text
Core MVP tables:

- products
- price_snapshots
- collection_items
- collection_import_staging

Supporting tables:

- watchlist
- analytics_signals
```

Short explanation:

```text
products stores the unified product catalog for singles and sealed products.

price_snapshots stores daily price guide snapshots.

collection_items stores every physical card or sealed product owned by the user.

collection_import_staging stores CSV/Excel import rows before they are validated and imported.

watchlist stores products the user wants to monitor.

analytics_signals stores calculated market and collection signals.
```

---

# 8. Collection Valuation Logic

Recommended README text:

```text
The MVP uses a simple estimated market value formula based on Cardmarket price guide fields:

estimated_market_value = (trend + avg30) / 2
```

Fallback logic:

```text
if trend exists and avg30 exists:
    use (trend + avg30) / 2

if trend exists and avg30 is missing:
    use trend

if trend is missing and avg30 exists:
    use avg30

if both are missing:
    value is null
```

Important limitation:

```text
Cardmarket price guide data does not provide precise valuation by the user's exact language and condition. German Near Mint cards are valued using aggregated Cardmarket price guide data.
```

---

# 9. Analytics Signals

Recommended README text:

```text
The project defines simple analytics signals that can be calculated from historical price snapshots.

MVP signals:

- growth
- price_spike
- new_product
- collection_gain
- collection_loss
- missing_price_data
```

An earlier draft of this section listed `sealed_growth` as an MVP signal. That was out of sync with `02-data-model.md`/`03-data-dictionary.md`/`09-analytics-signal-definitions.md`, all of which defer `sealed_growth` to a later phase until there is enough sealed-product price history to validate it against. `missing_price_data` was added to match the same three documents.

Important note:

```text
The MVP does not claim to predict the market. It focuses on explainable historical analytics and BI-friendly metrics.
```

---

# 10. Known Limitations

This section is new relative to the earlier draft of this document. The project has, over the course of its design docs, accumulated a real, specific list of honestly-stated limitations (see `03-data-dictionary.md`, "Known Data Limitations"). A portfolio README benefits far more from surfacing that list directly than from a single generic "interpret with caution" line — the specificity is what makes the honesty credible to a reviewer.

Recommended README text:

```text
This project is upfront about what it does not do:

- Price history only exists from the day the pipeline starts archiving
  snapshots; Cardmarket does not provide historical data retroactively.
- Missing days in the archive (due to an outage or failed run) are treated
  as permanent, accepted gaps, not backfilled.
- Prices are not broken down by exact language or condition; valuation uses
  aggregated Cardmarket price guide data.
- The `low` price field is intentionally not used for valuation because it
  can be noisy.
- Newly added products can have volatile early prices; growth and
  price-spike signals are suppressed or flagged as low-confidence for
  products less than 14 days old.
- No machine learning or price prediction is performed anywhere in the
  project.

See docs/03-data-dictionary.md for the complete, current list.
```

---

# 11. Repository Structure

Recommended README text:

```text
docs/ contains project documentation and design decisions.

data/sample/ contains small example files only.
data/import_templates/ contains templates for collection CSV/Excel import.

sql/schema/ contains database table definitions, applied manually in numeric order.

sql/views/ contains BI-friendly database views.

sql/checks/ contains data quality checks.

src/ contains ingestion, transformation, loading, collection import, and
analytics logic, organized by responsibility (see
docs/06-github-repository-structure.md for the full breakdown).

tests/ contains unit tests for parsing, matching, and calculation logic.

.github/workflows/ contains GitHub Actions workflow definitions.
```

---

# 12. Documentation Index

Recommended README section:

```text
## Documentation

| Document | Description |
|---|---|
| [01-mvp-scope.md](docs/01-mvp-scope.md) | Defines the MVP boundaries and project goals |
| [02-data-model.md](docs/02-data-model.md) | Explains the core tables and relationships |
| [03-data-dictionary.md](docs/03-data-dictionary.md) | Documents fields, meanings, and data rules |
| [04-etl-pipeline-design.md](docs/04-etl-pipeline-design.md) | Describes ingestion and transformation flows |
| [05-raw-archive-strategy.md](docs/05-raw-archive-strategy.md) | Explains raw JSON archive design |
| [06-github-repository-structure.md](docs/06-github-repository-structure.md) | Defines the repository layout |
| [07-github-actions-logic.md](docs/07-github-actions-logic.md) | Describes scheduled automation logic |
| [08-collection-import-flow.md](docs/08-collection-import-flow.md) | Explains CSV/Excel collection import through staging |
| [09-analytics-signal-definitions.md](docs/09-analytics-signal-definitions.md) | Defines BI and analytics signal logic |
| [10-readme-documentation-structure.md](docs/10-readme-documentation-structure.md) | Explains the documentation strategy (this document) |
| [11-local-environment-setup.md](docs/11-local-environment-setup.md) | Local-only folder structure, dev/prod env vars, first-time setup checklist |
```

The "(this document)" note on entry 10 is new — the earlier draft left a reviewer with no signal that doc 10 is the meta-document describing the documentation itself, rather than another pipeline-facing doc.

---

# 13. Current Status

Recommended README text:

```text
Project status: design and MVP planning phase.

Completed documentation:

- MVP scope
- data model
- data dictionary
- ETL / pipeline design
- raw archive strategy
- repository structure
- GitHub Actions logic concept
- collection import flow
- analytics signal definitions
- this documentation structure
```

When implementation starts, this section can be updated to:

```text
Project status: MVP implementation in progress.
```

Later:

```text
Project status: MVP implemented, BI views in progress.
```

Once implementation begins, status updates should reference the concrete, falsifiable success criteria defined in `01-mvp-scope.md` (for example: 30 consecutive archived days with no gap, zero duplicate `(snapshot_date, id_product)` pairs, at least one successful staging import) rather than only a qualitative phase label — this gives "MVP implemented" an actual, checkable meaning instead of being a subjective claim.

---

# 14. Roadmap

Recommended README text:

```text
## Roadmap

### MVP

- define documentation structure
- create database schema
- create sample data files
- implement daily price guide ingestion
- implement twice-monthly product catalog ingestion
- archive raw JSON files
- load normalized data into database
- create collection import staging flow
- create collection valuation views
- create basic analytics signal views

### Later Improvements

- better product matching (fuzzy matching)
- manual review UI for collection imports
- watchlist alerts
- price movement dashboards
- sealed vs single comparison (sealed_growth signal)
- CSV export
- backup and restore logic
- richer analytics after enough historical data exists

### Future Ideas

- lightweight web app
- mobile-friendly collection view
- premium analytics layer
- forecasting after sufficient historical data
```

---

# 15. What This Project Demonstrates

Recommended README text:

```text
This project demonstrates:

- data modeling
- raw data archiving
- ETL pipeline thinking
- scheduled automation with GitHub Actions
- normalized database design
- staging table pattern
- data quality awareness
- BI view design
- collection valuation logic
- analytics signal design
- clear MVP scoping
- technical documentation
```

This section is important because it helps reviewers understand the portfolio value of the project.

---

# 16. Disclaimer

Recommended README text:

```text
This project is for learning, portfolio, and personal collection analysis.

It is not financial advice, investment advice, or an official Cardmarket product.

All price analytics are based on available Cardmarket price guide data and should be interpreted with caution. See "Known Limitations" above for specifics.
```

---

# Root README Draft

Below is a compact draft version of the root `README.md`.

````markdown
# Pokémon Cardmarket BI Tracker

Pokémon Cardmarket BI Tracker is a learning-focused data engineering and BI portfolio project for tracking Pokémon product prices and personal collection value using official Cardmarket downloadable JSON files.

The project stores daily price snapshots, archives raw data, normalizes product and price information, supports personal collection imports, and defines BI-friendly analytics signals for market and collection analysis.

## Problem

Cardmarket price guide files are daily snapshots, not a ready-made historical dataset.

If these files are not saved regularly, historical price data is lost.

This project solves that problem by building a simple pipeline that downloads, archives, validates, and stores daily Cardmarket price data. It also connects that data to a personal collection table so collection value can be tracked over time.

## MVP Scope

The MVP includes:

- automated daily price guide collection
- twice-monthly product catalog collection
- raw JSON archiving
- normalized database tables
- personal collection import through CSV/Excel staging
- basic collection valuation
- simple analytics signals
- BI-ready views
- clear project documentation

Out of scope for the MVP:

- full web application
- Selenium/browser scraping
- automatic seller price updates
- machine learning
- price prediction
- real-time alerts
- mobile app

## Data Sources

The project uses official downloadable Cardmarket JSON files for Pokémon:

- `products_singles_6.json`
- `products_nonsingles_6.json`
- `price_guide_6.json`

Main relationship key:

```text
id_product
````

Important rule:

```text
The daily price guide is a snapshot. Historical data is created by saving snapshots every day.
```

## High-Level Architecture

```text
Cardmarket JSON files
→ scheduled download
→ raw archive
→ validation
→ normalization
→ database tables
→ BI views
→ collection valuation / analytics signals
```

## Core Tables

Core MVP tables:

* `products`
* `price_snapshots`
* `collection_items`
* `collection_import_staging`

Supporting tables:

* `watchlist`
* `analytics_signals`

## Collection Valuation

The MVP uses a simple estimated market value formula:

```text
estimated_market_value = (trend + avg30) / 2
```

Fallback logic:

```text
if trend exists and avg30 exists:
    use (trend + avg30) / 2

if trend exists and avg30 is missing:
    use trend

if trend is missing and avg30 exists:
    use avg30

if both are missing:
    value is null
```

## Analytics Signals

MVP analytics signals:

* `growth`
* `price_spike`
* `new_product`
* `collection_gain`
* `collection_loss`
* `missing_price_data`

The MVP does not claim to predict the Pokémon market.
It focuses on explainable historical analytics and BI-friendly metrics.

## Known Limitations

This project is upfront about what it does not do:

* Price history only exists from the day the pipeline starts archiving snapshots; Cardmarket does not provide historical data retroactively.
* Missing days in the archive are treated as permanent, accepted gaps, not backfilled.
* Prices are not broken down by exact language or condition.
* The `low` price field is intentionally not used for valuation.
* Newly added products can have volatile early prices; growth/price-spike signals are suppressed or flagged for products less than 14 days old.
* No machine learning or price prediction is performed anywhere in the project.

See [docs/03-data-dictionary.md](docs/03-data-dictionary.md) for the complete, current list.

## Repository Structure

```text
pokemon-cardmarket-bi/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
│
├── docs/
│   ├── 01-mvp-scope.md
│   ├── 02-data-model.md
│   ├── 03-data-dictionary.md
│   ├── 04-etl-pipeline-design.md
│   ├── 05-raw-archive-strategy.md
│   ├── 06-github-repository-structure.md
│   ├── 07-github-actions-logic.md
│   ├── 08-collection-import-flow.md
│   ├── 09-analytics-signal-definitions.md
│   ├── 10-readme-documentation-structure.md
│   └── 11-local-environment-setup.md
│
├── data/
│   ├── sample/
│   └── import_templates/
│
├── db/
│   └── backups/
│
├── sql/
│   ├── schema/
│   ├── views/
│   └── checks/
│
├── src/
│   ├── config/
│   ├── ingestion/
│   ├── transform/
│   ├── load/
│   ├── collection/
│   ├── analytics/
│   └── utils/
│
├── tests/
│
└── .github/
    └── workflows/
```

## Documentation

| Document                                                                          | Description                                          |
| --------------------------------------------------------------------------------- | ---------------------------------------------------- |
| [01-mvp-scope.md](docs/01-mvp-scope.md)                                           | Defines the MVP boundaries and project goals         |
| [02-data-model.md](docs/02-data-model.md)                                         | Explains the core tables and relationships           |
| [03-data-dictionary.md](docs/03-data-dictionary.md)                               | Documents fields, meanings, and data rules           |
| [04-etl-pipeline-design.md](docs/04-etl-pipeline-design.md)                       | Describes ingestion and transformation flows         |
| [05-raw-archive-strategy.md](docs/05-raw-archive-strategy.md)                     | Explains raw JSON archive design                     |
| [06-github-repository-structure.md](docs/06-github-repository-structure.md)       | Defines the repository layout                        |
| [07-github-actions-logic.md](docs/07-github-actions-logic.md)                     | Describes scheduled automation logic                 |
| [08-collection-import-flow.md](docs/08-collection-import-flow.md)                 | Explains CSV/Excel collection import through staging |
| [09-analytics-signal-definitions.md](docs/09-analytics-signal-definitions.md)     | Defines BI and analytics signal logic                |
| [10-readme-documentation-structure.md](docs/10-readme-documentation-structure.md) | Explains the documentation strategy (this document)  |
| [11-local-environment-setup.md](docs/11-local-environment-setup.md)              | Local-only folder structure, dev/prod env vars, first-time setup checklist |

## Current Status

Project status: design and MVP planning phase.

Completed documentation:

- MVP scope
- data model
- data dictionary
- ETL / pipeline design
- raw archive strategy
- repository structure
- GitHub Actions logic concept
- collection import flow
- analytics signal definitions
- this documentation structure

Once implementation begins, status updates will reference the concrete success criteria defined in [docs/01-mvp-scope.md](docs/01-mvp-scope.md) rather than a qualitative label alone.

## Roadmap

### MVP

- define documentation structure
- create database schema
- create sample data files
- implement daily price guide ingestion
- implement twice-monthly product catalog ingestion
- archive raw JSON files
- load normalized data into database
- create collection import staging flow
- create collection valuation views
- create basic analytics signal views

### Later Improvements

- better product matching (fuzzy matching)
- manual review UI for collection imports
- watchlist alerts
- price movement dashboards
- sealed vs single comparison (sealed_growth signal)
- CSV export
- backup and restore logic
- richer analytics after enough historical data exists

### Future Ideas

- lightweight web app
- mobile-friendly collection view
- premium analytics layer
- forecasting after sufficient historical data

## What This Project Demonstrates

This project demonstrates:

- data modeling
- raw data archiving
- ETL pipeline thinking
- scheduled automation with GitHub Actions
- normalized database design
- staging table pattern
- data quality awareness
- BI view design
- collection valuation logic
- analytics signal design
- clear MVP scoping
- technical documentation

## Disclaimer

This project is for learning, portfolio, and personal collection analysis.

It is not financial advice, investment advice, or an official Cardmarket product.

All price analytics are based on available Cardmarket price guide data and should be interpreted with caution. See "Known Limitations" above for specifics.
```

---

# Documentation Quality Rules

The documentation should follow these rules:

```text
Keep README short enough to read quickly.
Move technical details into docs/.
Use clear filenames with numbers.
Document decisions, not only structures.
Explain why decisions were made.
Separate MVP from later improvements.
Avoid pretending that the MVP is already a production system.
Avoid overclaiming analytics or prediction.
Keep examples small and realistic.
Keep repository structure, view definitions, and signal scope defined in
  exactly one document each (06, 03, and 02/03/09 respectively), and have
  every other document reference that source rather than repeating it.
```

The last rule is new relative to the earlier draft — it names, as an explicit documentation rule, the discipline that had to be applied after the fact multiple times across this doc set (repository structure, BI views, analytics signal scope) to fix drift between documents that had each defined the same thing slightly differently.

---

# Suggested Reading Order

A new reviewer should read the documentation in this order:

```text
README.md
01-mvp-scope.md
02-data-model.md
03-data-dictionary.md
04-etl-pipeline-design.md
05-raw-archive-strategy.md
06-github-repository-structure.md
07-github-actions-logic.md
08-collection-import-flow.md
09-analytics-signal-definitions.md
10-readme-documentation-structure.md (this document, describing the
  documentation set itself — read any time, doesn't depend on reading order)
11-local-environment-setup.md (read once you actually start setting up a
  machine to work on this — not needed to understand the design itself)
```

This reading order tells the story of the project:

```text
what the project is
what the MVP includes
how the data is modeled
how the data moves
how raw files are archived
how automation works
how personal collection data is imported
how analytics will be calculated
how the documentation itself is organized
how to actually set up a local machine to work on it
```

---

# Portfolio Presentation Advice

For portfolio use, the README should make the project look:

```text
realistic
structured
maintainable
well-scoped
honest about limitations
designed for BI and analytics
```

The strongest part of the project is not that it downloads JSON files.

The strongest part is that it shows the thinking behind a small real-world data product:

```text
source limitations
raw archive decisions
data modeling
staging tables
validation rules
price history creation
collection valuation
analytics signal design
documentation discipline
```

This is what makes the repository useful as a portfolio project.
