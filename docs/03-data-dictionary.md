# Data Dictionary

## Document Version

```text
Version: 0.5
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial data dictionary |
| 0.2 | 2026-07-04 | Resolved `grade` type, timezone hedging language, `id_category` reconciliation, `updated_at` triggers, `waiting_for_product` status, `vw_collection_summary` tie-break rule, and expanded Known Data Limitations based on architecture review |
| 0.3 | 2026-07-04 | Extended `analytics_signals` with `signal_strength`, `lookback_days`, `reference_value`, `current_value`; clarified `collection_item_id` keying for collection-level signals; deferred `sealed_growth` to Later Signal Types, based on architecture review of `09-analytics-signal-definitions.md` |
| 0.4 | 2026-07-04 | Added missing `storage_location`/`personal_note` fields to `collection_import_staging`; clarified `source_created_at` as an alias for download time in the MVP; specified `match_confidence = 0.00` (not `null`) as the value to store when matching was attempted but found no confident match, reserving `null` for rows the matcher hasn't processed yet |
| 0.5 | 2026-07-14 | Renamed every field in every table from camelCase to `snake_case` (e.g. `idProduct` → `id_product`), settling the convention this document's own "Naming Conventions" section already claimed (`snake_case`) but the field lists throughout the rest of the document hadn't actually followed until now — that mismatch predates this rewrite and is fixed here. Rewrote the Naming Conventions section itself for clarity. CSV/Excel import column headers (`08-collection-import-flow.md`) explicitly keep camelCase and are not affected. |

## Overview

This data dictionary documents the main tables, fields, defaults, relationships, and business rules for the Pokémon Cardmarket data engineering / BI project.

The project combines official Cardmarket Pokémon product catalogs and daily price guide snapshots with a personal collection tracking model.

The dictionary is intended to make the project understandable for GitHub reviewers, future contributors, and future application development.

**This document is the single source of truth for table field definitions and BI view definitions.** Other documents (ETL pipeline design, archive strategy) reference views and fields by name rather than re-specifying them, to avoid the two drifting apart.

## Naming Conventions

Database fields use `snake_case`, without exception. This is a deliberate
Postgres-idiomatic choice (see `DECISIONS.md` in the code repository): an
unquoted camelCase identifier like `idProduct` would be silently folded to
`idproduct` by Postgres unless quoted everywhere, in every query, forever —
`snake_case` avoids that entirely and is the standard convention for
Postgres schemas.

**Earlier drafts of this document (through v0.4) said "snake_case where
possible" and then listed fields like `idProduct` as the example — an
internal contradiction that predates this note. As of v0.5, that's
resolved: every field, in every table, is `snake_case`, no exceptions.**

Cardmarket's own source JSON uses camelCase field names (`idProduct`,
`idCategory`, `idExpansion`, `idMetacard`) and hyphenated price fields
(`avg-holo`, `trend-holo`, etc.). During normalization, all of these are
converted to `snake_case` database columns. Traceability to the source is
kept through the *name itself* (e.g. `id_product` is still obviously "the
same field as Cardmarket's `idProduct`"), not through preserving the
source's literal casing.

Examples:

```text
Cardmarket source field   →  database column
idProduct                 →  id_product
idCategory                 →  id_category
idExpansion                →  id_expansion
idMetacard                  →  id_metacard
```

**Exception — CSV/Excel collection import column headers stay camelCase.**
These are user-facing input files, not database objects, so they don't
follow the database naming convention above. See
`08-collection-import-flow.md`'s Naming Convention Note for the explicit
mapping between import column headers and the `collection_import_staging`
columns they load into.

Hyphenated price guide fields are converted to snake_case:

```text
avg-holo      -> avg_holo
low-holo      -> low_holo
trend-holo    -> trend_holo
avg1-holo     -> avg1_holo
avg7-holo     -> avg7_holo
avg30-holo    -> avg30_holo
```

This project prioritizes source traceability while normalizing fields that are inconvenient for database queries.

---

# Table: `products`

## Purpose

`products` stores the unified Pokémon product catalog from Cardmarket.

It combines:

```text
products_singles_6.json
products_nonsingles_6.json
```

into one table.

One row represents one Cardmarket product.

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `id_product` | integer / bigint | No | Cardmarket | Official Cardmarket product ID. Main key used to connect products with price data and collection items. |
| `name` | text | No | Cardmarket | Product name from the official catalog file. |
| `id_category` | integer / bigint | Yes | Cardmarket | Cardmarket category ID as of the last catalog refresh. See "id_category Reconciliation" below for how this relates to the category value stored per price snapshot. |
| `category_name` | text | Yes | Cardmarket | Human-readable category name. |
| `id_expansion` | integer / bigint | Yes | Cardmarket | Cardmarket expansion/set ID. Useful for expansion-level analysis. |
| `id_metacard` | integer / bigint | Yes | Cardmarket | Cardmarket metacard ID, mainly relevant for singles. May be missing for non-single products. |
| `date_added` | date / timestamp | Yes | Cardmarket | Date when the product was added to the Cardmarket catalog, if provided. |
| `product_group` | text | No | Derived | Identifies whether the row comes from the singles or non-singles catalog. |
| `source_file` | text | No | Derived | Original source file used for this product row. |
| `is_active_in_catalog` | boolean | No | Derived | Whether the product still appears in the latest downloaded catalog. Set to false the first time a product is missing from a freshly downloaded catalog file (no grace period in MVP). Never causes deletion. |
| `first_seen_at` | timestamp | No | Derived | First time this project saw the product in a downloaded catalog. Used to compute product "age" for the new-product reliability flag (see `analytics_signals`). |
| `last_seen_at` | timestamp | No | Derived | Most recent time this project saw the product in a downloaded catalog. |
| `updated_at` | timestamp | No | System | Last time the product row was updated in the project database. **Changes on any stored field change, including `last_seen_at`** — meaning it changes on essentially every catalog run that sees the product again, not only when a business field (name, category, etc.) changes. Do not use this field to infer "a meaningful attribute changed"; it means "the pipeline touched this row." |

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

## Primary Key

```text
id_product
```

## Business Rules

```text
id_product must be unique.
A product should not be deleted only because it disappears from the latest catalog.
If a product disappears from the latest catalog, set is_active_in_catalog = false.
Products from singles must get product_group = single.
Products from non-singles must get product_group = non_single.
Historical price_snapshots and collection_items referencing an inactive
  product remain valid and are not hidden or excluded from BI views.
