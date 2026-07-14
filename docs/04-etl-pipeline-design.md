# ETL / Pipeline Design

## Document Version

```text
Version: 0.6
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial ETL / pipeline design |
| 0.2 | 2026-07-04 | Fixed archive immutability/overwrite contradiction, added failure vs. warning thresholds, catalog-failure behavior, archive-gap handling, iterative staging review flow, `waiting_for_product` handling, reprocessing sketch, and de-duplicated BI view definitions in favor of the data dictionary, based on architecture review |
| 0.3 | 2026-07-04 | Added a Database Platform section confirming Postgres via Supabase (free tier) as the target database, with pooled-connection and free-tier project-pause considerations for GitHub Actions runs |
| 0.4 | 2026-07-05 | Confirmed a two-project Supabase split (dev + prod, both free tier) rather than a single shared project; added manual `pg_dump` backup guidance for the prod project, since the free tier has no automated backups; added `check_invalid_collection_items` as a sixth data quality check |
| 0.5 | 2026-07-12 | Two implementation-time corrections, both logged in `DECISIONS.md` in the code repository: (1) product catalog cadence changed from twice-monthly (1st/15th) to weekly (every Friday) — a genuine decision change, not an error fix; (2) the raw archive folder structure corrected from the originally-designed nested `/raw/cardmarket/pokemon/...` path to the actual, already-provisioned flat FTP layout (`price_guides/`, `product_catalogs/` directly under the FTP root) — this one *is* a doc fix, since the nested path was never actually built. |
| 0.6 | 2026-07-14 | Renamed all field-name references from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `snapshotDate` → `snapshot_date`), matching the project-wide database naming decision in `02-data-model.md` v0.5 / `03-data-dictionary.md` v0.5. This document only references fields by name rather than defining them, so no schema content changed — just the spelling of the names used. |

## Overview

This project uses a batch ETL pipeline for official Cardmarket Pokémon JSON files.

The pipeline has three separate ingestion flows:

1. Daily price guide pipeline
2. Twice-monthly product catalog pipeline
3. Manual collection import pipeline

This separation reflects the nature of the source data:

```text
price guide changes daily
product catalogs change mainly when new products are added
personal collection files are imported manually
```

The MVP focuses on reliable ingestion, raw file archiving, historical price storage, simple validation, and BI-ready data modeling.

---

# Pipeline Goals

The ETL pipeline should:

```text
Use official Cardmarket downloadable JSON files as the trusted source.
Archive raw files before transformation, without silently overwriting them.
Store the full daily price guide, not only selected products.
Combine singles and non-singles into one unified product catalog.
Build historical price data by saving daily snapshots.
Support data quality checks with clear failure vs. warning behavior.
Keep the project simple enough for a realistic GitHub portfolio.
Avoid browser scraping, Selenium, login automation, and seller automation.
```

---

# Database Platform

The project targets **Postgres via Supabase (free tier)**. This is a concrete implementation detail rather than a documentation nuance, because it settles a few things earlier drafts left conditional:

```text
Upserts for products (by id_product) and price_snapshots (by snapshot_date +
  id_product) use Postgres's native
    INSERT ... ON CONFLICT (...) DO UPDATE ...
  syntax.

The partial unique index on watchlist (one active row per id_product) is
  fully supported and is a firm MVP requirement, not a conditional fallback
  to application-level enforcement.

UUID primary keys use Postgres's built-in gen_random_uuid() (pgcrypto,
  enabled by default on Supabase) rather than requiring an external UUID
  library.
```

Two free-tier-specific things worth handling explicitly in `src/config` and the GitHub Actions workflows, since they can otherwise fail silently rather than raising a clear error:

```text
Connection pooling:
  GitHub Actions runs are short-lived processes. DATABASE_URL should use
  Supabase's pooled connection string (Supavisor, transaction mode) rather
  than the direct connection, so a hung or overlapping run doesn't exhaust
  the free tier's limited connection count.

