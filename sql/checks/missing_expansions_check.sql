-- missing_expansions_check.sql
-- Returns product expansion IDs that exist in products but are missing from the expansions reference table.

SELECT DISTINCT
    p.id_expansion
FROM products p
LEFT JOIN expansions e
    ON p.id_expansion = e.id_expansion
WHERE p.id_expansion IS NOT NULL
  AND e.id_expansion IS NULL
ORDER BY p.id_expansion;
