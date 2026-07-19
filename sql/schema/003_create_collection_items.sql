-- 003_create_collection_items.sql
-- Personal Pokemon collection. One row = one physical item (never quantity).
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md
--
-- id_product IS a strict foreign key here (unlike price_snapshots /
-- collection_import_staging): a row only reaches collection_items via
-- import once matched_id_product already exists in products (see
-- docs/08's ready_to_import rule), so referencing a real product is a
-- safe, enforceable invariant at this point in the pipeline.

CREATE TABLE IF NOT EXISTS collection_items (
    collection_item_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_product              BIGINT NOT NULL
                                REFERENCES products (id_product)
                                ON DELETE RESTRICT,
    language                TEXT NOT NULL DEFAULT 'DE',
    condition                TEXT NOT NULL DEFAULT 'Near Mint',
    acquisition_type         TEXT NOT NULL DEFAULT 'pulled'
                                CHECK (acquisition_type IN (
                                    'pulled', 'bought_single', 'bought_sealed',
                                    'trade', 'gift', 'unknown'
                                )),
    purchase_price           NUMERIC,
    purchase_date             DATE,
    is_sealed                 BOOLEAN NOT NULL DEFAULT FALSE,
    is_graded                 BOOLEAN NOT NULL DEFAULT FALSE,
    -- grading_company / grade are intentionally NOT constrained to be
    -- null when is_graded = false at the schema level. That consistency
    -- rule is enforced (informationally, non-blocking) by the
    -- check_invalid_collection_items data quality check instead -- see
    -- docs/04. A hard CHECK here would duplicate that check and turn a
    -- warning-level concern into a blocking one, which the docs don't ask for.
    grading_company           TEXT,
    grade                    TEXT,
    storage_location          TEXT,
    personal_note             TEXT,
    is_sold                   BOOLEAN NOT NULL DEFAULT FALSE,
    sold_price                NUMERIC,
    sold_date                 DATE,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE collection_items IS
    'Personal collection -- one row per physical card/sealed item. Never merged into a quantity field (see docs/01, docs/08).';

COMMENT ON COLUMN collection_items.grade IS
    'Stored as text, exact label as entered/imported (e.g. "10", "9.5", "Pristine 10"). Grading scales are not comparable across companies -- no normalization in MVP. See docs/02 "grade Type Decision".';

COMMENT ON COLUMN collection_items.updated_at IS
    'Changes only on real user-facing/lifecycle field changes -- unlike products.updated_at, nothing touches this row on a recurring schedule.';

CREATE INDEX IF NOT EXISTS ix_collection_items_id_product
    ON collection_items (id_product);

CREATE OR REPLACE FUNCTION set_updated_at_collection_items()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_collection_items_updated_at ON collection_items;
CREATE TRIGGER trg_collection_items_updated_at
    BEFORE UPDATE ON collection_items
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_collection_items();
