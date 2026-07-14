# GitHub Actions Logic Concept

## Document Version

```text
Version: 0.6
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial GitHub Actions logic concept |
| 0.2 | 2026-07-04 | Fixed the same-date overwrite rule to match the rerun-suffix decision in docs 04/05 (this doc previously reintroduced the contradiction those docs resolved), added the `waiting_for_product` recheck step, aligned the record-count warning threshold with doc 04, added explicit catalog-failure behavior, unified "pipeline run metadata table" naming with doc 05's `archive_manifest`, and added an explicit Europe/Vienna timezone requirement for GitHub Actions runners, based on architecture review |
| 0.3 | 2026-07-04 | Added Supabase-specific `DATABASE_URL` guidance (pooled connection, service credential over anon key), confirming Postgres/Supabase as the target database |
| 0.4 | 2026-07-05 | Confirmed the dev/prod Supabase project split (`DATABASE_URL` differs by context — dev locally, prod in GitHub Actions secrets); added `DATABASE_URL_BACKUP` secret for manual backups; noted a third, optional `backup-database.yml` workflow (weekly, lower urgency than the two data-critical workflows) |
| 0.5 | 2026-07-12 | Implementation-time corrections, all logged in `DECISIONS.md` in the code repository: (1) renamed the `FTP_PASSWORD`/`FTP_REMOTE_PATH` secrets to the real, already-provisioned `FTP_PASS`/`FTP_REMOTE_DIR` (§7); (2) changed the product catalog workflow's cadence from twice-monthly (1st/15th) to weekly, every Friday (§11) — a genuine decision change, not an error fix; (3) added optional `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` secrets for pipeline success/failure notifications, added to both workflows (§10). |
| 0.6 | 2026-07-14 | Renamed all field-name references from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `snapshotDate` → `snapshot_date`), matching the project-wide database naming decision in `02-data-model.md` v0.5 / `03-data-dictionary.md` v0.5. Field names here are references, not definitions, so only spelling changed. `FTP_PASS`/`FTP_REMOTE_DIR`/`DATABASE_URL`/etc. (GitHub Actions secrets, all-caps by convention) are untouched — this rename applies to database field names only. |

## Purpose

GitHub Actions is used as the automation layer for the project.

The main purpose of GitHub Actions in the MVP is to make sure that Cardmarket data is downloaded and archived consistently without manual work.

This is especially important for the daily price guide.

Cardmarket provides the Pokémon price guide as a current daily snapshot file, not as a complete historical database. Because of that, the project can only build price history by saving each daily file over time.

The most important automation goal is:

```text
Do not miss daily price guide snapshots.
```

If the project does not archive `price_guide_6.json` on a given day, that day's historical price data may be permanently missing.

For this reason, GitHub Actions is not just a convenience feature. It is part of the historical data collection strategy.

---

## Automation Role in the MVP

The MVP uses GitHub Actions to automatically run scheduled data collection workflows.

GitHub Actions is responsible for:

```text
starting pipelines on schedule
running pipelines without manual interaction
providing secrets and environment variables
showing success or failure status
allowing manual reruns when needed
```

GitHub Actions should not contain all business logic directly inside workflow files.

The workflow files should stay simple and should mostly answer:

```text
When does the pipeline run?
Which command starts the pipeline?
Which secrets are available?
What happens if the pipeline fails?
```

The actual pipeline logic should live in the project source code.

---

## Core Automation Principle

The project separates automation, archive storage, and analytical storage.

```text
GitHub Actions = scheduler and automation layer
FTP server     = persistent raw archive storage
Database       = normalized analytical layer
```

This separation is important.

GitHub Actions runs the workflow, but it is not the long-term data archive.

The FTP server stores the raw downloaded files.

The database stores cleaned and normalized data for analysis, BI views, and collection valuation.

---

## Timezone Requirement for Runners

GitHub Actions runners default to UTC. The project's `snapshot_date` and catalog archive date rules are both defined as **the pipeline run date in the Europe/Vienna timezone, with no exceptions** (see `02-data-model.md` and `03-data-dictionary.md`).

```text
This means the workflow must explicitly convert to Europe/Vienna before
computing a date-based filename or a snapshot_date value. It must not rely on
the runner's local date, since that will silently produce the wrong date
whenever UTC and Europe/Vienna fall on different calendar days near midnight
(for example, a run starting at 23:30 UTC is already the next day in
Europe/Vienna during summer time).

