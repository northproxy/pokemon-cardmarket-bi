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
