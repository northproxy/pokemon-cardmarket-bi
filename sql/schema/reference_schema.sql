-- ============================================================
-- Reference schema
-- Project: pokemon-cardmarket-bi
-- Purpose:
--   Store Cardmarket expansions, official Pokemon TCG sets,
--   and curated mappings between both source systems.
--
-- Design principle:
--   Cardmarket expansion != Pokemon TCG set.
--   They are connected through an explicit mapping layer.
-- ============================================================


-- ============================================================
-- 1. Cardmarket expansions
-- ============================================================

CREATE TABLE IF NOT EXISTS cardmarket_expansions (
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

    CONSTRAINT chk_cardmarket_expansions_card_count
        CHECK (card_count IS NULL OR card_count >= 0)
);


COMMENT ON TABLE cardmarket_expansions IS
'Cardmarket expansion reference data. This is the source of truth for Cardmarket expansion identifiers.';

COMMENT ON COLUMN cardmarket_expansions.id_expansion IS
'Cardmarket expansion identifier. Primary key.';

COMMENT ON COLUMN cardmarket_expansions.name_en IS
'English Cardmarket expansion name.';

COMMENT ON COLUMN cardmarket_expansions.name_de IS
'German Cardmarket expansion name.';

COMMENT ON COLUMN cardmarket_expansions.slug IS
'Cardmarket URL slug, for example Lost-Origin.';

COMMENT ON COLUMN cardmarket_expansions.series_en IS
'English Cardmarket series name, for example Sword & Shield.';

COMMENT ON COLUMN cardmarket_expansions.series_de IS
'German Cardmarket series name, for example Schwert & Schild.';

COMMENT ON COLUMN cardmarket_expansions.release_date IS
'Cardmarket or manually verified expansion release date.';

COMMENT ON COLUMN cardmarket_expansions.card_count IS
'Number of cards listed for the expansion on Cardmarket, if available.';

COMMENT ON COLUMN cardmarket_expansions.source_url_en IS
'English Cardmarket expansion page URL.';

COMMENT ON COLUMN cardmarket_expansions.source_url_de IS
'German Cardmarket expansion page URL.';

COMMENT ON COLUMN cardmarket_expansions.is_active IS
'Whether the expansion should be considered active in the reference dataset.';

COMMENT ON COLUMN cardmarket_expansions.notes IS
'Manual notes about source, uncertainty, mapping, or corrections.';


-- Helpful indexes

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_name_en
    ON cardmarket_expansions (name_en);

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_name_de
    ON cardmarket_expansions (name_de);

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_slug
    ON cardmarket_expansions (slug);

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_series_en
    ON cardmarket_expansions (series_en);

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_release_date
    ON cardmarket_expansions (release_date);

CREATE INDEX IF NOT EXISTS idx_cardmarket_expansions_is_active
    ON cardmarket_expansions (is_active);



-- ============================================================
-- 2. Pokemon TCG sets
-- ============================================================

CREATE TABLE IF NOT EXISTS pokemon_tcg_sets (
    pokemon_tcg_set_id TEXT PRIMARY KEY,

    name TEXT NOT NULL,
    series TEXT,

    printed_total INTEGER,
    total_cards INTEGER,

    secret_card_count INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN total_cards IS NOT NULL AND printed_total IS NOT NULL
            THEN total_cards - printed_total
            ELSE NULL
        END
    ) STORED,

    ptcgo_code TEXT,

    release_date DATE,
    source_updated_at TIMESTAMPTZ,

    legalities_json JSONB,

    symbol_url TEXT,
    logo_url TEXT,

    source_file TEXT,
    source_commit TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_pokemon_tcg_sets_printed_total
        CHECK (printed_total IS NULL OR printed_total >= 0),

    CONSTRAINT chk_pokemon_tcg_sets_total_cards
        CHECK (total_cards IS NULL OR total_cards >= 0),

    CONSTRAINT chk_pokemon_tcg_sets_total_ge_printed
        CHECK (
            total_cards IS NULL
            OR printed_total IS NULL
            OR total_cards >= printed_total
        )
);


COMMENT ON TABLE pokemon_tcg_sets IS
'Official Pokemon TCG set metadata imported from PokemonTCG pokemon-tcg-data sets/en.json.';

COMMENT ON COLUMN pokemon_tcg_sets.pokemon_tcg_set_id IS
'Official Pokemon TCG set ID, for example swsh11.';

COMMENT ON COLUMN pokemon_tcg_sets.name IS
'Official English Pokemon TCG set name, for example Lost Origin.';

COMMENT ON COLUMN pokemon_tcg_sets.series IS
'Official Pokemon TCG series or era, for example Sword & Shield.';

COMMENT ON COLUMN pokemon_tcg_sets.printed_total IS
'Number of cards in the printed main set. Source field: printedTotal.';

COMMENT ON COLUMN pokemon_tcg_sets.total_cards IS
'Total number of cards including secret cards. Source field: total.';

COMMENT ON COLUMN pokemon_tcg_sets.secret_card_count IS
'Generated value: total_cards - printed_total.';

