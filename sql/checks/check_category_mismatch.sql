-- check_category_mismatch.sql
--
-- WARNING-level check (docs/02/03: "id_category Reconciliation" /
-- "id_category Duplication"). This is intentional duplication, not
-- redundant data -- price_snapshots.id_category is source-observed and
-- point-in-time, products.id_category reflects the last catalog
-- refresh, and the two are EXPECTED to occasionally drift. This check
-- surfaces drift for review; it must never auto-correct either value
-- and must never block loading.
--
-- Usage:
--   psql "$DATABASE_URL" -v snapshot_date="'2026-07-19'" -f check_category_mismatch.sql
--
-- Empty result = check passes (no drift detected for that date). Rows
-- where either side's id_category is null are excluded -- this check is
-- specifically about disagreement between two present values, not
-- about missing data (that's a separate concern, not checked here).

SELECT
    ps.id_product,
    ps.snapshot_date,
    ps.id_category  AS price_snapshot_id_category,
    p.id_category   AS products_id_category
FROM price_snapshots ps
JOIN products p
    ON p.id_product = ps.id_product
WHERE ps.snapshot_date = :snapshot_date
  AND ps.id_category IS NOT NULL
  AND p.id_category IS NOT NULL
  AND ps.id_category != p.id_category
ORDER BY ps.id_product;
