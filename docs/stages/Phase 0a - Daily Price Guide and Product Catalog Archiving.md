# Phase 0a — Daily Price Guide & Product Catalog Archiving

## Document Version

```text
Version: 0.1
Status: Complete — implemented, tested, running against real FTP account
Last updated: 2026-07-15
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-15 | Initial version, written once Phase 0a was confirmed implemented. Consolidates `DECISIONS.md` §1–§12 (code repository) into a single stage summary for `docs/stages`. |

## Purpose

This document is a **stage summary**, not a design doc. It records what Phase 0a actually covers, what was built, and the exact line where Phase 0a ends and Phase 0b begins. The authoritative design reasoning lives in `01-mvp-scope.md`, `04-etl-pipeline-design.md`, `05-raw-archive-strategy.md`, `07-github-actions-logic.md`, and the implementation-time decisions in `DECISIONS.md` (code repository) — this doc references them rather than repeating them, per the project's own rule against defining the same thing in two places.

## Scope Statement

```text
Phase 0a = prove that raw Cardmarket files are downloaded and archived reliably, immutably, and idempotently — nothing past that.
```

Matches `project.md`'s phase label and `DECISIONS.md` §2's own framing: archiving reliably is the thing being proven first.

## What Is In Scope (Built)

Two runnable ingestion pipelines, mirroring each other in shape:

```text
download -> local save (dated filename, rerun-suffixed if needed)
         -> FTP upload
         -> Telegram notify (optional, non-blocking)
```

### 1. Daily price guide pipeline

```text
src/ingestion/download_price_guide.py
.github/workflows/daily-price-guide.yml
```

- Downloads `price_guide_6.json` (URL now has a default in `config.py`, still overridable — `DECISIONS.md` §9)
- Computes `snapshot_date` via `get_pipeline_date()` (Europe/Vienna, no exceptions)
- Saves as `price_guide_6_YYYY-MM-DD.json`, or a rerun-suffixed copy via `next_filename_for_upload()` if a file for that date already exists
- Uploads to `{FTP_REMOTE_DIR}/price_guides/` over explicit FTPS (`ftplib.FTP_TLS`)
- Sends a Telegram notification on success and on failure (`notify_telegram`)

### 2. Weekly product catalog pipeline

```text
src/ingestion/download_product_catalogs.py
.github/workflows/product-catalog.yml
```

- Downloads `products_singles_6.json` and `products_nonsingles_6.json`, weekly (every Friday — changed from an original twice-monthly plan, `DECISIONS.md` §11 Decision A)
- Same dated-filename / rerun-suffix / FTP-upload / Telegram-notify shape as the daily pipeline
- **Partial-failure rule at the archive stage:** singles and non-singles are archived fully independently — a failure on one never blocks archiving the other (`DECISIONS.md` §11 Decision B). This is an archive-stage rule only; it does **not** override the DB-load "all-or-nothing" rule in `04`/`07`, which applies once Phase 0b builds the load step.
- Run still exits non-zero and sends a "PARTIAL FAILURE" Telegram message if either file failed, so it stays visible.

### 3. Shared FTP helper

```text
src/utils/ftp_client.py
    connect_ftp()
    list_remote_filenames(ftps, remote_dir)
    upload_to_ftp(ftps, local_path, remote_dir, remote_filename)
```

Originally duplicated verbatim between both scripts as deliberate short-term debt (`DECISIONS.md` §11 Decision C), extracted once the catalog script was equally proven (`DECISIONS.md` §12). Both ingestion scripts now import from here instead of defining their own copies. No existing tests needed changes — both test files patch the names at the *ingestion* module's namespace, which `from ... import` preserves.

### 4. Telegram notifications

- Fired once at the end of a successful run, once in the top-level exception handler on failure (`DECISIONS.md` §10)
- `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are **optional** — read via `os.environ.get`, default to `None`; if either is unset, `notify_telegram()` logs and returns without raising
- Never blocks or fails the archiving run — the pipeline's exit code is the real success/failure signal, the Telegram message is a convenience layered on top
- Success message includes date, filename, byte size; item count is a deliberate `"TBD"` placeholder pending confirmation of `price_guide_6.json`'s root JSON structure (bare array vs. wrapper object) — see "Known Open Item" below

## What Is Explicitly Out of Scope (Deferred to Phase 0b+)

