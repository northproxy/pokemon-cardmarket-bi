# Collection Import Flow

## Document Version

```text
Version: 0.4
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial collection import flow |
| 0.2 | 2026-07-04 | Added `waiting_for_product` status, unified `match_confidence` scale and allowed-value lists with the data dictionary, broadened duplicate detection to match the cross-batch rule established elsewhere, made review/error correction explicitly iterative, tightened matching-order wording to require an exact name match for auto-resolution, and added same-file re-upload and empty-vs-missing-value guidance, based on architecture review |
| 0.3 | 2026-07-04 | Added missing `storage_location`/`personal_note` fields to this document's own staging table structure (they were already import columns and mapping targets here, but absent from the schema listing); set explicit `match_confidence = 0.00` for the two no-confident-match branches; confirmed as intentional (not an oversight) that a `provided_id_product` which doesn't resolve locally does not fall back to a name match |
| 0.4 | 2026-07-14 | Renamed all `collection_import_staging`/`collection_items` DB field references from camelCase to `snake_case`, matching the project-wide database naming decision (see `02-data-model.md` v0.5, `03-data-dictionary.md` v0.5). **CSV/Excel import column headers are explicitly excluded from this rename and stay camelCase** — see the new naming note under "Recommended MVP Import Columns" below for the translation boundary between the two. |

## Naming Convention Note (added v0.4)

This document has two different naming conventions living side by side,
deliberately:

```text
CSV/Excel import column headers   → camelCase (externalId, providedIdProduct,
                                     rawProductName, purchasePrice, ...)
collection_import_staging /
collection_items database columns → snake_case (external_id, provided_id_product,
                                     raw_product_name, purchase_price, ...)
