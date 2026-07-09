Here's a build plan based on the dependency structure in `project.md`.

**Phase 0 — Foundations (nothing works without this)**
- Create the Supabase project, grab the pooled (Supavisor) connection string
- Scaffold the repo folders from `06` (empty `src/` subfolders, `sql/`, `tests/`, `.github/workflows/`)
- `requirements.txt` + local Python env
- `.env.example` + real `.env` (gitignored)

**Phase 1 — Database schema**
- The six `sql/schema/00X_create_*.sql` files, in dependency order (`products` first, since almost everything FKs to it)
- Apply manually to Supabase, verify the `watchlist` partial unique index actually took
- Nothing else can be tested end-to-end until this exists

**Phase 2 — Shared utilities (`src/config`, `src/utils`)**
- Europe/Vienna timezone conversion (used by *everything* date-related)
- Filename generation + rerun-suffix detection + canonical-file resolution (used by ingestion *and* load)
- DB connection handling, FTP helper, JSON helper, logging
- Building these before the pipelines saves you from duplicating the same logic in both workflows

**Phase 3 — Daily price guide pipeline, end to end**
- Deliberately *before* the catalog pipeline: it's the simpler of the two (one file, one table, no dual-file failure case), so it's the best first real test of ingestion → archive → transform → load → checks working together
- `src/ingestion` → `src/transform` → `src/load` → `sql/checks`, wired into `run_daily_price_guide.py`
- Test it manually via `workflow_dispatch` before trusting the schedule

**Phase 4 — Product catalog pipeline**
- Reuses everything from Phase 2/3, adds: dual-file handling, `productGroup`/`sourceFile` enrichment, `isActiveInCatalog` logic, `waiting_for_product` recheck
- Test manually, then let both workflows run on schedule together for a few days before moving on — this is where you'd actually observe real record counts, informing the 20% warning threshold

**Phase 5 — Collection import**
- Depends on `products` already being populated (matching needs something to match against)
- `src/collection`: CSV parsing → staging → matching logic → review loop → `collection_items`
- This is the most logic-dense piece (matching order, `waiting_for_product`, duplicate handling) — good to tackle once the ingestion side is stable and boring

**Phase 6 — Valuation, analytics signals, BI views**
- `estimatedMarketValue` first (it's a dependency for both collection views and two signal types)
- Then the six MVP signals, then `sql/views/`
- Last because signals need real historical data to be meaningful at all

**Phase 7 — Tests, sample data, README**
- Not literally last chronologically — worth writing unit tests alongside each phase rather than batching them — but the final README/polish pass happens once behavior is stable

One thing worth deciding now: do you want to build and test each pipeline **locally against Supabase** before wiring up GitHub Actions at all, or get the workflow running early (even against a mostly-empty pipeline) so you're testing the automation layer in parallel? I'd lean toward local-first (faster feedback loop, no waiting on scheduled/manual triggers), but it's your call.