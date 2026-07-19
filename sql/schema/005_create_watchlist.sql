-- 005_create_watchlist.sql
-- Products monitored even if not in the personal collection.
-- Source: docs/02-data-model.md, docs/03-data-dictionary.md

CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_item_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_product               BIGINT NOT NULL
                                  REFERENCES products (id_product)
                                  ON DELETE RESTRICT,
    reason                    TEXT,
    target_price              NUMERIC,
    is_active                  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE watchlist IS
    'Products to monitor, independent of the personal collection. Only one active row per id_product (see partial unique index below).';

-- Firm MVP requirement per docs/02/docs/04 (Postgres/Supabase confirmed,
-- partial unique indexes fully supported) -- NOT a conditional fallback
-- to application-level enforcement.
CREATE UNIQUE INDEX IF NOT EXISTS ux_watchlist_active_product
    ON watchlist (id_product)
    WHERE is_active = TRUE;

CREATE OR REPLACE FUNCTION set_updated_at_watchlist()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_watchlist_updated_at ON watchlist;
CREATE TRIGGER trg_watchlist_updated_at
    BEFORE UPDATE ON watchlist
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at_watchlist();
