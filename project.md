# Project Reference — Pokémon Cardmarket Data Engineering / BI Project

## Document Version

```text
Version: 0.5
Status: Living reference, updated as decisions are made during implementation
Last updated: 2026-07-07
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-05 | Initial consolidated reference, built from docs `01`–`10` at their versions current at the time |
| 0.2 | 2026-07-05 | Updated after folder-structure review: confirmed the two-Supabase-project (dev/prod) split, added the manual `pg_dump` backup process, added `check_invalid_collection_items` as a 6th (informational) data quality check, fixed a stale note in `04` about a "pipeline-state table" to match `07`'s actual resolution (read the previous run's count directly from the database), and documented the local-only working-folder layout (`data/raw/`, `data/imports/`, `data/exports/`, `logs/`, `db/backups/`) |
| 0.3 | 2026-07-05 | Added this Document Version / Changelog block, so staleness is checkable the same way it is for docs `01`–`10` |
| 0.4 | 2026-07-05 | New doc `11-local-environment-setup.md` created, consolidating local-only folder/env-var content previously duplicated across `06` and this file; updated the repo-tree comment, local-only folder section, and Document Index (§18) here to match; `06` and `10` updated in parallel |
| 0.5 | 2026-07-07 | Corrected FTP archive folder layout (flat, not nested under `/raw/cardmarket/pokemon/`) and FTP env var names (`FTP_PASS`/`FTP_REMOTE_DIR`, not `FTP_PASSWORD`/`FTP_REMOTE_PATH`) throughout, matching corrections made in `04` v0.5, `05` v0.3, `06` v0.6, `07` v0.5, `11` v0.3; documented Phase 0a as implemented (§9, top-of-file status line); added corresponding entries to §16 |

**Purpose of this file:** a single, dense reference consolidating the resolved design across all 10 project docs (`01`–`10`). This is what Claude should consult to answer implementation questions — it is not a replacement for the source docs, but it should be accurate enough that you rarely need to open them. **If this file's "Last updated" date is older than the newest date in any of `01`–`10`'s own changelogs, treat this file as potentially stale and check the source doc directly.**

Project phase as of this writing: **Phase 0a (daily price guide archiving) implemented** — `src/ingestion/download_price_guide.py` + `.github/workflows/daily-price-guide.yml` download, save locally, and upload to FTP daily at 17:00 UTC. Validation/normalization/DB load (Phase 0b+) are not yet built. See §9 and `DECISIONS.md` (implementation-level decision log, separate from this file's §16 design-level log) for details.

---

## 1. What This Project Is

A learning-focused data engineering + BI project that:

```text
collects official Cardmarket Pokémon product/price JSON files daily/twice-monthly
archives the raw files immutably
loads them into a normalized Postgres database
builds historical daily price data over time
imports a personal card/sealed-product collection through a staging table
calculates simple, explainable valuation and analytics signals
exposes BI-ready SQL views
```

Explicitly **not**: a marketplace bot, ML system, seller pricing tool, real-time app, or multi-user platform.

---

## 2. Tech Stack & Platform Decisions

```text
Database:        Postgres via Supabase (free tier) — TWO projects: dev + prod
Automation:       GitHub Actions (two scheduled workflows, one optional backup workflow)
Raw archive:      FTP / object storage (NOT Git, NOT the database)
Source data:      Official Cardmarket downloadable JSON files (no scraping/Selenium)
Timezone anchor:  Europe/Vienna (for every date-based rule in the project)
```

**Why Postgres/Supabase matters concretely:**
- Upserts use `INSERT ... ON CONFLICT (...) DO UPDATE ...`
- UUID PKs use `gen_random_uuid()` (pgcrypto, enabled by default on Supabase)
- Partial unique indexes (used on `watchlist`) are fully supported — this is a firm schema requirement, not a fallback
- `DATABASE_URL` must be Supabase's **pooled connection string** (Supavisor, transaction mode), not the direct connection — GitHub Actions runs are short-lived and could exhaust the free tier's connection limit otherwise
- Free-tier Supabase projects **pause after ~1 week of inactivity** — shouldn't trigger given daily writes, but worth monitoring; a paused project fails the daily workflow with a connection error, not an obvious "paused" message
- `DATABASE_URL` credential should be a service/database-role credential, not the anon/public client key — RLS doesn't apply to this pipeline and shouldn't be blamed for write failures

**Dev/prod split (confirmed 2026-07-05):** the free tier allows two active projects per org at no cost, used deliberately rather than sharing one project between development and the real pipelines.
```text
prod project:  written to only by scheduled GitHub Actions workflows (and
               manual reruns). The historical dataset that must not be lost.
dev project:   all local development / manual testing. Same schema. Safe
               to break, reset, or reload at any time.
