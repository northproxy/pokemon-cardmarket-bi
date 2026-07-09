-- ============================================================
-- Basic Checks for Pokémon TCG Sets
-- Project: pokemon-cardmarket-bi
-- File: sql/checks/pokemon_tcg_sets_basic_check.sql
--
-- Purpose:
--   Runs simple validation checks after importing pokemon_tcg_sets.csv
--   into public.pokemon_tcg_sets.
-- ============================================================

-- ============================================================
-- 1. Total row count
-- ============================================================

select
    count(*) as total_sets
from public.pokemon_tcg_sets;

-- ============================================================
-- 2. Count active / inactive sets
-- ============================================================

select
    is_active,
    count(*) as set_count
from public.pokemon_tcg_sets
group by is_active
order by is_active desc;

-- ============================================================
-- 3. Check for missing primary IDs
-- Expected result: 0 rows
-- ============================================================

select *
from public.pokemon_tcg_sets
where pokemon_tcg_set_id is null
   or trim(pokemon_tcg_set_id) = '';

-- ============================================================
-- 4. Check for missing English names
-- Expected result: 0 rows
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en
from public.pokemon_tcg_sets
where name_en is null
   or trim(name_en) = '';

-- ============================================================
-- 5. Check for duplicate set IDs
-- Expected result: 0 rows
-- Primary key should prevent this, but this check is useful
-- when inspecting CSV/staging data.
-- ============================================================

select
    pokemon_tcg_set_id,
    count(*) as duplicate_count
from public.pokemon_tcg_sets
group by pokemon_tcg_set_id
having count(*) > 1;

-- ============================================================
-- 6. Check card count consistency
-- Expected result: 0 rows
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    printed_total,
    total_cards,
    secret_card_count
from public.pokemon_tcg_sets
where printed_total is not null
  and total_cards is not null
  and total_cards < printed_total;

-- ============================================================
-- 7. Check secret_card_count calculation
-- Expected result: 0 rows
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    printed_total,
    total_cards,
    secret_card_count,
    total_cards - printed_total as expected_secret_card_count
from public.pokemon_tcg_sets
where printed_total is not null
  and total_cards is not null
  and secret_card_count is distinct from (total_cards - printed_total);

-- ============================================================
-- 8. Check negative numeric values
-- Expected result: 0 rows
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    printed_total,
    total_cards,
    secret_card_count
from public.pokemon_tcg_sets
where printed_total < 0
   or total_cards < 0
   or secret_card_count < 0;

-- ============================================================
-- 9. Sets without release date
-- This may return rows. Not necessarily an error.
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    series_en,
    release_date
from public.pokemon_tcg_sets
where release_date is null
order by name_en;

-- ============================================================
-- 10. Sets without series
-- This may return rows. Not necessarily an error.
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    series_en
from public.pokemon_tcg_sets
where series_en is null
   or trim(series_en) = ''
order by name_en;

-- ============================================================
-- 11. Sets without PTCGO code
-- This may return rows. Not necessarily an error.
-- Older or special sets may not have a code.
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    series_en,
    ptcgo_code
from public.pokemon_tcg_sets
where ptcgo_code is null
   or trim(ptcgo_code) = ''
order by release_date desc nulls last;

-- ============================================================
-- 12. Series overview
-- Useful sanity check.
-- ============================================================

select
    series_en,
    count(*) as set_count,
    min(release_date) as first_release_date,
    max(release_date) as latest_release_date
from public.pokemon_tcg_sets
group by series_en
order by latest_release_date desc nulls last;

-- ============================================================
-- 13. Latest 20 sets by release date
-- Useful for visual inspection.
-- ============================================================

select
    pokemon_tcg_set_id,
    name_en,
    series_en,
    ptcgo_code,
    release_date,
    printed_total,
    total_cards,
    secret_card_count
from public.pokemon_tcg_sets
order by release_date desc nulls last
limit 20;

-- ============================================================
-- 14. Example lookup: Lost Origin
-- Expected: swsh11
-- ============================================================

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
    is_active
from public.pokemon_tcg_sets
where lower(name_en) = lower('Lost Origin')
   or pokemon_tcg_set_id = 'swsh11';

-- ============================================================
-- 15. Check created_at / updated_at metadata
-- Expected:
--   created_at is not null
--   updated_at is not null
-- ============================================================

select
    count(*) filter (where created_at is null) as rows_missing_created_at,
    count(*) filter (where updated_at is null) as rows_missing_updated_at
from public.pokemon_tcg_sets;