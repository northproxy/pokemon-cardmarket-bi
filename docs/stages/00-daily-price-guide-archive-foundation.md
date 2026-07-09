# Stage 0: Daily Price Guide Ingestion & Archive Foundation

## Status

Completed, for the scope this stage was defined to cover (Phase 0a per
`project.md` / `DECISIONS.md` §2: "daily price guide archiving").

The GitHub Actions workflow `daily-price-guide.yml` runs on schedule and on
manual dispatch, downloads the daily Pokémon price guide
(`price_guide_6.json`), saves a local working copy, and uploads it to the
FTP archive with rerun-suffix protection. Confirmed by a successful
production run and by unit tests covering the orchestration logic, the
Europe/Vienna date computation, and the archive filename rules.

**Deliberately out of scope for this stage** (`DECISIONS.md` §2): JSON
validation, required-field validation, holo field normalization, and
loading into `price_snapshots` — steps 5–8 of `04-etl-pipeline-design.md`'s
10-step daily pipeline. This matches the project's own stated phase
boundary; it's a scope cut, not an oversight, and Phase 0b+ picks these up.

---

## Stage Goal

Get the single most important automation in the project running reliably:
downloading and preserving the daily Cardmarket Pokémon price guide so that
historical price data can be built up over time. Per `01-mvp-scope.md`,
this is the core MVP deliverable — without it, a missed day's price history
is permanently lost (Cardmarket exposes only a current daily snapshot, not
history).

Confirmed scope for Stage 0 specifically:

```text
price_guide_6.json (Cardmarket, Pokémon price guide)
        ↓
GitHub Actions scheduled workflow (daily-price-guide.yml)
        ↓
snapshotDate computed in Europe/Vienna (date_helpers.get_pipeline_date)
        ↓
local working copy saved (plain overwrite on rerun)
        ↓
FTP archive upload (canonical filename, or rerun-suffixed if one already
  exists for that date — archive_filenames.next_filename_for_upload)
        ↓
[Stage 0 ends here — validate/transform/load are Phase 0b+]
```

---

## Main Decision

Automation is GitHub Actions as scheduler only; FTP is the durable raw
archive; the database (not touched by this stage) is the normalized
analytical layer — per `project.md` §9 and `07-github-actions-logic.md`.

**Local vs. FTP immutability scope** (matches `11-local-environment-setup.md`
v0.2): rerun-suffix/canonical-file logic applies to the **FTP archive
only**. The local `data/raw/` working copy is a plain overwrite-on-rerun
copy — never the durable or load-source copy of record for reruns.

**Packaging note** (`DECISIONS.md` §1): the Europe/Vienna date logic,
rerun-suffix filename logic, and FTP upload were each built as their own
small, independently unit-tested module — the right shape per
`02`/`04`/`05`/`07`. `download_price_guide.py` then consolidates them into
one runnable script that imports and calls those helpers rather than
re-deriving the logic inline. This is packaging, not an architecture
change.

---

## Source

Official Cardmarket **Pokémon** price guide:

```text
https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json
```

Matches `01`, `04`, `05`, and `project.md` throughout.

**`CARDMARKET_PRICE_GUIDE_URL` now has a default** (`DECISIONS.md` §9):
previously required with no fallback; now defaults to the real URL above
since it's known and not sensitive, while still overridable via env
var/secret if Cardmarket changes the path. This is a deliberately different
call than `PIPELINE_TIMEZONE`, which has no default on purpose — a wrong
timezone would silently corrupt `snapshotDate`, whereas a wrong/missing URL
here just fails loudly at the HTTP request step. No silent-corruption risk,
so no reason to withhold a sensible default.

**Note:** a Magic: The Gathering price guide URL came up once in
conversation while discussing this stage. It doesn't match anything in the
actual code — every implemented and documented source in this project is
the Pokémon `price_guide_6.json` file. Flagged for the record; no code
change was needed.

---

## Generated Output

**Local working copy:**

```text
data/raw/cardmarket/pokemon/price_guides/price_guide_6_YYYY-MM-DD.json
```

**FTP archive (durable, immutable, rerun-suffixed):**

```text
{FTP_REMOTE_DIR}/price_guides/price_guide_6_YYYY-MM-DD.json
{FTP_REMOTE_DIR}/price_guides/price_guide_6_YYYY-MM-DD_rerun-01.json  (if rerun)
```

**Confirmed deviation from `05-raw-archive-strategy.md`** (`DECISIONS.md`
§3): the actual FTP account has `price_guides/` and `product_catalogs/`
directly at the account root — flatter than `05`'s documented nested
`/raw/cardmarket/pokemon/...` structure. The code follows the real,
already-verified server layout. This is a genuine, unresolved discrepancy,
not a silent choice — `05`'s folder tree should be corrected to the flat
layout next time that doc is touched, since the FTP account is the actual
constraint and `05` was written before the account was provisioned.

