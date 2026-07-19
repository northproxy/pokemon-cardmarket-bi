# DECISIONS.md — Phase 0a Implementation Log

This is a running log of implementation-time decisions made while actually
building Phase 0a (daily price guide archiving). It is **not** a replacement
for `docs/01`–`11` or `project.md` — those remain the source of truth for
the project's design. This file exists for smaller, code-level calls that
don't belong in a versioned design doc but should still be written down
instead of living only in chat history.

---

## 1. Why this got complicated, and the fix

Each piece (Europe/Vienna date computation, rerun-suffix filename logic,
FTP upload) was built as its own small, independently unit-tested module,
because that's what `02`/`04`/`05`/`07` actually specify, and because each
was asked for by name in sequence. That's the right shape for a portfolio
project's `src/utils` — but it's the wrong shape to hand over as "here are
5 files" when the actual goal is "download today's price guide to FTP."

**Decision:** consolidate the pieces into one runnable script,
`src/ingestion/download_price_guide.py`, that imports and calls the
already-built helpers (`get_pipeline_date`, `next_filename_for_upload`)
rather than re-deriving that logic inline. The underlying design doesn't
change — this is packaging, not a scope or architecture change.

## 2. Phase 0a scope cut: archive only, no validate/transform/load

`04-etl-pipeline-design.md`'s daily pipeline has 10 steps; steps 5–8
(validate JSON structure, validate required fields, normalize field names,
load into `price_snapshots`) are **not** in this script.

**Decision:** this matches the project's own stated phase boundary
(`project.md`: *"Phase 0a: daily price guide archiving"*) — archiving
reliably is the thing being proven first. Validation, normalization, and DB
loading are Phase 0b+, deliberately, not an oversight or a shortcut taken
without noting it.

## 3. FTP folder layout: flat, not nested — docs need updating

`05-raw-archive-strategy.md` documents:

```text
/raw/cardmarket/pokemon/
  price_guides/
  product_catalogs/
```

But the actual, already-confirmed FTP account (`FTP_REMOTE_PATH=/`) has
`price_guides/` and `product_catalogs/` directly at the account root — no
`/raw/cardmarket/pokemon/` nesting.

**Decision:** the code follows the real, already-verified server layout
(`{FTP_REMOTE_PATH}/price_guides/...`), not the doc's nested path. This is
a genuine, unresolved discrepancy between `05` and reality, not something
I've silently picked a side on — **`05-raw-archive-strategy.md`'s folder
tree should be corrected to the flat layout** the next time that doc is
touched, since the FTP account is the actual constraint and the doc was
written before the account was provisioned.

## 4. `FTP_PASSWORD` missing from `06`'s `.env.example` listing

`07-github-actions-logic.md` lists `FTP_PASSWORD` as a required GitHub
Actions secret alongside `FTP_HOST`/`FTP_USER`/`FTP_REMOTE_PATH`, but `06`'s
`.env.example` block only shows the latter three.

**Decision:** treated as a small listing gap in `06`, not a signal that
`FTP_PASSWORD` is optional locally — `src/config/config.py` requires it,
since a real FTP login needs it regardless of what `.env.example` enumerates.
Worth a one-line fix in `06` next time it's touched; not blocking anything
now.

## 5. Explicit FTPS via stdlib `ftplib.FTP_TLS`, no new dependency

`11-local-environment-setup.md` requires explicit FTP over TLS (plain
`ftp://` gets a 530 from this provider). Python's stdlib `ftplib.FTP_TLS`
does exactly this (`AUTH TLS` + `PROT P`), so no extra library was added
for this.

## 6. `requests` used for the HTTP download

No doc mandates an HTTP library. `requests` was already present in this
environment and is the standard choice; noting it here only so it ends up
in `requirements.txt` deliberately rather than by accident.

## 7. FTP env var names: `FTP_PASS` / `FTP_REMOTE_DIR`, not `FTP_PASSWORD` / `FTP_REMOTE_PATH`

`06-github-repository-structure.md`, `07-github-actions-logic.md`, and
`11-local-environment-setup.md` all use `FTP_PASSWORD` and `FTP_REMOTE_PATH`.
The real, already-provisioned-and-tested GitHub secrets use `FTP_PASS` and
`FTP_REMOTE_DIR` instead.

**Decision:** code (`src/config/config.py`, the workflow) uses the real,
working secret names. This is the second doc-vs-reality naming gap found
during implementation (see §3 for the first, the FTP folder layout) —
`06`/`07`/`11` should be corrected to `FTP_PASS`/`FTP_REMOTE_DIR` next time
they're touched, rather than renaming already-working secrets to match a
doc written before the secrets existed.