```
Same variable name (`DATABASE_URL`), two different values: local `.env` → dev, GitHub Actions secret → prod. Never the same string in both places.

**Backups (the free tier has none automatically):** weekly `pg_dump` of the prod project, using the **Session Pooler** connection string (`DATABASE_URL_BACKUP` — different from `DATABASE_URL`'s transaction pooler, since `pg_dump` needs session semantics). Recommended flags: `--clean --if-exists --no-owner --no-privileges`, gzipped, stored in `db/backups/` locally and synced off-machine (never committed). Full command in `04-etl-pipeline-design.md`. Collection data is the thing a backup actually protects — price history can be reprocessed from the raw archive if ever needed.

---

## 3. Data Sources

Three official Cardmarket JSON files, joined on `idProduct`:

```text
products_singles_6.json       (catalog, twice/month)
products_nonsingles_6.json    (catalog, twice/month)
price_guide_6.json            (full daily price guide, daily)
```

Price guide holo fields use hyphens and must be normalized on load:

```text
avg-holo → avg_holo   low-holo → low_holo     trend-holo → trend_holo
avg1-holo → avg1_holo avg7-holo → avg7_holo   avg30-holo → avg30_holo
```

---

## 4. Repository Structure

```text
pokemon-cardmarket-bi/
│
├── README.md
├── LICENSE                    (MIT)
├── .gitignore
├── .env.example
│
├── docs/                      01–11, each with its own Version + Changelog
│
├── data/
│   ├── sample/                small representative JSON samples, safe to commit
│   └── import_templates/      collection_import_template.csv
│
├── db/
│   └── backups/               README.md committed; .sql.gz dump files gitignored
│                               (manual pg_dump backups of the PROD Supabase project)
│
├── sql/
│   ├── schema/                001–006, applied manually in numeric order (no migration tool in MVP)
│   ├── views/                 vw_*.sql implementing data-dictionary view definitions
│   └── checks/                6 checks: 5 pipeline data-quality checks + 1 informational
│                               collection-integrity check (check_invalid_collection_items)
│
├── src/
│   ├── config/                env/config loading, DB connection, Europe/Vienna timezone handling
│   ├── ingestion/              download + archive (no business logic)
│   ├── transform/              validate/normalize (no DB writes)
│   ├── load/                   upserts, canonical-file resolution, waiting_for_product recheck
│   ├── collection/              CSV/Excel import, staging, matching
│   ├── analytics/               valuation, signal generation
│   └── utils/                  date/file-naming/logging/FTP/JSON/validation helpers
│
├── tests/                      unit tests: normalization, validation, filename/rerun logic, valuation, matching
│
└── .github/
    └── workflows/
        ├── daily-price-guide.yml
        ├── product-catalog.yml
        └── backup-database.yml   (optional, lower urgency — weekly, not yet built)
```

**Why `transform/` and `load/` are split:** lets transformation logic (normalization, enrichment) be tested without a DB, and keeps upsert/idempotency logic in one findable place.

**`sql/schema/` migration approach:** manual, numeric order, no Alembic/Flyway. If a schema needs to change after being applied somewhere, add a new numbered file (e.g. `007_alter_...sql`) rather than editing an applied one in place.

**`tests/` vs `sql/checks/`:** `tests/` = unit-level Python logic (parsing, normalization, matching rules). `sql/checks/` = data quality checks against the live database. Complementary, not overlapping.

**There is no local application database file anywhere in this project.** Schema and data live in the two Supabase projects (dev + prod); `db/backups/` holds backup *dumps* of prod, not a live database.

### Local-only working folder (NOT part of the Git repository)

These exist on disk alongside the repo but are gitignored — a fresh `git clone` won't have them, and that's expected. Full folder-by-folder purpose, the dev/prod env-var handling, and a first-time setup checklist now live in `11-local-environment-setup.md`; this is just the quick-reference version:

```text
data/raw/                       the real dated raw archive (see §8) —
                                 only data/sample/ is committed
data/imports/collection/        incoming/ processed/ failed/ — personal
                                 filing convenience for CSV/Excel files;
                                 collection_import_staging.matchStatus is
                                 the actual source of truth, not these folders
data/exports/                   ad hoc CSV exports from BI views
db/backups/                     manual pg_dump dumps of the PROD Supabase
                                 project — folder + README committed, dumps not
logs/                           local run logs when scripts are run manually
                                 outside GitHub Actions
```

### `.env.example` keys

```text
CARDMARKET_PRICE_GUIDE_URL=   # defaults in code to the real known URL if unset (see §9)
CARDMARKET_PRODUCTS_SINGLES_URL=
CARDMARKET_PRODUCTS_NONSINGLES_URL=

FTP_HOST=
FTP_USER=
FTP_PASS=
FTP_REMOTE_DIR=

DATABASE_URL=              # pooled (Supavisor, transaction mode). LOCAL .env → dev project.
                            # GitHub Actions secret of the same name → prod project. Never mixed up.
DATABASE_URL_BACKUP=       # Session Pooler string, for manual pg_dump backups of prod

