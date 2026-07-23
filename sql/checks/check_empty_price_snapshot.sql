-- check_empty_price_snapshot.sql
--
-- FAILURE-level check (docs/04 "Failures": "file is empty / zero records
-- parsed"; docs/01 success criteria: archive contains 30 consecutive
-- days with no missing snapshot; docs/07: "number of loaded records is
-- greater than zero").
--
-- src/transform/price_guide.py already rejects a source file with zero
-- records before it ever reaches the database (ValidationError). This
-- check exists as a SEPARATE, DB-side safety net: it catches the case
-- where the source file validated fine but something in the load path
-- still resulted in zero rows landing in price_snapshots for that date
-- (e.g. an upstream orchestration bug) -- a scenario transform-time
-- validation cannot see, since it never touches the database.
--
-- Usage:
--   psql "$DATABASE_URL" -v snapshot_date="'2026-07-19'" -f check_empty_price_snapshot.sql
--
-- Empty result = check passes (at least one row exists for that date).
-- One result row = FAILURE (zero rows loaded for a date that should have data).

SELECT
    :snapshot_date::date AS snapshot_date,
    count(*) AS row_count
FROM price_snapshots
WHERE snapshot_date = :snapshot_date
HAVING count(*) = 0;
