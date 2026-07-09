# Reference Data

This folder contains curated project reference datasets.

Reference data is not raw Cardmarket archive data. It is manually reviewed or semi-automatically generated metadata used to enrich raw product and price data.

## Files

| File | Purpose |
|---|---|
| `expansions.csv` | Final curated expansion reference table used by the database and BI views. |
| `expansions_seed.csv` | Automatically generated working file with unique `idExpansion` values detected in Cardmarket product catalogs. |

## Update Flow

1. Download the latest Cardmarket product catalogs.
2. Run `scripts/reference/extract_expansions_seed.py`.
3. Check whether new `id_expansion` values appeared.
4. Add missing English/German expansion metadata to `expansions.csv`.
5. Run `scripts/reference/validate_expansions_reference.py`.
6. Load the curated file into the database with `scripts/reference/load_expansions.py`.
