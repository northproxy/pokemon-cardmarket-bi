# MVP Scope

## Document Version

```text
Version: 0.3
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-12
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial MVP scope |
| 0.2 | 2026-07-04 | Added idempotency, product lifecycle, matching strategy, retention policy, cadence justification, timezone rule, and falsifiable success criteria based on architecture review |
| 0.3 | 2026-07-12 | Changed product catalog cadence from twice-monthly (1st/15th) to weekly (every Friday), based on an implementation-time decision made during Stage 0 (see `DECISIONS.md` §11 in the code repository). This is a genuine change to the original design decision below, not a correction of an error — the original twice-monthly reasoning was sound for its own goals, but weekly was chosen once the pipeline was actually being built. Updated the "known limitation" staleness window from ~2 weeks to ~1 week accordingly. |

## Purpose

This project is a learning-focused data engineering and BI project for Pokémon product price analysis using official Cardmarket downloadable JSON files.

The goal of the MVP is to prove that the project can reliably collect official Cardmarket Pokémon product and price data, archive the raw files, store historical daily price snapshots, connect the data to a personal collection, and produce simple BI-ready outputs.

The MVP is not intended to be a full application, marketplace automation tool, machine learning system, or seller pricing bot.

## Core MVP Statement

The MVP is:

```text
automated daily price data collection
+ weekly (Friday) product catalog collection
+ raw JSON archive
+ normalized database tables
+ historical price snapshots
+ personal collection import
+ basic valuation logic
+ BI-ready views
+ clear documentation
```

## Trusted Data Sources

The project uses official Cardmarket downloadable JSON files for Pokémon:

```text
products_singles_6.json
products_nonsingles_6.json
price_guide_6.json
```

The main relationship key across files is:

```text
idProduct
```

## In Scope

### Official Cardmarket JSON Files

The MVP uses official downloadable Cardmarket files as the main data source.

The project intentionally avoids Selenium, browser scraping, login automation, and seller account automation as the primary data source.

### Raw File Archive

Raw JSON files are archived before transformation.

The archive preserves the original downloaded files unchanged so that historical files can be audited and reprocessed later if the transformation logic changes.

**Immutability rule:**

```text
Raw archive files are not silently overwritten.
If a same-date pipeline run is repeated, the rerun is saved as a suffixed copy
(e.g. price_guide_6_2026-07-03_rerun-01.json) instead of replacing the original file.
The database always loads from the canonical file for that date, defined as the
most recent successful run for that date (base file, or latest rerun if one exists).
```

**Reprocessing (later capability, enabled by design now):**

```text
Raw archive files make it possible to reprocess history later if transformation
logic changes. Full reprocessing automation is not built in the MVP, but the
raw archive is structured so a future reprocess step can read an archived file,
re-run current transformation logic, and upsert the result without needing to
re-download anything.
```

### Unified Product Catalog

The MVP combines singles and non-singles into one unified `products` table.

Input files:

```text
products_singles_6.json
products_nonsingles_6.json
```

Each product receives a derived `productGroup` value:

```text
single
non_single
```

This allows cards and sealed products to be analyzed together or separately.

**Product lifecycle rule:**

```text
A product is marked isActiveInCatalog = false the first time it is missing from
a freshly downloaded catalog file (no grace period / no N-miss tolerance in MVP).
Products are never deleted for being inactive.
Historical price_snapshots and collection_items referencing an inactive product
remain valid and are kept in BI views. "Inactive" means the product was not
present in the latest catalog snapshot — it does not mean its price history
is invalid.
```

### Catalog Collection Cadence

The product catalog is downloaded weekly, every Friday, while the price guide is downloaded daily.

**Changed from the original twice-monthly (1st/15th) decision** during
implementation — see `DECISIONS.md` §11 in the code repository for the
full record. Nothing about correctness depends on this change; weekly is
strictly more conservative (fresher catalog data) than twice-monthly, just
more frequent.

**Why this cadence:**

```text
Product metadata (name, category, expansion) changes far less often than price
data, so daily catalog downloads are still unnecessary. Weekly was chosen
over twice-monthly once the pipeline was actually being built, trading a
small amount of extra storage/processing for meaningfully fresher product
metadata. This cadence is a project decision, not a Cardmarket-imposed
schedule, and can be adjusted again later if needed.
```

**Known limitation this creates:**

```text
Because the catalog refreshes less often than the price guide, a newly
released product can appear in the daily price guide before it exists in the
local products table. This is expected and tolerated, not treated as a fatal
error:
  - the price row is still stored in price_snapshots
  - the missing product match is reported as a data quality warning
  - the next scheduled (weekly, Friday) or manually triggered catalog run
    resolves it — worst case, about a week of staleness, down from roughly
    two weeks under the original twice-monthly schedule