Free-tier project pausing:
  Supabase pauses inactive free-tier projects after a period with no
  activity (on the order of a week). The daily pipeline's regular writes
  should prevent this in practice, but a paused project would otherwise
  fail the daily workflow with a connection error rather than a clear
  "project paused" message — worth a one-line note in operational
  documentation so this isn't mistaken for a pipeline bug the first time
  it happens.
```

RLS (row-level security) does not need special handling for the MVP: the pipeline connects with its own database credentials (not the anon/public client key), so it is unaffected by RLS policies applied to tables intended for client-side access. This is called out only so nobody troubleshoots a write failure by assuming RLS is the cause without checking the credential type first.

## Two Supabase projects: dev and prod

The free tier allows two active projects per organization at no cost, and the project uses both of them deliberately rather than sharing one project between development and the real scheduled pipelines:

```text
prod project:  written to only by the scheduled GitHub Actions workflows
               (and manual reruns of them). This is the historical dataset
               that must not be lost or corrupted.

dev project:   used for all local development and manual testing of
               ingestion/transform/load/collection/analytics code. The same
               sql/schema/ files are applied here too. Safe to break,
               reset, or reload from a backup at any time.
```

Both projects run the identical schema. `DATABASE_URL` in a local `.env` points at the **dev** project; the `DATABASE_URL` GitHub Actions secret points at the **prod** project. These are two different values that happen to share a variable name in two different places — never the same string in both.

## Backing up the prod project

The free tier has no automated backups of any kind (Supabase's own guidance for free-tier projects is to self-manage this via `pg_dump`). This is a real requirement, not an optional nice-to-have, given the project's stated priority of not losing price guide history:

```text
Tool:        pg_dump (Postgres client tools — not the Supabase CLI, which
             pulls a large Docker image and is unnecessarily slow for this
             on a GitHub Actions runner)

Connection:  the SESSION pooler connection string, not the transaction
             pooler used by DATABASE_URL for normal pipeline runs — pg_dump
             needs full session semantics that the transaction pooler
             doesn't support. Kept as a separate variable,
             DATABASE_URL_BACKUP, pointed at the prod project.

Recommended flags: --clean --if-exists --no-owner --no-privileges
             (produces a dump that can be restored cleanly into a fresh
             project, e.g. if prod ever needed to be rebuilt from scratch)

Output:      gzip the .sql dump; never commit it or DATABASE_URL_BACKUP to
             Git. Store locally in db/backups/ and sync that folder
             somewhere off-machine (a cloud-synced folder is enough at this
             scale — no need for dedicated object storage).

Cadence:     weekly is reasonable for the MVP. Daily price data can be
             reprocessed from the raw archive if ever needed (see
             Reprocessing, above); collection data cannot be regenerated
             the same way, which is the main thing a backup actually
             protects here.