```

---

# Table: `price_snapshots`

## Purpose

`price_snapshots` stores the full daily Cardmarket price guide.

One row represents price data for one product on one snapshot date.

This table creates historical price data over time.

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `snapshot_date` | date | No | Derived | Date assigned to the daily price snapshot: the pipeline run date in the Europe/Vienna timezone. This rule applies to every run, including manual reruns and backfills — there is no separate rule for exceptional cases. |
| `source_created_at` | timestamp | Yes | System | Alias for the pipeline's download timestamp for this file. Cardmarket's source files don't carry a usable file-level timestamp of their own, so in the MVP this field always reflects when the project downloaded the file, not a source-provided value. |
| `id_product` | integer / bigint | No | Cardmarket | Product ID from the price guide. Connects logically to `products.id_product`. |
| `id_category` | integer / bigint | Yes | Cardmarket | Category ID as reported in this specific daily price guide snapshot (source-observed, point-in-time). See "id_category Reconciliation" below. |
| `avg` | decimal | Yes | Cardmarket | Average price value from the price guide. |
| `low` | decimal | Yes | Cardmarket | Lowest listed price from the price guide. Can be noisy and should not be the main valuation field. |
| `trend` | decimal | Yes | Cardmarket | Trend price from the price guide. Used in estimated value logic. |
| `avg1` | decimal | Yes | Cardmarket | Average price over the short recent period represented by Cardmarket. |
| `avg7` | decimal | Yes | Cardmarket | Average price over the 7-day period. |
| `avg30` | decimal | Yes | Cardmarket | Average price over the 30-day period. Used in estimated value logic. |
| `avg_holo` | decimal | Yes | Cardmarket | Normalized version of `avg-holo`. |
| `low_holo` | decimal | Yes | Cardmarket | Normalized version of `low-holo`. |
| `trend_holo` | decimal | Yes | Cardmarket | Normalized version of `trend-holo`. |
| `avg1_holo` | decimal | Yes | Cardmarket | Normalized version of `avg1-holo`. |
| `avg7_holo` | decimal | Yes | Cardmarket | Normalized version of `avg7-holo`. |
| `avg30_holo` | decimal | Yes | Cardmarket | Normalized version of `avg30-holo`. |
| `created_at` | timestamp | No | System | Time when the snapshot row was inserted into the project database. |

## Primary Key

Composite key:

```text
(snapshot_date, id_product)
```

## Relationship

For MVP, `price_snapshots.id_product` is an indexed logical relationship to `products.id_product`.

A strict foreign key can be added later after source synchronization behavior is observed.

Reason:

```text
Product catalogs are downloaded twice per month.
Price guides are downloaded daily.
A new product can appear in the price guide before the local product catalog is refreshed.
```

## `id_category` Reconciliation

```text
products.id_category        = catalog category, as of the last catalog refresh
price_snapshots.id_category = category as reported in that specific daily price
                              guide snapshot (source-observed, point-in-time)

