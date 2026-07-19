-- 002_create_price_snapshots.sql
-- Full daily Cardmarket price guide, one row per (snapshot_date, id_product).
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md
--
-- IMPORTANT: id_product is deliberately NOT a strict foreign key to
-- products.id_product. Product catalogs refresh weekly (Friday) while
-- the price guide refreshes daily, so a new id_product can legitimately
-- appear here before it exists in `products`. This is documented,
-- expected behavior, not an oversight -- see docs/02, docs/04
-- ("Foreign Key Recommendation for MVP") and docs/05.

CREATE TABLE IF NOT EXISTS price_snapshots (
    snapshot_date           DATE NOT NULL,
    source_created_at       TIMESTAMPTZ,
    id_product              BIGINT NOT NULL,
    id_category             BIGINT,
    avg                     NUMERIC,
    low                     NUMERIC,
    trend                   NUMERIC,
    avg1                    NUMERIC,
    avg7                    NUMERIC,
    avg30                   NUMERIC,
    avg_holo                NUMERIC,
    low_holo                NUMERIC,
    trend_holo              NUMERIC,
    avg1_holo                NUMERIC,
    avg7_holo                NUMERIC,
    avg30_holo               NUMERIC,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (snapshot_date, id_product)
);

COMMENT ON TABLE price_snapshots IS
    'Daily Cardmarket price guide snapshot. snapshot_date is always the pipeline run date in Europe/Vienna, with no exceptions (see docs/01, docs/02).';

COMMENT ON COLUMN price_snapshots.id_product IS
    'Logical relationship to products.id_product -- intentionally NOT a strict FK. See docs/02 "Foreign Key Recommendation for MVP".';

COMMENT ON COLUMN price_snapshots.id_category IS
    'Category as reported in THIS specific daily snapshot (source-observed, point-in-time). Can drift from products.id_category -- intentional duplication, surfaced by check_category_mismatch as a warning, never auto-corrected. See docs/02, docs/03.';

COMMENT ON COLUMN price_snapshots.low IS
    'Can be noisy (unusual listings, damaged cards, outliers). Never used as the main collection valuation field.';

-- Indexed per docs/02 "Indexing Guidance" -- id_product is joined/filtered
-- on in nearly every BI view even though it isn't part of a strict FK.
CREATE INDEX IF NOT EXISTS ix_price_snapshots_id_product
    ON price_snapshots (id_product);