```

### Raw File Retention

```text
No deletion or retention limit is applied during the MVP. Raw daily snapshots
and catalog files are kept indefinitely while storage volume remains
manageable. This is a conscious decision, not an oversight, and will be
revisited once real file sizes and growth are observed.

The full raw archive is not committed to Git. It lives on the archive storage
location (e.g. FTP/object storage). Small representative sample files may be
committed for documentation and testing purposes.
```

### Historical Price Snapshots

The MVP stores the full daily `price_guide_6.json`, not only a watchlist or collection subset.

Historical price data is created by saving each daily snapshot over time.

Important limitation:

```text
Cardmarket provides a daily snapshot, not a ready-made full historical dataset.
```

**Snapshot date and timezone rule:**

```text
snapshotDate = the pipeline run date in the Europe/Vienna timezone.
This applies to every daily run, including manual reruns and backfills — there
is no separate rule for exceptional cases. The same date is used in the raw
archive filename and in price_snapshots.snapshotDate, so the two stay easy to
cross-reference.
```

**Idempotency / rerun rule:**

```text
(snapshotDate, idProduct) is a unique constraint on price_snapshots.
Loading is an upsert by (snapshotDate, idProduct): if the same date is
reprocessed (e.g. after a manual rerun or a corrected raw file), new values
overwrite the existing row for that date rather than creating a duplicate or
failing. Running the same daily pipeline twice for the same date must never
create duplicate rows or break the database.
```

**Gaps in the archive timeline:**

```text
If a day is missed (outage, failed run, etc.), the gap is treated as a known
and accepted data quality limitation, not something the pipeline attempts to
backfill automatically. The MVP does not assume a missed Cardmarket snapshot
can be recovered after the fact. Missing dates are visible through archive
completeness checks and documented as a limitation of daily-snapshot-based
historical data.
```

**Trusting new product prices:**

```text
Newly added products can have sparse or volatile early price data. The MVP
does not exclude them from valuation, but analytics signals (growth, spikes)
treat a product as "new / less reliable" for the first 14 days after its
firstSeenAt date. This is a simple data-quality flag, not a prediction or
statistical model.
```

### Personal Collection Tracking

The MVP stores every physical card or sealed product as a separate collection item.

This means the project does not use only:

```text
idProduct + quantity
```

Instead, one row represents one physical item.

This supports differences in:

```text
language
condition
purchase price
purchase date
storage location
sale status
grading later
personal notes
```

### Collection Import Through Staging

The MVP supports CSV/Excel collection import through a staging table.

Collection rows are first loaded into:

```text
collection_import_staging
```

Then validated, matched, reviewed if needed, and imported into:

```text
collection_items
```

This prevents bad import rows from polluting the clean collection table.

**Matching strategy (basic, non-fuzzy):**

```text
Staging rows are matched to products in this order of preference:
  1. exact idProduct match, if the import provided one (highest confidence)
  2. exact product name match against the products table
  3. anything else (no confident match) is routed to needs_review for manual
     confirmation

Advanced fuzzy matching is explicitly out of scope for the MVP. Ambiguous or
low-confidence matches are surfaced for a human to resolve, not guessed at
automatically.
```

**Handling a match to a product that doesn't exist yet:**

```text
If a staging row resolves to an idProduct that is not yet present in the local
products table (new product, catalog not yet refreshed), the row is not
imported into collection_items. It is marked matchStatus = waiting_for_product
and is retried automatically after the next successful product catalog run.
This is treated as an expected timing delay, not an error.
```

**Duplicate import protection:**

```text
If an import row includes an externalId, it is used to prevent importing the
same source row more than once. If no externalId is provided, the pipeline
does not automatically deduplicate — since identical physical cards are a
legitimate case of multiple valid rows — but a row matching an existing
collection item on idProduct + language + condition + purchaseDate +
purchasePrice is surfaced as a possible-duplicate warning for manual review,
not blocked automatically.
```

**Review is iterative, not a dead end:**

```text
A staging row marked needs_review is not terminal. Once corrected (e.g. a
better product name or idProduct is supplied), it is re-validated and
re-matched, and can move to ready_to_import, waiting_for_product, or error
depending on the outcome.
```

### Estimated Collection Value

The MVP uses a simple, explainable valuation formula:

```text
estimatedMarketValue = (trend + avg30) / 2
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

