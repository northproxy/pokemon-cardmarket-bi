-- 01_expansions.sql
-- Curated reference table for Cardmarket Pokémon expansion metadata.
-- This table must be created before products, because products.id_expansion references it.

CREATE TABLE IF NOT EXISTS expansions (
    id_expansion INTEGER PRIMARY KEY,

    name_en TEXT NOT NULL,
    name_de TEXT,

    slug TEXT,
    series_en TEXT,
    series_de TEXT,

    release_date DATE,
    card_count INTEGER,

    source_url_en TEXT,
    source_url_de TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_expansions_card_count_non_negative
        CHECK (card_count IS NULL OR card_count >= 0),

    CONSTRAINT chk_expansions_release_date_reasonable
        CHECK (release_date IS NULL OR release_date >= DATE '1996-01-01')
);

CREATE INDEX IF NOT EXISTS idx_expansions_name_en
    ON expansions (name_en);

CREATE INDEX IF NOT EXISTS idx_expansions_name_de
    ON expansions (name_de);

CREATE INDEX IF NOT EXISTS idx_expansions_series_en
    ON expansions (series_en);

CREATE INDEX IF NOT EXISTS idx_expansions_release_date
    ON expansions (release_date);
