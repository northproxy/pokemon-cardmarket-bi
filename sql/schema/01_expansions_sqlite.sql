-- 01_expansions_sqlite.sql
-- SQLite-compatible version of the expansions table.
-- Use this for db/local/pokemon_cardmarket_bi.db.

CREATE TABLE IF NOT EXISTS expansions (
    id_expansion INTEGER PRIMARY KEY,

    name_en TEXT NOT NULL,
    name_de TEXT,

    slug TEXT,
    series_en TEXT,
    series_de TEXT,

    release_date TEXT,
    card_count INTEGER,

    source_url_en TEXT,
    source_url_de TEXT,

    is_active INTEGER NOT NULL DEFAULT 1,

    notes TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (card_count IS NULL OR card_count >= 0),
    CHECK (release_date IS NULL OR release_date >= '1996-01-01')
);

CREATE INDEX IF NOT EXISTS idx_expansions_name_en
    ON expansions (name_en);

CREATE INDEX IF NOT EXISTS idx_expansions_name_de
    ON expansions (name_de);

CREATE INDEX IF NOT EXISTS idx_expansions_series_en
    ON expansions (series_en);

CREATE INDEX IF NOT EXISTS idx_expansions_release_date
    ON expansions (release_date);