PIPELINE_TIMEZONE=Europe/Vienna
```

**Corrected 2026-07-07:** `FTP_PASS` / `FTP_REMOTE_DIR` are the actual,
already-provisioned-and-tested variable names — earlier drafts of this file
(and `06`/`07`/`11`) used `FTP_PASSWORD` / `FTP_REMOTE_PATH` instead, a
naming guess made before the FTP account and its GitHub Actions secrets
existed. `FTP_PASS` is a required GitHub Actions **secret**, same as the
other three FTP_* values.

---

## 5. Database Schema

All 6 tables. `idProduct` is the central join key across everything.

### `products`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `idProduct` | integer/bigint | No | **PK.** Official Cardmarket ID |
| `name` | text | No | |
| `idCategory` | integer/bigint | Yes | Catalog category as of last catalog refresh |
| `categoryName` | text | Yes | |
| `idExpansion` | integer/bigint | Yes | |
| `idMetacard` | integer/bigint | Yes | Mainly for singles |
| `dateAdded` | date/timestamp | Yes | From Cardmarket, if provided |
| `productGroup` | text | No | `single` \| `non_single` |
| `sourceFile` | text | No | `products_singles_6.json` \| `products_nonsingles_6.json` |
| `isActiveInCatalog` | boolean | No, default `true` | False the first time missing from a fresh catalog file (no grace period). Never triggers deletion. |
| `firstSeenAt` | timestamp | No | First time seen in any downloaded catalog |
| `lastSeenAt` | timestamp | No | Most recent time seen |
| `updatedAt` | timestamp | No | Changes on **any** field change including `lastSeenAt` — i.e. on almost every catalog run. Means "pipeline touched this row," not "a business field changed." |

Business rules: `idProduct` unique; never delete for inactivity; singles→`single`, non-singles→`non_single`.

### `price_snapshots`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `snapshotDate` | date | No | **PK (composite)**. Pipeline run date in Europe/Vienna, no exceptions (incl. reruns/backfills) |
| `sourceCreatedAt` | timestamp | Yes | Alias for pipeline download timestamp — Cardmarket files have no usable file-level timestamp of their own |
| `idProduct` | integer/bigint | No | **PK (composite)**. Logical FK to `products` (not strict — see §6) |
| `idCategory` | integer/bigint | Yes | Source-observed, point-in-time; can drift from `products.idCategory` (intentional — see reconciliation rule) |
| `avg`, `low`, `trend`, `avg1`, `avg7`, `avg30` | decimal | Yes | `low` excluded from valuation (noisy). `trend`+`avg30` used in valuation |
| `avg_holo`, `low_holo`, `trend_holo`, `avg1_holo`, `avg7_holo`, `avg30_holo` | decimal | Yes | Normalized from hyphenated source fields |
| `createdAt` | timestamp | No | DB insert time |

PK: `(snapshotDate, idProduct)`. Load = **upsert by this key**.

`idCategory` reconciliation: mismatch between `price_snapshots.idCategory` and `products.idCategory` → data-quality **warning** (`check_category_mismatch`), never blocks load, never auto-corrects either value.

### `collection_items`

| Field | Type | Nullable | Default |
|---|---|---|---|
| `collectionItemId` | uuid/integer | No | **PK** |
| `idProduct` | integer/bigint | No | FK → `products.idProduct` |
| `language` | text | No | `DE` |
| `condition` | text | No | `Near Mint` |
| `acquisitionType` | text | No | `pulled` |
| `purchasePrice` | decimal | Yes | — |
| `purchaseDate` | date | Yes | — |
| `isSealed` | boolean | No | `false` |
| `isGraded` | boolean | No | `false` |
| `gradingCompany` | text | Yes | null when `isGraded=false` |
| `grade` | text | Yes | Stored **as text**, exact label (e.g. `"10"`, `"Pristine 10"`) — grading scales aren't comparable across companies, no normalization in MVP |
| `storageLocation` | text | Yes | — |
| `personalNote` | text | Yes | — |
| `isSold` | boolean | No | `false` |
| `soldPrice` | decimal | Yes | usually null unless sold |
| `soldDate` | date | Yes | usually null unless sold |
| `createdAt` | timestamp | No | — |
| `updatedAt` | timestamp | No | Changes only on real user-facing/lifecycle field changes (unlike `products.updatedAt`) |

One row = one physical item, never a `quantity` field. `acquisitionType` values: `pulled`, `bought_single`, `bought_sealed`, `trade`, `gift`, `unknown`. `condition` values: `Mint`, `Near Mint`, `Excellent`, `Good`, `Light Played`, `Played`, `Poor`, `Unknown`. `language` values: `DE, EN, FR, IT, ES, JP, KR, CN, Other, Unknown`.

### `collection_import_staging`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `importRowId` | uuid/integer | No | **PK** |
| `importBatchId` | uuid/text | No | Identifies one upload event (not one file — re-uploads get a new batch ID) |
| `externalId` | text | Yes | User's own row ID; used for duplicate protection |
| `providedIdProduct` | integer/bigint | Yes | User-supplied, may not exist locally yet |
| `rawProductName` | text | Yes | Preserved verbatim, even post-match |
| `matchedIdProduct` | integer/bigint | Yes | Set by matcher; may point to a not-yet-local product |
| `language`, `condition`, `acquisitionType` | text | Yes | Same defaults as `collection_items` |
| `purchasePrice`, `purchaseDate` | decimal/date | Yes | — |
| `isSealed` | boolean | Yes | — |
| `storageLocation` | text | Yes | **(added v0.4 — was missing from schema in earlier drafts)** |
| `personalNote` | text | Yes | **(added v0.4, same reason)** |
| `matchStatus` | text | No | See §10 |
| `matchConfidence` | decimal | Yes | 0.00–1.00; see §10 |
| `errorMessage` | text | Yes | Updated on every re-validation, not just set once |
| `createdAt` | timestamp | No | — |
| `importedAt` | timestamp | Yes | Set only once imported |

`providedIdProduct` is **not** a strict FK (staging must be able to hold bad input). `matchedIdProduct` logically FKs to `products.idProduct`.

### `watchlist`

| Field | Type | Nullable | Default |
|---|---|---|---|
| `watchlistItemId` | uuid/integer | No | PK |
| `idProduct` | integer/bigint | No | FK → `products` |
| `reason` | text | Yes | — |
| `targetPrice` | decimal | Yes | — |
| `isActive` | boolean | No | `true` |
| `createdAt`, `updatedAt` | timestamp | No | — |

**Firm requirement (Postgres confirmed):**
```sql
CREATE UNIQUE INDEX ux_watchlist_active_product
  ON watchlist (idProduct) WHERE isActive = true;