```

Restoring is the same idea in reverse (`psql "$DATABASE_URL_BACKUP" < backup.sql`) against either the same project or, as a restore drill, the dev project. A backup that has never been restored from is unverified, not proven.

---

# Source Files

The project uses three official Cardmarket Pokémon JSON files:

```text
products_singles_6.json
products_nonsingles_6.json
price_guide_6.json
```

Main relationship key:

```text
id_product
```

---

# Pipeline Frequency

## Daily

The daily pipeline processes:

```text
price_guide_6.json
```

This file is archived and loaded every day because it represents the daily market price snapshot.

## Weekly

The catalog pipeline processes:

```text
products_singles_6.json
products_nonsingles_6.json
```

These files are downloaded weekly because the product catalog changes much less frequently than price data, but weekly still keeps metadata reasonably fresh without daily downloads. This cadence is a project decision, not a Cardmarket-imposed schedule, and was changed from an original twice-monthly (1st/15th) plan to weekly during implementation (see `DECISIONS.md` §11 in the code repository).

Recommended MVP schedule:

```text
every Friday
```

The exact schedule can be adjusted again later if catalog changes need to be captured even more (or less) often.

## Manual / User-Triggered

The collection import pipeline processes:

```text
CSV or Excel collection files
```

This pipeline is not scheduled. It is triggered when collection data needs to be imported.

---

# Raw Archive Strategy

Raw Cardmarket JSON files are archived before transformation.

The archive keeps original downloaded files unchanged so that the pipeline can be audited and historical files can be reprocessed later if transformation logic changes.

The archive uses flat folders with dated filenames.

## Price Guide Archive

**Corrected in v0.5** (see `DECISIONS.md` §3 in the code repository): the
folder structure below is the actual, already-provisioned flat layout —
`price_guides/` and `product_catalogs/` sit directly at the FTP account
root (`FTP_REMOTE_DIR`), not nested under a `/raw/cardmarket/pokemon/`
path. The original nested design was written before the FTP account was
provisioned and was never actually built; the implementation followed the
real server layout instead of the other way around.

Daily price guide files are stored in one folder:

```text
{FTP_REMOTE_DIR}/price_guides/
```

File naming pattern:

```text
price_guide_6_YYYY-MM-DD.json
```

Example:

```text
{FTP_REMOTE_DIR}/price_guides/price_guide_6_2026-07-03.json
```

The date in the filename should match the `snapshot_date` stored in the database.

Recommended MVP rule:

```text
YYYY-MM-DD = pipeline run date in Europe/Vienna timezone, for every run
including manual reruns and backfills. There is no exception case.
```

## Product Catalog Archive

Product catalog files are stored in one folder:

```text
{FTP_REMOTE_DIR}/product_catalogs/
```

File naming patterns:

```text
products_singles_6_YYYY-MM-DD.json
products_nonsingles_6_YYYY-MM-DD.json
```

Example:

```text
{FTP_REMOTE_DIR}/product_catalogs/products_singles_6_2026-07-01.json
{FTP_REMOTE_DIR}/product_catalogs/products_nonsingles_6_2026-07-01.json
{FTP_REMOTE_DIR}/product_catalogs/products_singles_6_2026-07-08.json
{FTP_REMOTE_DIR}/product_catalogs/products_nonsingles_6_2026-07-08.json
```

(Dates above reflect the weekly/Friday cadence — see "Weekly" under
Pipeline Frequency.)

Singles and non-singles are stored in the same `product_catalogs` folder because the filename already contains:

```text
source type
Cardmarket game/category ID
archive date
```

This keeps the FTP archive simple and easy to index.

## Final Raw Archive Structure

```text
{FTP_REMOTE_DIR}/
  price_guides/
    price_guide_6_2026-07-03.json
    price_guide_6_2026-07-04.json
    price_guide_6_2026-07-05.json

  product_catalogs/
    products_singles_6_2026-07-01.json
    products_nonsingles_6_2026-07-01.json
    products_singles_6_2026-07-08.json
    products_nonsingles_6_2026-07-08.json
```

## Archive Immutability and Reruns

Raw archive files should be treated as immutable source data. The MVP follows these rules:

```text
Do not edit archived raw files.
Do not normalize archived raw files.
Do not manually clean archived raw files.
Do not silently overwrite an existing dated archive file.
```

**Rerun rule:**

```text
If a pipeline for a given date is rerun and the canonical dated file already
exists, the rerun does NOT overwrite it. Instead, the rerun is saved as a
suffixed copy:

price_guide_6_2026-07-03.json            (first run of the day)
price_guide_6_2026-07-03_rerun-01.json   (first rerun)
price_guide_6_2026-07-03_rerun-02.json   (second rerun, if needed)

The same pattern applies to product catalog files:

products_singles_6_2026-07-15.json
products_singles_6_2026-07-15_rerun-01.json
```

**Canonical file for database loading:**

```text
The canonical file for a given date is the most recent successful run for
that date: the highest-numbered rerun file if one exists, otherwise the base
(non-suffixed) file. The database always loads from the canonical file, so a
rerun that corrects bad data takes effect, while the original attempt is
still preserved on disk for audit and debugging.
```

**Why this replaces plain overwrite:**

```text
An earlier draft of this design allowed same-day reruns to silently replace
the existing file, which conflicted with the stated immutability rule — if
Cardmarket's price guide changes intra-day and the pipeline is rerun, the
first version would be lost with no trace it existed. Rerun-suffixed files
resolve this: nothing is ever silently discarded, and "immutable" applies
uniformly to every file that lands in the archive, including reruns.
```

## Archive Gaps

```text
If a day is missed entirely (download failure, outage, skipped run with no
rerun), the archive simply has no file for that date. This is treated as an
accepted, documented data quality limitation, not something the pipeline
attempts to backfill automatically. The MVP does not assume a missed
Cardmarket snapshot can be recovered after the fact. Gaps are surfaced
through archive completeness checks (see Data Quality Checks) and documented
in the project's known limitations, not silently ignored.
```

---

# Daily Price Guide Pipeline

The daily pipeline runs once per day.

Input:

```text
price_guide_6.json
```

Archive output:

```text
{FTP_REMOTE_DIR}/price_guides/price_guide_6_YYYY-MM-DD.json
(or a _rerun-NN suffixed file if this is a rerun for that date)
```

Database output:

```text
price_snapshots
```

## Daily Pipeline Steps

```text
1. Start scheduled GitHub Actions run.
2. Download official price_guide_6.json.
3. Assign snapshot_date using Europe/Vienna date.
4. Archive raw file as price_guide_6_YYYY-MM-DD.json, or as a rerun-suffixed
   copy if a file for that date already exists.
5. Validate JSON structure.
6. Validate required fields.
7. Normalize field names.
8. Insert or upsert rows into price_snapshots from the canonical file for
   that date.
9. Run data quality checks (see thresholds below).
10. Expose updated data through BI views.
```

## Price Guide Transformation

The source file contains hyphenated holo fields.

Cardmarket source fields:

```text
avg-holo
low-holo
trend-holo
avg1-holo
avg7-holo
avg30-holo
```

Database fields:

```text
avg_holo
low_holo
trend_holo
avg1_holo
avg7_holo
avg30_holo
```

This normalization makes the fields easier to query in SQL.

## Price Snapshot Date Logic

The MVP uses:

```text
snapshot_date = pipeline run date in Europe/Vienna timezone
```

The same date is used in:

```text
price_guide_6_YYYY-MM-DD.json
```

and:

```text
price_snapshots.snapshot_date
```

This makes the raw archive and database rows easy to connect.

If reliable source metadata is available later, it can be stored separately as:

```text
source_created_at
```

## Price Snapshot Load Logic

The `price_snapshots` table stores one row per product per snapshot date.

Unique row definition:

```text
snapshot_date + id_product
```

Recommended MVP loading strategy:

```text
upsert by snapshot_date + id_product
```

This makes the pipeline idempotent. If the same daily pipeline is rerun for the same date — reading from the canonical archive file — it overwrites the existing row values for that date rather than creating duplicates or failing.

---

# Weekly Product Catalog Pipeline

The product catalog pipeline runs weekly, every Friday. (Changed from an
original twice-monthly plan during implementation — see `DECISIONS.md`
§11 in the code repository.)

Inputs:

```text
products_singles_6.json
products_nonsingles_6.json
```

Archive outputs:

```text
{FTP_REMOTE_DIR}/product_catalogs/products_singles_6_YYYY-MM-DD.json
{FTP_REMOTE_DIR}/product_catalogs/products_nonsingles_6_YYYY-MM-DD.json
(or rerun-suffixed copies if files for that date already exist)
```

Database output:

```text
products
```

## Product Catalog Pipeline Steps

```text
1. Start scheduled GitHub Actions run.
2. Download products_singles_6.json.
3. Download products_nonsingles_6.json.
4. Assign catalog_archive_date using Europe/Vienna date.
5. Archive both raw files with dated filenames (or rerun-suffixed copies).
6. Validate both JSON files.
7. Add product_group to each row.
8. Add source_file to each row.
9. Combine singles and non-singles.
10. Check for duplicate id_product values.
11. Upsert products into the products table from the canonical files.
12. Update is_active_in_catalog.
13. Detect newly added products.
14. Re-check any collection_import_staging rows with match_status =
    waiting_for_product against the refreshed products table.