## 8. Schedule: `17:00 UTC` cron, accepted DST drift

Target is "~7pm Europe/Vienna, a few hours after Cardmarket's 3pm data
refresh." GitHub Actions `schedule` cron is UTC-only and does not shift for
DST, so a single fixed cron can't stay at exactly 7pm Vienna time
year-round:

```text
17:00 UTC = 19:00 Vienna during CEST (summer, UTC+2)  ← chosen value
17:00 UTC = 18:00 Vienna during CET   (winter, UTC+1)
```

**Decision:** accept the ±1h seasonal drift rather than build a
DST-aware dual-schedule workaround — this is a "run comfortably after 3pm"
buffer, not a precision requirement, and nothing about archive correctness
depends on it: `get_pipeline_date()` computes `snapshotDate` from
Europe/Vienna at whatever instant the job actually starts, so the archived
date is correct regardless of which side of the DST boundary the run lands
on.

## 9. `CARDMARKET_PRICE_GUIDE_URL` now has a default

Previously required with no fallback. Now that the real URL is known and
isn't sensitive, `config.py` defaults to it
(`https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_6.json`)
while still allowing override via env var/secret if Cardmarket ever changes
the path. Unlike `PIPELINE_TIMEZONE` (§ no-fallback-on-purpose, since a
wrong timezone silently corrupts `snapshotDate`), a wrong/missing URL here
just fails loudly at the HTTP request step — there's no silent-corruption
risk that argues for withholding a sensible default.

## 10. Telegram notification added — optional config, item-count deferred

Added a Telegram notification (`notify_telegram`) fired once at the end of
a successful run and once in the top-level exception handler on failure.
Two calls were made that aren't specified anywhere in `01`–`11`, since
notifications aren't part of the versioned design at all yet:

**Decision A — `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are optional, not
required.** Unlike `FTP_*` (`_require_env`), these are read with
`os.environ.get` and default to `None`. If either is unset,
`notify_telegram()` logs a line and returns — it does not raise, and it
never blocks or fails the archiving run. Rationale: archiving is the thing
Stage 0 exists to guarantee; a notification is a convenience on top of it,
and making the whole pipeline depend on a Telegram bot being configured
would be backwards. This deliberately breaks from the `FTP_*` precedent
(§7) rather than copying it blindly.

**Decision B — the message includes date, filename, and byte size now; item
count / last `idProduct` is a placeholder (`"TBD"`) for the moment.**
Reporting the actual last item (or item count) requires knowing whether
`price_guide_6.json`'s root is a bare array or a nested object with a
wrapper key — not yet confirmed. Rather than guess at the structure and
risk a wrong assumption baked into a notification message, `build_success_
message()` reports what's already known to be correct (date, filename,
size) and leaves the item field explicitly marked as pending, to be
revisited once the real file structure is confirmed. Note this is *not* the
same thing as JSON validation (§2, still out of scope) — reading one field
to report in a notification is a much smaller ask than validating the file,
but it's still new territory worth flagging rather than silently expanding
Phase 0a's scope.

**Failure path also notifies.** The top-level `except` block in
`__main__` now calls `notify_telegram(build_failure_message(exc))` before
`sys.exit(1)`, so a failed run (download error, FTP error, etc.) produces a
Telegram message too, not just successful ones. Like the success path, this
never raises even if Telegram itself is unreachable — the pipeline's exit
code is still what actually signals failure to GitHub Actions; the Telegram
message is a convenience notification layered on top, not the source of
truth for success/failure.

## 11. Product catalog archive pipeline — weekly cadence, partial-failure archiving, duplicated FTP helpers

Built `src/ingestion/download_product_catalogs.py` +
`.github/workflows/product-catalog.yml`, mirroring the daily price guide
script's shape (download -> local save -> FTP upload -> Telegram notify),
for both `products_singles_6.json` and `products_nonsingles_6.json`.

**Decision A — cadence changed to weekly (every Friday), not twice-monthly.**
`01-mvp-scope.md`, `04-etl-pipeline-design.md`, `05-raw-archive-strategy.md`,
`06-github-repository-structure.md`, and `07-github-actions-logic.md` all
document a 1st/15th-of-the-month schedule, with stated reasoning (product
metadata changes far less often than price data; twice-monthly avoids
unnecessary storage/processing). This is a genuine, explicit deviation from
that documented decision, not an oversight — requested directly, flagged at
the time it was requested. **Those five docs have not been updated to
match.** Their "twice per month" language should be treated as stale on
this one point until they're corrected. Nothing about correctness depends
on this — weekly is strictly more conservative (fresher catalog data) than
twice-monthly, just more frequent.

**Decision B — partial-file failure at the archive stage does not block the
other file.** `04`/`07` document a DATABASE LOAD rule: "if one catalog file
succeeds and the other fails, do not update `products` at all." That rule
is about the `products` table, which this script does not touch. At the
*archive* stage, singles and non-singles are attempted and archived fully
independently — a failure downloading/uploading one never prevents
archiving the other, since silently discarding already-successfully-
downloaded data would contradict the raw archive's core "never discard
data" principle (`05`). The run still exits non-zero and sends a
"PARTIAL FAILURE" Telegram message if either file failed, so it stays
visible. When the actual DB-load stage is eventually built, *that* stage
should still enforce the all-or-nothing `products` table rule from `04`/`07`
as documented — this decision only concerns archiving, not loading.

**Decision C (RESOLVED — see §12) — `connect_ftp`/`list_remote_filenames`/`upload_to_ftp` were
duplicated from `download_price_guide.py`, not extracted into a shared
`src/utils/ftp_client.py`.** Deliberate short-term debt: extracting a
shared helper now means touching the already-tested, already-working daily
price guide script while building a new one. Worth doing as a follow-up
refactor once the catalog script is equally proven in production — not
before. `06-github-repository-structure.md` already anticipates an FTP
helper living in `src/utils/` eventually; this is the natural point to
finally build it.

**Not addressed by this change:** JSON validation, `productGroup`/
`sourceFile` enrichment, duplicate `idProduct` detection across the two
files, and loading into `products` remain out of scope, same as the daily
pipeline's Phase 0a boundary (§2).

## 12. FTP helper extracted into src/utils/ftp_client.py (resolves §11 Decision C)

`connect_ftp`, `list_remote_filenames`, and `upload_to_ftp` were duplicated
verbatim between `download_price_guide.py` and `download_product_catalogs.py`
(§11 Decision C, deliberately, as short-term debt). Now that the product
catalog script has run and its tests pass against the real archive-writing
logic, extracted both copies into one shared module:

```text
src/utils/ftp_client.py
    connect_ftp()
    list_remote_filenames(ftps, remote_dir)
    upload_to_ftp(ftps, local_path, remote_dir, remote_filename)