```
Inactive rows kept indefinitely; a product can be deactivated and re-added without conflict.

### `analytics_signals`

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `signalId` | uuid/integer | No | PK |
| `signalDate` | date | No | — |
| `idProduct` | integer/bigint | Yes | Nullable for collection-only signals; populated alongside `collectionItemId` on collection-level signals for join convenience |
| `collectionItemId` | uuid/integer | Yes | **Required** for `collection_gain`/`collection_loss` — two copies of the same product can have different `purchasePrice`, so keying only on `idProduct` can't represent one copy's change |
| `signalType` | text | No | See §11 |
| `signalValue` | decimal | Yes | Main numeric result (e.g. % change) |
| `signalStrength` | text | Yes | `low` \| `medium` \| `high` (optionally `critical` later) |
| `lookbackDays` | integer | Yes | Window used, if freely chosen (null for `price_spike`, which uses Cardmarket's fixed `avg30`) |
| `referenceValue` | decimal | Yes | "Before" value |
| `currentValue` | decimal | Yes | "After" value |
| `signalDescription` | text | Yes | Human-readable |
| `createdAt` | timestamp | No | — |

A signal is an **observation, not a prediction** — never presented as financial advice.

### Indexing baseline (all tables)

```text
price_snapshots.idProduct
collection_items.idProduct
collection_import_staging.matchedIdProduct
watchlist.idProduct
analytics_signals.idProduct
analytics_signals.collectionItemId
```

### `sql/schema/` file order

```text
001_create_products.sql
002_create_price_snapshots.sql
003_create_collection_items.sql
004_create_collection_import_staging.sql
005_create_watchlist.sql
006_create_analytics_signals.sql
```

---

## 6. Cross-Cutting Business Rules

**Timezone anchor (applies everywhere a date is computed):**
```text
snapshotDate / catalog archive date = pipeline run date in Europe/Vienna,
for EVERY run including manual reruns and backfills — no exceptions.
GitHub Actions runners default to UTC; conversion must happen explicitly in
src/config or src/utils, shared by both workflows, never computed ad hoc.
```

**Product lifecycle:** `isActiveInCatalog=false` the instant a product is missing from a fresh catalog file — no grace period. Never deleted. Historical `price_snapshots`/`collection_items` referencing an inactive product stay valid and visible in BI views.

**No strict FK `price_snapshots.idProduct → products.idProduct`:** catalogs refresh twice/month, prices daily, so new products can appear in prices before catalog. Handled via indexed logical relationship + data quality warnings, not a hard constraint. Same reasoning underlies `waiting_for_product` in staging.

**Valuation formula (used everywhere estimated value appears — `vw_latest_prices`, collection views, `collection_gain`/`loss` signals):**
```text
if trend exists and avg30 exists:  estimatedMarketValue = (trend + avg30) / 2
if only trend exists:              estimatedMarketValue = trend
if only avg30 exists:               estimatedMarketValue = avg30
if neither exists:                  estimatedMarketValue = null
```
`low` is never used for valuation (noisy).

**New-product reliability flag (the one canonical "how new is new" rule, reused by `new_product`/`growth`/`price_spike` signals):**
```text
priceAgeDays = snapshotDate - products.firstSeenAt
isNewProduct = priceAgeDays < 14
```
Valuation still uses latest price regardless of age. Only signal generation treats `isNewProduct` products as unstable/suppressed.

**Idempotency (rerunning any pipeline for the same date must never duplicate or corrupt data):**
```text
products:                upsert by idProduct
price_snapshots:          upsert by (snapshotDate, idProduct)
raw archive files:        never overwritten — rerun-suffixed instead (see §8)
collection_import_staging: importBatchId per upload; externalId (if present)
                           prevents re-importing the same source row across batches
collection_items:         only ready_to_import staging rows import; no
                           auto-dedup without externalId (possible-duplicate
                           warning instead — see §10)
