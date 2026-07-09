# Data Dictionary

## Document Version

```text
Version: 0.4
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-04
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial data dictionary |
| 0.2 | 2026-07-04 | Resolved `grade` type, timezone hedging language, `idCategory` reconciliation, `updatedAt` triggers, `waiting_for_product` status, `vw_collection_summary` tie-break rule, and expanded Known Data Limitations based on architecture review |
| 0.3 | 2026-07-04 | Extended `analytics_signals` with `signalStrength`, `lookbackDays`, `referenceValue`, `currentValue`; clarified `collectionItemId` keying for collection-level signals; deferred `sealed_growth` to Later Signal Types, based on architecture review of `09-analytics-signal-definitions.md` |
| 0.4 | 2026-07-04 | Added missing `storageLocation`/`personalNote` fields to `collection_import_staging`; clarified `sourceCreatedAt` as an alias for download time in the MVP; specified `matchConfidence = 0.00` (not `null`) as the value to store when matching was attempted but found no confident match, reserving `null` for rows the matcher hasn't processed yet |

## Overview

This data dictionary documents the main tables, fields, defaults, relationships, and business rules for the Pokémon Cardmarket data engineering / BI project.

The project combines official Cardmarket Pokémon product catalogs and daily price guide snapshots with a personal collection tracking model.

The dictionary is intended to make the project understandable for GitHub reviewers, future contributors, and future application development.

**This document is the single source of truth for table field definitions and BI view definitions.** Other documents (ETL pipeline design, archive strategy) reference views and fields by name rather than re-specifying them, to avoid the two drifting apart.

## Naming Conventions

Database fields use `snake_case` where possible.

Some Cardmarket source fields use camelCase or hyphenated names. During normalization, these fields are converted into database-friendly names.

Examples:

```text
idProduct is kept as idProduct because it is the official Cardmarket product identifier.
idCategory, idExpansion, and idMetacard are also kept close to the source naming for traceability.
```

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
| `idProduct` | integer / bigint | No | Cardmarket | Official Cardmarket product ID. Main key used to connect products with price data and collection items. |
| `name` | text | No | Cardmarket | Product name from the official catalog file. |
| `idCategory` | integer / bigint | Yes | Cardmarket | Cardmarket category ID as of the last catalog refresh. See "idCategory Reconciliation" below for how this relates to the category value stored per price snapshot. |
| `categoryName` | text | Yes | Cardmarket | Human-readable category name. |
| `idExpansion` | integer / bigint | Yes | Cardmarket | Cardmarket expansion/set ID. Useful for expansion-level analysis. |
| `idMetacard` | integer / bigint | Yes | Cardmarket | Cardmarket metacard ID, mainly relevant for singles. May be missing for non-single products. |
| `dateAdded` | date / timestamp | Yes | Cardmarket | Date when the product was added to the Cardmarket catalog, if provided. |
| `productGroup` | text | No | Derived | Identifies whether the row comes from the singles or non-singles catalog. |
| `sourceFile` | text | No | Derived | Original source file used for this product row. |
| `isActiveInCatalog` | boolean | No | Derived | Whether the product still appears in the latest downloaded catalog. Set to false the first time a product is missing from a freshly downloaded catalog file (no grace period in MVP). Never causes deletion. |
| `firstSeenAt` | timestamp | No | Derived | First time this project saw the product in a downloaded catalog. Used to compute product "age" for the new-product reliability flag (see `analytics_signals`). |
| `lastSeenAt` | timestamp | No | Derived | Most recent time this project saw the product in a downloaded catalog. |
| `updatedAt` | timestamp | No | System | Last time the product row was updated in the project database. **Changes on any stored field change, including `lastSeenAt`** — meaning it changes on essentially every catalog run that sees the product again, not only when a business field (name, category, etc.) changes. Do not use this field to infer "a meaningful attribute changed"; it means "the pipeline touched this row." |

## Allowed Values

### `productGroup`

```text
single
non_single
```

### `sourceFile`

```text
products_singles_6.json
products_nonsingles_6.json
```

## Primary Key

```text
idProduct
```

## Business Rules

```text
idProduct must be unique.
A product should not be deleted only because it disappears from the latest catalog.
If a product disappears from the latest catalog, set isActiveInCatalog = false.
Products from singles must get productGroup = single.
Products from non-singles must get productGroup = non_single.
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
| `snapshotDate` | date | No | Derived | Date assigned to the daily price snapshot: the pipeline run date in the Europe/Vienna timezone. This rule applies to every run, including manual reruns and backfills — there is no separate rule for exceptional cases. |
| `sourceCreatedAt` | timestamp | Yes | System | Alias for the pipeline's download timestamp for this file. Cardmarket's source files don't carry a usable file-level timestamp of their own, so in the MVP this field always reflects when the project downloaded the file, not a source-provided value. |
| `idProduct` | integer / bigint | No | Cardmarket | Product ID from the price guide. Connects logically to `products.idProduct`. |
| `idCategory` | integer / bigint | Yes | Cardmarket | Category ID as reported in this specific daily price guide snapshot (source-observed, point-in-time). See "idCategory Reconciliation" below. |
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
| `createdAt` | timestamp | No | System | Time when the snapshot row was inserted into the project database. |