```

Both ingestion scripts now `from src.utils.ftp_client import connect_ftp,
list_remote_filenames, upload_to_ftp` instead of defining their own copies.
This matches `06-github-repository-structure.md`'s own anticipated shape
for `src/utils/` ("FTP helpers" is explicitly listed there already) — this
is the point that expectation gets fulfilled, not a new architectural
choice.

**No changes were needed in either existing test file**
(`test_download_price_guide.py`, `test_download_product_catalogs.py`).
Both patch `connect_ftp` etc. as attributes of the *ingestion* module
(e.g. `@patch("src.ingestion.download_price_guide.connect_ftp")`), and
`unittest.mock.patch` resolves that against wherever the name is bound at
call time — which, after a `from ... import connect_ftp`, is still the
ingestion module's own namespace, not `ftp_client`'s. The refactor is
therefore transparent to every test written before it.

Added `tests/test_ftp_client.py` to test the extracted module directly
(connection setup, empty-listing error handling, upload path construction)
rather than only indirectly through the two scripts that use it.

## 13. `source_created_at` corrected to use Cardmarket's own `createdAt`, not download time

`03-data-dictionary.md` §4 (v0.4) stated Cardmarket's source files "don't
carry a usable file-level timestamp of their own," so `source_created_at`
was implemented as an alias for the pipeline's download time.

A real `price_guide_6.json` sample (checked 2026-07-19) showed this
assumption was wrong:

```json
{"version":1,"createdAt":"2026-06-29T02:55:18+0200","priceGuides":[...]}
```

**Decision:** `source_created_at` now stores Cardmarket's own root-level
`createdAt` value, parsed once per file and applied to every row loaded
from it (`src/transform/price_guide.py::extract_source_created_at`,
used by default in `transform_price_guide`). Falls back to `None` if the
field is ever missing or unparseable, rather than failing the pipeline
over one nullable field.

This is a genuine correction of a wrong factual premise, not a design
change -- `02`, `03`, and `04` are updated accordingly (v0.6, v0.6, v0.7).