```

**Retention:** no retention limit on raw archive or `price_snapshots` in MVP — kept indefinitely, revisited once real growth is observed. Full raw archive lives on FTP/object storage, **not committed to Git** (small samples only, in `data/sample/`).

---

## 7. ETL Pipelines (three, separate)

```text
1. Daily price guide pipeline       — scheduled, daily
2. Twice-monthly catalog pipeline   — scheduled, 1st + 15th of month
3. Manual collection import        — user-triggered, not scheduled
```

**Load order when both scheduled pipelines run same day:** catalog pipeline **before** daily price pipeline (increases chance new products are known before their prices load) — but the daily pipeline must still run independently and successfully even if catalog didn't run or failed that day.

### Daily price guide pipeline — steps
```text
1. Start scheduled run
2. Download price_guide_6.json
3. Assign snapshotDate (Europe/Vienna)
4. Archive raw file (canonical name, or rerun-suffixed copy if one exists for that date)
5. Validate JSON structure
6. Validate required fields (idProduct required; price fields nullable)
7. Normalize hyphenated holo field names
8. Upsert into price_snapshots from the canonical file for that date
9. Run data quality checks
10. Expose via BI views
```

### Twice-monthly catalog pipeline — steps
```text
1. Start scheduled run
2. Download products_singles_6.json + products_nonsingles_6.json
3. Assign catalogArchiveDate (Europe/Vienna)
4. Archive both raw files (canonical or rerun-suffixed)
5. Validate both JSON files
6. Add productGroup + sourceFile per row
7. Combine singles + non-singles
8. Check for duplicate idProduct across combined set
9. Upsert into products from canonical files
10. Update isActiveInCatalog (true for present, false for missing — no grace period)
11. Detect newly added products
12. Recheck collection_import_staging rows with matchStatus=waiting_for_product
13. Run product catalog data quality checks
```

**Duplicate idProduct across combined catalog:** same data → keep one row, log warning. Conflicting data → **fail the pipeline** (recommended MVP rule).

**If one catalog file succeeds and the other fails:** do **not** update `products` at all; fail the whole catalog run. A partially-unified catalog is considered worse than a stale-but-consistent one.

**If the catalog pipeline fails/misses entirely:** existing `products` table stays in use as-is (stale, not blocked). Daily price pipeline continues normally against it. New unmatched `idProduct`s reported as warnings like any other day. No automatic retry — manual rerun or wait for next scheduled date (1st/15th). This accepts up to ~2 weeks of staleness by design.

### Failure vs. Warning — authoritative thresholds (defined once in `04`, mirrored elsewhere)

**Always a failure (no data loaded):**
```text
required file couldn't be downloaded
raw archiving failed
invalid JSON / empty file / zero records
required field missing on a row (idProduct; name for catalogs)
FTP/archive upload failed
database connection/transaction failed
duplicate (snapshotDate, idProduct) remaining after upsert
conflicting duplicate idProduct within a combined catalog load
one catalog file succeeds while the other fails
```

**Warning (success, but flagged):**
```text
price rows with no matching product
idCategory mismatch between price_snapshots and products
new idProduct in price guide not yet in products
products with no latest price
record count differs from previous successful run by more than 20%
  (not statistically derived — a starting sanity threshold; requires storing
  the previous run's row count, e.g. read directly from price_snapshots for
  the most recent prior snapshotDate — no dedicated pipeline_runs table in MVP)
```

### Validation minimums
```text
Catalog files:  file exists, valid JSON, not empty, idProduct exists, name exists
Price guide:    file exists, valid JSON, not empty, idProduct exists (price fields nullable)
```

### Reprocessing (sketch only, not automated in MVP)
```text
1. Select an archived raw file (or date range) — read directly, no re-download
2. Run current (possibly fixed) validation/transformation against it
3. Upsert result into target table (price_snapshots by snapshotDate+idProduct,
   or products by idProduct)
4. Run standard data quality checks
5. Compare loaded counts against the original load, if available
```
Reprocessing reads raw files; never mutates them.

---

## 8. Raw Archive Strategy

**Folder structure (flat, dated filenames, no year/month partitioning in MVP):**
```text
{FTP_REMOTE_DIR}/
  price_guides/
    price_guide_6_YYYY-MM-DD.json
  product_catalogs/
    products_singles_6_YYYY-MM-DD.json
    products_nonsingles_6_YYYY-MM-DD.json
```
(Corrected 2026-07-07 — this was previously shown nested under
`/raw/cardmarket/pokemon/`, which never matched the actual FTP account and
contradicted this section's own "flat" heading. See `05` v0.3.)

**Immutability + rerun rule (the core resolved design decision):**
```text
Existing dated files are NEVER silently overwritten.
A rerun for a date that already has a file produces a suffixed copy:
  price_guide_6_2026-07-03.json            (first run)
  price_guide_6_2026-07-03_rerun-01.json   (first rerun)
  price_guide_6_2026-07-03_rerun-02.json   (second rerun)