This conversion should happen once, in src/config or src/utils (see
06-github-repository-structure.md), and be reused by both workflows — not
computed ad hoc inside each workflow's steps.
```

This is called out here specifically, separate from the data model docs, because it is the one place where a documentation rule can be silently violated by infrastructure defaults if nobody remembers to handle it in code.

---

## MVP Automation Scope

The MVP uses two scheduled GitHub Actions workflows for the core data pipelines:

```text
daily-price-guide.yml
product-catalog.yml
```

These workflows match the two Cardmarket ingestion flows:

```text
Daily price guide pipeline
Twice-monthly product catalog pipeline
```

The manual collection import pipeline is not automated by GitHub Actions in the MVP.

Collection import depends on user-provided CSV or Excel files and may require manual review before records are moved into `collection_items`.

**A third, optional workflow** — `backup-database.yml` — can automate the manual `pg_dump` backup process described in `04-etl-pipeline-design.md` ("Backing up the prod project"). It's lower urgency than the two above (weekly is enough, versus daily), and can reasonably be added after the core pipelines are stable rather than in the first implementation pass. See "Environment Variables and Secrets" below for its one additional secret.

---

## Workflow 1: Daily Price Guide Pipeline

### File

```text
.github/workflows/daily-price-guide.yml
```

### Schedule

Recommended schedule:

```text
daily
```

This workflow should run automatically once per day.

The exact time can be adjusted later, but the important MVP rule is:

```text
The project should create one canonical archived price guide snapshot per
calendar day, using the Europe/Vienna date.
```

---

## Daily Price Guide Workflow Goal

The daily price guide workflow exists to protect the historical price dataset from gaps.

Source file:

```text
price_guide_6.json
```

Raw archive filename pattern:

```text
price_guide_6_YYYY-MM-DD.json
```

If a file for that date already exists (a rerun), the workflow saves a rerun-suffixed copy instead of overwriting it — see "Archive Immutability and Reruns" below.

Target raw archive folder:

```text
{FTP_REMOTE_DIR}/price_guides/
```

Target database table:

```text
price_snapshots
```

The main success condition is:

```text
One canonical archived price guide file exists for every calendar day after
the project starts collecting data.
```

Example archive result:

```text
{FTP_REMOTE_DIR}/price_guides/
  price_guide_6_2026-07-01.json
  price_guide_6_2026-07-02.json
  price_guide_6_2026-07-03.json
```

---

## Daily Price Guide Workflow Responsibilities

The daily price guide workflow should perform the following high-level steps:

```text
1. Start scheduled workflow
2. Compute snapshot_date using the Europe/Vienna timezone
3. Download current price_guide_6.json
4. Save raw file with dated filename, or a rerun-suffixed copy if a file for
   that date already exists
5. Upload raw file to FTP archive
6. Validate downloaded file
7. Normalize field names
8. Load records into price_snapshots from the canonical file for that date
9. Run data quality checks
10. Report success, warning, or failure status
```

The raw archive step should happen before transformation.

This guarantees that the original source file is preserved even if validation, transformation, or database loading fails later.

---

## Daily Price Guide Workflow Logic

The daily workflow should follow this logical flow:

```text
Compute snapshot_date (Europe/Vienna)
→ download official Cardmarket price guide
→ save unchanged raw JSON archive (canonical filename, or rerun-suffixed
  copy if one already exists for that date)