COMMENT ON COLUMN pokemon_tcg_sets.ptcgo_code IS
'Pokemon TCG Online code, for example LOR. Source field: ptcgoCode.';

COMMENT ON COLUMN pokemon_tcg_sets.release_date IS
'Official Pokemon TCG release date converted to ISO format. Source field: releaseDate.';

COMMENT ON COLUMN pokemon_tcg_sets.source_updated_at IS
'Timestamp from the source JSON. Source field: updatedAt.';

COMMENT ON COLUMN pokemon_tcg_sets.legalities_json IS
'Raw legalities object from the source JSON.';

COMMENT ON COLUMN pokemon_tcg_sets.symbol_url IS
'Set symbol image URL. Source field: images.symbol.';

COMMENT ON COLUMN pokemon_tcg_sets.logo_url IS
'Set logo image URL. Source field: images.logo.';

COMMENT ON COLUMN pokemon_tcg_sets.source_file IS
'Source file path used for import, for example sets/en.json.';

COMMENT ON COLUMN pokemon_tcg_sets.source_commit IS
'Git commit hash of the imported Pokemon TCG data source.';


-- Helpful indexes

CREATE INDEX IF NOT EXISTS idx_pokemon_tcg_sets_name
    ON pokemon_tcg_sets (name);

CREATE INDEX IF NOT EXISTS idx_pokemon_tcg_sets_series
    ON pokemon_tcg_sets (series);

CREATE INDEX IF NOT EXISTS idx_pokemon_tcg_sets_ptcgo_code
    ON pokemon_tcg_sets (ptcgo_code);

CREATE INDEX IF NOT EXISTS idx_pokemon_tcg_sets_release_date
    ON pokemon_tcg_sets (release_date);

CREATE INDEX IF NOT EXISTS idx_pokemon_tcg_sets_source_commit
    ON pokemon_tcg_sets (source_commit);



-- ============================================================
-- 3. Expansion to Pokemon TCG set mappings
-- ============================================================