Canonical file for a date = highest-numbered rerun if any exist, else the
base file. The database ALWAYS loads from the canonical file. Superseded
files stay on disk for audit but are never loaded.
```
No manifest/log table records which file is canonical — determined by filename convention at load time (deliberately deferred; see `archive_manifest` in Later Improvements).

**Archive gaps:** a missing date = accepted, documented limitation. No automatic backfill — Cardmarket doesn't expose historical data, only a current daily snapshot. Surfaced via completeness checks, not silently ignored.

**Retention:** indefinite, no limit, revisit once real volume is observed. Not committed to Git.

---

## 9. GitHub Actions

Two scheduled workflows only; collection import is **not** automated.

```text
.github/workflows/daily-price-guide.yml     — daily — IMPLEMENTED 2026-07-07
.github/workflows/product-catalog.yml       — twice/month (1st, 15th) — not yet built
```

Both:
- compute their working date in Europe/Vienna explicitly (never trust runner's UTC clock)
- archive raw file(s) **before** any transformation
- treat the **FTP** archive as immutable (rerun → suffixed copy, never overwrite); the local `data/raw/` working copy is a separate plain-overwrite concern (see `11`)
- daily-price-guide.yml's load/processing step reads directly from the local working copy, since it's always the latest attempt for that date — no canonical-file resolution needed locally (see `04` v0.5)
- support manual triggering (manual rerun for an existing date → rerun-suffixed copy on FTP, same as a scheduled rerun)
- run data quality checks with the same failure/warning thresholds as §7

`daily-price-guide.yml` is scheduled at `17:00 UTC` (~7pm Europe/Vienna in
summer; ~6pm in winter, since GH Actions cron doesn't shift for DST — see
`07` v0.5). It currently covers download → local save → FTP upload only;
validation/normalization/DB load (steps 5–8 of §7's daily pipeline) are not
yet wired in (Phase 0b+).

**Secrets (GitHub Actions secrets, never in `.env.example` or workflow files):**
```text
FTP_HOST, FTP_USER, FTP_PASS, FTP_REMOTE_DIR
DATABASE_URL   (Supabase pooled connection string, service credential)
```

**Corrected 2026-07-07:** `FTP_PASS` / `FTP_REMOTE_DIR`, not `FTP_PASSWORD` /
`FTP_REMOTE_PATH` — see `06` v0.6, `07` v0.5.

**Non-secret config:**
```text
CARDMARKET_PRICE_GUIDE_URL, CARDMARKET_PRODUCTS_SINGLES_URL,
CARDMARKET_PRODUCTS_NONSINGLES_URL, PIPELINE_TIMEZONE=Europe/Vienna
```

**Architecture separation:** GitHub Actions = scheduler only. FTP = raw archive storage. Database = normalized analytical layer. None of these substitute for another.

**No dedicated `pipeline_runs`/`archive_manifest` table in MVP** — previous-run row counts are read directly from the DB when needed (e.g., for the 20% threshold check); canonical-vs-rerun status is filename-convention-only.

---

## 10. Collection Import Flow

```text
CSV/Excel → collection_import_staging (one importBatchId per upload)
          → validate fields
          → match product (see order below)
          → matchStatus assigned
          → manual review loop for needs_review/error (not terminal)
          → automatic recheck for waiting_for_product after next catalog run
          → ready_to_import rows → collection_items
```

**Recommended import columns:**
```text
externalId, providedIdProduct, rawProductName, language, condition,
acquisitionType, purchasePrice, purchaseDate, isSealed, storageLocation,
personalNote
```
Empty cell and missing column are treated identically — both fall back to the field's default. No enforced file size/row count limit in MVP.

**Matching order (confirmed intentional design, including the no-fallback branch):**
```text
1. providedIdProduct exists:
   - exists in products?  → ready_to_import, matchConfidence = 1.00
   - doesn't exist yet?    → matchedIdProduct = providedIdProduct anyway,
                             matchStatus = waiting_for_product,
                             matchConfidence = null
                             (INTENTIONALLY does not fall back to a name
                             match — an explicit user-supplied ID is trusted
                             over a name-based guess, even if that ID isn't
                             catalogued yet)

2. providedIdProduct missing → try EXACT rawProductName match against products.name

3. exactly one exact name match → ready_to_import, matchConfidence = 0.90

4. multiple exact matches, or anything less than exact →
   needs_review, matchConfidence = 0.00

5. no match at all →
   needs_review or error (depending on salvageability), matchConfidence = 0.00
```
`matchConfidence = null` means "not attempted yet" (expected to be rare given synchronous matching); `0.00` means "attempted, no confident result." Fuzzy matching (0.70/0.40 confidence bands) is defined but **unused** in MVP — reserved for later.

**`matchStatus` values:** `ready_to_import`, `needs_review`, `waiting_for_product`, `error`, `imported`. None except `imported` is terminal — `needs_review`/`error` re-validate on correction; `waiting_for_product` auto-rechecks after every successful catalog pipeline run.

**Duplicate handling:**
```text
Within a batch:      same externalId twice → data quality error on the duplicate
Across batches:       externalId checked against all previously imported rows,
                      not just the current batch (protects against re-uploading
                      the same file)
No externalId:        NOT auto-deduplicated (multiple identical physical cards
                      are legitimate) — but a row matching an existing
                      collection_items row on idProduct + language + condition
                      + purchaseDate + purchasePrice together is surfaced as a
                      possible-duplicate warning for manual review, not blocked
```

**Staging → collection_items field mapping:** direct 1:1 for `matchedIdProduct→idProduct`, `language`, `condition`, `acquisitionType`, `purchasePrice`, `purchaseDate`, `isSealed`, `storageLocation`, `personalNote`.

**Import safety rules:** never auto-import `needs_review`/`waiting_for_product`/`error`; never delete staging rows post-import; never overwrite `rawProductName`; never silently change user values; never merge physical items into quantity rows.

---

## 11. Analytics Signals

MVP signal types: `growth`, `price_spike`, `new_product`, `collection_gain`, `collection_loss`, `missing_price_data`.
Deferred (not MVP): `sealed_growth`, `potential_buy_opportunity`, `watchlist_target_reached`, `price_drop`, `unusual_volatility`.

Collection-level signals (`collection_gain`/`collection_loss`) **must** key on `collectionItemId` (populate `idProduct` too, for convenience). Product-level signals (`growth`, `price_spike`, `new_product`, `missing_price_data`) key on `idProduct`, leave `collectionItemId` null.

### `growth`
```text
growthPercent = ((currentTrend - previousTrend) / previousTrend) * 100
lookbackDays ∈ {7, 30, 90}
Strength: low 5–10%, medium 10–25%, high >25%
Suppressed/flagged low-confidence while isNewProduct is true.
Ignore if previous value missing or zero.
```

### `price_spike`
```text
priceSpikePercent = ((trend - avg30) / avg30) * 100
lookbackDays = null ALWAYS (avg30 is Cardmarket's fixed field, not a chosen window —
  a past draft wrongly set lookbackDays=30 here; corrected)