Per `DECISIONS.md` §2, referencing `04-etl-pipeline-design.md`'s 10-step daily pipeline, steps 5–8 are **not** built yet:

```text
5. Validate JSON structure
6. Validate required fields
7. Normalize field names (avg-holo -> avg_holo, etc.; product_group/source_file enrichment)
8. Load into price_snapshots / products
```

Also not built: any Supabase schema (`sql/schema/001`–`006`), `src/transform/`, `src/load/`, data quality checks, `waiting_for_product` staging recheck. No database writes happen anywhere in Phase 0a.

## Real-World Corrections Made During Implementation

These are genuine implementation-time decisions, not oversights — each is logged in `DECISIONS.md` and has since been back-ported into the corresponding numbered doc(s):

| # | What changed | Why | Where corrected |
|---|---|---|---|
| 1 | Five separate helper modules consolidated into two runnable scripts | Portfolio deliverable needs "download today's file to FTP," not "here are 5 files" | `DECISIONS.md` §1 |
| 2 | FTP folder layout: flat, not `/raw/cardmarket/pokemon/...` nested | Real FTP account (`FTP_REMOTE_DIR=/`) has `price_guides/`/`product_catalogs/` at root; nested path was never built | `DECISIONS.md` §3; `05` v0.3 |
| 3 | Env var names: `FTP_PASS`/`FTP_REMOTE_DIR`, not `FTP_PASSWORD`/`FTP_REMOTE_PATH` | Real, already-provisioned GitHub secrets use the shorter names | `DECISIONS.md` §7; `06`/`07`/`11` |
| 4 | Product catalog cadence: weekly (Friday), not twice-monthly (1st/15th) | Genuine decision change during build, not an error fix | `DECISIONS.md` §11 Decision A; `01`/`04`/`05`/`07` |
| 5 | `CARDMARKET_PRICE_GUIDE_URL` now has a real default | URL is known, not sensitive, and a wrong/missing value fails loudly rather than silently corrupting data | `DECISIONS.md` §9 |
| 6 | Telegram notifications added (not in any versioned design doc) | Convenience layer, optional and non-blocking by design | `DECISIONS.md` §10 |
| 7 | FTP helpers duplicated first, then extracted to `src/utils/ftp_client.py` | Avoided touching a working, tested script mid-build; extracted once both scripts were proven | `DECISIONS.md` §11 Decision C, §12 |

## Known Open Item Carried Into Phase 0b

The Telegram success message's item-count field is `"TBD"` because `price_guide_6.json`'s root JSON structure (bare array vs. wrapper object with a key) has not been confirmed (`DECISIONS.md` §10 Decision B). This is not just a notification cosmetic issue — the same structural fact is required to write `src/transform/` in Phase 0b (validation and field normalization both need to know how to walk the file). **Recommended: confirm this before starting Phase 0b transform work**, rather than deferring it again.

## Exit Criteria (How We Know Phase 0a Is Actually Done)

```text
Daily script runs end-to-end against the real FTP account: download ->
  dated archive (or rerun-suffixed copy) -> FTP upload -> Telegram notify
Weekly catalog script runs end-to-end for both singles and non-singles,
  independently archiving each even if one fails
Rerun-suffix logic verified: a second run on the same date produces
  _rerun-01, not a silent overwrite
FTP connection uses explicit FTPS (ftplib.FTP_TLS), confirmed against the
  provider (plain ftp:// returns 530)
Shared FTP client extracted and both scripts' existing tests still pass
  unmodified
Telegram notifications fire on both success and failure paths without
  ever blocking the pipeline's own exit code
```

All of the above are satisfied as of this writing — see `project.md` §16 (Decision Log) for the consolidated cross-reference.

## What Comes Next

**Phase 0b — validate → transform → load into the database:**

```text
1. Stand up Supabase (dev + prod projects), apply sql/schema/001-006
2. Build src/transform/ (JSON validation, required-field checks,
   hyphenated field normalization, product_group/source_file enrichment)
3. Build src/load/ (canonical-file resolution, upsert into price_snapshots
   by snapshot_date+id_product, upsert into products by id_product,
   waiting_for_product recheck, data quality checks per 04's
   failure/warning thresholds)
```

See `04-etl-pipeline-design.md` for the full step list and `project.md` §5–§7 for the schema and pipeline reference.
