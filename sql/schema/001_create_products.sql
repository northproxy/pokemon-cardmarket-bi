-- 001_create_products.sql
-- Unified Cardmarket product catalog (singles + non-singles).
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md
--
-- Applied manually, in numeric order, against both the dev and prod
-- Supabase projects (see docs/04-etl-pipeline-design.md, "Database
-- Platform"). If this table needs to change after being applied
-- somewhere, add a new numbered file (e.g. 007_alter_products_...sql)
-- rather than editing this one in place (docs/06).

CREATE TABLE IF NOT EXISTS products (
    id_product              BIGINT PRIMARY KEY,
    name                    TEXT NOT NULL,
    id_category             BIGINT,
    category_name           TEXT,
    id_expansion            BIGINT,
    id_metacard             BIGINT,
    date_added              TIMESTAMPTZ,
    product_group           TEXT NOT NULL
                                CHECK (product_group IN ('single', 'non_single')),
    source_file             TEXT NOT NULL
                                CHECK (source_file IN (
                                    'products_singles_6.json',
                                    'products_nonsingles_6.json'
                                )),
    is_active_in_catalog    BOOLEAN NOT NULL DEFAULT TRUE,
    -- first_seen_at / last_seen_at are set by application logic, not a
    -- DB default, since "first seen" must reflect when THIS pipeline
    -- first saw the product in a downloaded catalog file, not row
    -- insert time. See src/load/ for that logic.
    first_seen_at           TIMESTAMPTZ NOT NULL,
    last_seen_at            TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE products IS
    'Unified Pokemon product catalog from products_singles_6.json + products_nonsingles_6.json. One row per Cardmarket id_product.';

COMMENT ON COLUMN products.updated_at IS
    'Changes on ANY stored field change, including last_seen_at -- i.e. on effectively every catalog run that sees the product again. Means "the pipeline touched this row," not "a business field changed." See docs/03-data-dictionary.md.';

COMMENT ON COLUMN products.is_active_in_catalog IS
    'Set false the FIRST time a product is missing from a freshly downloaded catalog file. No grace period / N-miss tolerance in MVP. Never causes deletion.';

-- updated_at should bump on every UPDATE to this row (per the trigger
-- rule documented in 02/03), regardless of which column changed.
CREATE OR REPLACE FUNCTION set_updated_at_products()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_products();