Strength: low 10–20%, medium 20–40%, high >40%
Suppressed/flagged low-confidence while isNewProduct is true.
```

### `new_product`
```text
priceAgeDays = signalDate - products.firstSeenAt   (same calc as isNewProduct)
Strength: high ≤3 days, medium ≤14 days (= isNewProduct true), low ≤30 days
No signal generated past 30 days.
```

### `collection_gain` / `collection_loss`
```text
collectionGain  = estimatedMarketValue - purchasePrice   (gain if positive)
collectionLoss  = purchasePrice - estimatedMarketValue   (loss if positive)
Percent = (that value / purchasePrice) * 100
Keyed per collectionItemId. Only one of gain/loss (or neither, at breakeven)
  generates per item per signalDate. Requires purchasePrice to exist.
Strength (gain): low 5–15%, medium 15–40%, high >40%
Strength (loss): low 5–15%, medium 15–40%, high >40%
```

### `missing_price_data`
```text
Fires when trend AND avg30 are both null in a product's latest price_snapshots row.
signalValue/referenceValue/currentValue = null; explanation lives in signalDescription.
Strength: low <14 days missing, medium 14–30 days, high >30 days
  (independent of isNewProduct — a product can be old and still lack prices)
Only fires once a product has had at least one full daily pipeline cycle to
  appear in price_snapshots and didn't — not for products just added.
