-- 004_create_collection_import_staging.sql
-- Staging area for CSV/Excel collection imports, before rows become
-- trusted collection_items rows.
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md, docs/08-collection-import-flow.md
--
-- Neither provided_id_product nor matched_id_product is a strict
-- foreign key:
--   - provided_id_product must be able to hold invalid user input for review.
--   - matched_id_product can legitimately point to an id_product that
--     does not exist in `products` yet (match_status = waiting_for_product,
--     see docs/08) -- a strict FK would make that state impossible to store.

CREATE TABLE IF NOT EXISTS collection_import_staging (
    import_row_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_batch_id           TEXT NOT NULL,
    external_id                TEXT,
    provided_id_product        BIGINT,
    raw_product_name           TEXT,
    matched_id_product         BIGINT,
    language                  TEXT DEFAULT 'DE',
    condition                  TEXT DEFAULT 'Near Mint',
    acquisition_type            TEXT DEFAULT 'pulled',
    purchase_price              NUMERIC,
    purchase_date                DATE,
    is_sealed                    BOOLEAN,
    storage_location              TEXT,
    personal_note                 TEXT,
    match_status                  TEXT NOT NULL
                                      CHECK (match_status IN (
                                          'ready_to_import', 'needs_review',
                                          'waiting_for_product', 'error', 'imported'
                                      )),
    match_confidence               NUMERIC
                                      CHECK (match_confidence IS NULL
                                             OR (match_confidence >= 0.00 AND match_confidence <= 1.00)),
    error_message                   TEXT,
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
    imported_at                       TIMESTAMPTZ
);

COMMENT ON TABLE collection_import_staging IS
    'Raw imported collection rows before validation/matching/import into collection_items. See docs/08 for the full matching and review flow.';

COMMENT ON COLUMN collection_import_staging.import_batch_id IS
    'Identifies one UPLOAD EVENT, not one source file. Re-uploading the same CSV produces a new batch_id -- external_id is the cross-batch duplicate defense, not this field. See docs/08.';

COMMENT ON COLUMN collection_import_staging.provided_id_product IS
    'User-supplied id_product, may be invalid or not-yet-catalogued. Deliberately NOT a foreign key -- staging must be able to store bad input for review.';

COMMENT ON COLUMN collection_import_staging.matched_id_product IS
    'Set by the matching process. Deliberately NOT a foreign key -- can point to an id_product not yet present in products (match_status = waiting_for_product). See docs/02, docs/08.';

COMMENT ON COLUMN collection_import_staging.match_confidence IS
    '1.00 = exact id_product match, 0.90 = exact name match, 0.70/0.40 = fuzzy bands reserved but UNUSED in MVP, 0.00 = attempted/no confident match, NULL = matching not attempted yet (expected to be rare given synchronous matching). See docs/03, docs/08.';

-- Cross-batch duplicate protection (docs/08 "Duplicate Handling") needs
-- to look up external_id across all previously imported rows quickly.
CREATE INDEX IF NOT EXISTS ix_collection_import_staging_external_id
    ON collection_import_staging (external_id)
    WHERE external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_collection_import_staging_matched_id_product
    ON collection_import_staging (matched_id_product);

-- Fast lookup of rows waiting on the next successful catalog run
-- (docs/07 step 10, docs/08 "waiting_for_product").
CREATE INDEX IF NOT EXISTS ix_collection_import_staging_waiting_for_product
    ON collection_import_staging (match_status)
    WHERE match_status = 'waiting_for_product';