→ upload raw archive file through FTP
→ validate JSON structure
→ normalize Cardmarket field names
→ insert or upsert daily price snapshot records from the canonical file
→ run basic quality checks
```

The workflow should not rely on manual downloads.

Manual downloads may still be useful for:

```text
testing
debugging
emergency reruns
checking the current source file manually
```

But manual downloading should not be the main data collection method.

The project should assume that if a daily file is not archived automatically, the historical dataset may have a permanent gap.

---

## Daily Archive Completeness

Daily archive completeness means that the project can verify whether a price guide file exists for every expected date.

Expected archive pattern:

```text
price_guide_6_YYYY-MM-DD.json
```

Example:

```text
price_guide_6_2026-07-01.json
price_guide_6_2026-07-02.json
price_guide_6_2026-07-03.json
```

A later data quality check can compare the expected calendar dates with existing archive files.

Example logic:

```text
For every date between the first project run date and today:
  check whether a canonical price_guide_6_YYYY-MM-DD.json (or a
  rerun-suffixed variant) exists
```

If a file is missing, the project should report the missing date clearly.

This does not automatically restore missing data — the MVP does not assume a missed Cardmarket snapshot can be recovered later, since Cardmarket only exposes a current daily file, not history. This is an accepted and documented limitation (see `05-raw-archive-strategy.md`), not something the check is expected to fix.

For the MVP, this can start as a simple check or documented quality rule. It does not need to be a complex monitoring system.

---

## Workflow 2: Product Catalog Pipeline

### File

```text
.github/workflows/product-catalog.yml
```

### Schedule

Recommended schedule:

```text
weekly
```

Suggested day:

```text
every Friday
```

Changed from an original twice-monthly (1st/15th) plan during
implementation — see `DECISIONS.md` §11 in the code repository. The
product catalog still changes far less frequently than prices, so daily
catalog downloads remain unnecessary; weekly was chosen as fresher than
twice-monthly without adding meaningful storage/processing cost.

**If a scheduled Friday run fails:** the catalog remains stale and the existing `products` table stays in use as-is. The daily price guide pipeline continues to run normally against it — new `id_product` values with no match are reported as a warning, the same as on any other day. The catalog workflow can be manually rerun before the next scheduled date; if it isn't, catalog refresh simply waits until the next Friday. There is no automatic retry built into the MVP. This is an explicit decision to accept up to roughly a week (down from roughly two weeks under the original twice-monthly schedule) of a stale catalog rather than build retry logic, matching the failure-handling rule in `04-etl-pipeline-design.md`.

---

## Product Catalog Workflow Goal

The product catalog workflow keeps product metadata reasonably fresh.

Source files:

```text
products_singles_6.json
products_nonsingles_6.json
```

Raw archive filename patterns:

```text
products_singles_6_YYYY-MM-DD.json
products_nonsingles_6_YYYY-MM-DD.json
```

If files for that date already exist (a rerun), the workflow saves rerun-suffixed copies instead of overwriting them.

Target raw archive folder:

```text
{FTP_REMOTE_DIR}/product_catalogs/
```

Target database table:

```text
products
```

The product catalog pipeline supports the price history pipeline by maintaining local product metadata for `id_product` values. It also unblocks any `collection_import_staging` rows that were waiting on a product that hadn't been catalogued yet.

---

## Product Catalog Workflow Responsibilities

The product catalog workflow should perform the following high-level steps:

```text
1. Start scheduled workflow
2. Compute the catalog archive date using the Europe/Vienna timezone
3. Download products_singles_6.json
4. Download products_nonsingles_6.json
5. Save both raw files with dated filenames, or rerun-suffixed copies if
   files for that date already exist
6. Upload both raw files to FTP archive
7. Validate downloaded files
8. Add product_group and source_file metadata
9. Load records into unified products table from the canonical files
10. Recheck collection_import_staging rows with match_status =
    waiting_for_product against the refreshed products table