This is intentional duplication, not redundant normalization debt. The price
guide reports its own category value independently of the product catalog,
and the two can drift.

Reconciliation rule (data quality warning, not a load failure):
  For a given id_product, if price_snapshots.id_category differs from
  products.id_category, the row is surfaced by a data quality check
  (check_category_mismatch). This does not block loading and does not
  overwrite either value — it is a signal for review, not a correction.
```

## Load / Rerun Behavior

```text
Loading is an upsert by (snapshot_date, id_product). If the same date is
reprocessed (manual rerun, or a corrected raw file), new values overwrite the
existing row for that date rather than creating a duplicate or failing.
Running the same daily pipeline twice for the same date must never create
duplicate rows or leave the table half-loaded.
```

## Business Rules

```text
One product can have only one price row per snapshot_date.
The full price guide should be stored every day, not only collection or watchlist products.
Historical data starts from the first successful saved snapshot.
Hyphenated source fields must be normalized before database insertion.
Price fields may be null if Cardmarket does not provide a value.
low should not be used as the main collection valuation source.
Price snapshots for inactive products (is_active_in_catalog = false) remain
  valid historical observations and are not deleted or hidden.
```

## Important Note

The Cardmarket price guide is a daily snapshot, not a historical dataset. This project creates historical price data by saving the full price guide every day.

Therefore, price history begins on the first day the pipeline successfully archives and stores a snapshot.

If a day is missed, the resulting gap in the historical series is an accepted, documented limitation — see "Known Data Limitations" below — not something the pipeline attempts to backfill automatically.

---

# Table: `collection_items`

## Purpose

`collection_items` stores the user's personal Pokémon collection.

One row represents one physical item.

That item can be:

```text
one individual card
one sealed product
one graded card later
one sold item kept for history
```

The table deliberately does not use a simple `quantity` field because physical items can differ by condition, language, purchase date, purchase price, grading, storage location, and sale status.

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `collection_item_id` | uuid / integer | No | System | Unique identifier for one physical collection item. |
| `id_product` | integer / bigint | No | User import / matched | Cardmarket product ID connected to `products.id_product`. |
| `language` | text | No | User / default | Language of the physical item. Default is `DE`. |
| `condition` | text | No | User / default | Condition of the item. Default is `Near Mint`. |
| `acquisition_type` | text | No | User / default | How the item was acquired. Default is `pulled`. |
| `purchase_price` | decimal | Yes | User | Price paid for the item. Can be null for pulled cards, gifts, or unknown cost. |
| `purchase_date` | date | Yes | User | Date when the item was purchased, pulled, traded, or received. |
| `is_sealed` | boolean | No | User / derived | Whether the physical item is sealed. |
| `is_graded` | boolean | No | User / default | Whether the item has been graded by a grading company. Default is `false`. |
| `grading_company` | text | Yes | User | Grading company, for example PSA, CGC, BGS. Null when `is_graded = false`. |
| `grade` | text | Yes | User | Grade value stored exactly as entered or imported — for example `"10"`, `"9.5"`, `"Pristine 10"`, or `"Gem Mint 10"`. Null when `is_graded = false`. Kept as text because grading companies use different, non-comparable scales; the MVP does not normalize across them. A later `grading_scale` / `grade_numeric` split can be added once graded items are part of a real workflow. |
| `storage_location` | text | Yes | User | Where the item is stored, for example binder, box, shelf, case. |
| `personal_note` | text | Yes | User | Free text note about the item. |
| `is_sold` | boolean | No | User / default | Whether the item has been sold. Default is `false`. |
| `sold_price` | decimal | Yes | User | Sale price if the item was sold. |
| `sold_date` | date | Yes | User | Date when the item was sold. |
| `created_at` | timestamp | No | System | Time when the item was created in the database. |
| `updated_at` | timestamp | No | System | Last time the item row was updated. **Changes whenever any user-facing or lifecycle field changes** — language, condition, acquisition_type, purchase_price, purchase_date, is_sealed, is_graded, grading_company, grade, storage_location, personal_note, is_sold, sold_price, or sold_date. Unlike `products.updated_at`, this field only reflects a real data change, since nothing touches this row on a recurring schedule. |

## Primary Key

```text
collection_item_id
```

## Relationship

```text
collection_items.id_product → products.id_product
```

## Default Values

```text
language = DE
condition = Near Mint
acquisition_type = pulled
is_graded = false
is_sold = false
```

## Allowed Values

### `language`

For MVP:

```text
DE
EN
FR
IT
ES
JP
KR
CN
Other
Unknown
```

### `condition`

Recommended Cardmarket-style values:

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

### `acquisition_type`

Recommended values:

```text
pulled
bought_single
bought_sealed
trade
gift
unknown
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