15. Run product catalog data quality checks.
```

## Product Transformation Logic

Rows from:

```text
products_singles_6.json
```

receive:

```text
product_group = single
source_file = products_singles_6.json
```

Rows from:

```text
products_nonsingles_6.json
```

receive:

```text
product_group = non_single
source_file = products_nonsingles_6.json
```

Both datasets are then combined into one unified `products` table.

## Product Catalog Update Logic

The `products` table should not be fully replaced.

Instead, it should be updated through upsert logic.

For products found in the latest catalog files:

```text
insert if new
update name/category fields if changed
set is_active_in_catalog = true
update last_seen_at
```

For products already in the database but missing from the latest catalog files:

```text
set is_active_in_catalog = false immediately (no grace period / no N-miss
  tolerance in MVP)
```

Products should not be deleted only because they disappear from the latest catalog.

Historical price rows and collection items may still reference them, and remain valid.

## Product Deduplication Rule

Expected source behavior:

```text
id_product should be unique across combined singles and non-singles catalog files
```

The pipeline should still check this.

If duplicate `id_product` values are found:

```text
same data:
    keep one row and log warning

conflicting data:
    fail the catalog pipeline or mark for manual review
```

Recommended MVP rule:

```text
fail on conflicting duplicate id_product
```

This keeps the unified product catalog reliable.

---

# Relationship Between Daily Prices and Product Catalog

The daily price guide pipeline does not download the product catalog every day.

Instead:

```text
daily price guide uses the latest available products table
```

This keeps the daily pipeline lightweight and avoids unnecessary catalog downloads.

Because the product catalog is refreshed only weekly (every Friday), a daily price guide may sometimes contain `id_product` values that are not yet present in the local `products` table.

This should be treated as a data quality warning, not necessarily as a fatal error.

Possible reason:

```text
Cardmarket added a new product after the last local catalog refresh.
```

The next product catalog refresh should usually resolve this — including automatically re-checking any `collection_import_staging` rows that were waiting on that product (see `waiting_for_product` below).

---

# Foreign Key Recommendation for MVP

For the first MVP, avoid a strict foreign key from:

```text
price_snapshots.id_product
```

to:

```text
products.id_product
```

Instead:

```text
products.id_product is the primary key
price_snapshots.id_product is indexed
the relationship is documented logically
data quality checks detect missing products
```

Reason:

Price guide files and product catalog files may not be perfectly synchronized, especially when product catalogs are downloaded less frequently.

This is more tolerant of real source data behavior.

A strict foreign key can be added later after observing the data for a while.

---

# Validation Rules

## Product Files

For both product catalog files, expected fields are:

```text
id_product
name
id_category
category_name
id_expansion
id_metacard
date_added
```

Minimum MVP validation:

```text
file exists
file is valid JSON
file is not empty
id_product exists
name exists
```

Other fields may be nullable.

## Price Guide File

Expected fields:

```text
id_product
id_category
avg
low
trend
avg1
avg7
avg30
avg-holo
low-holo
trend-holo
avg1-holo
avg7-holo
avg30-holo
```

Minimum MVP validation:

```text
file exists
file is valid JSON
file is not empty
id_product exists
```

Price fields may be null.

---

# Load Order

The catalog pipeline and price pipeline are separate, but when both run on the same day, recommended order is:

```text
1. Product catalog pipeline
2. Daily price guide pipeline
```

Reason:

If new products appear in both files, the product catalog is updated before the price snapshot is loaded.

However, the daily price guide pipeline should still be able to run independently using the latest available `products` table.

---

# Data Quality Checks

Data quality checks should run after each pipeline.

They make the project stronger as a BI/data engineering portfolio project, and they are the mechanism that turns "we tolerate mismatches" into something actually observable.

## Failure vs. Warning: MVP Thresholds

Not every irregularity should stop the pipeline. The MVP draws the line as follows.

**Always a failure (pipeline run marked failed, no data loaded/committed):**

```text
required source file could not be downloaded
raw file archiving failed
file is not valid JSON
file is empty / zero records parsed
a required field (id_product, and name for catalogs) is missing on a row
FTP/archive upload failed
database connection failed
database load/transaction failed
duplicate (snapshot_date, id_product) remaining after upsert
conflicting duplicate id_product within a combined catalog load
one catalog file (singles or non-singles) succeeds while the other fails
```

**Warning (pipeline run marked "success with warnings," data still loaded):**

```text
price rows with no matching product in the products table
id_category mismatch between price_snapshots and products for the same id_product
new id_product values appearing in the price guide that aren't in products yet
products with no latest price data
record count differs from the previous successful run by more than 20%
```

```text
The 20% record-count threshold is an MVP sanity check, not a statistically
derived figure, and can be adjusted after observing real data volumes. It
requires knowing the previous successful run's row count, which is read
directly from the database (e.g. count of price_snapshots for the most
recent prior snapshot_date) rather than from a dedicated pipeline-state
table — see docs/07-github-actions-logic.md, which resolves this the same
way. A dedicated pipeline_runs/archive_manifest table is a reasonable later
improvement, not an MVP requirement.
```

This threshold table is the authoritative definition of failure vs. warning for both pipelines below; the per-pipeline check lists describe *what* is measured, and this section decides *what it means*.

## Daily Price Guide Checks

Recommended checks:

```text
Was price_guide_6.json downloaded?
Was it archived with the correct date (canonical or rerun-suffixed)?
Is the file valid JSON?
How many price rows were loaded?
How many duplicate snapshot_date + id_product rows exist?
How many rows have missing id_product?
How many rows have trend and avg30 both missing?
How many price rows have no matching product in the products table?
How many products have no latest price?
Does the loaded row count differ from the previous successful run by more
  than 20%?