11. Run product data quality checks
12. Report success, warning, or failure status
```

---

## Product Catalog Workflow Logic

The product catalog workflow should follow this logical flow:

```text
Compute catalog archive date (Europe/Vienna)
→ download official Cardmarket product catalog files
→ save unchanged raw JSON archive files (canonical filenames, or
  rerun-suffixed copies if ones already exist for that date)
→ upload raw archive files through FTP
→ validate JSON structure
→ enrich records with product_group and source_file
→ upsert records into products from the canonical files
→ update catalog activity metadata
→ recheck waiting_for_product staging rows
→ run basic quality checks
```

The two catalog files are loaded into one unified `products` table.

The pipeline enriches each record with:

```text
product_group
source_file
is_active_in_catalog
first_seen_at
last_seen_at
updated_at
```

If singles load successfully but non-singles fails (or vice versa), the `products` table is not updated at all and the workflow fails — a unified catalog built from only one of the two source files is considered worse than a stale-but-consistent one. This matches the catalog failure rule in `04-etl-pipeline-design.md`.

---

## Recommended Execution Order

On days when both workflows run, the product catalog workflow should run before the daily price guide workflow.

Recommended order:

```text
1. product-catalog.yml
2. daily-price-guide.yml
```

Reason:

The price guide may contain new `id_product` values. Running the product catalog pipeline first increases the chance that product metadata already exists before daily price records are loaded.

This does not fully eliminate missing product metadata, but it reduces the issue. The daily price guide workflow must still be able to run independently and successfully even when the product catalog workflow has not run that day, or has failed — it always uses whatever `products` table currently exists.

---

## Manual Trigger Support

Both workflows should support manual execution.

This is useful for:

```text
testing the pipeline
rerunning after a failed scheduled run
manually collecting data after project changes
checking configuration changes
```

Manual trigger support is important, but it should not replace scheduled automation.

The daily scheduled workflow remains the primary mechanism for historical price collection.

A manual rerun for a date that already has an archived file produces a rerun-suffixed copy, per the Archive Immutability and Reruns rule below — it never silently replaces the existing file.

---

## Environment Variables and Secrets

GitHub Actions should not contain sensitive values directly in workflow files.

Sensitive values should be stored as GitHub Actions secrets.

Recommended secrets:

```text
FTP_HOST
FTP_USER
FTP_PASS
FTP_REMOTE_DIR

DATABASE_URL
DATABASE_URL_BACKUP   (only needed if backup-database.yml is implemented)

TELEGRAM_BOT_TOKEN    (optional — pipeline success/failure notifications)
TELEGRAM_CHAT_ID      (optional, same as above)
```

**Corrected in v0.5** (see `DECISIONS.md` §7 in the code repository):
`FTP_PASS`/`FTP_REMOTE_DIR` are the real, already-provisioned secret names
— an earlier draft of this doc used `FTP_PASSWORD`/`FTP_REMOTE_PATH`
instead. `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are new, added once
pipeline notifications were built (§10) — unlike the other secrets here,
both are optional: if either is unset, the pipeline simply skips sending a
notification rather than failing.

Recommended non-secret configuration values:

```text
CARDMARKET_PRICE_GUIDE_URL
CARDMARKET_PRODUCTS_SINGLES_URL
CARDMARKET_PRODUCTS_NONSINGLES_URL
PIPELINE_TIMEZONE=Europe/Vienna
```

Depending on the final setup, source URLs can also be stored as secrets or environment variables.

The real credentials should never be committed to the repository.

**Supabase-specific note on `DATABASE_URL`:** the project runs on Postgres via Supabase's free tier, using two separate projects (dev and prod — see `04-etl-pipeline-design.md`). The `DATABASE_URL` **secret** in this repository always points at the **prod** project — the local `.env` value of the same name points at dev instead, and the two should never be swapped. `DATABASE_URL` should be Supabase's pooled connection string (Supavisor, transaction mode), not the direct connection — GitHub Actions runs are short-lived, and a hung or overlapping run against the direct connection can exhaust the free tier's limited connection count. The credential itself should be a database-role/service credential rather than the anon/public client key, since the pipeline writes as itself rather than as an end user and doesn't need to go through RLS-governed client access paths.

