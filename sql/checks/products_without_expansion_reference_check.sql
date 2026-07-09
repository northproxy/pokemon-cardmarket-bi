-- products_without_expansion_reference_check.sql
-- Returns product rows that cannot be enriched with expansion metadata.

SELECT
    p.id_product,
    p.product_name,
    p.id_expansion,
    p.id_category,
    p.date_added
FROM products p
LEFT JOIN expansions e
    ON p.id_expansion = e.id_expansion
WHERE p.id_expansion IS NOT NULL
  AND e.id_expansion IS NULL
ORDER BY p.id_expansion, p.id_product;
