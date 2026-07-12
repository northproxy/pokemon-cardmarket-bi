# Pokémon Cardmarket BI Tracker

The project stores daily price snapshots, archives raw data, normalizes product and price information, supports personal collection imports, and defines BI-friendly analytics signals for market and collection analysis.

## Problem

Cardmarket's price guide is a daily *snapshot*, not a historical dataset. If it isn't saved regularly, historical price data is permanently lost.

This project builds a pipeline that downloads, archives, validates, and stores daily Cardmarket price data, and connects it to a personal collection table so collection value can be tracked over time.

## Current Status

**Implemented:**
- Daily price guide download → local archive → FTP upload (`src/ingestion/`, scheduled via `.github/workflows/daily-price-guide.yml`)
- Full documented database design for the core MVP tables (`docs/02`, `docs/03`)
- A Pokémon TCG expansions/sets reference-data layer (`data/reference/`, `sql/schema/00_pokemon_tcg_sets.sql`, `01_expansions.sql`, `scripts/reference/`, `.github/workflows/expansions-reference-check.yml`) — see `docs/stages/` for its planning notes

**In progress / not yet reconciled with the core design docs:**
- A local SQLite database (`db/local/pokemon_cardmarket_bi.db`) exists alongside the documented Postgres/Supabase target (`docs/04`, `project.md` §2). Some SQL is duplicated in Postgres and SQLite-specific variants (`01_expansions_sqlite.sql`, `vw_products_enriched_sqlite.sql`). Whether SQLite is a local dev convenience or a platform pivot is an open question — not yet settled in the docs.
- Product catalog pipeline (`product-catalog.yml`) and full validate → transform → load stages (Phase 0b+) are not yet built.

See `project.md` for the consolidated design reference and `DECISIONS.md` for implementation-level decisions made along the way.

## MVP Scope

In scope:
- automated daily price guide collection
- twice-monthly product catalog collection
- raw JSON archiving
- normalized database tables
- personal collection import through CSV/Excel staging
- basic collection valuation
- simple analytics signals
- BI-ready views
- clear project documentation

Out of scope:
- full web application
- Selenium/browser scraping
- automatic seller price updates
- machine learning
- price prediction
- real-time alerts
- mobile app

## Data Sources

Official Cardmarket JSON files for Pokémon:
- `products_singles_6.json`
- `products_nonsingles_6.json`
- `price_guide_6.json`

Main relationship key: `idProduct`

A separate reference dataset — Pokémon TCG expansions/sets — is also maintained under `data/reference/` to enrich product records with expansion metadata (see `docs/future-cardmarket-expansions.md` and `docs/stages/`).

## High-Level Architecture

```text
Cardmarket JSON files
→ scheduled download
→ raw archive (local + FTP)
→ validation
→ normalization
→ database tables
→ BI views
→ collection valuation / analytics signals

Pokémon TCG sets (external reference)
→ load / validate
→ expansions reference table
→ enrichment of products (vw_products_enriched)
```

## Core Tables

Core MVP tables:
- `products`
- `price_snapshots`
- `collection_items`
- `collection_import_staging`

Supporting tables:
- `watchlist`
- `analytics_signals`

Reference tables (see `sql/schema/`):
- `pokemon_tcg_sets` / `expansions`

## Collection Valuation

```text
estimatedMarketValue = (trend + avg30) / 2
```

Fallback logic:
```text
if trend exists and avg30 exists: use (trend + avg30) / 2
if only trend exists: use trend
if only avg30 exists: use avg30
if both are missing: value is null
```

## Analytics Signals

MVP signals: `growth`, `price_spike`, `new_product`, `collection_gain`, `collection_loss`, `missing_price_data`.

The project does not claim to predict the Pokémon market — it focuses on explainable historical analytics and BI-friendly metrics.

## Known Limitations

- Price history only exists from the day the pipeline starts archiving; Cardmarket provides no historical backfill.
- Missing archive days are accepted gaps, not backfilled.
- Prices aren't broken down by exact language or condition.
- The `low` price field is intentionally excluded from valuation (noisy).
- Products under 14 days old have growth/price-spike signals suppressed.
- No machine learning or price prediction anywhere in the project.
- **Database platform is not fully settled** — Postgres/Supabase is the documented target, but a local SQLite database and SQLite-specific SQL also exist. See "Current Status" above.

Full details: `docs/03-data-dictionary.md`.

## Repository Structure

```text
pokemon-cardmarket-bi/
│   .env.example
│   .gitignore
│   DECISIONS.md
│   LICENSE
│   project.md
│   README.md
│   requirements.txt
│
├── .github/workflows/
│       daily-price-guide.yml
│       product-catalog.yml
│       expansions-reference-check.yml
│
├── data/
│   ├── exports/
│   ├── imports/collection/{incoming,processed,failed}
│   ├── import_templates/
│   ├── raw/cardmarket/pokemon/{price_guides,product_catalogs}/
│   ├── reference/
│   │   └── pokemon_tcg/sets/
│   └── sample/
│
├── db/
│   ├── backups/            (prod Supabase pg_dump backups)
│   └── local/               (local SQLite db — see Current Status)
│
├── docs/
│   │   01–11 numbered design docs
│   │   future-cardmarket-expansions.md
│   └── stages/               (staged implementation plans)
│
├── logs/{ingestion,validation,collection_import}/
├── scripts/reference/        (expansions/sets loading & validation scripts)
│
├── sql/
│   ├── checks/
│   ├── import/
│   ├── schema/
│   └── views/
│
├── src/
│   ├── analytics/
│   ├── collection/
│   ├── config/
│   ├── ingestion/
│   ├── load/
│   ├── transform/
│   └── utils/
│
└── tests/
```

## Documentation

| Document | Description |
|---|---|
| [01-mvp-scope.md](docs/01-mvp-scope.md) | MVP boundaries and project goals |
| [02-data-model.md](docs/02-data-model.md) | Core tables and relationships |
| [03-data-dictionary.md](docs/03-data-dictionary.md) | Field-level definitions and data rules |
| [04-etl-pipeline-design.md](docs/04-etl-pipeline-design.md) | Ingestion and transformation flows |
| [05-raw-archive-strategy.md](docs/05-raw-archive-strategy.md) | Raw JSON archive design |
| [06-github-repository-structure.md](docs/06-github-repository-structure.md) | Repository layout |
| [07-github-actions-logic.md](docs/07-github-actions-logic.md) | Scheduled automation logic |
| [08-collection-import-flow.md](docs/08-collection-import-flow.md) | CSV/Excel collection import via staging |
| [09-analytics-signal-definitions.md](docs/09-analytics-signal-definitions.md) | BI and analytics signal logic |
| [10-readme-documentation-structure.md](docs/10-readme-documentation-structure.md) | Documentation strategy |
| [11-local-environment-setup.md](docs/11-local-environment-setup.md) | Local-only folders, dev/prod env vars, setup checklist |
| [future-cardmarket-expansions.md](docs/future-cardmarket-expansions.md) | Expansions/reference-data planning |
| [stages/](docs/stages/) | Staged implementation plans for later phases |
| [project.md](project.md) | Single dense consolidated reference |
| [DECISIONS.md](DECISIONS.md) | Implementation-level decision log |

## Disclaimer

This project is for learning, portfolio, and personal collection analysis. It is not financial advice, investment advice, or an official Cardmarket product. All price analytics are based on available Cardmarket price guide data and should be interpreted with caution.
