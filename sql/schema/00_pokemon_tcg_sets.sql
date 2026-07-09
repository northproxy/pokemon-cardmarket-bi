-- ============================================================
-- Pokémon TCG Sets Reference Table
-- Project: pokemon-cardmarket-bi
-- Table: pokemon_tcg_sets
-- Purpose:
--   Stores a clean local reference list of official Pokémon TCG sets.
--   Version 1 is populated from Pokémon TCG en.json.
-- ============================================================

create table if not exists public.pokemon_tcg_sets (
    -- Primary identifier from Pokémon TCG source
    pokemon_tcg_set_id text primary key,

    -- Basic set metadata
    name_en text not null,
    series_en text,
    ptcgo_code text,

    -- Dates
    release_date date,

    -- Card counts
    printed_total integer,
    total_cards integer,
    secret_card_count integer,

    -- Raw source metadata
    legalities jsonb,
    symbol_url text,
    logo_url text,
    source_updated_at timestamp,

    -- Local project metadata
    is_active boolean not null default true,
    notes text,

    -- Database metadata
    created_at timestamp not null default now(),
    updated_at timestamp not null default now(),

    -- Basic data quality checks
    -- Note: this table does not enforce total_cards >= printed_total.
    -- Some promo/special sets in the Pokémon TCG source have total_cards lower than printed_total.
    constraint pokemon_tcg_sets_printed_total_non_negative
        check (printed_total is null or printed_total >= 0),

    constraint pokemon_tcg_sets_total_cards_non_negative
        check (total_cards is null or total_cards >= 0),

    constraint pokemon_tcg_sets_secret_card_count_non_negative
        check (secret_card_count is null or secret_card_count >= 0)
);

-- Helpful for filtering sets by series
create index if not exists idx_pokemon_tcg_sets_series_en
on public.pokemon_tcg_sets (series_en);

-- Helpful for sorting and filtering by release date
create index if not exists idx_pokemon_tcg_sets_release_date
on public.pokemon_tcg_sets (release_date);

-- Helpful for filtering active reference rows
create index if not exists idx_pokemon_tcg_sets_is_active
on public.pokemon_tcg_sets (is_active);

-- ============================================================
-- updated_at trigger
-- Automatically updates updated_at when a row changes
-- ============================================================

create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_pokemon_tcg_sets_updated_at
on public.pokemon_tcg_sets;

create trigger trg_pokemon_tcg_sets_updated_at
before update on public.pokemon_tcg_sets
for each row
execute function public.set_updated_at();