## Primary Key

Composite key:

```text
(snapshotDate, idProduct)
```

## Relationship

For MVP, `price_snapshots.idProduct` is an indexed logical relationship to `products.idProduct`.

A strict foreign key can be added later after source synchronization behavior is observed.

Reason:

```text
Product catalogs are downloaded twice per month.
Price guides are downloaded daily.
A new product can appear in the price guide before the local product catalog is refreshed.
```

## `idCategory` Reconciliation

```text
products.idCategory        = catalog category, as of the last catalog refresh
price_snapshots.idCategory = category as reported in that specific daily price
                              guide snapshot (source-observed, point-in-time)

This is intentional duplication, not redundant normalization debt. The price
guide reports its own category value independently of the product catalog,
and the two can drift.

Reconciliation rule (data quality warning, not a load failure):
  For a given idProduct, if price_snapshots.idCategory differs from
  products.idCategory, the row is surfaced by a data quality check
  (check_category_mismatch). This does not block loading and does not
  overwrite either value — it is a signal for review, not a correction.
```

## Load / Rerun Behavior

```text
Loading is an upsert by (snapshotDate, idProduct). If the same date is
reprocessed (manual rerun, or a corrected raw file), new values overwrite the
existing row for that date rather than creating a duplicate or failing.
Running the same daily pipeline twice for the same date must never create
duplicate rows or leave the table half-loaded.
```

## Business Rules

```text
One product can have only one price row per snapshotDate.
The full price guide should be stored every day, not only collection or watchlist products.
Historical data starts from the first successful saved snapshot.
Hyphenated source fields must be normalized before database insertion.
Price fields may be null if Cardmarket does not provide a value.
low should not be used as the main collection valuation source.
Price snapshots for inactive products (isActiveInCatalog = false) remain
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
| `collectionItemId` | uuid / integer | No | System | Unique identifier for one physical collection item. |
| `idProduct` | integer / bigint | No | User import / matched | Cardmarket product ID connected to `products.idProduct`. |
| `language` | text | No | User / default | Language of the physical item. Default is `DE`. |
| `condition` | text | No | User / default | Condition of the item. Default is `Near Mint`. |
| `acquisitionType` | text | No | User / default | How the item was acquired. Default is `pulled`. |
| `purchasePrice` | decimal | Yes | User | Price paid for the item. Can be null for pulled cards, gifts, or unknown cost. |
| `purchaseDate` | date | Yes | User | Date when the item was purchased, pulled, traded, or received. |
| `isSealed` | boolean | No | User / derived | Whether the physical item is sealed. |
| `isGraded` | boolean | No | User / default | Whether the item has been graded by a grading company. Default is `false`. |
| `gradingCompany` | text | Yes | User | Grading company, for example PSA, CGC, BGS. Null when `isGraded = false`. |
| `grade` | text | Yes | User | Grade value stored exactly as entered or imported — for example `"10"`, `"9.5"`, `"Pristine 10"`, or `"Gem Mint 10"`. Null when `isGraded = false`. Kept as text because grading companies use different, non-comparable scales; the MVP does not normalize across them. A later `gradingScale` / `gradeNumeric` split can be added once graded items are part of a real workflow. |
| `storageLocation` | text | Yes | User | Where the item is stored, for example binder, box, shelf, case. |
| `personalNote` | text | Yes | User | Free text note about the item. |
| `isSold` | boolean | No | User / default | Whether the item has been sold. Default is `false`. |
| `soldPrice` | decimal | Yes | User | Sale price if the item was sold. |
| `soldDate` | date | Yes | User | Date when the item was sold. |
| `createdAt` | timestamp | No | System | Time when the item was created in the database. |
| `updatedAt` | timestamp | No | System | Last time the item row was updated. **Changes whenever any user-facing or lifecycle field changes** — language, condition, acquisitionType, purchasePrice, purchaseDate, isSealed, isGraded, gradingCompany, grade, storageLocation, personalNote, isSold, soldPrice, or soldDate. Unlike `products.updatedAt`, this field only reflects a real data change, since nothing touches this row on a recurring schedule. |

## Primary Key

```text
collectionItemId
```

## Relationship

```text
collection_items.idProduct → products.idProduct
```

## Default Values

```text
language = DE
condition = Near Mint
acquisitionType = pulled
isGraded = false
isSold = false
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

