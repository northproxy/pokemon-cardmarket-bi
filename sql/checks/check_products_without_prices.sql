-- check_products_without_prices.sql
--
-- WARNING-level check (docs/04 "How many products have no latest
-- price?"; mirrors docs/02/03's vw_products_without_prices view intent:
-- "products that exist in the catalog but do not have price data in the
-- latest price snapshot").
--
-- IMPORTANT, confirmed against a real price_guide_6.json sample
-- (2026-07-19): the price guide is a FULL daily dump, so a catalogued
-- product almost always gets a row in price_snapshots every day -- even
-- when it has no real price info. In the real sample, id_product 895109
-- has a full row with avg/low/trend/avg1/avg7/avg30 ALL null. So "no
-- latest price" can NOT be defined as "row missing entirely" -- it must
-- also catch "row exists but trend AND avg30 are both null" (the same
-- pair used by the missing_price_data signal, docs/09). This check
-- covers BOTH cases with one LEFT JOIN.
--
-- Usage:
--   psql "$DATABASE_URL" -v snapshot_date="'2026-07-19'" -f check_products_without_prices.sql
--
-- Empty result = check passes. Only active products are considered --
-- an inactive product lacking fresh prices isn't a data quality concern
-- (docs/02/03: inactive just means "not in the latest catalog").

SELECT
    p.id_product,
    p.name,
    p.product_group,
    p.category_name,
    p.last_seen_at
FROM products p
LEFT JOIN price_snapshots ps
    ON ps.id_product = p.id_product
   AND ps.snapshot_date = :snapshot_date
WHERE p.is_active_in_catalog = TRUE
  AND (
        ps.id_product IS NULL                          -- no row at all for this date
        OR (ps.trend IS NULL AND ps.avg30 IS NULL)       -- row exists, but unusable for valuation
      )
ORDER BY p.id_product;