```

The import file is user-facing input, not a database object, so it keeps
its original camelCase column names. Everything from the moment a row
lands in `collection_import_staging` onward is a real Postgres table, so
it follows the project's `snake_case` database convention (see
`02-data-model.md`, `03-data-dictionary.md`). The "Column Explanation"
table below shows the exact mapping between the two.

## Purpose

The collection import flow describes how personal Pokémon collection data enters the project database.

The goal is to keep the first version simple, transparent, and safe:

```text
CSV / Excel file
→ staging table
→ validation and product matching
→ review of problematic rows (including rows waiting on a product that
  doesn't exist locally yet)
→ import into collection_items
→ collection valuation views
```

This project does not assume that every imported row is immediately correct. Instead, imported data first lands in a staging table where it can be checked, matched, corrected, and only then moved into the final collection table.

This approach makes the project more realistic and portfolio-friendly because it separates raw user input from trusted collection data.

---

## Why Use a Staging Table?

A direct import into `collection_items` would be simpler, but it would also be risky.

Collection files can contain:

* missing product IDs
* slightly different product names
* spelling mistakes
* duplicate rows
* incomplete purchase data
* unknown conditions
* manually entered notes
* products that are not yet matched to the Cardmarket catalog
* products that exist on Cardmarket but haven't reached the local catalog yet

For this reason, the MVP uses a dedicated staging table:

```text
collection_import_staging
```

The staging table acts as a temporary review area before data becomes part of the real collection.

---

## Import Flow Overview

```text
1. User prepares a CSV or Excel file
2. File is loaded into collection_import_staging under one import_batch_id
3. Each row is validated
4. Each row is matched to a Cardmarket id_product
5. Rows are assigned a match_status, including waiting_for_product if the
   matched id_product isn't in the local products table yet
6. Valid (ready_to_import) rows are imported into collection_items
7. Imported staging rows are marked as imported
8. needs_review / error rows can be corrected and re-validated — this is a
   loop, not a dead end
9. waiting_for_product rows are automatically rechecked after the next
   successful product catalog pipeline run
10. Collection valuation views use collection_items + latest prices
```

---

## Source File Format

For the MVP, the collection file should contain one row per physical item.

This means that if the user owns three copies of the same card, the file should contain three separate rows.

This is intentional because every physical item can have its own:

* condition
* language
* purchase price
* purchase date
* storage location
* note
* sold status
* grading status in the future

Example:

```text
rawProductName,providedIdProduct,language,condition,acquisitionType,purchasePrice,purchaseDate,isSealed,storageLocation,personalNote
Pikachu,12345,DE,Near Mint,pulled,,,false,Binder 1,
Pikachu,12345,DE,Near Mint,pulled,,,false,Binder 1,Second copy
Charizard ex,,DE,Near Mint,bought_single,25.00,2026-07-01,false,Toploader Box,
```

The third row deliberately illustrates a realistic ambiguous case: "Charizard ex" alone is not enough to identify a specific print or set on Cardmarket, so without a `providedIdProduct` this row is expected to land in `needs_review` rather than being auto-matched (see Matching Logic below). (`providedIdProduct` here is the CSV column header — see the naming note at the top of this document for how it maps to the staging table's `provided_id_product` column.)

---

## Recommended MVP Import Columns

The MVP import file should support the following columns:

```text
externalId
providedIdProduct
rawProductName
language
condition
acquisitionType
purchasePrice
purchaseDate
isSealed
storageLocation
personalNote
```

### Column Explanation

| Column              | Description                                                    | Maps to staging column |
| ------------------- | -------------------------------------------------------------- | ----------------------- |
| `externalId`        | Optional user-defined row/item identifier from the source file | `external_id`            |
| `providedIdProduct` | Optional Cardmarket product ID if already known                | `provided_id_product`    |
| `rawProductName`    | Product name as entered by the user                            | `raw_product_name`       |
| `language`          | Card/product language, default: `DE`                           | `language`               |
| `condition`         | Item condition, default: `Near Mint`                            | `condition`              |
| `acquisitionType`   | How the item was acquired, default: `pulled`                   | `acquisition_type`       |
| `purchasePrice`     | Optional purchase price                                        | `purchase_price`         |
| `purchaseDate`      | Optional purchase date                                         | `purchase_date`          |
| `isSealed`          | Whether the item is sealed                                     | `is_sealed`              |
| `storageLocation`   | Optional physical storage location                              | `storage_location`       |
| `personalNote`      | Optional user note                                              | `personal_note`          |

**Column naming stays camelCase by design.** CSV/Excel import headers are user-facing input, not database columns, so they keep the original camelCase naming even though the database layer (this table's own `collection_import_staging`, and `collection_items`) uses `snake_case`. The "Maps to staging column" column above is the explicit translation boundary between the two — see `import_reader.py` (once implemented) for where that mapping actually happens in code.

**Empty value vs. missing column:** an empty cell (`""`) for `language`, `condition`, or `acquisitionType` is treated the same as the column being absent entirely — both fall back to the documented default. This is called out explicitly because CSV parsers can distinguish an empty string from a missing field, and the MVP intentionally does not: an intentional empty value and an omitted one are not meaningfully different for this project's purposes.

**No enforced file size or row count limit** exists for the MVP, consistent with the project's general approach to volume limits elsewhere (see `01-mvp-scope.md`) — this may need revisiting once real import files are observed.

---

## Collection Import Staging Table

Imported rows first land in:

```text
collection_import_staging
```

Recommended table structure:

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

---

## Field Roles

### `import_row_id`

Unique technical ID for each staging row.

This is generated by the database.

---

### `import_batch_id`

Identifier for one import run.

All rows from the same uploaded file should receive the same `import_batch_id`.

This makes it possible to review, troubleshoot, or reprocess one import separately.

Example:

```text
import_batch_id = 2026-07-04_collection_import_001
```

**Re-uploading the same file:** `import_batch_id` identifies one *upload event*, not one *source file*. If the same CSV is uploaded twice, it produces two different batch IDs and, without further protection, two sets of staging rows. The system does not detect this by file content in the MVP (no file hashing/checksum). Protection instead relies on `external_id`, when present: see "Duplicate Handling" below. If the file has no `external_id` column at all, re-uploading it is the user's responsibility to avoid — this is a stated MVP limitation, not a silent risk, and is a stronger version of the same duplicate concern discussed there.

---

### `external_id`

Optional ID from the user's own file.

This can be useful if the user exports data from another collection tool or keeps their own numbering system.

When present, it is also the main defense against importing the same source row more than once — see "Duplicate Handling" below.

---

### `provided_id_product`

Cardmarket `id_product` provided directly by the user.

If this field exists and matches a product in the local `products` table, it should be treated as the strongest matching signal.

If it exists but does **not** match any product currently in the local `products` table, this is not automatically an error — see `waiting_for_product` in Match Status Rules, since the product may simply not have reached the local catalog yet.

---

### `raw_product_name`

Original product name from the import file.

This field should be preserved exactly as provided.

It should not be silently cleaned or overwritten because it is useful for debugging failed matches, and it remains in place even after the row is corrected and re-matched.

---

### `matched_id_product`

The Cardmarket `id_product` selected by the import process.

This may come from:

```text
provided_id_product
```

or from an exact name match using:

```text
raw_product_name
```

Note that `matched_id_product` can be set even when the row is not yet importable — see `waiting_for_product` below, where a match exists but the product isn't in the local catalog yet.

---

### `match_status`

Current import status of the row.

Allowed MVP values:

```text
ready_to_import
needs_review
waiting_for_product
error
imported
```

None of `needs_review`, `waiting_for_product`, or `error` are terminal. See "Iterative Review" below.

---

### `match_confidence`

Confidence score for how the match was made, on a 0.00–1.00 scale.

```text
1.00 = exact id_product match
0.90 = exact product name match
0.70 = strong fuzzy name match (unused while fuzzy matching is out of scope
       for the MVP — reserved for a later improvement)
0.40 = weak possible match (unused while fuzzy matching is out of scope)
0.00 = no useful match
null = matching was not attempted
```

This scale is shared with the data dictionary and the data model docs. It intentionally does not include an "uncertain name match" band between exact and fuzzy — for the MVP, a name match is either exact (0.90) or it isn't a match at all; anything less confident than exact goes to `needs_review` rather than being auto-accepted at a lower confidence score.

This field is useful for review workflows but should not be overengineered at the beginning.

---

### `error_message`

Human-readable explanation of why a row cannot currently be imported.

Examples:

```text
Missing product name and product ID
No matching product found
Multiple possible products found
Product matched, but not yet present in the local catalog
Invalid purchase price
Invalid purchase date
Unknown condition value
```

This field should be updated (not just set once) each time a row is re-validated, so it always reflects the current reason a row isn't `ready_to_import`, if any.

---

### `imported_at`

Timestamp showing when the staging row was successfully imported into `collection_items`.

Rows that were not imported should keep this field empty.

---

## Matching Logic

The MVP matching logic should be simple and explainable.

Recommended order:

```text
1. If provided_id_product exists:
   - check whether it exists in products
   - if yes: set matched_id_product, match_status = ready_to_import,
     match_confidence = 1.00
   - if no: set matched_id_product = provided_id_product anyway (it's still the
     user's stated intent), match_status = waiting_for_product,
     match_confidence = null, and record the reason in error_message.
     This is intentionally a dead end rather than a fallback to name
     matching — an explicit user-supplied id_product is trusted over a
     name-based guess, even when that ID isn't in the catalog yet. If the
     row's raw_product_name should also be checked against products.name in
     this case, that's a deliberate future change, not an oversight in
     this version.

2. If provided_id_product is missing:
   - try an EXACT match of raw_product_name against products.name (not a
     fuzzy/partial match)

3. If exactly one exact name match is found:
   - set matched_id_product, match_status = ready_to_import,
     match_confidence = 0.90

4. If multiple exact name matches are found, or the name match is anything
   less than exact:
   - set match_status = needs_review
   - set match_confidence = 0.00 (matching was attempted; no single
     confident result came out of it)
   - write an explanation into error_message

5. If no match is found at all:
   - set match_status = needs_review or error, depending on whether the row
     is otherwise salvageable (see Match Status Rules)
   - set match_confidence = 0.00 for the same reason as step 4
   - write an explanation into error_message
```

`match_confidence = null` is reserved for rows the matcher hasn't processed yet. In the MVP's synchronous import flow that's expected to be rare in practice, since matching runs immediately — but keeping the two values distinct (`null` = not attempted, `0.00` = attempted and inconclusive) leaves room for an async/batched matcher later without a schema change.

Advanced fuzzy matching is explicitly out of scope for the MVP. A name match either resolves exactly, or the row goes to a human for review — the MVP does not guess at a "probably right" match.

For the MVP, it is acceptable to keep product matching semi-manual.

The goal is not to build a perfect fuzzy matching engine immediately. The goal is to create a reliable import process that clearly separates trusted rows from uncertain rows.

---

## Match Status Rules

### `ready_to_import`

The row passed validation and has a valid `matched_id_product` that exists in the local `products` table right now.

These rows can be moved into `collection_items`.

---

### `needs_review`

The row is not clearly wrong, but it needs manual review.

Typical reasons:

```text
multiple exact product name matches
no exact name match found and no provided_id_product
missing id_product and unclear product name
```

These rows should not be imported automatically.

---

### `waiting_for_product`

A product match was found (`matched_id_product` is set, from either an exact `provided_id_product` value or an exact name match), but that `id_product` does not yet exist in the local `products` table.

This happens because the product catalog refreshes only twice per month, while a product can appear on Cardmarket (and therefore be knowable by name or ID) before that refresh happens.

This is a **timing state, not an error**. It is automatically rechecked after the next successful product catalog pipeline run and moves to `ready_to_import` at that point — or to `needs_review` / `error` if something else about the row is also wrong.

---

### `error`

The row has a blocking issue unrelated to product matching timing.

Typical reasons:

```text
invalid date
invalid price
missing required data
invalid condition
invalid language
```

These rows should not be imported until corrected.

---

### `imported`

The row was successfully inserted into `collection_items`.

After import, the staging row should keep its history and receive an `imported_at` timestamp.

---

## Iterative Review

`needs_review` and `error` are not dead ends, and `waiting_for_product` is not purely passive either:

```text
needs_review / error:
    a person corrects the row (e.g. supplies a provided_id_product, fixes an
    invalid date) → the row is re-validated and re-matched using the same
    logic as a fresh import → it can move to ready_to_import,
    waiting_for_product, or remain in needs_review / error if the
    correction didn't fully resolve the issue

waiting_for_product:
    automatically rechecked by the system itself after each successful
    product catalog pipeline run, with no manual action required — though a
    person can also manually trigger a recheck at any time
```

A staging row's `match_status` should therefore be understood as "current best assessment," not a permanent classification.

---

## Import Into collection_items

Only rows with this status should be imported:

```text
ready_to_import
```

When imported, the row creates a new record in:

```text
collection_items
```

Mapping:

| Staging Field      | Collection Field  |
| ------------------ | ----------------- |
| `matched_id_product` | `id_product`       |
| `language`         | `language`        |
| `condition`        | `condition`       |
| `acquisition_type`  | `acquisition_type` |
| `purchase_price`    | `purchase_price`   |
| `purchase_date`     | `purchase_date`    |
| `is_sealed`         | `is_sealed`        |
| `storage_location`  | `storage_location` |
| `personal_note`     | `personal_note`    |

Default values should be applied when fields are missing or empty (see "Empty value vs. missing column" above).

---

## Default Values

The project uses the following collection defaults:

```text
language = DE
condition = Near Mint
acquisition_type = pulled
is_graded = false
is_sold = false
```

These defaults reflect the current collection style:

```text
German-language cards
mostly Near Mint
mostly pulled from packs
not graded by default
not sold by default
```

---

## Important Rule: One Row = One Physical Item

The collection table should not store only quantity per product.

Instead, every physical card or sealed product should have its own row.

Example:

```text
3 copies of the same Pikachu card
= 3 rows in collection_items
```

Reason:

Each item may later have different:

```text
condition
purchase price
sale price
storage location
grading status
personal note
```

This also makes the collection history cleaner and more flexible.

---

## Duplicate Handling

For MVP, duplicates should be handled carefully but not overengineered.

The system should allow multiple rows with the same `id_product` because owning multiple copies of the same card is normal.

Allowed:

```text
same id_product
same language
same condition
multiple physical copies
```

**Within a batch:** if `external_id` is provided, the same `external_id` should not appear twice in the same import batch. This should be treated as a data quality error for the duplicate row.

**Across batches, including re-uploads of the same file:** if `external_id` is provided, it is also checked against previously imported rows (any batch), not just the current one — the same source row should not be importable more than once even if it arrives in a different upload. This is the mechanism that protects against the "same file uploaded twice" case described under `import_batch_id` above.

**When `external_id` is not provided:** the system does not automatically block anything, since multiple genuinely identical physical cards are a normal, legitimate case (see "One Row = One Physical Item"). Instead, a row that matches an *existing* `collection_items` row on `id_product` + `language` + `condition` + `purchase_date` + `purchase_price` all at once is surfaced as a possible-duplicate warning for manual review at import time. It is not blocked automatically, and it is not the same as a hard validation error — the person importing has the context to know whether it's a real second copy or an accidental re-import.

---

## Validation Rules

Before a row can be imported, the following checks should be performed.

### Required for Import

```text
matched_id_product is not null
matched_id_product exists in the local products table right now (otherwise
  the row is waiting_for_product, not ready_to_import)
language is not null
condition is not null
acquisition_type is not null
is_sealed is not null
```

### Recommended Checks

```text
purchase_price must be numeric if provided
purchase_price must not be negative
purchase_date must be a valid date if provided
condition should use allowed values
language should use allowed values
acquisition_type should use allowed values
```

---

## Suggested Allowed Values

These match the values defined in `03-data-dictionary.md` and `02-data-model.md`; they are repeated here so the import file format and the database allowed values never quietly diverge.

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

Default:

```text
DE
```

---

### `condition`

For MVP:

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

Default:

```text
Near Mint
```

---

### `acquisition_type`

For MVP:

```text
pulled
bought_single
bought_sealed
trade
gift
unknown
```

Default:

```text
pulled
```

---

## Import Safety Rules

The MVP should follow these import safety rules:

```text
Do not import rows with match_status = needs_review
Do not import rows with match_status = waiting_for_product
Do not import rows with match_status = error
Do not delete staging rows after successful import
Do not overwrite raw_product_name
Do not silently change user-provided values
Do not merge physical items into quantity rows
Do not treat needs_review / error / waiting_for_product as permanent —
  always allow correction and re-validation
```

The staging table should preserve import history.

---

## Relationship to Price Data

Collection items are valued by joining:

```text
collection_items.id_product
```

to the latest available price in:

```text
price_snapshots.id_product
```

The estimated market value uses the existing MVP formula:

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

The project should not use `low` as the main collection value because it can be noisy.

---

## Known Limitations

The MVP collection import flow has several intentional limitations.

```text
No fuzzy matching — only exact id_product or exact name matches auto-resolve
No file content hashing/checksum to detect a re-uploaded file automatically
No automatic image recognition
No automatic Cardmarket seller data scraping
No language-specific market price
No condition-specific market price
No grading price logic
No mobile app import flow
No enforced file size or row count limit
```

These limitations are acceptable for the MVP.

The goal is to build a reliable and understandable import process first.

---

## Later Improvements

Possible later improvements:

```text
better fuzzy product matching (introducing the 0.70 / 0.40 confidence bands
  that are currently reserved but unused)
file content hashing to detect and warn on re-uploaded files automatically
manual review UI
import preview screen
CSV export
backup and restore
duplicate detection across batches beyond external_id matching
support for graded cards
support for sealed product-specific fields
support for multiple collection owners
support for collection folders or binders
```

---

## Portfolio Value

This collection import flow demonstrates several useful data engineering and BI concepts:

```text
staging before final import
data validation
manual review workflow
timing-aware matching (waiting_for_product) rather than treating every
  unmatched row as an error
iterative correction rather than one-shot pass/fail import
separation of raw user input and trusted data
logical product matching
batch-based imports
collection valuation
realistic handling of imperfect data
```

This makes the project stronger than a simple script because it shows how messy real-world data can be handled safely and transparently.