```

Example summary:

```text
Daily price pipeline summary

Date: 2026-07-03

Raw archive:
- price_guide_6_2026-07-03.json: OK

Prices:
- price rows loaded: 70,000
- rows without matching product: 14
- rows with missing trend and avg30: 480

Status: success with warnings
```

## Product Catalog Checks

Recommended checks:

```text
Were both catalog files downloaded?
Were both catalog files archived with the correct date (canonical or
  rerun-suffixed)?
Are both files valid JSON?
How many singles were loaded?
How many non-singles were loaded?
How many total active products exist?
How many new products were detected?
How many products became inactive?
How many duplicate id_product values were found, and were any conflicting?
How many products are missing name?
How many collection_import_staging rows moved out of waiting_for_product
  as a result of this run?
```

Example summary:

```text
Product catalog pipeline summary

Date: 2026-07-15

Raw archive:
- products_singles_6_2026-07-15.json: OK
- products_nonsingles_6_2026-07-15.json: OK

Products:
- singles loaded: 65,000
- non-singles loaded: 8,000
- total active products: 73,000
- new products detected: 120
- products marked inactive: 4
- staging rows resolved from waiting_for_product: 7

Status: success
```

## Collection Integrity Check (Informational)

A sixth check, `check_invalid_collection_items`, is a lightweight sanity check over `collection_items` rather than part of either scheduled pipeline — it's meant to be run after a collection import, or periodically, not on the daily/twice-monthly schedule. It never blocks anything and isn't part of the failure/warning thresholds above; it's informational, surfaced the same way a warning would be.

```text
is_graded = true but grading_company or grade is null (grading isn't part of
  the MVP import flow, so this would only happen from a manual edit)
is_sold = true but sold_price or sold_date is null, or the reverse
  (sold_price/sold_date populated while is_sold = false)
purchase_price or sold_price is negative
purchase_date or sold_date is in the future
```

This complements, rather than duplicates, the import-time safety rules in `08-collection-import-flow.md` — those prevent bad *staging* rows from becoming `collection_items` in the first place; this check catches inconsistencies introduced afterward (e.g. a manual correction in the database).

---

# Failure Handling

## Download Failure

If a required file cannot be downloaded:

```text
do not load transformed data
log the error
mark the pipeline run as failed
keep previous database state unchanged
```

## Archive Failure

If raw file archiving fails:

```text
do not continue with database loading
mark the run as failed
```

Reason:

The project should preserve raw data before transformation.

## Validation Failure

If validation fails:

```text
do not load transformed data
keep the archived raw file for debugging if it was already saved
log validation errors
mark the run as failed
```

## Product Catalog Failure

If one catalog file succeeds and the other fails:

```text
do not update the products table
mark catalog pipeline as failed
```

Reason:

The unified `products` table should be based on both singles and non-singles catalog files.

## Catalog Pipeline Fails Entirely (Scheduled Run Missed or Failed)

```text
the existing products table remains in use as-is (stale, not blocked)
the daily price guide pipeline continues to run normally against it
new id_product values with no product match are reported as warnings, same as
  any other day