`collection_import_staging` stores raw imported collection rows before they become real collection items.

This table exists because CSV/Excel imports are often messy.

The staging table protects the clean `collection_items` table from bad imports.

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `import_row_id` | uuid / integer | No | System | Unique ID for one imported staging row. |
| `import_batch_id` | uuid / text | No | System | Identifier for one CSV/Excel import batch. |
| `external_id` | text | Yes | User import | Optional ID from the original spreadsheet or external system. When present, used to prevent importing the same source row twice (see Business Rules). |
| `provided_id_product` | integer / bigint | Yes | User import | Product ID provided by the user, if available. May be invalid. |
| `raw_product_name` | text | Yes | User import | Product name as written in the imported file. Preserved even after a match is found. |
| `matched_id_product` | integer / bigint | Yes | Matching process | Product ID selected by the matching process. Null if no match exists yet. |
| `language` | text | Yes | User import / default | Imported or default language. Default is `DE`. |
| `condition` | text | Yes | User import / default | Imported or default condition. Default is `Near Mint`. |
| `acquisition_type` | text | Yes | User import / default | Imported or default acquisition type. Default is `pulled`. |
| `purchase_price` | decimal | Yes | User import | Imported purchase price. |
| `purchase_date` | date | Yes | User import | Imported purchase/acquisition date. |
| `is_sealed` | boolean | Yes | User import / derived | Whether the imported item is sealed. |
| `storage_location` | text | Yes | User import | Optional physical storage location, carried through to `collection_items.storage_location` on import. Added in v0.4 — previously documented as an import column in `08-collection-import-flow.md` but missing from this table. |
| `personal_note` | text | Yes | User import | Optional free-text note, carried through to `collection_items.personal_note` on import. Added in v0.4 for the same reason as `storage_location` above. |
| `match_status` | text | No | Matching process | Current status of the import row. See allowed values below, including `waiting_for_product`. |
| `match_confidence` | decimal | Yes | Matching process | Confidence score between 0.00 and 1.00. `0.00` means matching was attempted and found no confident match (zero or multiple candidates); `null` means matching has not been attempted on this row yet. In the MVP's synchronous flow, matching runs immediately on insert, so `null` is expected to be rare in practice — but the distinction is kept in case matching is ever made asynchronous. |
| `error_message` | text | Yes | Validation process | Explanation if the row cannot be imported. |
| `created_at` | timestamp | No | System | Time when the staging row was created. |
| `imported_at` | timestamp | Yes | System | Time when the row was imported into `collection_items`. |