**`DATABASE_URL_BACKUP`** is only needed if `backup-database.yml` is implemented, and is deliberately a different connection type than `DATABASE_URL`: the Session Pooler string, since `pg_dump` requires session semantics the transaction pooler doesn't support. See `04`, "Backing up the prod project," for the exact command and flags.

---

## FTP Server Role

The FTP server is used as the persistent raw archive storage for the MVP.

The daily workflow uploads each archived `price_guide_6_YYYY-MM-DD.json` file (or its rerun-suffixed variant) to the FTP server.

This means the FTP server stores the long-term raw history, while GitHub Actions only runs the automation.

The basic architecture is:

```text
GitHub Actions scheduled workflow
→ compute date (Europe/Vienna)
→ download Cardmarket JSON
→ create dated raw archive file, or a rerun-suffixed copy if one exists
→ upload raw file to FTP server
→ load normalized records into database from the canonical file
```

Using FTP is acceptable for the MVP because it is simple, already available, and matches the current project constraints.

The project does not need a full cloud data lake at this stage.

---

## Archive Immutability and Reruns

Raw archive files are treated as immutable: nothing already written to the archive is ever silently edited or replaced.

```text
If a workflow runs for a date that does not yet have an archived file, it
writes the canonical file:

  price_guide_6_2026-07-03.json

If the workflow is rerun for a date that already has a file (whether the
scheduled run is manually retried, or triggered again after a failure), it
does NOT overwrite that file. It writes a rerun-suffixed copy instead:

  price_guide_6_2026-07-03_rerun-01.json
  price_guide_6_2026-07-03_rerun-02.json   (if rerun again)

The same rule applies to both product catalog files.
```

**Canonical file for database loading:**

```text
The canonical file for a given date is the most recent successful run: the
highest-numbered rerun file if one exists, otherwise the base file. The
load step always reads from the canonical file. Superseded files remain on
disk for audit and debugging but are not loaded.
```

An earlier draft of this document said "same-date raw archive files may be overwritten," which directly contradicted the immutability principle stated for the raw archive elsewhere in this same document and in `05-raw-archive-strategy.md`. The rerun-suffix rule above is the resolution: nothing in the archive is ever silently discarded, in workflow behavior as well as in the written policy.

---

## Recommended Failure Behavior

The workflows should fail clearly if an important step fails.

Examples of failure conditions:

```text
source file cannot be downloaded
downloaded file is empty
downloaded file is not valid JSON
required fields are missing
FTP upload fails
database connection fails
database loading fails
critical data quality check fails
one product catalog file succeeds while the other fails
```

The workflow should not silently continue when the data is incomplete or invalid.

For this project, a failed daily price guide workflow is important because it may mean that the historical dataset has a missing day.

---

## Data Quality Checks in GitHub Actions

After loading data into the database, the workflows should run simple quality checks. The authoritative list of checks and their failure/warning classification lives in `04-etl-pipeline-design.md`; the lists below are the subset most directly tied to workflow success/failure reporting.

### Daily price guide checks

Recommended MVP checks:

```text
price guide file exists
price guide file is valid JSON
price guide file contains records
required price fields exist
snapshot_date was computed using Europe/Vienna and loaded correctly
no duplicate snapshot_date + id_product records
number of loaded records is greater than zero
canonical archive file exists for the current date
```

### Product catalog checks

Recommended MVP checks:

```text
products_singles file exists
products_nonsingles file exists
both files are valid JSON
both files contain records
required product fields exist
product_group was assigned
source_file was assigned
products table contains both single and non_single records
collection_import_staging rows with match_status = waiting_for_product were
  rechecked
```

### Cross-checks

Recommended MVP cross-check:

```text
detect price records without matching products
detect id_category mismatches between price_snapshots and products
```

Both should be reported as data quality warnings, not fatal errors.

Reason:

The product catalog is downloaded less frequently than the price guide, so temporary missing product metadata is expected. A category mismatch is a signal for review, not evidence of a load error.

---

## Warnings vs Failures

Not every issue should fail the workflow. This section mirrors the thresholds defined in `04-etl-pipeline-design.md`; both documents should be kept in sync if the thresholds change.

### Failures

The workflow should fail when the pipeline cannot safely continue.

Examples:

```text
download failed
file is empty
JSON is invalid
required fields are missing
FTP upload failed
database loading failed
duplicate snapshot_date + id_product remains after upsert
conflicting duplicate id_product within a combined catalog load
one product catalog file succeeds while the other fails
```

### Warnings

The workflow can finish successfully but report warnings for non-critical issues.

Examples:

```text
some price records do not have matching product metadata
some products do not have prices yet
new product IDs appeared in price guide
id_category mismatch between price_snapshots and products
loaded record count differs from the previous successful run by more than 20%
```

```text
The 20% threshold is an MVP sanity check, not a statistically derived
figure, and can be adjusted after observing real data volumes. Comparing
against "the previous successful run" requires the workflow to read a
small stored value (the last successful run's row count) rather than
recomputing it from scratch each time — see "Pipeline Run Metadata" below.
```

This distinction makes the pipeline more realistic.

Real data pipelines often allow expected data quality warnings while still failing on critical problems.

---

## Pipeline Run Metadata

Two checks above depend on knowing something about previous runs: the 20% record-count comparison, and being able to tell later which archive file was canonical for a given date versus a superseded rerun.

```text
For the MVP, this is the same underlying need referred to as an
"archive_manifest" idea in 05-raw-archive-strategy.md and a "pipeline run
metadata table" idea below — these are one future feature, not two. The MVP
does not build this table. Instead:

  - the previous run's row count can be read directly from the database
    (e.g. count of rows in price_snapshots for the most recent prior
    snapshot_date) rather than stored separately
  - canonical-vs-rerun status is determined by filename convention at load
    time (highest rerun suffix wins), not recorded as queryable data

A dedicated pipeline_runs / archive_manifest table is a natural later
improvement once this filename-convention approach starts to feel
insufficient (see Later Improvements).
```

---

## Logging Expectations

The workflows should print useful progress information.

Recommended log messages:

```text
which pipeline is running
the computed snapshot_date / catalog archive date (Europe/Vienna)
which source file is being downloaded
which archive filename was created (including whether it was a rerun-suffixed copy)
whether FTP upload succeeded
number of records read
number of records loaded
number of warnings found
whether the pipeline finished successfully
```

Logs should not expose secrets.

Do not print:

```text
FTP password
database password
full connection strings
private server credentials
```

---

## Idempotency

The workflows should be safe to rerun for the same date.

For the MVP, this means:

```text
a rerun for a date that already has an archived file produces a
  rerun-suffixed copy, never a silent overwrite
database loading always reads from the canonical file for that date (the
  latest rerun if one exists, otherwise the base file)
price_snapshots is loaded via upsert by snapshot_date + id_product, so
  reprocessing a date's canonical file overwrites that date's rows rather
  than creating duplicates or failing
products is loaded via upsert by id_product
```

This makes manual reruns safer.

If a scheduled run fails and the workflow is started again manually, it should not create duplicate database records, and it should not silently discard the previous attempt's archived file.

---

## Database Loading Expectations

### Price snapshots

The `price_snapshots` table should use the logical uniqueness rule:

```text
snapshot_date + id_product
```

This prevents duplicate daily price records for the same product. Loading is an upsert against this key, reading from the canonical archive file for that date.

### Products

The `products` table should use:

```text
id_product
```

as the primary key.

Product catalog loading should update existing products and insert new ones.