the catalog workflow can be manually rerun before the next scheduled date
if it is not manually rerun, catalog refresh simply waits until the next
  scheduled date (the following Friday) — there is no automatic retry in the MVP
```

```text
This is an explicit decision, not a silent gap: the MVP accepts a stale
catalog for up to roughly a week (down from roughly two weeks under the
original twice-monthly schedule) rather than building automatic retry
logic. GitHub Actions supports manual re-triggering of a failed workflow if
faster recovery is needed.
```

## Price Guide Failure

If the price guide file fails:

```text
do not create a price snapshot for that date
mark daily price pipeline as failed
```

The previous snapshot remains available for BI views. The resulting gap in the archive/snapshot timeline is treated as an accepted data quality limitation (see "Archive Gaps" above), not something requiring backfill.

## Database Load Failure

Daily price snapshot loading should be transaction-safe where possible.

Recommended rule:

```text
either the full daily snapshot is inserted/upserted
or the load is rolled back
```

This prevents half-loaded daily snapshots.

---

# Idempotency

Idempotency means:

```text
running the same pipeline twice for the same date should not create duplicate data or break the database
```

Recommended MVP idempotency rules:

```text
price guide archive:
    same date produces the same canonical filename; a rerun for an existing
    date produces a rerun-suffixed file instead of overwriting

product catalog archive:
    same rule as above, applied to both catalog files

products:
    upsert by id_product

price_snapshots:
    upsert by snapshot_date + id_product, loaded from the canonical file for
    that date

collection_import_staging:
    use import_batch_id; additionally, if external_id is present on a row, it
    is used to prevent importing the same source row twice across batches

collection_items:
    only import staging rows that are ready_to_import and not already
    imported; rows without an external_id are not auto-deduplicated against
    existing items, since identical physical cards are legitimately separate
    rows — instead, likely duplicates are surfaced as a warning for manual
    review
```

This is important because GitHub Actions jobs can be rerun manually.

---

# Reprocessing From the Raw Archive (Sketch)

Full reprocessing automation is not built in the MVP, but the raw archive is deliberately structured to make it possible later. A future reprocess flow would look like:

```text
For price snapshots:
  1. select an archived price_guide_6_YYYY-MM-DD.json (or a date range)
  2. read the raw JSON directly from the archive (no re-download needed)
  3. run the current validation and transformation logic against it
  4. upsert the result into price_snapshots by (snapshot_date, id_product)
  5. run the standard data quality checks
  6. compare loaded counts against the original load, if available

For products:
  1. select an archived products_singles/products_nonsingles pair for a
     given catalog date
  2. run current transformation logic (product_group/source_file enrichment)
  3. upsert into products by id_product
```

```text
Reprocessing reuses raw files; it never mutates them. This is the entire
reason the archive is kept in the first place — if a bug is found in the
transformation logic, historical data can be corrected by replaying the
archive, rather than being permanently wrong.
```

---

# Collection Import Pipeline

The collection import pipeline is separate from the scheduled Cardmarket pipelines.

It is user-triggered, not daily.

Input:

```text
CSV or Excel file
```

Staging output:

```text
collection_import_staging
```

Final output:

```text
collection_items
```

## Collection Import Flow

```text
CSV / Excel file
      ↓
read rows
      ↓
insert raw rows into collection_import_staging
      ↓
validate fields
      ↓
match product (exact id_product → exact name → needs_review)
      ↓
set match_status (including waiting_for_product if matched product doesn't
  exist locally yet)
      ↓
manual review if needed
      ↓
      ├── corrected → re-validate → re-match (loop back up, not terminal)
      ↓