## Primary Key

```text
import_row_id
```

## Relationship

```text
collection_import_staging.matched_id_product → products.id_product
```

Important:

```text
provided_id_product should not be a strict foreign key in the staging table.
```

Reason:

```text
The staging table must be able to store invalid input for review.
```

## Matching Strategy (Basic, Non-Fuzzy)

```text
Staging rows are matched in this order of preference:
  1. exact id_product match, if the import provided one (highest confidence)
  2. exact product name match against the products table
  3. no confident match — routed to needs_review for manual confirmation

Advanced fuzzy matching is explicitly out of scope for the MVP.
```

## Handling a Match to a Product That Doesn't Exist Yet

```text
If matched_id_product resolves to an id_product not yet present in the local
products table (new product, catalog not yet refreshed), the row is set to
match_status = waiting_for_product rather than imported, needs_review, or
error. It is automatically re-checked after the next successful product
catalog pipeline run.
```

## Allowed Values

### `match_status`

```text
ready_to_import
needs_review
waiting_for_product
error
imported
```

### `match_confidence`

Suggested meaning:

```text
1.00 = exact id_product match
0.90 = exact product name match
0.70 = strong fuzzy name match (unused while fuzzy matching is out of scope)
0.40 = weak possible match (unused while fuzzy matching is out of scope)
0.00 = no useful match
null = matching was not attempted
```

## Business Rules

```text
Rows with match_status = ready_to_import can be inserted into collection_items.
Rows with match_status = needs_review require manual confirmation, and are not
  a dead end — once corrected, the row is re-validated and re-matched, and
  can move to ready_to_import, waiting_for_product, or error.
Rows with match_status = waiting_for_product are retried automatically after
  the next successful product catalog pipeline run.
Rows with match_status = error cannot be imported until fixed; once corrected,
  the same re-validation applies as for needs_review.
Rows with match_status = imported should not be imported again.
A staging row should keep the original raw_product_name even after matching.
Bad input should be stored and explained, not silently deleted.
If external_id is provided, it is used to prevent importing the same source
  row more than once.
If external_id is not provided, rows are not automatically deduplicated
  (identical physical cards are a legitimate case of multiple valid rows);
  instead, a row matching an existing collection_items row on id_product +
  language + condition + purchase_date + purchase_price is surfaced as a
  possible-duplicate warning for manual review.
```

---

# Table: `watchlist`

## Purpose

`watchlist` stores products that should be monitored even if they are not in the collection.

It is useful for:

```text
cards to buy later
sealed products to observe
products with interesting price movement
nostalgia targets
future collection targets
```

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `watchlist_item_id` | uuid / integer | No | System | Unique ID for one watchlist row. |
| `id_product` | integer / bigint | No | User | Product being watched. |
| `reason` | text | Yes | User | Why the product is being watched. |
| `target_price` | decimal | Yes | User | Optional price target. |
| `is_active` | boolean | No | User / default | Whether the watchlist entry is still active. |
| `created_at` | timestamp | No | System | Time when the watchlist row was created. |
| `updated_at` | timestamp | No | System | Last time the row was updated. |

## Primary Key

```text
watchlist_item_id
```

## Relationship

```text
watchlist.id_product → products.id_product
```

## Uniqueness Enforcement

```text
Only one active watchlist entry is allowed per id_product, enforced at the
schema level where supported (partial unique index on id_product where
is_active = true). Inactive rows are kept indefinitely for history and do not
conflict with a later active entry for the same product.
```

## Business Rules

```text
A product can be watched even if it is not in the collection.
Inactive watchlist rows should be kept for history.
Only one active watchlist entry per id_product is allowed (schema-enforced
  where possible, application-enforced otherwise).
```

