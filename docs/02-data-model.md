# Data Model

## Document Version

```text
Version: 0.5
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial MVP data model |
| 0.2 | 2026-07-04 | Resolved `grade` type, `id_category` duplication, `updated_at` triggers, watchlist uniqueness, inactive-product price retention, `waiting_for_product` staging status, gain/loss percent formula, and index guidance based on architecture review |
| 0.3 | 2026-07-04 | Extended `analytics_signals` schema with `signal_strength`, `lookback_days`, `reference_value`, `current_value`; keyed collection-level signals on `collection_item_id`; deferred `sealed_growth` to Later Signal Types, based on architecture review of `09-analytics-signal-definitions.md` |
| 0.4 | 2026-07-04 | Added missing `storage_location`/`personal_note` fields to `collection_import_staging` (previously documented as import columns in `08-collection-import-flow.md` but absent from this table's schema); clarified `source_created_at` as an alias for download time in the MVP; confirmed Postgres/Supabase as the target database, so the partial unique index on `watchlist` is a firm MVP requirement rather than a conditional fallback |
| 0.5 | 2026-07-14 | Renamed every field in every table from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `isActiveInCatalog` → `is_active_in_catalog`), matching Postgres's native lowercase-folding behavior and avoiding a project-wide need to quote every identifier. This was a genuine decision, made explicitly rather than discovered as a doc/reality mismatch — at the time of this rewrite, the real `sql/schema/001`–`006` files were still unbuilt placeholders, so this rewrite defines the convention the first real implementation should follow, rather than correcting a live table. CSV/Excel import column headers (`08-collection-import-flow.md`) are explicitly **not** part of this rename — see that document's own naming note. |

## Naming Convention

All table and column names in this document are `snake_case` (see
`03-data-dictionary.md`'s Naming Conventions section for the full
reasoning). Where a field name is discussed only as a future/deferred
possibility (e.g. `grading_scale`/`grade_numeric`/`grade_label` under
`collection_items`), the same convention applies so nothing needs
renaming again if it's built later.

## Overview

The data model is centered around the official Cardmarket product identifier:

```text
id_product
```

This key connects the product catalog, daily price guide snapshots, personal collection items, watchlist entries, and analytical outputs.

High-level flow:

```text
official Cardmarket product catalogs
        ↓
products

official daily price guide
        ↓
price_snapshots

personal collection import
        ↓
collection_import_staging
        ↓
collection_items

optional personal tracking
        ↓
watchlist

derived analytics
        ↓
analytics_signals / BI views
```

## Core MVP Tables

The required MVP tables are:

```text
products
price_snapshots
collection_items
collection_import_staging
```

Supporting or later-MVP tables:

```text
watchlist
analytics_signals
```

## Relationship Overview

```text
products 1 ──── * price_snapshots
products 1 ──── * collection_items
products 1 ──── * collection_import_staging
products 1 ──── * watchlist
products 1 ──── * analytics_signals
```

`products` is the central table.

All major analytical and collection-related tables connect through `id_product`.

## Indexing Guidance

Standard indexes are added on every foreign-key-like column, not only where explicitly called out per table below:

```text
price_snapshots.id_product
collection_items.id_product
collection_import_staging.matched_id_product
watchlist.id_product
analytics_signals.id_product
analytics_signals.collection_item_id
```

This is a conscious MVP baseline rather than an afterthought — these columns are joined or filtered on in nearly every BI view.

---

# Table: `products`

## Purpose

Stores the unified Cardmarket Pokémon product catalog.

This table contains both:

```text
single cards
sealed / non-single products
```

One row represents one Cardmarket product.

## Recommended Fields

```text
id_product
name
id_category
category_name
id_expansion
id_metacard
date_added
product_group
source_file
is_active_in_catalog
first_seen_at
last_seen_at
updated_at
```

## Suggested Schema

```text
products

