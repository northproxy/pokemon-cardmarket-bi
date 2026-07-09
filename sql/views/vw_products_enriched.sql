-- vw_products_enriched.sql
-- Product catalog enriched with expansion reference metadata.

CREATE OR REPLACE VIEW vw_products_enriched AS
SELECT
    p.id_product,
    p.product_name,
    p.id_expansion,

    e.name_en AS expansion_name_en,
    e.name_de AS expansion_name_de,
    e.slug AS expansion_slug,
    e.series_en,
    e.series_de,
    e.release_date AS expansion_release_date,
    e.card_count AS expansion_card_count,

    p.id_category,
    p.date_added,
    p.is_active_in_catalog,
    p.updated_at
FROM products p
LEFT JOIN expansions e
    ON p.id_expansion = e.id_expansion;