The MVP does not use `low` as the main collection valuation field because it can be noisy.

### Basic BI Outputs

The MVP should support basic analytical outputs such as:

```text
current collection value
collection value by productGroup
collection value by expansion
collection value by category
unrealized gain/loss where purchasePrice exists
daily price history per product
top movers by trend vs avg30
new products detected in catalog
missing price data report
```

These can be implemented as SQL views, CSV exports, or simple dashboard-ready queries later.

Full field-level definitions for these outputs live in the data dictionary, which is the single source of truth for view definitions; this document only lists intent.

## Core MVP Tables

The required core tables are:

```text
products
price_snapshots
collection_items
collection_import_staging
```

Supporting tables that may exist in a light form:

```text
watchlist
analytics_signals
```

## MVP Table Summary

### `products`

Stores the unified Cardmarket Pokémon product catalog.

Includes both singles and sealed/non-single products.

Important fields:

```text
idProduct
name
idCategory
categoryName
idExpansion
idMetacard
dateAdded
productGroup
sourceFile
isActiveInCatalog
```

### `price_snapshots`

Stores full daily price guide snapshots.

Important fields:

```text
snapshotDate
sourceCreatedAt
idProduct
idCategory
avg
low
trend
avg1
avg7
avg30
avg_holo
low_holo
trend_holo
avg1_holo
avg7_holo
avg30_holo
```

Hyphenated Cardmarket fields are normalized:

```text
avg-holo      -> avg_holo
low-holo      -> low_holo
trend-holo    -> trend_holo
avg1-holo     -> avg1_holo
avg7-holo     -> avg7_holo
avg30-holo    -> avg30_holo
```

### `collection_items`

Stores the personal Pokémon collection.

One row equals one physical item.

Default values:

```text
language = DE
condition = Near Mint
acquisitionType = pulled
isGraded = false
isSold = false
```

### `collection_import_staging`

Stores imported CSV/Excel rows before they become collection items.

Possible statuses:

```text
ready_to_import
needs_review
waiting_for_product
error
imported
```

## Out of Scope for MVP

The following are intentionally excluded from the MVP:

```text
machine learning
price prediction
automatic buy/sell recommendations
browser scraping
Selenium
Cardmarket login automation
seller price updates
real-time alerts
mobile app
full web app
complex dashboards
user accounts
multi-user support
advanced fuzzy matching
graded card valuation
language-specific valuation
condition-specific valuation
automatic image recognition
premium subscription logic
```

These ideas may be considered later after the core data pipeline and historical dataset are stable.

## MVP Success Criteria

The MVP is successful when the following, concrete, checkable conditions are met:

```text
The daily price guide archive contains 30 consecutive days without a missing
file.

price_snapshots contains exactly one snapshotDate row set per archived price
guide date, with zero duplicate (snapshotDate, idProduct) pairs.

Singles and sealed products are unified into one product catalog with zero
duplicate idProduct values.

At least one real CSV/Excel collection file has been imported successfully
through collection_import_staging into collection_items.

vw_collection_current_value returns a non-null estimatedMarketValue for every
collection item whose matched product has available trend or avg30 price
data.

Known data limitations (daily-snapshot-only history, no language/condition-
specific pricing, low-field noise, new-product volatility, un-backfillable
archive gaps) are documented in the project's README and data dictionary, not
just implied.

The documentation set (scope, data model, data dictionary, ETL design, archive
strategy) matches the actually implemented MVP schema and pipeline behavior.
```

A reviewer should be able to understand:

```text
what data comes in
where it is stored
how it is transformed
how history is created
how collection value is calculated
what is MVP
what belongs later
```

## Final MVP Boundary

```text
MVP = official source files + raw archive + normalized database + historical snapshots + collection import + basic valuation + BI-ready documentation
```
