# Raw Archive Strategy

## Document Version

```text
Version: 0.4
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-14
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial raw archive strategy |
| 0.2 | 2026-07-04 | Resolved immutability/overwrite contradiction with rerun-suffixed files, added archive-gap handling, a reprocessing sketch, an explicit retention policy, and a cross-reference to the ETL doc for the full data quality check list, based on architecture review |
| 0.3 | 2026-07-12 | Two corrections made once the FTP account was actually provisioned and the pipeline built, both logged in `DECISIONS.md` in the code repository: (1) folder structure corrected from a nested `/raw/cardmarket/pokemon/...` path (never actually built) to the real flat layout — `price_guides/` and `product_catalogs/` directly under the FTP account root; (2) product catalog cadence changed from twice-monthly (1st/15th) to weekly (every Friday) — a genuine decision change, not an error fix. |
| 0.4 | 2026-07-14 | Renamed all field-name references from camelCase to `snake_case` (e.g. `idProduct` → `id_product`, `productGroup` → `product_group`), matching the project-wide database naming decision in `02-data-model.md` v0.5 / `03-data-dictionary.md` v0.5. This document only references fields in passing (mostly around `products`/`price_snapshots` enrichment metadata) rather than defining them, so only spelling changed. |

## Purpose

The raw archive is the first persistent layer of the project.

Its goal is to store original Cardmarket JSON files exactly as they were downloaded, before any validation, cleaning, normalization, or database loading happens.

This is important because the project creates its own historical dataset from daily Cardmarket snapshots. Since the Cardmarket price guide is only a daily file and not a historical API, price history exists only if the files are downloaded and saved consistently over time.

The raw archive makes the project:

- reproducible
- auditable
- easier to debug
- safer against transformation errors
- more realistic as a data engineering portfolio project

The raw archive is not intended to be queried directly for analytics. It is the source-of-truth storage layer for downloaded files.

---

## Raw Data Sources

The MVP uses official downloadable Cardmarket JSON files for Pokémon.

### Daily price guide

```text
price_guide_6.json
```

This file contains the current daily price guide for Pokémon products.

It is downloaded once per day and stored as a dated snapshot.

### Product catalogs

```text
products_singles_6.json
products_nonsingles_6.json
```

These files contain product metadata for Pokémon singles and non-single products.

They are downloaded weekly (every Friday) because product catalog information changes much less frequently than prices, though weekly still keeps metadata reasonably fresh. This cadence is a project decision, not something Cardmarket requires, and was changed from an original twice-monthly (1st/15th) plan to weekly during implementation (see `DECISIONS.md` §11 in the code repository) — see the ETL pipeline design doc for the known limitation this creates around newly released products.

---

## Archive Design

The raw archive uses a simple folder structure with dated filenames.

The project does not use deeply nested year/month/day folders in the MVP. A flat folder with clear filenames is easier to understand, easier to inspect manually, and sufficient for the expected project size.

---

## Folder Structure

**Corrected in v0.3** (see `DECISIONS.md` §3 in the code repository): this
is the real, already-provisioned flat layout. An earlier draft of this doc
specified a nested `/raw/cardmarket/pokemon/...` path, written before the
FTP account existed — that nested path was never actually built. The
implementation follows the real server layout below.

```text
{FTP_REMOTE_DIR}/
  price_guides/
  product_catalogs/
