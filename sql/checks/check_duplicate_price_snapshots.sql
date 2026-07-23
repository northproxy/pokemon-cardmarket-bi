-- check_duplicate_price_snapshots.sql
--
-- FAILURE-level check (docs/04 "Failures"): "duplicate (snapshot_date,
-- id_product) remaining after upsert."
--
-- Under normal operation this is structurally impossible: the composite
-- PRIMARY KEY on (snapshot_date, id_product) (sql/schema/002) means
-- src/load/price_snapshots.py::upsert_price_snapshots can never produce
-- a duplicate. This check exists as a defensive/regression safety net --
-- e.g. to catch a future bulk-load path that bypasses the upsert
-- function, or a manual data-fix script run outside the normal pipeline.
--
-- Usage: psql "$DATABASE_URL" -f check_duplicate_price_snapshots.sql
-- (no parameters -- checks the whole table)
--
-- Empty result = check passes (expected outcome, always, given the schema).

SELECT
    snapshot_date,
    id_product,
    count(*) AS row_count
FROM price_snapshots
GROUP BY snapshot_date, id_product
HAVING count(*) > 1
ORDER BY snapshot_date, id_product;