---

# Table: `analytics_signals`

## Purpose

`analytics_signals` stores generated analytical observations.

For MVP, this table should stay simple and explainable.

A signal is not a prediction.

## Fields

| Field | Type | Nullable | Source | Description |
|---|---|---|---|---|
| `signal_id` | uuid / integer | No | System | Unique ID for one generated signal. |
| `signal_date` | date | No | System | Date when the signal was generated. |
| `id_product` | integer / bigint | Yes | Derived | Product connected to the signal. Nullable for collection-only signals. Populated alongside `collection_item_id` on collection-level signals for convenient joins/filtering, even though `collection_item_id` is what makes those rows unambiguous. |
| `collection_item_id` | uuid / integer | Yes | Derived | Collection item connected to the signal. Nullable for product-level signals. **Required for `collection_gain`/`collection_loss`** — two physical copies of the same product can have different `purchase_price` values, so a gain/loss signal keyed only on `id_product` cannot represent a specific copy's change in value. |
| `signal_type` | text | No | Derived | Type of analytical signal. |
| `signal_value` | decimal | Yes | Derived | Main numeric value connected to the signal, for example a percentage change. |
| `signal_strength` | text | Yes | Derived | Simple category: `low`, `medium`, or `high` (optionally `critical` later). Lets BI views/dashboards filter or color-code without re-deriving strength from `signal_value`. |
| `lookback_days` | integer | Yes | Derived | Historical window used for the calculation, when the signal has one (e.g. `30` for a 30-day growth signal). Null for signals with no freely chosen window — `price_spike`, for example, compares against Cardmarket's own fixed `avg30` field rather than a window this project selects. |
| `reference_value` | decimal | Yes | Derived | The "before" / comparison value used in the calculation (e.g. `previous_trend` for growth, `purchase_price` for collection gain/loss). |
| `current_value` | decimal | Yes | Derived | The "after" / current value used in the calculation (e.g. `current_trend` for growth, `estimated_market_value` for collection gain/loss). |
| `signal_description` | text | Yes | Derived | Human-readable explanation of the signal. |
| `created_at` | timestamp | No | System | Time when the signal row was created. |

`signal_strength`, `lookback_days`, `reference_value`, and `current_value` were added after the initial draft, once `09-analytics-signal-definitions.md` made clear a signal is much easier to review and display when it carries its own comparison context instead of forcing every consumer to recompute it from `price_snapshots`/`collection_items` at query time.

## Primary Key

```text
signal_id
```

## Relationships

```text
analytics_signals.id_product → products.id_product
analytics_signals.collection_item_id → collection_items.collection_item_id
```

## New-Product Reliability Flag

```text
price_age_days = snapshot_date - products.first_seen_at
is_new_product = price_age_days < 14

Growth and price-spike signals treat a product as unstable/less reliable
while is_new_product is true. This does not affect valuation
(estimated_market_value uses the latest price data regardless of product age)
— only signal generation. The 14-day window is a starting assumption, not a
statistically derived threshold, and can be adjusted after observing real
data.
```

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

## Later Signal Types

```text
potential_buy_opportunity
sealed_growth
watchlist_target_reached
price_drop
unusual_volatility
```

`sealed_growth` is deferred for the same reason as `potential_buy_opportunity`: meaningfully separating sealed products from singles benefits from having enough historical data across both groups to compare, which the project won't have on day one. It can be promoted to MVP later once real sealed-product price history exists to validate the logic against.

## Business Rules

```text
Signals should be explainable.
Signals should not be presented as financial advice.
Signals should not be called predictions in MVP.
Machine learning should not be added until enough historical data exists.
Growth/spike signals should treat products with fewer than 14 days since
  first_seen_at as unstable/new.
```

---

# Views

## View: `vw_latest_prices`

Purpose:

```text
Returns the latest available price row for each product.
```

Used by:

```text
collection valuation
watchlist overview
current price analysis
```

Fields:

| Field | Description |
|---|---|
| `id_product` | Product ID. |
| `snapshot_date` | Latest available snapshot date. |
| `trend` | Latest trend price. |
| `avg30` | Latest 30-day average price. |
| `low` | Latest low price. |
| `estimated_market_value` | Calculated estimated value using trend and avg30 fallback logic. |
| `is_active_in_catalog` | Whether the product is present in the latest catalog. Included so consumers can filter or flag inactive products without an extra join. |

Business logic:

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

## View: `vw_collection_current_value`

Purpose:

```text
Returns current estimated value for every unsold collection item.
```

Fields:

| Field | Description |
|---|---|
| `collection_item_id` | Physical collection item ID. |
| `id_product` | Cardmarket product ID. |
| `name` | Product name. |
| `product_group` | `single` or `non_single`. |
| `language` | Item language. |
| `condition` | Item condition. |
| `purchase_price` | Price paid, if known. |
| `estimated_market_value` | Estimated current value from latest price data. |
| `estimated_gain_loss` | Estimated value minus purchase price. |
| `estimated_gain_loss_percent` | Estimated gain/loss percentage. |
| `storage_location` | Physical storage location. |

Business logic:

```text
Only include collection items where is_sold = false.

estimated_gain_loss = estimated_market_value - purchase_price
estimated_gain_loss_percent = (estimated_gain_loss / purchase_price) * 100
```

If `purchase_price` is missing or zero:

```text
estimated_gain_loss_percent = null
```

## View: `vw_collection_summary`

Purpose:

```text
High-level collection summary.
```

Useful metrics:

```text
active item count
sold item count
single item count
sealed item count
total purchase price
total estimated market value
total estimated gain/loss
average estimated item value
most valuable item
```

`most valuable item` logic:

```text
Returns the collection item (full row, not just the value) with the highest
estimated_market_value among unsold items. If two or more items are tied for
the highest value, the tie is broken by the earliest purchase_date; if
purchase_date is also equal or null, by the lowest collection_item_id, purely to
keep the result deterministic. This is a display convenience, not an
analytical ranking.
```

## View: `vw_product_price_history`

Purpose:

```text
BI-ready historical price data for products.
```

Fields:

| Field | Description |
|---|---|
| `id_product` | Product ID. |
| `name` | Product name. |
| `product_group` | `single` or `non_single`. |
| `snapshot_date` | Date of price snapshot. |
| `trend` | Trend price. |
| `avg30` | 30-day average price. |
| `estimated_market_value` | Estimated value calculated from trend and avg30. |
| `is_active_in_catalog` | Whether the product is currently active in the catalog. Historical rows remain in this view regardless of this flag. |

## View: `vw_products_without_prices`

Purpose:

```text
Data quality view showing products that exist in the catalog but do not have price data in the latest price snapshot.
```

Fields:

```text
id_product
name
product_group
category_name
last_seen_at
```

---

# Known Data Limitations

The Cardmarket price guide is a daily snapshot. It does not provide full historical data by itself. This project creates historical price data by saving each daily snapshot over time.

If a day is missed (outage, failed pipeline run, etc.), the resulting gap in the historical series is an accepted, documented limitation. The MVP does not assume a missed Cardmarket snapshot can be recovered after the fact, and does not attempt automatic backfill.

The price guide does not fully separate values by language or condition. The personal collection currently defaults to German-language Near Mint items, but estimated values are based on aggregated Cardmarket price guide data.

The `low` value can be noisy because it may reflect unusual listings, damaged cards, outliers, or temporary underpriced offers. For this reason, the MVP does not use `low` as the main collection valuation field.

New products can have unstable prices because early market data may be sparse or volatile. Valuation still uses the latest available price data for new products, but growth/spike analytics signals treat products with fewer than 14 days of history (since `first_seen_at`) as less reliable. This is a simple data-quality flag, not a prediction.

No retention limit is applied to raw archive files or historical price snapshots during the MVP. Storage growth is accepted and will be revisited once real file sizes and growth rates are observed.

The MVP does not perform machine learning or price prediction. Analytics signals are simple, explainable observations based on stored historical data.