---

## Files Involved

### Workflow

```text
.github/workflows/daily-price-guide.yml
```

Daily UTC cron (`0 17 * * *`) + manual `workflow_dispatch`. See DST/Cron
note below.

### Config / environment loading

```text
src/config/config.py
```

Intentionally narrow scope for Phase 0a: `PIPELINE_TIMEZONE`,
`CARDMARKET_PRICE_GUIDE_URL`, `FTP_HOST`, `FTP_USER`, `FTP_PASS`,
`FTP_REMOTE_DIR`. `DATABASE_URL` and other `CARDMARKET_*_URL` values are
deliberately not stubbed out ahead of time.

### Ingestion entry point

```text
src/ingestion/download_price_guide.py
```

Download → local save → FTP upload, using FTPS (`AUTH TLS` + `PROT P`) via
stdlib `ftplib.FTP_TLS` — no new dependency needed for this, per
`DECISIONS.md` §5, to satisfy the explicit-FTPS requirement in `11`.
`requests` handles the HTTP download (`DECISIONS.md` §6 — no doc mandates a
specific library; noted so it lands in `requirements.txt` deliberately).

### Filename logic

```text
src/utils/archive_filenames.py
```

Pure, dependency-free: `build_filename`, `parse_filename`,
`next_filename_for_upload`, `get_latest_file_for_date`. Decides *what
filename to use* given a directory listing; doesn't talk to FTP itself.
`get_latest_file_for_date` isn't used by any load step yet (none exists in
this stage) — reserved for FTP-side audit/inspection.

### Timezone logic

```text
src/utils/date_helpers.py
```

`get_pipeline_date(tz_name, now=None)` — the one shared Europe/Vienna
conversion point, per `07`'s requirement that this not be computed ad hoc
per workflow. Rejects naive datetimes explicitly.

### Tests

```text
tests/conftest.py
tests/test_date_helpers.py
tests/test_archive_filenames.py
tests/test_download_price_guide.py
```

HTTP/FTP calls are mocked — no real network/FTP server used in tests.

### Implementation decision log

```text
DECISIONS.md
```

Running log of implementation-time, code-level decisions for Phase 0a —
explicitly **not** a replacement for the versioned `docs/01`–`11` or
`project.md`, which remain the design source of truth. This stage doc
cites it by section (§1–§9) rather than restating its contents.

---

## Resolved: Environment Variable Naming

**Decision confirmed** (`DECISIONS.md` §7): `FTP_PASS` and `FTP_REMOTE_DIR`
are the correct, intentional names — matching the real, already-tested
GitHub Actions secrets. Code follows the working secret names rather than
the docs.

**Two separate doc issues still outstanding, not one:**

1. **Naming mismatch** (`DECISIONS.md` §7): `06`, `07`, and `11` all
   document `FTP_PASSWORD` / `FTP_REMOTE_PATH` instead of `FTP_PASS` /
   `FTP_REMOTE_DIR`. Needs correcting in all three.
2. **Separate listing gap in `06`** (`DECISIONS.md` §4): independent of the
   naming question, `07` lists `FTP_PASSWORD` as a required secret
   alongside `FTP_HOST`/`FTP_USER`/`FTP_REMOTE_PATH`, but `06`'s own
   `.env.example` block only shows the latter three — the password entry
   is simply missing from `06`'s listing, not just misnamed. Not a signal
   that it's optional (`config.py` requires it unconditionally); just an
   incomplete enumeration in `06` specifically.

Both are small, low-risk doc fixes — noted so they don't get lost, not
blocking anything currently.

---

## DST / Cron Timing Note

Target schedule intent (`DECISIONS.md` §8): run comfortably after
Cardmarket's ~3pm data refresh, Europe/Vienna time — not a precision
requirement. `17:00 UTC` was chosen because it lands at 19:00 Vienna during
CEST (summer); during CET (winter) the same cron fires at 18:00 Vienna
instead, since GitHub Actions cron is UTC-only and doesn't shift for DST.

This ±1h seasonal drift is accepted rather than solved with a dual-schedule
workaround, because nothing about archive *correctness* depends on it:
`get_pipeline_date()` computes the actual Europe/Vienna calendar date at
whatever instant the job starts, so `snapshotDate` is correct regardless of
which side of the DST boundary the run lands on. Confirmed by
`test_late_utc_evening_in_winter_cet_offset` and the corresponding summer
case in `test_date_helpers.py`.

---

## Secrets Required (confirmed correct)

```text
FTP_HOST
FTP_USER
FTP_PASS
FTP_REMOTE_DIR
```

Non-secret config, currently inlined in the workflow's `env:` block:

```text
PIPELINE_TIMEZONE=Europe/Vienna
CARDMARKET_PRICE_GUIDE_URL=https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json
```