id_product              integer / bigint, primary key
name                   text, not null
id_category             integer / bigint, nullable
category_name           text, nullable
id_expansion            integer / bigint, nullable
id_metacard             integer / bigint, nullable
date_added              date or timestamp, nullable
product_group           text, not null
source_file             text, not null
is_active_in_catalog      boolean, not null, default true
first_seen_at            timestamp, not null
last_seen_at             timestamp, not null
updated_at              timestamp, not null
```

## Primary Key

```text
id_product
```

## Allowed Values

### `product_group`

```text
single
non_single
```

### `source_file`

```text
products_singles_6.json
products_nonsingles_6.json
```

## `updated_at` Trigger Rule

```text
updated_at changes whenever any stored field on the product row changes,
including last_seen_at.

This means updated_at will change on effectively every successful catalog run
that sees the product again, not only when a business field (name, category,
etc.) changes. For the MVP this is accepted for simplicity:

  last_seen_at = when the product was last seen in a downloaded source catalog
  updated_at  = when the product row was last modified in the local database

updated_at should not be used to mean "a business field changed" — it means
"the pipeline touched this row." A separate catalog_data_changed_at field can be
added later if that distinction becomes useful.
```

## Product Lifecycle Rule

```text
A product is marked is_active_in_catalog = false the first time it is missing
from a freshly downloaded catalog file. There is no grace period or N-miss
tolerance in the MVP.

Products are never deleted for being inactive. Historical price_snapshots and
collection_items referencing an inactive product remain valid and continue to
appear in BI views. "Inactive" means the product was absent from the latest
catalog snapshot — it does not mean its price history is invalid or should be
hidden.
```

## Business Rules

```text
id_product must be unique.
Products from singles must get product_group = single.
Products from non-singles must get product_group = non_single.
Products should not be deleted only because they disappear from the latest catalog.
If a product disappears from the latest catalog, set is_active_in_catalog = false.
```

---

# Table: `price_snapshots`

## Purpose

Stores the full daily Cardmarket price guide.

One row represents price data for one product on one snapshot date.

This table creates historical price data over time.

## Recommended Fields

```text
snapshot_date
source_created_at
id_product
id_category
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
created_at
```

## Suggested Schema

```text
price_snapshots

snapshot_date          date, not null
source_created_at       timestamp, nullable  -- alias for download time (MVP)
id_product             integer / bigint, not null
id_category            integer / bigint, nullable
avg                   decimal, nullable
low                   decimal, nullable
trend                 decimal, nullable
avg1                  decimal, nullable
avg7                  decimal, nullable
avg30                 decimal, nullable
avg_holo              decimal, nullable
low_holo              decimal, nullable
trend_holo            decimal, nullable
avg1_holo             decimal, nullable
avg7_holo             decimal, nullable
avg30_holo            decimal, nullable
created_at             timestamp, not null
```

## Primary Key

Recommended composite key:

```text
(snapshot_date, id_product)
```

The same product appears in many daily snapshots, so `id_product` alone is not unique in this table.

## Relationship to `products`

For MVP, the relationship can be logical rather than enforced with a strict foreign key.

Recommended MVP approach:

```text
products.id_product is primary key
price_snapshots.id_product is indexed
missing product matches are reported through data quality checks
```

Reason:

Product catalogs are downloaded twice per month, while the price guide is downloaded daily. A price guide may temporarily contain a new `id_product` before the local product catalog is refreshed.

## `id_category` Duplication — Why It Exists in Both Tables

```text
products.id_category       = catalog category, as of the last catalog refresh
price_snapshots.id_category = category as reported in that specific daily price
                              guide snapshot (source-observed, point-in-time)