Complements (doesn't duplicate) vw_products_without_prices: the view is
  "missing right now"; the signal is "was missing as of this dated record."
```

### Minimum history requirements
```text
growth:               7 days; suppressed while isNewProduct
price_spike:          current snapshot only; suppressed while isNewProduct
new_product:          firstSeenAt only, no price history needed
collection_gain/loss: latest price + purchasePrice on that specific item
missing_price_data:   ≥1 completed daily pipeline cycle since cataloguing
```

---

## 12. BI Views

Single source of truth for view definitions: `03-data-dictionary.md`. Implemented as plain SQL views (no refresh logic needed).

| View | Purpose |
|---|---|
| `vw_latest_prices` | One latest price row per product + `estimatedMarketValue` + `isActiveInCatalog` |
| `vw_collection_current_value` | Current value per unsold collection item; `estimatedGainLoss`, `estimatedGainLossPercent` (null if `purchasePrice` missing/zero) |
| `vw_collection_summary` | Aggregate counts/totals + "most valuable item" (tie-break: highest value → earliest `purchaseDate` → lowest `collectionItemId`) |
| `vw_product_price_history` | Historical trend per product, incl. `isActiveInCatalog` (history stays visible regardless) |
| `vw_products_without_prices` | Data-quality view: catalog products with no current price data |
| `vw_top_growth_products`, `vw_recent_price_spikes`, `vw_new_products`, `vw_collection_gains`, `vw_collection_losses` | Signal-driven views (from `09`); field-level defs belong in `03` once added |

---

## 13. MVP Scope Boundaries

**In MVP:** official JSON files only; immutable raw archive with rerun-suffixing; unified `products` catalog; full daily price snapshots; upsert-based idempotent loading; data quality checks with defined failure/warning thresholds; CSV/Excel collection import via staging (incl. `waiting_for_product`); BI views; six MVP analytics signals; documentation.

**Out of scope:** Selenium/browser scraping/login automation; seller price automation; real-time processing/alerts; Airflow/Kafka/complex orchestration; ML/price prediction; advanced fuzzy matching; automatic retry of failed scheduled catalog runs; automated archive backfill; full web/mobile app; multi-user support; graded/language/condition-specific valuation; premium subscription logic.

---

## 14. MVP Success Criteria (falsifiable, from `01`)

```text
30 consecutive days of daily price guide archive with no missing file
price_snapshots: exactly one row set per archived date, zero duplicate
  (snapshotDate, idProduct) pairs
products: singles + sealed unified, zero duplicate idProduct
At least one real CSV/Excel collection file imported successfully through
  staging into collection_items
vw_collection_current_value returns non-null estimatedMarketValue for every
  item whose matched product has trend or avg30 data
Known limitations documented in README + data dictionary (not just implied)
Documentation set matches the actually implemented schema/pipeline behavior
```

---

## 15. Known Limitations (accepted, documented — not bugs to fix)

```text
Daily snapshot only, not a historical API — history exists only from the
  first day the pipeline successfully ran
Archive gaps from missed days are not backfilled (Cardmarket doesn't expose
  history)
No language- or condition-specific pricing (collection defaults to
  DE/Near Mint, valuation uses aggregated Cardmarket data)
low is noisy — never used for valuation
New products (<14 days since firstSeenAt) have unstable prices — growth/spike
  signals suppressed, valuation unaffected
No retention limit on raw archive / price_snapshots yet
No ML / prediction — signals are simple explainable observations only
```

---

## 16. Decision Log (things explicitly resolved during review — useful if you wonder "was this considered?")

```text
✓ storageLocation/personalNote added to collection_import_staging schema
  (was documented as import columns but missing from the table in 02/03/08)
✓ LICENSE = MIT, added to repo tree (06) to match 10
✓ matchConfidence: 0.00 = attempted/no match, null = not attempted yet
✓ providedIdProduct-not-found does NOT fall back to name matching (intentional)
✓ sourceCreatedAt = plain alias for download time (no real "source timestamp"
  branch exists in practice)
✓ Database confirmed: Postgres via Supabase free tier — settles upsert syntax,
  partial unique index support, UUID generation, pooled-connection requirement
✓ Archive immutability vs. same-date overwrite contradiction resolved via
  rerun-suffixed files + canonical-file-at-load-time resolution
✓ waiting_for_product status added for the catalog-lag timing gap
✓ analytics_signals extended with signalStrength/lookbackDays/referenceValue/
  currentValue; collection-level signals keyed on collectionItemId
✓ sealed_growth deferred out of MVP (needs historical data across both groups
  first) — 09 originally listed it as MVP, corrected to match 02/03
✓ missing_price_data added to MVP signal list to match 02/03
✓ price_spike.lookbackDays corrected to always be null (avg30 is a fixed
  Cardmarket field, not a chosen window)
✓ Two Supabase projects confirmed (dev + prod, both free tier) rather than
  one shared project or a local SQLite file — DATABASE_URL means different
  things in .env (dev) vs. GitHub Actions secrets (prod)
✓ Manual pg_dump backup process defined for prod (free tier has zero
  automated backups) — Session Pooler connection, DATABASE_URL_BACKUP,
  weekly cadence, stored in db/backups/ and synced off-machine
✓ check_invalid_collection_items added as a 6th, informational-only data
  quality check (post-import consistency, not tied to either scheduled
  pipeline)
✓ 04's "small single-row pipeline-state table" note for the 20% threshold
  check was stale/inconsistent with 07's resolution — fixed to match 07:
  read the previous run's count directly from the database, no dedicated
  table in MVP
✓ FTP archive folder layout corrected (2026-07-07) from a nested
  /raw/cardmarket/pokemon/{price_guides,product_catalogs}/ structure to the
  flat structure the actual, already-provisioned FTP account uses —
  price_guides/ and product_catalogs/ directly under FTP_REMOTE_DIR. The
  nested path was a pre-provisioning guess in 04/05/07; corrected in those
  docs (04 v0.5, 05 v0.3, 07 v0.5) and here
✓ FTP env var names corrected (2026-07-07) to FTP_PASS / FTP_REMOTE_DIR,
  matching the actual, already-tested GitHub Actions secrets — earlier
  drafts of 06/07/11/this file used FTP_PASSWORD / FTP_REMOTE_PATH, again a
  pre-provisioning naming guess. Corrected in 06 v0.6, 07 v0.5, 11 v0.3
✓ Local data/raw/ working copy confirmed as plain-overwrite-on-rerun (no
  suffix logic locally) — rerun-suffixing/canonical-file resolution applies
  to the FTP archive only. Local nested folder convention
  (data/raw/cardmarket/pokemon/...) is unaffected and distinct from the
  FTP-side flat layout above. See 11 v0.2–v0.3, 04 v0.5
✓ Phase 0a (daily price guide: download → local save → FTP upload)
  implemented via src/ingestion/download_price_guide.py +
  .github/workflows/daily-price-guide.yml, scheduled at 17:00 UTC
  (~7pm Europe/Vienna in summer, ~6pm in winter — GH Actions cron doesn't
  shift for DST; snapshotDate correctness is unaffected either way).
  Validation/normalization/DB load intentionally not yet included — see
  DECISIONS.md for the full implementation-level reasoning behind all five
  entries above
```

---

## 17. Later Improvements (explicitly deferred, not MVP — don't build unless asked)

```text
archive_manifest / pipeline_runs table (canonical/rerun status + row counts
  as queryable data, replacing filename-convention-only resolution)
automated reprocessing/replay tooling (only a sketch exists today)
automatic retry of failed scheduled catalog runs
fuzzy matching (0.70/0.40 confidence bands already reserved in the scale)
file content hashing to detect re-uploaded import files automatically
graded card / sealed-product-specific valuation fields
sealed_growth, potential_buy_opportunity, watchlist_target_reached,
  price_drop, unusual_volatility signals
gradingScale / gradeNumeric / gradeLabel normalization on collection_items
multi-user support, full web/mobile app, dashboards/, notebooks/, app/, infra/
retention policy with real limits (once real growth is observed)
```

---

## 18. Document Index (for going deeper than this file)

```text
01-mvp-scope.md                    — why the project exists, MVP boundary, success criteria
02-data-model.md                   — full schema, business rules, relationships (source of truth for schema)
03-data-dictionary.md              — field-level defs + BI view defs (source of truth for views)
04-etl-pipeline-design.md          — pipeline steps, thresholds, Supabase platform notes
05-raw-archive-strategy.md         — archive folder structure, immutability, retention
06-github-repository-structure.md — repo tree, folder purposes, LICENSE, .env.example
07-github-actions-logic.md         — workflow schedules, secrets, timezone handling
08-collection-import-flow.md       — staging table, matching logic, duplicate handling
09-analytics-signal-definitions.md — signal formulas, thresholds, minimum history
10-readme-documentation-structure.md — README content plan, doc index for the repo itself
11-local-environment-setup.md      — local-only folder structure, dev/prod env vars, setup checklist
```

When a question can't be answered confidently from this file, go to the specific numbered doc above rather than guessing — each one is more detailed and is the actual source of truth for its area.
