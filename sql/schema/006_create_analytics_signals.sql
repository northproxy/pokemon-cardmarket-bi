-- 006_create_analytics_signals.sql
-- Generated analytical observations (not predictions).
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md, docs/09-analytics-signal-definitions.md
--
-- signal_type is constrained to the current MVP list only. sealed_growth
-- / potential_buy_opportunity / etc. are deferred (docs/09) -- promoting
-- one of them later means a new numbered migration file that alters this
-- CHECK, per docs/06's stated migration approach, not editing this file.

CREATE TABLE IF NOT EXISTS analytics_signals (
    signal_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_date                DATE NOT NULL,
    id_product                 BIGINT
                                    REFERENCES products (id_product)
                                    ON DELETE RESTRICT,
    collection_item_id          UUID
                                    REFERENCES collection_items (collection_item_id)
                                    ON DELETE RESTRICT,
    signal_type                  TEXT NOT NULL
                                      CHECK (signal_type IN (
                                          'growth', 'price_spike', 'new_product',
                                          'collection_gain', 'collection_loss',
                                          'missing_price_data'
                                      )),
    signal_value                  NUMERIC,
    signal_strength                TEXT
                                      CHECK (signal_strength IS NULL
                                             OR signal_strength IN ('low', 'medium', 'high')),
    lookback_days                   INTEGER,
    reference_value                  NUMERIC,
    current_value                     NUMERIC,
    signal_description                 TEXT,
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Hard rule from docs/02/03/09: collection_gain / collection_loss
    -- MUST carry collection_item_id, since two copies of the same
    -- product can have different purchase_price values and a row keyed
    -- only on id_product can't represent one specific copy's change.
    CONSTRAINT chk_collection_signals_require_item
        CHECK (
            signal_type NOT IN ('collection_gain', 'collection_loss')
            OR collection_item_id IS NOT NULL
        )
);

COMMENT ON TABLE analytics_signals IS
    'Simple, explainable analytical observations -- never predictions or financial advice. See docs/09.';

COMMENT ON COLUMN analytics_signals.lookback_days IS
    'The freely-chosen historical window (e.g. 30 for growth), when the signal has one. NULL for price_spike -- it compares against Cardmarket''s fixed avg30 field, not a window this project selects.';

CREATE INDEX IF NOT EXISTS ix_analytics_signals_id_product
    ON analytics_signals (id_product);

CREATE INDEX IF NOT EXISTS ix_analytics_signals_collection_item_id
    ON analytics_signals (collection_item_id);
