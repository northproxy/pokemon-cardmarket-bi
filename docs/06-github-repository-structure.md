# GitHub Repository Structure

## Document Version

```text
Version: 0.7
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial repository structure |
| 0.2 | 2026-07-04 | Clarified status of not-yet-written docs, schema migration approach, transform/load split, test scope, and added a timezone safeguard to `.env.example`, based on architecture review |
| 0.3 | 2026-07-04 | Added `LICENSE` (MIT) to the repository tree so it matches `10-readme-documentation-structure.md`; documented Supabase pooled-connection and service-credential/RLS guidance for `DATABASE_URL` in `.env.example` |
| 0.4 | 2026-07-05 | Added `db/backups/` to the repository tree and `DATABASE_URL_BACKUP` to `.env.example` for the dev/prod Supabase split and manual backup process (see `04-etl-pipeline-design.md`); added `check_invalid_collection_items.sql` to `sql/checks/`; added a Local-Only Folders section documenting the working-folder additions (`data/raw/`, `data/imports/`, `data/exports/`, `logs/`) that exist on disk but are intentionally not part of this repository tree |
| 0.5 | 2026-07-05 | Added `11-local-environment-setup.md` to the docs tree; trimmed this document's own "Local-Only Folders" section to a pointer at the new doc instead of duplicating its content, per the project's own rule against defining the same thing in two places |
| 0.6 | 2026-07-12 | Two corrections to `.env.example`, both logged in `DECISIONS.md` §4 and §7 in the code repository: (1) renamed `FTP_REMOTE_PATH` to `FTP_REMOTE_DIR`, matching the real, already-provisioned GitHub Actions secret name; (2) added the FTP password variable to the listing at all — it was previously entirely absent from this doc's `.env.example` block even though `07-github-actions-logic.md` already listed it as a required secret, and is now included as `FTP_PASS` (also renamed from the `FTP_PASSWORD` originally implied by `07`). Also added optional `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` entries for the pipeline notification feature added during implementation. |
| 0.7 | 2026-07-14 | Renamed all field-name references from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `matchStatus` → `match_status`, `estimatedMarketValue` → `estimated_market_value`), matching the project-wide database naming decision in `02-data-model.md` v0.5 / `03-data-dictionary.md` v0.5. Only field-name mentions changed; folder paths, filenames, and all-caps env var names (`FTP_PASS`, `DATABASE_URL`, etc.) are untouched. |

## Purpose

The repository structure should make the project easy to understand, review, and extend.

This project is not only a script collection. It is a learning-focused data engineering and BI portfolio project. Because of that, the repository should clearly separate:

- documentation
- raw data archive logic
- ingestion pipeline logic
- database models
- collection import logic
- analytics and BI logic
- configuration
- tests or validation checks

The goal is to keep the repository realistic and maintainable without making the MVP look overengineered.

---

## Recommended MVP Repository Structure

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

This structure is enough for the MVP while still showing clear data engineering thinking.

**Note on `docs/08`–`docs/10`:** these files are part of the planned numbered documentation set but may not exist yet at every point in the project's history. If a file in this range is referenced elsewhere before it is written, it should be treated as "planned," not as a broken link — the README's documentation index (see doc 10 once written) should only link to files that actually exist at that point.

---

## Root Files

### `README.md`

The main project entry point.

It should explain:

```text
What the project does
Why the project exists
What data source is used
What the MVP includes
How the pipeline works at a high level
What is already implemented
What is planned later
```

The README should stay readable. Detailed technical explanations should live in the `docs/` folder.

---

### `LICENSE`

MIT License. Chosen because this is a public learning/portfolio project: MIT is permissive, immediately recognizable to anyone browsing the repo, and doesn't restrict later reuse, forking, or rebuilding parts of the pipeline. There's no proprietary logic here that would call for a more restrictive license.

---

### `.gitignore`

The `.gitignore` file prevents sensitive, generated, or large local files from being committed.

It should exclude files such as:

```text
.env
local database files
temporary downloads
logs
cache files
Python virtual environments
large raw data files if they are not meant to be stored in Git
database backup dumps (db/backups/*.sql.gz, *.dump) — see db/ above
```

The raw archive may exist on the server or external storage, but the full archive does not need to be committed to Git. The same applies to database backup dumps: `db/backups/README.md` is committed, the dump files themselves are not.

---

### `.env.example`

This file documents required environment variables without exposing secrets.

Example variables may include:

```text
CARDMARKET_PRICE_GUIDE_URL=
CARDMARKET_PRODUCTS_SINGLES_URL=
CARDMARKET_PRODUCTS_NONSINGLES_URL=

FTP_HOST=
FTP_USER=
FTP_PASS=
FTP_REMOTE_DIR=

DATABASE_URL=
DATABASE_URL_BACKUP=

PIPELINE_TIMEZONE=Europe/Vienna

# Optional — pipeline success/failure notifications (see DECISIONS.md §10
# in the code repository). If either is unset, notifications are skipped
# rather than failing the pipeline.
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

**Corrected in v0.6** (see `DECISIONS.md` §4 and §7 in the code
repository): this block previously used `FTP_REMOTE_PATH` and, separately,
omitted the FTP password variable entirely — a listing gap independent of
naming, since `07-github-actions-logic.md` already documented a required
password secret that never appeared here. The real, already-provisioned
GitHub Actions secrets are `FTP_PASS` and `FTP_REMOTE_DIR`, shown above.

**Why `PIPELINE_TIMEZONE` is listed explicitly:** the data model and ETL design docs define `snapshot_date` as the pipeline run date in the Europe/Vienna timezone, with no exceptions. GitHub Actions runners default to UTC, so this conversion has to be an explicit, enforced step in code — not an assumption baked only into documentation. Listing it here as a required variable makes that dependency visible to anyone setting up the project, and gives the ingestion code one obvious place to read it from instead of hardcoding a timezone string.

**Why `DATABASE_URL` should be the pooled Supabase connection string:** the project targets Postgres via Supabase's free tier. GitHub Actions runs are short-lived, so `DATABASE_URL` should point at Supabase's pooled connection (Supavisor, transaction mode) rather than the direct connection, to avoid exhausting the free tier's limited connection count if a run hangs or overlaps with another. This should also be a database-role/service credential, not the anon/public client key — the pipeline writes as itself, not as an end user, so RLS policies on any client-facing tables don't apply to it and shouldn't be mistaken for the cause of a write failure.

**`DATABASE_URL` points at a different project depending on where it's set.** The project uses two Supabase projects, dev and prod (see `04-etl-pipeline-design.md`). Locally, in your own `.env`, `DATABASE_URL` should point at the **dev** project — safe to break, reset, or reload at any time. In the GitHub Actions secret of the same name, `DATABASE_URL` points at the **prod** project instead. Same variable name, two different values, never mixed up in the same place.

**`DATABASE_URL_BACKUP`** is the Session Pooler connection string (not the transaction pooler used above) for whichever project you're backing up — normally prod. It's kept separate because `pg_dump` needs session semantics the transaction pooler doesn't support. See `04-etl-pipeline-design.md`, "Backing up the prod project," for the full command.

The real `.env` file should never be committed.

`.env.example` is useful for portfolio reviewers because it shows what configuration the project expects.

---

## Local-Only Folders (Not Part of This Repository)

Your local working folder will contain more than what's in this tree — `data/raw/`, `data/imports/`, `data/exports/`, `db/backups/`'s actual dump contents, `logs/`, `.venv/`, `.env`. None of these need to exist for the repository to be complete; they're where your own working data lives alongside the code, not something a fresh clone is missing.

Full folder-by-folder purpose, the local setup checklist, and the dev/prod `DATABASE_URL` env-var handling are documented once, in `11-local-environment-setup.md` — this section doesn't repeat them.

---

## `docs/`

The `docs/` folder contains project documentation.

Recommended structure:

```text
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

Using numbered documentation files is intentional.

It shows that the project was designed step by step:

```text
scope first
then data model
then dictionary
then pipeline
then archive
then repository structure
then automation
then collection import
then analytics
then README structure
then local environment setup (added once implementation started surfacing
  local-only concerns the design phase hadn't needed yet)
```

This is especially useful for a portfolio project because reviewers can follow the thinking process.

Each doc carries its own `Document Version` and `Changelog` section at the top, so a reviewer (or future you) can tell at a glance whether a given doc reflects the latest resolved architecture decisions or is still an earlier draft.

---

## `data/`

The `data/` folder should not contain the full production raw archive.

Instead, it should contain small examples and templates that help others understand the project.

Recommended structure:

```text
data/
  sample/
  import_templates/
```

### `data/sample/`

Contains small sample files for documentation, testing, and demonstration.

Example:

```text
data/sample/sample_price_guide_6.json
data/sample/sample_products_singles_6.json
data/sample/sample_products_nonsingles_6.json
```

These files should be small and safe to commit.

They are not the real archive. They are only examples.

### `data/import_templates/`

Contains templates for collection import.

Example:

```text
data/import_templates/collection_import_template.csv
```

This helps demonstrate how a user can prepare their collection data before importing it into the staging table.

---

## `sql/`

The `sql/` folder contains database-related files.

Recommended structure:

```text
sql/
  schema/
  views/
  checks/
```

### `sql/schema/`

Contains table definitions.

Example:

```text
sql/schema/001_create_products.sql
sql/schema/002_create_price_snapshots.sql
sql/schema/003_create_collection_items.sql
sql/schema/004_create_collection_import_staging.sql
sql/schema/005_create_watchlist.sql
sql/schema/006_create_analytics_signals.sql
```

The numbering makes the expected creation order clear, and matches the dependency order in the data model doc (`products` before anything that references `id_product`).

**Migration approach for MVP:** schema files are applied manually, in numeric order, against the target database. A dedicated migration tool (Alembic, Flyway, or similar) is not required for the MVP given the small number of tables, but this is a conscious simplification, not an oversight — if a schema file needs to change after it has already been applied somewhere (for example, adding `waiting_for_product` to the `match_status` allowed values), that change should be captured as a new numbered file (e.g. `007_alter_collection_import_staging_add_waiting_for_product.sql`) rather than editing an already-applied file in place, so the numbered sequence stays an honest history of what was actually run.

### `sql/views/`

Contains BI and reporting views.

Example:

```text
sql/views/vw_latest_prices.sql
sql/views/vw_collection_current_value.sql
sql/views/vw_collection_summary.sql
sql/views/vw_product_price_history.sql
sql/views/vw_products_without_prices.sql
```

Views are important because they show how raw and normalized data becomes useful for analysis.

Field-level definitions and business logic for these views are documented once, in the data dictionary (`03-data-dictionary.md`); the SQL files here should implement that logic rather than redefining it.

### `sql/checks/`

Contains data quality checks.

Example:

```text
sql/checks/check_missing_products.sql
sql/checks/check_duplicate_price_snapshots.sql
sql/checks/check_empty_price_snapshot.sql
sql/checks/check_products_without_prices.sql
sql/checks/check_category_mismatch.sql
sql/checks/check_invalid_collection_items.sql
```

These checks help make the project look more like a real data pipeline instead of a simple import script. The full check list and which checks are failures vs. warnings are documented in `04-etl-pipeline-design.md`; these SQL files implement that list. `check_invalid_collection_items` is the one exception — it's informational rather than tied to either scheduled pipeline, run after a collection import or periodically (see `04` for its exact scope).

---

## `db/`

Holds manual backups of the **prod** Supabase project (see `04-etl-pipeline-design.md`, "Two Supabase projects: dev and prod" and "Backing up the prod project"). There is no local application database file in this project — schema and data live in Supabase, not in a committed or local `.db` file.

```text
db/
  backups/
```

`db/backups/` should contain a `README.md` (committed) explaining the backup process, but the actual `.sql.gz` dump files are not committed — they're gitignored, kept locally, and synced somewhere off-machine. See `.gitignore` below.

---

## `src/`

The `src/` folder contains the project logic.

Recommended structure:

```text
src/
  config/
  ingestion/
  transform/
  load/
  collection/
  analytics/
  utils/
```

This structure separates responsibilities without creating too many folders.

**Why `transform/` and `load/` are separate:** validating/normalizing a file and actually writing it to the database are distinct responsibilities in the ETL pipeline doc (validate → transform → load are separate pipeline stages). Keeping them in separate folders makes it possible to test transformation logic (e.g. field normalization, product_group enrichment) without touching a database at all, and makes the upsert/idempotency logic (by `id_product`, or by `snapshot_date + id_product`) easy to find in one place.

---

### `src/config/`

Contains configuration loading logic.

Examples of what belongs here:

```text
environment variable handling
database connection settings
remote archive path settings
source URL settings
pipeline timezone handling (Europe/Vienna)
```

This keeps configuration separate from pipeline logic.

---

### `src/ingestion/`

Contains logic for downloading and archiving source files.

Example responsibilities:

```text
download price_guide_6.json
download products_singles_6.json
download products_nonsingles_6.json
compute snapshot_date / catalog archive date using the Europe/Vienna timezone
save dated raw files
detect an existing file for the same date and save a rerun-suffixed copy
  instead of overwriting it
upload raw files to FTP archive
handle failed downloads
```

This folder is about getting data from the source into the raw archive.

It should not contain business logic or BI calculations.

---

### `src/transform/`

Contains logic for validating and transforming downloaded files before database loading.

Example responsibilities:

```text
validate JSON structure
check required fields
normalize hyphenated field names
prepare product records
prepare price snapshot records
```

This folder is where raw Cardmarket files become database-ready records. It does not write to the database itself — that responsibility lives in `src/load/`.

---

### `src/load/`

Contains logic for writing transformed records into the database.

Example responsibilities:

```text
resolve the canonical raw archive file for a given date (base file, or the
  latest rerun-suffixed file if one exists)
upsert products by id_product
upsert price_snapshots by snapshot_date + id_product
recheck collection_import_staging rows with match_status = waiting_for_product
  after a successful product catalog load
run data quality checks after loading
```

Separating this from `transform/` makes the idempotency rules (upsert keys, canonical-file resolution) easy to locate and test independently of parsing/validation logic.

---

### `src/collection/`

Contains logic related to personal collection tracking.

Example responsibilities:

```text
read CSV or Excel collection import files
load rows into collection_import_staging
validate required collection fields
match raw product names to id_product (exact id_product, then exact name, then
  needs_review)
detect matches to products that don't exist locally yet and set
  match_status = waiting_for_product
move reviewed/ready rows into collection_items
re-validate and re-match rows after manual correction (needs_review and
  error are not terminal states)
```

This keeps personal collection logic separate from Cardmarket ingestion.

That separation is important because the Cardmarket pipeline and the personal collection pipeline have different purposes.

---

### `src/analytics/`

Contains logic for calculated metrics or analytics signals.

For the MVP, this should stay light.

Example responsibilities:

```text
calculate estimated market value
prepare summary metrics
generate basic analytics signals
flag products younger than 14 days since first_seen_at as new/less reliable
  for growth and price-spike signals
```

The main MVP valuation formula is:

```text
estimated_market_value = (trend + avg30) / 2
```

Fallback logic should be handled consistently:

```text
if trend exists and avg30 exists: use average of both
if only trend exists: use trend
if only avg30 exists: use avg30
if both are missing: value is null
```

Advanced prediction logic does not belong in the MVP.

---

### `src/utils/`

Contains shared helper functions.

Examples:

```text
date helpers (including Europe/Vienna timezone conversion)
file naming helpers (including rerun-suffix generation and canonical-file
  resolution)
logging helpers
FTP helpers
JSON helpers
basic validation helpers
```

This folder should not become a dumping ground.

If a helper becomes specific to ingestion, transformation, loading, collection import, or analytics, it should move into the relevant folder.

---

## `.github/workflows/`

This folder contains GitHub Actions workflow files.

Recommended structure:

```text
.github/
  workflows/
    daily-price-guide.yml
    product-catalog.yml
```

### `daily-price-guide.yml`

Responsible for the daily price guide pipeline.

High-level flow:

```text
download price_guide_6.json
compute snapshot_date using Europe/Vienna, not the runner's local time
save dated raw archive file (or a rerun-suffixed copy if one already exists
  for that date)
upload archive file through FTP
validate file
normalize fields
load price_snapshots from the canonical file for that date
run data quality checks
```

### `product-catalog.yml`

Responsible for the product catalog pipeline.

High-level flow:

```text
download products_singles_6.json
download products_nonsingles_6.json
compute catalog archive date using Europe/Vienna
save dated raw archive files (or rerun-suffixed copies)
upload archive files through FTP
validate files
enrich with product_group and source_file
load products table from the canonical files
recheck collection_import_staging rows with match_status = waiting_for_product
run product data quality checks
```

Keeping the workflows separate makes scheduling easier and easier to explain. Full failure/warning behavior and thresholds for both workflows are defined in `07-github-actions-logic.md` and `04-etl-pipeline-design.md`.

---

## `tests/`

The `tests/` folder can start small.

For the MVP, it can include simple tests for:

```text
field normalization
required field validation
filename generation (including rerun-suffix and canonical-file resolution)
estimated market value calculation
collection import validation and matching (including the
  waiting_for_product case)
```

**Scope relative to `sql/checks/`:** `tests/` covers unit-level Python logic (parsing, normalization, filename/date handling, matching rules). `sql/checks/` covers data quality checks that run against the loaded database. These are complementary, not overlapping — a unit test verifies "does this function normalize `avg-holo` correctly," while a SQL check verifies "does the live `price_snapshots` table actually contain duplicates today."

This folder does not need to be large at the beginning.

A few simple tests are enough to show that the project is designed responsibly.

---

## What Should Not Be Committed

The repository should avoid committing sensitive or large generated files.

Do not commit:

```text
.env
FTP credentials
database passwords
full raw archive
large downloaded Cardmarket files
local database files
temporary files
logs with secrets
```

The project can include small sample files, but not the full raw data history.

This keeps the GitHub repository lightweight and safe.

---

## Why Not Put Everything in One Script?

A single script may be enough technically, but it is not ideal for this project.

The goal is to demonstrate pipeline thinking.

Separating the repository into documentation, source logic, SQL, workflows, and sample data shows that the project has a clear architecture.

This makes it easier for a reviewer to see that the project is about data engineering and BI, not just file downloading.

---

## Why Not Build an App Folder Now?

The MVP does not need a frontend or full application layer.

The current focus is:

```text
automated data collection
raw archive
normalized database
collection import
basic valuation
BI-ready views
documentation
```

A future app can be added later if the data foundation becomes stable.

Adding an app too early would distract from the main learning goal.

---

## MVP Scope

The MVP repository structure includes:

```text
README.md
documentation files, each versioned with its own changelog
sample data files
collection import template
SQL schema files, applied manually in numeric order
SQL views
basic data quality checks
source folders for ingestion, transform, load, collection, analytics, and utilities
GitHub Actions workflows
```

The MVP repository structure does not include:

```text
full frontend application
complex orchestration framework
large raw archive committed to Git
machine learning folder
cloud data lake structure
advanced monitoring stack
production deployment setup
a dedicated schema migration tool
```

---

## Later Improvements

Possible future repository additions:

```text
dashboards/
notebooks/
app/
infra/
scripts/
reports/
metadata/
```

These should be added only when the project actually needs them.

### Possible future folders

```text
dashboards/
```

For exported BI dashboard definitions or screenshots.

```text
notebooks/
```

For exploratory analysis, but not for production pipeline logic.

```text
app/
```

For a future collection tracking interface.

```text
infra/
```

For infrastructure-as-code if the project becomes more advanced.

```text
reports/
```

For generated portfolio reports or monthly collection summaries.

---

## Design Decision Summary

The repository structure is intentionally simple but professional.

It separates documentation, source logic, SQL, workflows, and sample data, and keeps `transform` and `load` distinct so that idempotency and upsert logic have one clear home.

This makes the project easy to understand as a GitHub portfolio project while keeping the MVP realistic and maintainable.
