-- check_invalid_collection_items.sql
--
-- INFORMATIONAL check (docs/04 "Collection Integrity Check
-- (Informational)"). NOT part of either scheduled pipeline's
-- failure/warning thresholds -- never blocks anything. Meant to be run
-- after a collection import, or periodically, to catch inconsistencies
-- introduced AFTER import (e.g. a manual database edit). This
-- complements, rather than duplicates, the import-time safety rules in
-- docs/08 -- those prevent bad staging rows from becoming collection_items
-- in the first place; this catches drift that happens afterward.
--
-- Usage: psql "$DATABASE_URL" -f check_invalid_collection_items.sql
-- (no parameters -- checks the whole table)
--
-- One row per (collection_item_id, issue) -- a single item can appear
-- more than once if it has multiple issues. Empty result = check passes.

SELECT collection_item_id, 'graded item missing grading_company or grade' AS issue
FROM collection_items
WHERE is_graded = TRUE
  AND (grading_company IS NULL OR grade IS NULL)

UNION ALL

SELECT collection_item_id, 'sold item missing sold_price or sold_date'
FROM collection_items
WHERE is_sold = TRUE
  AND (sold_price IS NULL OR sold_date IS NULL)

UNION ALL

SELECT collection_item_id, 'sold_price/sold_date populated while is_sold = false'
FROM collection_items
WHERE is_sold = FALSE
  AND (sold_price IS NOT NULL OR sold_date IS NOT NULL)

UNION ALL

SELECT collection_item_id, 'negative purchase_price'
FROM collection_items
WHERE purchase_price IS NOT NULL
  AND purchase_price < 0

UNION ALL

SELECT collection_item_id, 'negative sold_price'
FROM collection_items
WHERE sold_price IS NOT NULL
  AND sold_price < 0

UNION ALL

SELECT collection_item_id, 'purchase_date in the future'
FROM collection_items
WHERE purchase_date IS NOT NULL
  AND purchase_date > CURRENT_DATE

UNION ALL

SELECT collection_item_id, 'sold_date in the future'
FROM collection_items
WHERE sold_date IS NOT NULL
  AND sold_date > CURRENT_DATE

ORDER BY collection_item_id;