CREATE TABLE IF NOT EXISTS expansion_set_mappings (
    id_expansion INTEGER NOT NULL,
    pokemon_tcg_set_id TEXT NOT NULL,

    match_status TEXT NOT NULL,
    match_method TEXT NOT NULL DEFAULT 'none',

    match_confidence NUMERIC(4, 3),

    is_primary_mapping BOOLEAN NOT NULL DEFAULT TRUE,
    needs_review BOOLEAN NOT NULL DEFAULT TRUE,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT pk_expansion_set_mappings
        PRIMARY KEY (id_expansion, pokemon_tcg_set_id),

    CONSTRAINT fk_expansion_set_mappings_cardmarket
        FOREIGN KEY (id_expansion)
        REFERENCES cardmarket_expansions (id_expansion)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_expansion_set_mappings_pokemon_tcg
        FOREIGN KEY (pokemon_tcg_set_id)
        REFERENCES pokemon_tcg_sets (pokemon_tcg_set_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT chk_expansion_set_mappings_match_status
        CHECK (
            match_status IN (
                'matched',
                'manual_review',
                'unmatched',
                'not_applicable'
            )
        ),

    CONSTRAINT chk_expansion_set_mappings_match_method
        CHECK (
            match_method IN (
                'exact_name',
                'normalized_name',
                'slug',
                'code',
                'date_name_combo',
                'manual',
                'none'
            )
        ),

    CONSTRAINT chk_expansion_set_mappings_confidence
        CHECK (
            match_confidence IS NULL
            OR (
                match_confidence >= 0.000
                AND match_confidence <= 1.000
            )
        )
);


COMMENT ON TABLE expansion_set_mappings IS
'Curated mapping table between Cardmarket expansions and official Pokemon TCG sets.';

COMMENT ON COLUMN expansion_set_mappings.id_expansion IS
'Cardmarket expansion ID. Foreign key to cardmarket_expansions.';

COMMENT ON COLUMN expansion_set_mappings.pokemon_tcg_set_id IS
'Pokemon TCG set ID. Foreign key to pokemon_tcg_sets.';

COMMENT ON COLUMN expansion_set_mappings.match_status IS
'Mapping status: matched, manual_review, unmatched, or not_applicable.';

COMMENT ON COLUMN expansion_set_mappings.match_method IS
'Method used to create the mapping: exact_name, normalized_name, slug, code, date_name_combo, manual, or none.';

COMMENT ON COLUMN expansion_set_mappings.match_confidence IS
'Confidence score between 0.000 and 1.000.';

COMMENT ON COLUMN expansion_set_mappings.is_primary_mapping IS
'Whether this is the primary mapping for the Cardmarket expansion.';

COMMENT ON COLUMN expansion_set_mappings.needs_review IS
'Whether this mapping still requires manual review.';

COMMENT ON COLUMN expansion_set_mappings.notes IS
'Manual notes explaining mapping uncertainty, source decisions, or corrections.';


-- Helpful indexes

CREATE INDEX IF NOT EXISTS idx_expansion_set_mappings_id_expansion
    ON expansion_set_mappings (id_expansion);

CREATE INDEX IF NOT EXISTS idx_expansion_set_mappings_pokemon_tcg_set_id
    ON expansion_set_mappings (pokemon_tcg_set_id);

CREATE INDEX IF NOT EXISTS idx_expansion_set_mappings_match_status
    ON expansion_set_mappings (match_status);

CREATE INDEX IF NOT EXISTS idx_expansion_set_mappings_needs_review
    ON expansion_set_mappings (needs_review);

CREATE INDEX IF NOT EXISTS idx_expansion_set_mappings_confidence
    ON expansion_set_mappings (match_confidence);


-- Only one primary mapping per Cardmarket expansion.
-- This allows multiple candidate mappings, but only one can be marked primary.

CREATE UNIQUE INDEX IF NOT EXISTS unique_primary_mapping_per_expansion
    ON expansion_set_mappings (id_expansion)
    WHERE is_primary_mapping = TRUE;



-- ============================================================
-- 4. Updated_at trigger helper
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_cardmarket_expansions_updated_at
ON cardmarket_expansions;

CREATE TRIGGER trg_cardmarket_expansions_updated_at
BEFORE UPDATE ON cardmarket_expansions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


DROP TRIGGER IF EXISTS trg_pokemon_tcg_sets_updated_at
ON pokemon_tcg_sets;

CREATE TRIGGER trg_pokemon_tcg_sets_updated_at
BEFORE UPDATE ON pokemon_tcg_sets
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


DROP TRIGGER IF EXISTS trg_expansion_set_mappings_updated_at
ON expansion_set_mappings;

CREATE TRIGGER trg_expansion_set_mappings_updated_at
BEFORE UPDATE ON expansion_set_mappings
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();



-- ============================================================
-- 5. Optional BI-safe view
-- ============================================================
-- This view exposes only trusted mappings.
-- Default BI queries should prefer this view instead of directly joining
-- all mapping candidates.

CREATE OR REPLACE VIEW vw_trusted_expansion_set_mappings AS
SELECT
    cem.id_expansion,
    ce.name_en AS cardmarket_name_en,
    ce.name_de AS cardmarket_name_de,
    ce.slug AS cardmarket_slug,
    ce.series_en AS cardmarket_series_en,
    ce.series_de AS cardmarket_series_de,
    ce.release_date AS cardmarket_release_date,
    ce.card_count AS cardmarket_card_count,

    pts.pokemon_tcg_set_id,
    pts.name AS pokemon_tcg_name,
    pts.series AS pokemon_tcg_series,
    pts.ptcgo_code,
    pts.release_date AS pokemon_tcg_release_date,
    pts.printed_total,
    pts.total_cards,
    pts.secret_card_count,
    pts.symbol_url,
    pts.logo_url,

    cem.match_status,
    cem.match_method,
    cem.match_confidence,
    cem.is_primary_mapping,
    cem.needs_review
FROM expansion_set_mappings cem
JOIN cardmarket_expansions ce
    ON ce.id_expansion = cem.id_expansion
JOIN pokemon_tcg_sets pts
    ON pts.pokemon_tcg_set_id = cem.pokemon_tcg_set_id
WHERE cem.match_status = 'matched'
  AND cem.match_confidence >= 0.900
  AND cem.is_primary_mapping = TRUE
  AND cem.needs_review = FALSE
  AND ce.is_active = TRUE;


COMMENT ON VIEW vw_trusted_expansion_set_mappings IS
'BI-safe view exposing only trusted Cardmarket expansion to Pokemon TCG set mappings.';



-- ============================================================
-- 6. Optional manual review view
-- ============================================================
-- This view helps find mappings that need human review.

CREATE OR REPLACE VIEW vw_expansion_set_mappings_for_review AS
SELECT
    cem.id_expansion,
    ce.name_en AS cardmarket_name_en,
    ce.name_de AS cardmarket_name_de,
    ce.slug AS cardmarket_slug,
    ce.series_en AS cardmarket_series_en,
    ce.release_date AS cardmarket_release_date,

    cem.pokemon_tcg_set_id,
    pts.name AS pokemon_tcg_name,
    pts.series AS pokemon_tcg_series,
    pts.release_date AS pokemon_tcg_release_date,

    cem.match_status,
    cem.match_method,
    cem.match_confidence,
    cem.is_primary_mapping,
    cem.needs_review,
    cem.notes
FROM expansion_set_mappings cem
LEFT JOIN cardmarket_expansions ce
    ON ce.id_expansion = cem.id_expansion
LEFT JOIN pokemon_tcg_sets pts
    ON pts.pokemon_tcg_set_id = cem.pokemon_tcg_set_id
WHERE cem.needs_review = TRUE
   OR cem.match_status = 'manual_review'
   OR cem.match_confidence < 0.900
   OR cem.match_confidence IS NULL;


COMMENT ON VIEW vw_expansion_set_mappings_for_review IS
'Review view for uncertain, weak, incomplete, or manually flagged expansion mappings.';