This is intentional duplication, not redundant normalization debt. It exists
because the price guide reports its own category value independently of the
product catalog, and the two can drift (e.g. a temporary miscategorization, or
a category change that hasn't reached the catalog file yet).

Reconciliation rule (data quality warning, not a failure):
  For a given id_product, if price_snapshots.id_category differs from
  products.id_category, the row is reported by a data quality check
  (check_category_mismatch). This surfaces drift for review; it does not
  block loading and does not overwrite either value.
```

## Load / Rerun Behavior

```text
Loading is an upsert by (snapshot_date, id_product).

If the same date is reprocessed — for example after a manual rerun, or
because a corrected raw file was archived — the new values overwrite the
existing row for that date rather than creating a duplicate row or failing
with a primary key violation. Running the same daily pipeline twice for the
same date must never create duplicate data or leave the table in a
half-loaded state.
```

## Field Normalization

Cardmarket source fields with hyphens are normalized to snake_case:

```text
avg-holo      -> avg_holo
low-holo      -> low_holo
trend-holo    -> trend_holo
avg1-holo     -> avg1_holo
avg7-holo     -> avg7_holo
avg30-holo    -> avg30_holo
```

## Business Rules

```text
One product can have only one price row per snapshot_date.
The full price guide should be stored every day.
Historical data starts from the first successful saved snapshot.
Price fields may be null.
low should not be used as the main collection valuation field.
Price snapshots for products that later become is_active_in_catalog = false are
kept and remain valid historical observations; they are not deleted or
excluded from historical BI views.
```

---

# Table: `collection_items`

## Purpose

Stores the user's personal Pokémon collection.

One row represents one physical item.

This can be:

```text
one individual card
one sealed product
one graded card later
one sold item kept for history
```

The table intentionally does not use a simple `quantity` field because physical items can differ by condition, language, purchase price, purchase date, storage location, grading, and sale status.

## Recommended Fields

```text
collection_item_id
id_product
language
condition
acquisition_type
purchase_price
purchase_date
is_sealed
is_graded
grading_company
grade
storage_location
personal_note
is_sold
sold_price
sold_date
created_at
updated_at
```

## Suggested Schema

```text
collection_items

collection_item_id       uuid or integer, primary key
id_product              integer / bigint, not null
language               text, not null, default 'DE'
condition              text, not null, default 'Near Mint'
acquisition_type        text, not null, default 'pulled'
purchase_price          decimal, nullable
purchase_date           date, nullable
is_sealed               boolean, not null, default false
is_graded               boolean, not null, default false
grading_company         text, nullable
grade                  text, nullable
storage_location        text, nullable
personal_note           text, nullable
is_sold                 boolean, not null, default false
sold_price              decimal, nullable
sold_date               date, nullable
created_at              timestamp, not null
updated_at              timestamp, not null
```

## `grade` Type Decision

```text
grade is text, nullable. grading_company is text, nullable.

Grading is not a single numeric scale across companies (e.g. "PSA 10",
"BGS 9.5", "CGC Pristine 10", "SGC 9"). Forcing a decimal now would either
lose information or require guessing a normalization scheme before the
project has any real graded items to validate it against.

grade stores the label exactly as entered or imported — for example "10",
"9.5", "Pristine 10", or "Gem Mint 10". The MVP does not normalize grading
scales, since grading is not part of the first collection workflow.

Later improvement (not built in MVP):
  grading_scale   e.g. PSA_STANDARD
  grade_numeric   e.g. 10
  grade_label     e.g. "GEM MINT"
```

## Primary Key

```text
collection_item_id
```

UUID is recommended for future app compatibility, but integer autoincrement is also acceptable for MVP.

## Relationship to `products`

```text
collection_items.id_product → products.id_product
```

## `updated_at` Trigger Rule

```text
updated_at changes whenever any user-facing or lifecycle field changes:

language, condition, acquisition_type, purchase_price, purchase_date, is_sealed,
is_graded, grading_company, grade, storage_location, personal_note, is_sold,
sold_price, sold_date

For example, correcting a condition value or marking an item as sold both
update updated_at. Unlike products.updated_at, this field only reflects
meaningful data changes, since collection_items is not touched by an
unrelated recurring pipeline the way products is.
```

## Default Values

```text
language = DE
condition = Near Mint
acquisition_type = pulled
is_graded = false
is_sold = false
```

## Recommended `acquisition_type` Values

```text
pulled
bought_single
bought_sealed
trade
gift
unknown
```

## Recommended `condition` Values

```text
Mint
Near Mint
Excellent
Good
Light Played
Played
Poor
Unknown
```

## Business Rules

```text
One row equals one physical item.
Multiple copies of the same card should be stored as multiple rows.
Sold items should not be deleted.
Sold items should be kept with is_sold = true.
If is_graded = false, grading_company and grade should be null.
If is_sold = false, sold_price and sold_date should usually be null.
If purchase_price is null, gain/loss cannot be calculated.
```

---

# Table: `collection_import_staging`

## Purpose

Stores raw imported collection rows before they become real collection items.

This table protects `collection_items` from invalid or unclear import rows.

Rows can be:

```text
valid
incomplete
matched automatically
unclear
invalid
already imported
waiting on a product that doesn't exist locally yet
```

## Recommended Fields

```text
import_row_id
import_batch_id
external_id
provided_id_product
raw_product_name
matched_id_product
language
condition
acquisition_type
purchase_price
purchase_date
is_sealed
storage_location
personal_note
match_status
match_confidence
error_message
created_at
imported_at
```

## Suggested Schema

```text
collection_import_staging

import_row_id            uuid or integer, primary key
import_batch_id          uuid or text, not null
external_id             text, nullable
provided_id_product      integer / bigint, nullable
raw_product_name         text, nullable
matched_id_product       integer / bigint, nullable
language               text, default 'DE'
condition              text, default 'Near Mint'
acquisition_type        text, default 'pulled'
purchase_price          decimal, nullable
purchase_date           date, nullable
is_sealed               boolean, nullable
storage_location        text, nullable
personal_note           text, nullable
match_status            text, not null
match_confidence        decimal, nullable
error_message           text, nullable
created_at              timestamp, not null
imported_at             timestamp, nullable
```

**`storage_location` and `personal_note` were added in v0.4.** These are part of the recommended MVP import columns (see `08-collection-import-flow.md`) and are mapped directly into `collection_items` on import, but were missing from this table's schema in earlier drafts — a gap, not an intentional omission, since the mapping table in doc 08 already assumed they existed here.

## Primary Key

```text
import_row_id
```

## Relationship to `products`

```text
collection_import_staging.matched_id_product → products.id_product
```

`provided_id_product` should not be a strict foreign key in staging because staging must be able to store bad input.

## Matching Strategy (Basic, Non-Fuzzy)

```text
Staging rows are matched to products in this order of preference:
  1. exact id_product match, if the import provided one (highest confidence)
  2. exact product name match against the products table
  3. no confident match — routed to needs_review for manual confirmation

Advanced fuzzy matching is explicitly out of scope for the MVP. Ambiguous or
low-confidence matches are surfaced for a human to resolve, not guessed at
automatically.
```

## Handling a Match to a Product That Doesn't Exist Yet

```text
If matched_id_product resolves to an id_product that is not yet present in the
local products table (new product, catalog not yet refreshed), the row is
NOT imported into collection_items. It is set to match_status =
waiting_for_product instead of needs_review or error, since this is a timing
delay, not a data problem.

waiting_for_product rows are automatically re-checked after the next
successful product catalog pipeline run and move to ready_to_import (or
needs_review / error, if something else is also wrong) at that point.
```

## `match_status` Values

```text
ready_to_import
needs_review
waiting_for_product
error
imported
```

## Review Is Iterative, Not Terminal

```text
A row marked needs_review is not a dead end. Once corrected (e.g. a better
product name or id_product is supplied by manual review), the row is
re-validated and re-matched, and can move to ready_to_import,
waiting_for_product, or error depending on the outcome. The same applies to
error rows once the underlying issue is fixed.
```

## `match_confidence` Meaning

```text
1.00 = exact id_product match
0.90 = exact product name match
0.70 = strong fuzzy name match (not used while fuzzy matching is out of scope)
0.40 = weak possible match (not used while fuzzy matching is out of scope)
0.00 = no useful match
null = matching was not attempted
```

## Duplicate Import Protection

```text
If external_id is provided on an import row, it is used to prevent importing
the same source row more than once within the same source.

If external_id is not provided, the pipeline does NOT automatically
deduplicate — multiple identical physical cards are a legitimate case of
multiple valid rows. Instead, a row matching an existing collection_items row
on id_product + language + condition + purchase_date + purchase_price is
surfaced as a possible-duplicate warning for manual review. It is not
blocked automatically.
```

## Business Rules

```text
Rows with match_status = ready_to_import can be inserted into collection_items.
Rows with match_status = needs_review require manual confirmation.
Rows with match_status = waiting_for_product are retried after the next
  successful product catalog pipeline run.
Rows with match_status = error cannot be imported until fixed.
Rows with match_status = imported should not be imported again.
A staging row should keep the original raw_product_name even after matching.
Bad input should be stored and explained, not silently deleted.
```

---

# Table: `watchlist`

## Purpose

Stores products that should be monitored even if they are not in the collection.

This table is useful for future watch targets, price targets, and buy-interest tracking.

## Suggested Schema

```text
watchlist

watchlist_item_id        uuid or integer, primary key
id_product              integer / bigint, not null
reason                 text, nullable
target_price            decimal, nullable
is_active               boolean, not null, default true
created_at              timestamp, not null
updated_at              timestamp, not null
```

## Relationship to `products`

```text
watchlist.id_product → products.id_product
```

## Uniqueness Enforcement

```text
Only one active watchlist entry is allowed per id_product. This is enforced at
the schema level where the database supports it:

  partial unique index on id_product where is_active = true

Inactive (is_active = false) historical watchlist rows are allowed to remain
indefinitely — a product can be deactivated from the watchlist and re-added
later without conflicting with its own history.

The project targets Postgres (Supabase free tier), which fully supports
partial unique indexes. This is therefore a firm MVP requirement, not a
conditional fallback to application-level enforcement:

  CREATE UNIQUE INDEX ux_watchlist_active_product
    ON watchlist (id_product) WHERE is_active = true;
```

## Business Rules

```text
A product can be watched even if it is not in the collection.
Inactive watchlist rows should be kept for history.
Only one active watchlist entry per id_product is allowed (schema-enforced).
```

---

# Table: `analytics_signals`

## Purpose

Stores generated analytical observations.

For MVP, this table should stay simple and explainable.

A signal is not a prediction. It is an observation.

## Suggested Schema

```text
analytics_signals

signal_id               uuid or integer, primary key
signal_date             date, not null
id_product              integer / bigint, nullable
collection_item_id       uuid or integer, nullable
signal_type             text, not null
signal_value            decimal, nullable
signal_strength         text, nullable
lookback_days           integer, nullable
reference_value         decimal, nullable
current_value           decimal, nullable
signal_description      text, nullable
created_at              timestamp, not null
```

**`signal_strength`, `lookback_days`, `reference_value`, and `current_value` were added after the initial draft**, once `09-analytics-signal-definitions.md` made clear a signal is much easier to review and display when it carries its own comparison context instead of forcing every consumer to recompute it:

```text
signal_strength   a simple low / medium / high category, so BI views/
                 dashboards can filter or color-code without re-deriving
                 strength from signal_value each time.

lookback_days     the historical window used for the calculation, when the
                 signal has one (e.g. 30 for a 30-day growth signal). Null
                 for signals with no freely chosen window — price_spike, for
                 example, compares against Cardmarket's own fixed avg30
                 field rather than a window this project selects.

reference_value   the "before" / comparison value used in the calculation
                 (e.g. previous_trend for growth, purchase_price for
                 collection_gain/loss).

current_value     the "after" / current value used in the calculation (e.g.
                 current_trend for growth, estimated_market_value for
                 collection_gain/loss).
```

## Relationships

```text
analytics_signals.id_product → products.id_product
analytics_signals.collection_item_id → collection_items.collection_item_id
```

Both can be nullable because some signals are product-level, while others are collection-level.

**Collection-level signals (`collection_gain`, `collection_loss`) must be keyed on `collection_item_id`, not only `id_product`.** Two physical copies of the same product can have different `purchase_price` values, so a gain/loss signal keyed only on `id_product` cannot represent "this specific copy gained value" once more than one copy exists. `id_product` should still be populated alongside `collection_item_id` on these rows for convenient joins/filtering, but `collection_item_id` is what makes the row unambiguous.

## MVP Signal Types

```text
new_product
growth
price_spike
collection_gain
collection_loss
missing_price_data
```

`sealed_growth` is intentionally not in this list — see Later Signal Types below.

## New-Product Reliability Flag

```text
A product is considered "new / less reliable" for signal purposes while:

  price_age_days = snapshot_date - products.first_seen_at
  is_new_product = price_age_days < 14

Valuation (estimated_market_value) uses latest price data immediately regardless
of product age. Only growth/spike-style analytics signals treat products
younger than 14 days as unstable. This is a simple data quality flag, not a
prediction or statistical model, and the 14-day window is a starting
assumption that can be adjusted after observing real data.

This is the one canonical "how new is new" rule for signal purposes. The
new_product signal itself (see 09-analytics-signal-definitions.md) uses this
same 14-day boundary for its own strength tiers, rather than defining a
second, different aging scale.
```

## Later Signal Types

```text
potential_buy_opportunity
sealed_growth
watchlist_target_reached
price_drop
unusual_volatility
```

`sealed_growth` is deferred rather than shipped in the MVP for the same reason as `potential_buy_opportunity`: separating sealed products from singles meaningfully benefits from having enough historical data across both groups to compare, which the project won't have on day one. It can be promoted to MVP later once there is real sealed-product price history to validate the logic against.

## Business Rules

```text
Signals should be explainable.
Signals should not be presented as financial advice.
Signals should not be called predictions in MVP.
Machine learning should not be added until enough historical data exists.
```

---

# Recommended MVP Views

Views make the database BI-ready without duplicating calculated data.

Detailed field-level definitions for these views are maintained in
`03-data-dictionary.md`, which is the single source of truth for view
definitions. This document lists intent and the business logic that must stay
consistent wherever the view is defined.

Recommended MVP views:

```text
vw_latest_prices
vw_collection_current_value
vw_collection_summary
vw_product_price_history
vw_products_without_prices
```

## `vw_latest_prices`

Purpose:

```text
One latest price row per product.
```

Used for:

```text
collection valuation
watchlist valuation
current product overview
```

Estimated value logic:

```text
if trend exists and avg30 exists:
    estimated_market_value = (trend + avg30) / 2

if trend exists and avg30 is missing:
    estimated_market_value = trend

if trend is missing and avg30 exists:
    estimated_market_value = avg30

if both are missing:
    estimated_market_value = null
```

This view includes `is_active_in_catalog` so consumers can filter or flag
inactive products without needing to join back to `products`.

## `vw_collection_current_value`

Purpose:

```text
Current estimated value of every unsold collection item.
```

Business logic:

```text
estimated_gain_loss = estimated_market_value - purchase_price
estimated_gain_loss_percent = (estimated_gain_loss / purchase_price) * 100
```

If `purchase_price` is missing or zero:

```text
estimated_gain_loss_percent = null
```

## `vw_collection_summary`

Purpose:

```text
High-level personal collection overview.
```

Useful metrics:

```text
number of active items
number of sold items
number of singles
number of sealed products
total purchase price
total estimated market value
total estimated gain/loss
average estimated item value
```

## `vw_product_price_history`

Purpose:

```text
Historical price trend per product.
```

Useful fields:

```text
id_product
name
product_group
snapshot_date
trend
avg30
estimated_market_value
is_active_in_catalog
```

Including `is_active_in_catalog` makes clear that a product's price history
remains valid and visible even after it stops appearing in the current
catalog.

## `vw_products_without_prices`

Purpose:

```text
Data quality view showing products that exist in the catalog but do not have price data in the latest price snapshot.
```

Useful fields:

```text
id_product
name
product_group
category_name
last_seen_at
```

---

# Final Recommended MVP Data Model

```text
products
├── id_product PK
├── product_group
├── source_file
└── is_active_in_catalog

price_snapshots
├── snapshot_date PK
├── id_product PK / indexed relationship
└── normalized price fields

collection_items
├── collection_item_id PK
├── id_product FK / logical relationship
└── one row per physical item

collection_import_staging
├── import_row_id PK
├── import_batch_id
├── provided_id_product
├── raw_product_name
├── matched_id_product
└── match_status (including waiting_for_product)

watchlist
├── watchlist_item_id PK
├── id_product (unique while is_active = true)
└── simple tracking fields

analytics_signals
├── signal_id PK
├── signal_date
├── id_product nullable
└── simple signal fields
```