```

`FTP_REMOTE_DIR` is the FTP account's configured root path (see
`.env.example` / GitHub Actions secrets in `06-github-repository-structure.md`).

### Price guide archive

Daily price guide files are stored in:

```text
{FTP_REMOTE_DIR}/price_guides/
```

Filename pattern:

```text
price_guide_6_YYYY-MM-DD.json
```

Example:

```text
{FTP_REMOTE_DIR}/price_guides/price_guide_6_2026-07-03.json
```

### Product catalog archive

Product catalog files are stored in:

```text
{FTP_REMOTE_DIR}/product_catalogs/
```

Filename patterns:

```text
products_singles_6_YYYY-MM-DD.json
products_nonsingles_6_YYYY-MM-DD.json
```

Examples (dates reflect the weekly/Friday cadence — see "Download Frequency" below):

```text
{FTP_REMOTE_DIR}/product_catalogs/products_singles_6_2026-07-03.json
{FTP_REMOTE_DIR}/product_catalogs/products_nonsingles_6_2026-07-03.json
{FTP_REMOTE_DIR}/product_catalogs/products_singles_6_2026-07-10.json
{FTP_REMOTE_DIR}/product_catalogs/products_nonsingles_6_2026-07-10.json
```

---

## Download Frequency

The project has two separate raw archive flows.

### Daily price guide

```text
price_guide_6.json
```

Recommended schedule:

```text
daily
```

Reason:

Cardmarket updates the price guide daily. Saving this file every day creates the historical price dataset used later for trend analysis, valuation, and BI reporting.

### Product catalogs

```text
products_singles_6.json
products_nonsingles_6.json
```

Recommended schedule:

```text
weekly
```

Suggested day:

```text
every Friday
```

Reason:

Product metadata does not need to be downloaded every day. New products are added mainly around new product releases, while prices change much more frequently. Weekly was chosen over an original twice-monthly plan during implementation (see `DECISIONS.md` §11 in the code repository) — still far less frequent than the daily price guide, but fresh enough to keep catalog staleness to about a week at worst.

**If a scheduled catalog run fails or is missed:** the catalog simply remains stale until the next scheduled Friday, or until it is manually rerun. There is no automatic retry in the MVP — see the ETL pipeline design doc for the full failure-handling rule.

---

## Pipeline Order

On days when both the product catalog pipeline and the daily price guide pipeline run, the recommended order is:

```text
1. Product catalog pipeline
2. Daily price guide pipeline
```

Reason:

A newly released product may appear in the price guide. Running the product catalog pipeline first increases the chance that the local `products` table already contains the product metadata before the price snapshot is loaded.

This does not fully eliminate temporary mismatches, but it reduces them.

---

## Raw Archive Rules

Archived raw files should be treated as immutable data.

The MVP follows these rules:

```text
Do not edit archived raw files.
Do not normalize archived raw files.
Do not manually clean archived raw files.
Do not silently overwrite an existing dated archive file.
```

Raw files should represent exactly what was downloaded from Cardmarket.

Any cleaning, renaming, validation, or transformation happens later in the ETL process, not inside the raw archive.

---

## Same-Date Reruns

An earlier version of this design allowed a same-date rerun to silently overwrite the existing archive file for that date, which directly contradicted the immutability rule above: if Cardmarket's price actually changes between two runs on the same day, silently overwriting would discard the first version with no trace it ever existed. That contradiction is resolved as follows.

**Rule:**

```text
If a pipeline for a given date is rerun and a file for that date already
exists, the rerun is saved as a suffixed copy rather than replacing the
original:

price_guide_6_2026-07-03.json            (first run)
price_guide_6_2026-07-03_rerun-01.json   (first rerun)
price_guide_6_2026-07-03_rerun-02.json   (second rerun, if it happens)
```

The same pattern applies to product catalog files.

**Canonical file:**

```text
The canonical file for a given date is the most recent successful run: the
highest-numbered rerun file if any exist, otherwise the base file. The
database always loads from the canonical file. Non-canonical (superseded)
files remain on disk for audit and debugging but are not loaded.
```

**What this costs:**

```text
The MVP does not build a manifest or log table recording which file is
canonical for a given date, or why a rerun happened — that determination is
made by filename convention (highest rerun suffix wins) at load time, not
recorded as a queryable fact. This means there is no first-class answer to
"was this date's data corrected mid-day, and why?" beyond noticing multiple
files exist for that date. A future archive_manifest table (see Later
Improvements) would close this gap; it is deliberately deferred for MVP
simplicity.
```

This keeps the MVP simple while making "immutable" mean the same thing everywhere in the project: nothing in the raw archive is ever silently discarded or replaced.

---

## Why Not Timestamp Every File in the MVP?

A more advanced naming pattern could include the exact download time.

Example:

```text
price_guide_6_2026-07-03_08-30-00.json
```

This would preserve every rerun separately.

However, for the MVP, this is not necessary because the goal is to store one official canonical daily snapshot per day, with reruns as suffixed exceptions rather than the normal case. Using rerun counters instead of full timestamps keeps the common case (one file per day) visually simple while still never discarding data.

Full timestamped filenames can be added later if the project needs:

- multiple *routine* (not exceptional) downloads per day
- retry comparison
- audit-level traceability
- detection of intra-day source changes
- safer manual reruns beyond what the rerun-suffix convention already provides

---

## Why Use One Folder for Product Catalogs?

Both catalog files are stored in the same folder:

```text
{FTP_REMOTE_DIR}/product_catalogs/
```

This is intentional.

The filenames already clearly identify the file type:

```text
products_singles_6_YYYY-MM-DD.json
products_nonsingles_6_YYYY-MM-DD.json
```

Using one folder keeps the archive simple and avoids unnecessary nesting.

Singles and non-singles are downloaded together on the same schedule and later merged into one unified `products` table, so storing them in the same raw archive folder is logical for the MVP.

---

## Archive Gaps in the Historical Timeline

The historical price dataset only exists because files are downloaded and saved consistently over time — but consistency will not be perfect in practice (outages, failed runs, GitHub Actions issues).

**Decision:**

```text
A missing date in the archive means no snapshot was captured that day. This
is a known and accepted limitation of building history from daily snapshots,
not a bug to reconcile after the fact.

The MVP does not assume a missed Cardmarket snapshot can be recovered later
(Cardmarket does not expose historical data through the daily file), and does
not build automated backfill. Gaps are surfaced through archive completeness
checks and documented as a known data limitation, both in the data dictionary
and in the project README.
```

This applies the same "prevent, don't rely on recovering" philosophy as the same-date rerun handling above: the MVP's honesty about the archive's limitations is treated as more valuable than pretending gaps can always be fixed later.

---

## Relationship to the Database

The raw archive is separate from the normalized database.

Raw files are first downloaded and archived. Only after that does the pipeline validate and load them into database tables.

### Price guide loading

```text
price_guide_6_YYYY-MM-DD.json (canonical file for that date)
→ validation
→ field normalization
→ price_snapshots
```

The raw file keeps the original Cardmarket field names, including hyphenated fields such as:

```text
avg-holo
low-holo
trend-holo
avg1-holo
avg7-holo
avg30-holo
```

These fields are normalized only during transformation:

```text
avg-holo      → avg_holo
low-holo      → low_holo
trend-holo    → trend_holo
avg1-holo     → avg1_holo
avg7-holo     → avg7_holo
avg30-holo    → avg30_holo
```

### Product catalog loading

```text
products_singles_6_YYYY-MM-DD.json (canonical)
products_nonsingles_6_YYYY-MM-DD.json (canonical)
→ validation
→ product_group/source_file enrichment
→ products
```

During loading, the pipeline adds project-specific metadata:

```text
product_group
source_file
is_active_in_catalog
first_seen_at
last_seen_at
updated_at
```

These fields do not exist in the raw files. They belong to the normalized database layer.

---

## Handling Missing Product Metadata

The price guide is downloaded daily, while product catalogs are downloaded only weekly (every Friday).

Because of this, the price guide may temporarily contain an `id_product` that is not yet available in the local `products` table.

For this reason, the MVP does not enforce a strict database foreign key from:

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

This makes the pipeline more robust while still preserving a clear logical relationship between prices and products. The same timing gap is why `collection_import_staging` has a dedicated `waiting_for_product` status — see the data model and ETL pipeline docs for details.

---

## Reprocessing From the Archive (Sketch)

Being able to reprocess history is one of the archive's stated goals, so it deserves at least a sketch of how it would actually work, even though full automation is not built in the MVP.

```text
1. Select an archived raw file (or a date range of files).
2. Read the raw JSON directly from the archive — no re-download needed, since
   the point of the archive is that the original data is already preserved.