This allows the catalog to evolve over time without creating duplicate products. Loading only proceeds if both the singles and non-singles files were validated successfully; otherwise the table is left unchanged and the workflow fails (see "Product Catalog Workflow Logic" above).

---

## What Happens If a Day Is Missed?

If the daily price guide workflow does not run successfully, the project may miss one daily historical snapshot.

The project should report this clearly.

A missed day should be treated as an archive completeness issue.

For the MVP, the project does not need to automatically recover missing days because the Cardmarket source may no longer provide the old daily file. This is the same "prevent, don't rely on recovering" position taken in `05-raw-archive-strategy.md`.

The realistic goal is:

```text
prevent missed days through scheduled automation
make missing days visible if they happen
allow manual reruns for the current day when needed (as a rerun-suffixed
  archive copy, not an overwrite, if a file for that day already exists)
```

This is a practical and honest MVP approach.

---

## Why Keep Workflow Files Simple?

The GitHub Actions YAML files should not contain all pipeline logic.

They should mostly answer:

```text
When does the pipeline run?
Which environment does it use?
Which command starts the pipeline?
Which secrets are available?
```

The project source code should answer:

```text
How are files downloaded?
How is the run date computed (Europe/Vienna)?
How are archive filenames created, and how are reruns detected?
How are fields validated?
How are records transformed?
How is the database loaded, and from which file (canonical vs. superseded)?
How are data quality checks handled?
```

This separation makes the project easier to test and easier to review.

---

## MVP Scope

The MVP GitHub Actions logic includes:

```text
daily scheduled price guide workflow
weekly (Friday) scheduled product catalog workflow
manual workflow trigger support
Europe/Vienna date computation shared by both workflows
rerun-suffixed archive files instead of silent overwrites
canonical-file resolution for database loading
FTP archive upload
database loading
basic validation
basic data quality checks with defined failure/warning thresholds
daily archive completeness awareness
clear failure behavior, including catalog partial-failure handling
safe rerun logic
waiting_for_product staging recheck after catalog loads
```

The MVP GitHub Actions logic does not include:

```text
complex orchestration framework
Airflow
Dagster
cloud-native data lake jobs
advanced alerting
Slack notifications
multi-environment deployment
automatic dashboard refresh orchestration
machine learning workflows
automatic retry of a failed scheduled catalog run
a dedicated pipeline_runs / archive_manifest table
```

These can be considered later only if the project grows.

---

## Later Improvements

Possible future improvements:

```text
a pipeline_runs / archive_manifest table (unifying the two ideas referenced
  in this document and in 05-raw-archive-strategy.md) recording canonical
  vs. rerun status and per-run record counts as queryable data
workflow notifications
file checksum validation
automated download retry strategy
automatic retry of a failed scheduled catalog run
separate staging database environment
pipeline status dashboard
automatic issue creation on failure
monthly archive health report
daily archive completeness report
```

These are useful future ideas, but they are not required for the MVP.

---

## Design Decision Summary

GitHub Actions is used as a simple scheduler and automation layer.

The project has two workflows:

```text
daily-price-guide.yml
product-catalog.yml
```

The daily workflow is the most important automation in the MVP because it creates the project's historical price dataset.

The weekly (Friday) catalog workflow keeps product metadata reasonably fresh, and unblocks any collection import rows that were waiting on a not-yet-catalogued product.

Both workflows compute their working date in the Europe/Vienna timezone explicitly, rather than relying on the runner's default UTC clock.

Both workflows treat the raw archive as immutable: a rerun never overwrites an existing archived file, it adds a rerun-suffixed copy, and loading always reads from the canonical file for that date.

The FTP server stores the raw archived files. The database stores normalized records for BI and collection valuation.

Both workflows archive raw files first, then validate, transform, load, and run quality checks, with a clear, documented line between what causes a failure and what is only a warning.

This design is realistic, easy to explain, and strong enough for a GitHub data engineering / BI portfolio project.
