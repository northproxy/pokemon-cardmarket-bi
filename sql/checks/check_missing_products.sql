-- check_missing_products.sql
--
-- WARNING-level check (docs/04-etl-pipeline-design.md "Warnings vs Failures"):
-- "price rows with no matching product in the products table" and
-- "new id_product values appearing in the price guide that aren't in
-- products yet" are the SAME underlying condition described from two
-- angles in docs/04 -- one check covers both.
--
-- Expected and tolerated by design: price_snapshots.id_product is NOT a
-- strict FK to products (docs/02/03/04), because the catalog refreshes
-- weekly while the price guide refreshes daily. Non-empty results here
-- are a normal, expected occurrence, not evidence of a bug -- they
-- become a genuine concern only if a product is STILL unmatched a week
-- (one catalog cycle) later.
--
-- Usage (manual/ad hoc):
--   psql "$DATABASE_URL" -v snapshot_date="'2026-07-19'" -f check_missing_products.sql
--
-- Empty result = check passes (no unmatched rows for that date).

SELECT
    ps.id_product,
    ps.snapshot_date
FROM price_snapshots ps
LEFT JOIN products p
    ON p.id_product = ps.id_product
WHERE ps.snapshot_date = :snapshot_date
  AND p.id_product IS NULL
ORDER BY ps.id_product;