`DATABASE_URL` is not used by this stage.

---

## Validation Result

```text
Production: GitHub Actions run succeeded after FTP_PASS and FTP_REMOTE_DIR
were added as repository secrets.

Unit tests (mocked HTTP/FTP):
  - fetch_price_guide_bytes: returns content on success, raises on empty
    response
  - save_local_copy: writes correct filename, overwrites on rerun (no
    local suffixing)
  - run() orchestration: uploads base filename when nothing exists on FTP
    for that date; uploads rerun-01 when a base file already exists;
    always closes the FTP connection
  - get_pipeline_date: correct across UTC/Vienna day-boundary edge cases in
    both CEST and CET, rejects naive datetimes, supports explicit `now` for
    backfills, isn't accidentally Vienna-specific internally
  - archive filename build/parse/next-filename/latest-file logic: base and
    rerun filenames, zero-padding, cross-prefix isolation (singles vs.
    non-singles), cross-date isolation, unordered/non-contiguous rerun
    listings
```

No data-level validation (JSON structure, required fields, row counts) is
covered — intentionally not part of this stage.

---

## What This Stage Does Not Do

Confirmed out of scope (`DECISIONS.md` §2):

- JSON validation or field normalization (`avg-holo` → `avg_holo`, etc.)
- Loading into `price_snapshots`
- Any data quality checks from `04-etl-pipeline-design.md`
- The product catalog pipeline (separate workflow, twice-monthly)
- Collection import or analytics signal logic

---

## Recommended Repository Placement

```text
docs/stages/
├── 00-daily-price-guide-archive-foundation.md   (this file)
├── 01-pokemon-tcg-sets-reference.md
├── 02-cardmarket-product-catalog-foundation.md
└── README.md
```

`01`/`02` belong to a separate reference-data track (Pokémon TCG sets →
Cardmarket mapping); this `00` file belongs to the core ingestion pipeline
track. Both currently share `docs/stages/` — worth revisiting the folder
split once more stage docs accumulate on either track.

---

## Stage 0 Completion Checklist

- [x] GitHub Actions workflow created and triggers correctly (schedule +
      manual dispatch).
- [x] Required environment variables identified and confirmed correct
      (`FTP_PASS`, `FTP_REMOTE_DIR`).
- [x] Secrets configured in GitHub Actions.
- [x] Workflow run completes successfully end-to-end.
- [x] Local working copy saved (plain overwrite on rerun) — confirmed by
      test.
- [x] FTP archive upload with rerun-suffix protection — confirmed by test.
- [x] `snapshotDate` (Europe/Vienna, DST-aware) computation — confirmed by
      test across CEST/CET boundary cases.
- [x] Archive filename build/parse/next-filename logic — confirmed by
      test, including cross-prefix and cross-date isolation.
- [x] `DECISIONS.md` reviewed and cross-referenced directly in this doc.
- [ ] `06`/`07`/`11` updated: `FTP_PASSWORD`/`FTP_REMOTE_PATH` →
      `FTP_PASS`/`FTP_REMOTE_DIR`.
- [ ] `06`'s `.env.example` listing updated to include the FTP password
      entry at all (currently missing, not just misnamed).
- [ ] `05-raw-archive-strategy.md`'s folder structure diagram updated to
      the actual flat FTP layout (`price_guides/`, `product_catalogs/`
      directly under `FTP_REMOTE_DIR`).

Everything needed for Stage 0's own scope (download → archive) is done.
The remaining checklist items are documentation cleanup, not missing
functionality.

---

## Suggested Commit

```bash
git add .github/workflows/daily-price-guide.yml
git add src/config/config.py
git add src/ingestion/download_price_guide.py
git add src/utils/date_helpers.py
git add src/utils/archive_filenames.py
git add tests/conftest.py
git add tests/test_date_helpers.py
git add tests/test_archive_filenames.py
git add tests/test_download_price_guide.py
git add DECISIONS.md
git add docs/stages/00-daily-price-guide-archive-foundation.md

git commit -m "Complete Stage 0: daily price guide download + FTP archive automation"
```

---

## Final Summary

Stage 0 delivers the single most time-sensitive piece of automation in the
project: the daily Pokémon price guide is downloaded, dated correctly in
Europe/Vienna regardless of DST, and archived immutably to FTP with
rerun-suffix protection — confirmed by both a real production run and a
focused unit test suite covering the tricky edge cases.

Three documentation gaps were found and resolved *in code* during this
stage — FTP credential naming, a missing `.env.example` entry, and FTP
folder layout — all logged in `DECISIONS.md` and tracked above rather than
left silently drifting. Validation, normalization, and loading into
`price_snapshots` remain deliberately out of scope, to be picked up once
archiving itself was proven reliable.