3. Run the current (possibly updated/fixed) validation and transformation
   logic against it.
4. Upsert the result into the target table (price_snapshots by
   snapshot_date + id_product, or products by id_product).
5. Run the standard data quality checks against the reprocessed data.
```

```text
Reprocessing reads raw files; it never edits them. This is consistent with
the immutability rule above, and is the entire reason the archive exists in
the first place: if transformation logic turns out to be wrong, historical
data can be corrected by replaying the archive with fixed logic, instead of
being permanently wrong or requiring re-downloading data that Cardmarket may
no longer expose (since it only serves a current daily snapshot, not
history).
```

---

## Data Quality Checks

The raw archive supports later data quality checks. The full check list and the failure-vs-warning thresholds that apply to them are maintained in `04-etl-pipeline-design.md`, to avoid this list drifting out of sync with that one. At the archive level specifically, the checks that matter most are:

```text
Was today's price guide downloaded and archived?
Was the archive file for today's date the canonical one (or a rerun copy)?
Were product catalog files downloaded and archived on scheduled catalog days?
Is there a gap (missing date) in the archive timeline?
```

The goal is not to build a complex monitoring system in the MVP.

The goal is to make the pipeline reliable enough to trust the historical data being collected — and to be honest, in the documentation, about the gaps that will inevitably still occur.

---

## MVP Scope

The MVP raw archive includes:

```text
Daily archived price guide files
Twice-monthly archived product catalog files
Flat folder structure
Dated filenames
Rerun-suffixed files instead of silent overwrites
Raw files kept unchanged
Basic validation before database loading
Logical separation between raw files and normalized tables
```

The MVP does not include:

```text
Timestamped archive versions for every routine run (only for reruns, via
  the rerun-NN suffix)
Complex partitioned folder structures
Cloud data lake architecture
Raw archive compression
Checksum-based file deduplication
Advanced lineage tracking
Automated rollback system
Automated backfill of missing archive dates
An archive_manifest table recording canonical/rerun status as queryable data
```

These features can be considered later if the project grows.

---

## Retention Policy

```text
No deletion or retention limit is applied during the MVP. Raw daily snapshots
and catalog files (including rerun copies) are kept indefinitely while
storage volume remains manageable. This is a conscious decision, not an
oversight, and will be revisited once real file sizes and growth rates are
observed.

The full raw archive is not committed to Git — it lives on the archive
storage location (e.g. FTP/object storage). Small representative sample
files may be committed for documentation and testing purposes.
```

---

## Later Improvements

Possible future improvements include:

```text
Full timestamped filenames for every routine run (not just reruns)
Year/month folder partitioning
File checksums
Archive compression
Raw file manifest table (canonical/rerun status, download metadata, as
  queryable data instead of filename convention)
Download status logs
Failed download retry tracking
Source file size tracking
Data lineage metadata
Automatic alerts when files are missing
Automated reprocessing/replay tooling built on the sketch above
Retention policy with actual limits, once real growth is observed
```

A possible future structure could look like this:

```text
/raw/cardmarket/pokemon/price_guides/year=2026/month=07/
  price_guide_6_2026-07-03_08-30-00.json
```

This is intentionally not part of the MVP because it would add complexity before the project needs it.

---

## Design Decision Summary

The raw archive strategy is intentionally simple, while treating "immutable" as a rule that must hold everywhere it's claimed — including reruns.

The project stores one canonical daily price guide snapshot and two canonical product catalog snapshots per month using dated filenames, with rerun-suffixed copies (never silent overwrites) when a pipeline for a given date is repeated. Gaps in the timeline are accepted and documented rather than backfilled.

This creates a reliable, honestly-scoped historical data foundation without overengineering the storage layer.

The raw archive is easy to explain, easy to inspect, and realistic for a learning-focused data engineering / BI portfolio project.
