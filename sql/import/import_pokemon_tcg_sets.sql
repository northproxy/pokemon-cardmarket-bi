-- ============================================================
-- Import Pokémon TCG Sets CSV
-- Project: pokemon-cardmarket-bi
-- File: sql/imports/import_pokemon_tcg_sets.sql
--
-- Purpose:
--   Imports data from pokemon_tcg_sets.csv into public.pokemon_tcg_sets.
--
-- Source CSV:
--   data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv
--
-- Important:
--   This script is intended for local PostgreSQL usage with COPY.
--   For Supabase hosted database, use the Supabase Table Editor CSV import
--   or psql with \copy from your local machine.
-- ============================================================

-- Optional safety check:
-- Make sure the target table exists before importing.
select
    table_schema,
    table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'pokemon_tcg_sets';

-- ============================================================
-- Option A: Local PostgreSQL server-side COPY
-- ============================================================
--
-- Use this only if PostgreSQL can access the file path directly.
-- On Windows, you need to use an absolute path.
--
-- Example:
--
-- copy public.pokemon_tcg_sets (
--     pokemon_tcg_set_id,
--     name_en,
--     series_en,
--     ptcgo_code,
--     release_date,
--     printed_total,
--     total_cards,
--     secret_card_count,
--     legalities,
--     symbol_url,
--     logo_url,
--     source_updated_at,
--     is_active,
--     notes
-- )
-- from 'R:/_fun/Pokemon cardmarket bi/data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv'
-- with (
--     format csv,
--     header true,
--     encoding 'UTF8'
-- );

-- ============================================================
-- Option B: psql client-side \copy
-- ============================================================
--
-- Recommended for local files.
-- Run this from psql, not from Supabase SQL Editor.
--
-- Example:
--
-- \copy public.pokemon_tcg_sets (
--     pokemon_tcg_set_id,
--     name_en,
--     series_en,
--     ptcgo_code,
--     release_date,
--     printed_total,
--     total_cards,
--     secret_card_count,
--     legalities,
--     symbol_url,
--     logo_url,
--     source_updated_at,
--     is_active,
--     notes
-- )
-- from 'data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv'
-- with (
--     format csv,
--     header true,
--     encoding 'UTF8'
-- );

-- ============================================================
-- Option C: Upsert import pattern
-- ============================================================
--
-- Use this pattern later when you want repeatable imports.
-- For v1, manual CSV import is enough.
--
-- Recommended flow:
--   1. Create temporary staging table.
--   2. COPY CSV into staging table.
--   3. Insert into pokemon_tcg_sets with ON CONFLICT update.
--
-- This avoids duplicate primary key errors when importing the same file again.

begin;

create temporary table tmp_pokemon_tcg_sets_import (
    pokemon_tcg_set_id text,
    name_en text,
    series_en text,
    ptcgo_code text,
    release_date date,
    printed_total integer,
    total_cards integer,
    secret_card_count integer,
    legalities jsonb,
    symbol_url text,
    logo_url text,
    source_updated_at timestamp,
    is_active boolean,
    notes text
);

-- IMPORTANT:
-- This COPY command requires PostgreSQL server access to the file path.
-- Replace the file path before running locally.
--
-- For psql, replace COPY with \copy.
--
-- copy tmp_pokemon_tcg_sets_import (
--     pokemon_tcg_set_id,
--     name_en,
--     series_en,
--     ptcgo_code,
--     release_date,
--     printed_total,
--     total_cards,
--     secret_card_count,
--     legalities,
--     symbol_url,
--     logo_url,
--     source_updated_at,
--     is_active,
--     notes
-- )
-- from 'R:/_fun/Pokemon cardmarket bi/data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv'
-- with (
--     format csv,
--     header true,
--     encoding 'UTF8'
-- );

insert into public.pokemon_tcg_sets (
    pokemon_tcg_set_id,
    name_en,
    series_en,
    ptcgo_code,
    release_date,
    printed_total,
    total_cards,
    secret_card_count,
    legalities,
    symbol_url,
    logo_url,
    source_updated_at,
    is_active,
    notes
)
select
    pokemon_tcg_set_id,
    name_en,
    series_en,
    ptcgo_code,
    release_date,
    printed_total,
    total_cards,
    secret_card_count,
    legalities,
    symbol_url,
    logo_url,
    source_updated_at,
    coalesce(is_active, true),
    notes
from tmp_pokemon_tcg_sets_import
on conflict (pokemon_tcg_set_id)
do update set
    name_en = excluded.name_en,
    series_en = excluded.series_en,
    ptcgo_code = excluded.ptcgo_code,
    release_date = excluded.release_date,
    printed_total = excluded.printed_total,
    total_cards = excluded.total_cards,
    secret_card_count = excluded.secret_card_count,
    legalities = excluded.legalities,
    symbol_url = excluded.symbol_url,
    logo_url = excluded.logo_url,
    source_updated_at = excluded.source_updated_at,
    is_active = excluded.is_active,
    notes = excluded.notes;

commit;

-- Check imported row count.
select count(*) as imported_sets_count
from public.pokemon_tcg_sets;