import approved (ready_to_import) rows into collection_items
```

## Collection Import Status Logic

### `ready_to_import`

Use when:

```text
row is valid
matched product exists in products
required fields are acceptable
no blocking errors exist
```

### `needs_review`

Use when:

```text
provided_id_product is missing
product name match is unclear
multiple possible matches exist
match confidence is low
manual confirmation is needed
```

Rows in this state are not terminal: once corrected, they are re-validated and re-matched, moving to `ready_to_import`, `waiting_for_product`, or `error` depending on the outcome.

### `waiting_for_product`

Use when:

```text
a product match was found (matched_id_product is set) but that id_product does
not yet exist in the local products table — the catalog simply hasn't been
refreshed since the product was added on Cardmarket's side
```

This is a timing state, not an error. It is automatically re-checked after the next successful product catalog pipeline run, and moves to `ready_to_import` (or `needs_review` / `error`, if something else is also wrong) at that point.

### `error`

Use when:

```text
provided_id_product is invalid
purchase_price is invalid
purchase_date is invalid
condition value is unknown
language value is unknown
both id_product and product name are missing
```

Like `needs_review`, this is not terminal — once the underlying issue is fixed, the row is re-validated.

### `imported`

Use when:

```text
row was successfully inserted into collection_items
```

---

# BI Views

BI view definitions (fields, purpose, business logic) are maintained as a single source of truth in `03-data-dictionary.md`. This document intentionally does not repeat them, to avoid the two documents drifting apart.

The MVP views are:

```text
vw_latest_prices
vw_collection_current_value
vw_collection_summary
vw_product_price_history
vw_products_without_prices
```

For MVP, these are implemented as normal SQL views: no refresh logic is needed, and they always reflect the current underlying tables.

---

# MVP Pipeline Components

The project can later organize code around these conceptual components:

```text
download_price_guide
download_product_catalogs
archive_price_guide
archive_product_catalogs
validate_price_guide
validate_product_catalogs
transform_price_guide
transform_product_catalogs
load_price_snapshots
load_products
run_price_data_quality_checks
run_product_data_quality_checks
import_collection_file
match_collection_staging_rows
recheck_waiting_for_product_rows
load_collection_items
```

---

# MVP Scope

## In MVP

```text
daily price guide download
daily price guide raw archive (with rerun-suffixed files, not overwrites)
daily full price snapshot loading
twice-monthly product catalog download
twice-monthly product catalog raw archive (with rerun-suffixed files)
unified products table
basic JSON validation
field normalization
upsert logic
data quality checks with defined failure/warning thresholds
manual collection CSV/Excel import through staging, including
  waiting_for_product handling
BI-ready views (defined in the data dictionary)
```

## Not in MVP

```text
Selenium
browser scraping
Cardmarket login automation
seller price automation
real-time processing
Airflow
Kafka
complex orchestration
machine learning
price prediction
advanced fuzzy matching
alert delivery system
automatic retry of failed scheduled catalog runs
automated archive backfill
full web app
mobile app
multi-user support
```

---

# Final ETL Boundary

```text
Daily price pipeline:
    price_guide_6.json
    → raw archive as price_guide_6_YYYY-MM-DD.json (or rerun-suffixed copy)
    → validation
    → field normalization
    → price_snapshots (upsert by snapshot_date + id_product)
    → data quality checks (failure/warning thresholds)
    → BI views

Twice-monthly catalog pipeline:
    products_singles_6.json + products_nonsingles_6.json
    → raw archive as dated catalog files (or rerun-suffixed copies)
    → validation
    → product_group/source_file enrichment
    → unified products table (upsert by id_product)
    → recheck waiting_for_product staging rows
    → product data quality checks

Manual collection pipeline:
    CSV/Excel
    → collection_import_staging
    → validation/matching (exact id_product → exact name → needs_review)
    → match_status (ready_to_import / needs_review / waiting_for_product / error)
    → collection_items
    → valuation views
```

The MVP intentionally keeps the system focused: official source files, raw archive, historical snapshots, unified product catalog, collection import, and BI-ready outputs.