### `acquisitionType`

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
Sold items should be kept with isSold = true.
If isGraded = false, gradingCompany and grade should be null.
If isSold = false, soldPrice and soldDate should usually be null.
If purchasePrice is null, gain/loss cannot be calculated.
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
| `importRowId` | uuid / integer | No | System | Unique ID for one imported staging row. |
| `importBatchId` | uuid / text | No | System | Identifier for one CSV/Excel import batch. |
| `externalId` | text | Yes | User import | Optional ID from the original spreadsheet or external system. When present, used to prevent importing the same source row twice (see Business Rules). |
| `providedIdProduct` | integer / bigint | Yes | User import | Product ID provided by the user, if available. May be invalid. |
| `rawProductName` | text | Yes | User import | Product name as written in the imported file. Preserved even after a match is found. |
| `matchedIdProduct` | integer / bigint | Yes | Matching process | Product ID selected by the matching process. Null if no match exists yet. |
| `language` | text | Yes | User import / default | Imported or default language. Default is `DE`. |
| `condition` | text | Yes | User import / default | Imported or default condition. Default is `Near Mint`. |
| `acquisitionType` | text | Yes | User import / default | Imported or default acquisition type. Default is `pulled`. |
| `purchasePrice` | decimal | Yes | User import | Imported purchase price. |
| `purchaseDate` | date | Yes | User import | Imported purchase/acquisition date. |
| `isSealed` | boolean | Yes | User import / derived | Whether the imported item is sealed. |
| `storageLocation` | text | Yes | User import | Optional physical storage location, carried through to `collection_items.storageLocation` on import. Added in v0.4 — previously documented as an import column in `08-collection-import-flow.md` but missing from this table. |
| `personalNote` | text | Yes | User import | Optional free-text note, carried through to `collection_items.personalNote` on import. Added in v0.4 for the same reason as `storageLocation` above. |
| `matchStatus` | text | No | Matching process | Current status of the import row. See allowed values below, including `waiting_for_product`. |
| `matchConfidence` | decimal | Yes | Matching process | Confidence score between 0.00 and 1.00. `0.00` means matching was attempted and found no confident match (zero or multiple candidates); `null` means matching has not been attempted on this row yet. In the MVP's synchronous flow, matching runs immediately on insert, so `null` is expected to be rare in practice — but the distinction is kept in case matching is ever made asynchronous. |
| `errorMessage` | text | Yes | Validation process | Explanation if the row cannot be imported. |
| `createdAt` | timestamp | No | System | Time when the staging row was created. |
| `importedAt` | timestamp | Yes | System | Time when the row was imported into `collection_items`. |

## Primary Key

```text
importRowId
```

## Relationship

```text
collection_import_staging.matchedIdProduct → products.idProduct
```

Important:

```text
providedIdProduct should not be a strict foreign key in the staging table.
```

Reason:

```text
The staging table must be able to store invalid input for review.
```

## Matching Strategy (Basic, Non-Fuzzy)

```text
Staging rows are matched in this order of preference:
  1. exact idProduct match, if the import provided one (highest confidence)
  2. exact product name match against the products table
  3. no confident match — routed to needs_review for manual confirmation

Advanced fuzzy matching is explicitly out of scope for the MVP.
```

## Handling a Match to a Product That Doesn't Exist Yet

```text
If matchedIdProduct resolves to an idProduct not yet present in the local
products table (new product, catalog not yet refreshed), the row is set to
matchStatus = waiting_for_product rather than imported, needs_review, or
error. It is automatically re-checked after the next successful product
catalog pipeline run.
```

## Allowed Values

### `matchStatus`

```text
ready_to_import
needs_review
waiting_for_product
error
imported
```

### `matchConfidence`

Suggested meaning:

```text
1.00 = exact idProduct match
0.90 = exact product name match
0.70 = strong fuzzy name match (unused while fuzzy matching is out of scope)
0.40 = weak possible match (unused while fuzzy matching is out of scope)
0.00 = no useful match
null = matching was not attempted
```

## Business Rules

```text
Rows with matchStatus = ready_to_import can be inserted into collection_items.
Rows with matchStatus = needs_review require manual confirmation, and are not
  a dead end — once corrected, the row is re-validated and re-matched, and
  can move to ready_to_import, waiting_for_product, or error.
Rows with matchStatus = waiting_for_product are retried automatically after
  the next successful product catalog pipeline run.
Rows with matchStatus = error cannot be imported until fixed; once corrected,
  the same re-validation applies as for needs_review.
Rows with matchStatus = imported should not be imported again.
A staging row should keep the original rawProductName even after matching.
Bad input should be stored and explained, not silently deleted.
If externalId is provided, it is used to prevent importing the same source
  row more than once.
If externalId is not provided, rows are not automatically deduplicated
  (identical physical cards are a legitimate case of multiple valid rows);
  instead, a row matching an existing collection_items row on idProduct +
  language + condition + purchaseDate + purchasePrice is surfaced as a
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
| `watchlistItemId` | uuid / integer | No | System | Unique ID for one watchlist row. |
| `idProduct` | integer / bigint | No | User | Product being watched. |
| `reason` | text | Yes | User | Why the product is being watched. |
| `targetPrice` | decimal | Yes | User | Optional price target. |
| `isActive` | boolean | No | User / default | Whether the watchlist entry is still active. |
| `createdAt` | timestamp | No | System | Time when the watchlist row was created. |
| `updatedAt` | timestamp | No | System | Last time the row was updated. |

## Primary Key

```text
watchlistItemId
```

## Relationship

```text
watchlist.idProduct → products.idProduct
```

## Uniqueness Enforcement

```text
Only one active watchlist entry is allowed per idProduct, enforced at the
schema level where supported (partial unique index on idProduct where
isActive = true). Inactive rows are kept indefinitely for history and do not
conflict with a later active entry for the same product.
```

## Business Rules

```text
A product can be watched even if it is not in the collection.
Inactive watchlist rows should be kept for history.
Only one active watchlist entry per idProduct is allowed (schema-enforced
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
| `signalId` | uuid / integer | No | System | Unique ID for one generated signal. |
| `signalDate` | date | No | System | Date when the signal was generated. |
| `idProduct` | integer / bigint | Yes | Derived | Product connected to the signal. Nullable for collection-only signals. Populated alongside `collectionItemId` on collection-level signals for convenient joins/filtering, even though `collectionItemId` is what makes those rows unambiguous. |
| `collectionItemId` | uuid / integer | Yes | Derived | Collection item connected to the signal. Nullable for product-level signals. **Required for `collection_gain`/`collection_loss`** — two physical copies of the same product can have different `purchasePrice` values, so a gain/loss signal keyed only on `idProduct` cannot represent a specific copy's change in value. |
| `signalType` | text | No | Derived | Type of analytical signal. |
| `signalValue` | decimal | Yes | Derived | Main numeric value connected to the signal, for example a percentage change. |
| `signalStrength` | text | Yes | Derived | Simple category: `low`, `medium`, or `high` (optionally `critical` later). Lets BI views/dashboards filter or color-code without re-deriving strength from `signalValue`. |
| `lookbackDays` | integer | Yes | Derived | Historical window used for the calculation, when the signal has one (e.g. `30` for a 30-day growth signal). Null for signals with no freely chosen window — `price_spike`, for example, compares against Cardmarket's own fixed `avg30` field rather than a window this project selects. |
| `referenceValue` | decimal | Yes | Derived | The "before" / comparison value used in the calculation (e.g. `previousTrend` for growth, `purchasePrice` for collection gain/loss). |
| `currentValue` | decimal | Yes | Derived | The "after" / current value used in the calculation (e.g. `currentTrend` for growth, `estimatedMarketValue` for collection gain/loss). |
| `signalDescription` | text | Yes | Derived | Human-readable explanation of the signal. |
| `createdAt` | timestamp | No | System | Time when the signal row was created. |

`signalStrength`, `lookbackDays`, `referenceValue`, and `currentValue` were added after the initial draft, once `09-analytics-signal-definitions.md` made clear a signal is much easier to review and display when it carries its own comparison context instead of forcing every consumer to recompute it from `price_snapshots`/`collection_items` at query time.

## Primary Key

```text
signalId
```

## Relationships

```text
analytics_signals.idProduct → products.idProduct
analytics_signals.collectionItemId → collection_items.collectionItemId
```

## New-Product Reliability Flag

```text
priceAgeDays = snapshotDate - products.firstSeenAt
isNewProduct = priceAgeDays < 14

Growth and price-spike signals treat a product as unstable/less reliable
while isNewProduct is true. This does not affect valuation
(estimatedMarketValue uses the latest price data regardless of product age)
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
  firstSeenAt as unstable/new.
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
| `idProduct` | Product ID. |
| `snapshotDate` | Latest available snapshot date. |
| `trend` | Latest trend price. |
| `avg30` | Latest 30-day average price. |
| `low` | Latest low price. |
| `estimatedMarketValue` | Calculated estimated value using trend and avg30 fallback logic. |
| `isActiveInCatalog` | Whether the product is present in the latest catalog. Included so consumers can filter or flag inactive products without an extra join. |

Business logic:

```text
if trend exists and avg30 exists:
    estimatedMarketValue = (trend + avg30) / 2

if trend exists and avg30 is missing:
    estimatedMarketValue = trend

if trend is missing and avg30 exists:
    estimatedMarketValue = avg30

if both are missing:
    estimatedMarketValue = null
```

## View: `vw_collection_current_value`

Purpose:

```text
Returns current estimated value for every unsold collection item.
```

Fields:

| Field | Description |
|---|---|
| `collectionItemId` | Physical collection item ID. |
| `idProduct` | Cardmarket product ID. |
| `name` | Product name. |
| `productGroup` | `single` or `non_single`. |
| `language` | Item language. |
| `condition` | Item condition. |
| `purchasePrice` | Price paid, if known. |
| `estimatedMarketValue` | Estimated current value from latest price data. |
| `estimatedGainLoss` | Estimated value minus purchase price. |
| `estimatedGainLossPercent` | Estimated gain/loss percentage. |
| `storageLocation` | Physical storage location. |

Business logic:

```text
Only include collection items where isSold = false.

estimatedGainLoss = estimatedMarketValue - purchasePrice
estimatedGainLossPercent = (estimatedGainLoss / purchasePrice) * 100
```

If `purchasePrice` is missing or zero:

```text
estimatedGainLossPercent = null
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
estimatedMarketValue among unsold items. If two or more items are tied for
the highest value, the tie is broken by the earliest purchaseDate; if
purchaseDate is also equal or null, by the lowest collectionItemId, purely to
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
| `idProduct` | Product ID. |
| `name` | Product name. |
| `productGroup` | `single` or `non_single`. |
| `snapshotDate` | Date of price snapshot. |
| `trend` | Trend price. |
| `avg30` | 30-day average price. |
| `estimatedMarketValue` | Estimated value calculated from trend and avg30. |
| `isActiveInCatalog` | Whether the product is currently active in the catalog. Historical rows remain in this view regardless of this flag. |

## View: `vw_products_without_prices`

Purpose:

```text
Data quality view showing products that exist in the catalog but do not have price data in the latest price snapshot.
```

Fields:

```text
idProduct
name
productGroup
categoryName
lastSeenAt
```

---

# Known Data Limitations

The Cardmarket price guide is a daily snapshot. It does not provide full historical data by itself. This project creates historical price data by saving each daily snapshot over time.

If a day is missed (outage, failed pipeline run, etc.), the resulting gap in the historical series is an accepted, documented limitation. The MVP does not assume a missed Cardmarket snapshot can be recovered after the fact, and does not attempt automatic backfill.

The price guide does not fully separate values by language or condition. The personal collection currently defaults to German-language Near Mint items, but estimated values are based on aggregated Cardmarket price guide data.

The `low` value can be noisy because it may reflect unusual listings, damaged cards, outliers, or temporary underpriced offers. For this reason, the MVP does not use `low` as the main collection valuation field.

New products can have unstable prices because early market data may be sparse or volatile. Valuation still uses the latest available price data for new products, but growth/spike analytics signals treat products with fewer than 14 days of history (since `firstSeenAt`) as less reliable. This is a simple data-quality flag, not a prediction.

No retention limit is applied to raw archive files or historical price snapshots during the MVP. Storage growth is accepted and will be revisited once real file sizes and growth rates are observed.

The MVP does not perform machine learning or price prediction. Analytics signals are simple, explainable observations based on stored historical data.
