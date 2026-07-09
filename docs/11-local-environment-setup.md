# Local Environment Setup

## Document Version

```text
Version: 0.3
Status: Draft / MVP design (architecture decisions applied); Phase 0a implemented
Last updated: 2026-07-07
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-05 | Initial version. Consolidates the local-only folder structure previously described in `06-github-repository-structure.md` ("Local-Only Folders") and `project.md` (§4), plus the dev/prod Supabase environment-variable setup from `04-etl-pipeline-design.md`, into one dedicated reference. `06` and `project.md` now point here instead of each carrying their own copy. |
| 0.2 | 2026-07-07 | Clarified that rerun-suffix/canonical-file immutability logic applies to the FTP archive only; local data/raw/ is a plain overwrite-on-rerun working copy, since it's never the durable or load-source copy of record for reruns. |
| 0.3 | 2026-07-07 | Corrected `FTP_REMOTE_PATH`/`FTP_PASSWORD` references to the actual, already-tested `FTP_REMOTE_DIR`/`FTP_PASS` names (matching `04` v0.5, `05` v0.3, `06` v0.6, `07` v0.5); clarified that the FTP side of the archive is flat (`price_guides/`, `product_catalogs/` directly under `FTP_REMOTE_DIR`), distinct from and unaffected by the local nested `data/raw/cardmarket/pokemon/...` working-copy convention described below. |

## Purpose

`06-github-repository-structure.md` documents the **Git repository** — everything a fresh `git clone` produces. This document covers everything else: the folders, files, and environment variables that exist **only on your local machine**, are deliberately excluded from Git via `.gitignore`, and that you (or your scripts) create yourself.

A fresh clone of the repository will not have any of the folders described here. That's expected, not a sign something is missing.

---

## 1. Relationship to the Git Repository

```text
Git repository (see 06):        docs/, sql/, src/, tests/, .github/,
                                  data/sample/, data/import_templates/,
                                  README.md, LICENSE, .gitignore, .env.example

Local-only (this document):      data/raw/, data/imports/, data/exports/,
                                  db/backups/ (contents, not the folder itself),
                                  logs/, .venv/, .env
```

The dividing line is simple: if it's real data, a secret, a generated log, or a local dependency environment, it's local-only. If it's code, SQL, documentation, or a small safe-to-share sample, it's in the repo.

---

## 2. Full Local Folder Tree

```text
pokemon-cardmarket-bi/                      (git repo root)
│
├── [everything in 06-github-repository-structure.md's tree]
│
├── data/
│   ├── sample/                             tracked
│   ├── import_templates/                   tracked
│   │
│   ├── raw/                                LOCAL ONLY — gitignored
│   │   └── cardmarket/pokemon/
│   │       ├── price_guides/
│   │       │   ├── price_guide_6_2026-07-03.json
│   │       │   ├── price_guide_6_2026-07-04.json
│   │       │   └── ...
│   │       └── product_catalogs/
│   │           ├── products_singles_6_2026-07-01.json
│   │           ├── products_nonsingles_6_2026-07-01.json
│   │           └── ...
│   │
│   ├── imports/                            LOCAL ONLY — gitignored
│   │   └── collection/
│   │       ├── incoming/
│   │       ├── processed/
│   │       └── failed/
│   │
│   └── exports/                            LOCAL ONLY — gitignored
│
├── db/
│   └── backups/                            folder + README.md tracked;
│       └── *.sql.gz                        dump files gitignored
│
├── logs/                                   LOCAL ONLY — gitignored
│   ├── ingestion/
│   ├── validation/
│   └── collection_import/
│
├── .venv/                                  LOCAL ONLY — gitignored (Python virtual env)
└── .env                                    LOCAL ONLY — gitignored (real secrets)
```

---

## 3. Folder-by-Folder Purpose

### `data/raw/`

~~The real raw archive — dated JSON files exactly as downloaded, following the immutability and rerun-suffix rules defined in `05-raw-archive-strategy.md`. This is a **local working copy**; the durable, long-term archive is wherever `FTP_HOST`/`FTP_REMOTE_PATH` actually points (or an object storage bucket, once that's finalized). Local disk alone is not durable enough for the one thing this project is built around not losing.~~

The local working copy of the daily download — dated JSON files, overwritten on rerun (no suffix logic locally). The durable archive with immutability/rerun-suffix rules is FTP (`FTP_HOST`/`FTP_REMOTE_DIR` — corrected in v0.3; not `FTP_REMOTE_PATH`, see below), per 05-raw-archive-strategy.md — that's the copy the immutability rule actually protects. The load step reads directly from this local file, since it's always the latest attempt for that date; FTP's suffixed history is for audit/durability only and is never read back for loading.

**One more distinction, also corrected in v0.3:** the local tree above is nested (`data/raw/cardmarket/pokemon/price_guides/...`), but the actual FTP side is flat — `price_guides/` and `product_catalogs/` sit directly under `FTP_REMOTE_DIR`, with no `cardmarket/pokemon/` nesting on the FTP account itself (see `05-raw-archive-strategy.md` v0.3). The local nested path is just this project's own working-folder convention and is unaffected by that correction; only the FTP-side path changed.

### `data/imports/collection/{incoming,processed,failed}`

Personal filing convenience for collection CSV/Excel files — **not** a second source of truth. The real status of an import row lives in `collection_import_staging.matchStatus` (see `08-collection-import-flow.md`). Moving a file from `incoming/` to `processed/` or `failed/` is just how you keep track of which files you've already run, not something any script depends on.

```text
incoming/    files you haven't imported yet
processed/   files whose batch fully resolved (ready_to_import / imported)
failed/      files whose batch had rows ending in needs_review / error
             and still need attention
```

A file can move to `processed/` even if a few of its rows are sitting in `waiting_for_product` — that's an expected timing state, not a failure (see `08`).

### `data/exports/`

Ad hoc CSV exports from BI views (`vw_collection_current_value`, `vw_collection_summary`, etc.) for your own use — reporting, sharing, or just eyeballing data outside a SQL client. Nothing reads from this folder; it's an output-only convenience.

### `db/backups/`

Manual `pg_dump` backups of the **prod** Supabase project. The folder and its `README.md` are tracked in Git; the actual `.sql.gz` dump files are not (see `06`, `.gitignore`). Full command, connection-string requirements, recommended flags, and cadence are documented once, in `04-etl-pipeline-design.md` ("Backing up the prod project") — this document doesn't repeat them.

### `logs/`

Local run logs when scripts are executed manually outside GitHub Actions (which has its own logs in the Actions UI). Organized to mirror `src/ingestion`, `src/transform` (validation), and `src/collection`.

### `.venv/`

Standard Python virtual environment. Created via `python -m venv .venv`; never committed.

### `.env`

Your real secrets and connection strings, copied from `.env.example` and filled in. Never committed. See §4 below for exactly which values go here versus in GitHub Actions secrets.

---

## 4. Environment Variables: Local vs. GitHub Actions vs. Two Supabase Projects

Full reasoning lives in `04-etl-pipeline-design.md` ("Two Supabase projects: dev and prod") and `06-github-repository-structure.md` (`.env.example` section) — this is the short version, kept here because it's the thing most likely to get mixed up when actually sitting down at your machine:

```text
Same variable name, different value depending on WHERE it's set:

  DATABASE_URL
    in your local .env              → points at the DEV Supabase project
    as a GitHub Actions secret       → points at the PROD Supabase project

  DATABASE_URL_BACKUP
    Session Pooler connection string (not the transaction pooler used by
    DATABASE_URL above) for whichever project you're backing up —
    normally PROD. Only needed when you're actually running a backup,
    locally or as a GitHub Actions secret if backup-database.yml exists.
```

Never let `DATABASE_URL` in your local `.env` accidentally point at prod — the entire reason the dev project exists is so local development/testing can't touch the historical dataset that must not be lost.

## FTP Connection Requirements

The FTP account used for the raw archive (see 05-raw-archive-strategy.md)
requires explicit FTP over TLS (FTPS) — plain unencrypted ftp:// connections
are rejected by the server with a 530 authentication error, even with
correct credentials. Any tool connecting to FTP_HOST must support and enable
explicit FTPS.

For manual testing with curl:
  curl --ssl-reqd -u FTP_USER:FTP_PASS ftp://FTP_HOST/

This is specific to the current hosting provider's server configuration,
not a general project requirement — but it's easy to lose an hour to if
you (or a future contributor) assume plain FTP works.

---

## 5. What Backs Up What

| Data | Where it lives | What actually protects it |
|---|---|---|
| Raw JSON archive | `data/raw/` locally + FTP/object storage | Immutability + rerun-suffix rule (`05`); can rebuild `price_snapshots` from it via the reprocessing sketch (`04`) if ever needed |
| Dev database | Supabase dev project | Nothing — safe to break, reset, or reload at any time, by design |
| Prod database | Supabase prod project | Manual weekly `pg_dump` → `db/backups/` → synced off-machine (`04`) |
| Collection data specifically | `collection_items` table, prod project | Same `pg_dump` backup — this is the one thing that genuinely can't be regenerated from anywhere else |
| Code, SQL, docs | Git repository | Pushing to GitHub regularly — that's the whole point of the repo existing |

---

## 6. First-Time Local Setup Checklist

```text
[ ] confirm FTP connection requires explicit FTPS — test with:
    curl --ssl-reqd -u FTP_USER:FTP_PASS ftp://FTP_HOST/${FTP_REMOTE_DIR}/
[ ] git clone the repository
[ ] cp .env.example .env — fill in DEV Supabase DATABASE_URL, FTP
    credentials, Cardmarket source URLs
[ ] python -m venv .venv && source .venv/bin/activate
[ ] pip install -r requirements.txt
[ ] mkdir -p data/raw/cardmarket/pokemon/price_guides
    data/raw/cardmarket/pokemon/product_catalogs
    data/imports/collection/incoming data/imports/collection/processed
    data/imports/collection/failed data/exports
    logs/ingestion logs/validation logs/collection_import
[ ] apply sql/schema/*.sql to the DEV Supabase project
[ ] apply the same sql/schema/*.sql to the PROD Supabase project
    (once it's ready to receive real scheduled runs)
[ ] confirm DATABASE_URL_BACKUP (Session Pooler, prod) works with a test
    pg_dump before you need it for real
```

`db/backups/` itself is created by cloning the repo (the folder and its `README.md` are tracked); it's listed above only as a reminder to verify the backup connection string works, not because the folder needs creating.
