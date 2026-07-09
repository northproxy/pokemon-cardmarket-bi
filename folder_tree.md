\Pokemon-cardmarket-bi
│   .env
│   .env.example
│   .gitignore
│   DECISIONS.md
│   LICENSE
│   project.md
│   README.md
│   requirements.txt
│
├───.github
│   └───workflows
│           daily-price-guide.yml
│           expansions-reference-check.yml
│           product-catalog.yml
│
├───data
│   ├───exports
│   │       README.md
│   │
│   ├───imports
│   │   │   README.md
│   │   │
│   │   └───collection
│   │       ├───failed
│   │       ├───incoming
│   │       └───processed
│   ├───import_templates
│   │       .gitkeep
│   │       collection_import_template.csv
│   │
│   ├───raw
│   │   │   README.md
│   │   │
│   │   └───cardmarket
│   │       └───pokemon
│   │           ├───price_guides
│   │           │       price_guide_6_2026-06-29.json
│   │           │       price_guide_6_2026-06-30.json
│   │           │       price_guide_6_2026-07-01.json
│   │           │       price_guide_6_2026-07-02.json
│   │           │       price_guide_6_2026-07-03.json
│   │           │       price_guide_6_2026-07-04.json
│   │           │       price_guide_6_2026-07-05.json
│   │           │       price_guide_6_2026-07-06.json
│   │           │       price_guide_6_2026-07-07.json
│   │           │       price_guide_6_2026-07-08.json
│   │           │
│   │           └───product_catalogs
│   │                   products_nonsingles_6_2026-07-05.json
│   │                   products_singles_6_2026-07-05.json
│   │
│   ├───reference
│   │   │   expansions.csv
│   │   │   expansions_seed.csv
│   │   │   README.md
│   │   │   reference_data.md
│   │   │
│   │   └───pokemon_tcg
│   │       └───sets
│   │               en.json
│   │               pokemon_tcg_sets.csv
│   │               Pokemon_TCG_Sets_Reference_Dataset.md
│   │               README.md
│   │
│   └───sample
│           .gitkeep
│           README.md
│
├───db
│   ├───backups
│   │       README.md
│   │
│   └───local
│           pokemon_cardmarket_bi.db
│           pokemon_cardmarket_bi.db-journal
│           README.md
│
├───docs
│   │   01-mvp-scope.md
│   │   02-data-model.md
│   │   03-data-dictionary.md
│   │   04-etl-pipeline-design.md
│   │   05-raw-archive-strategy.md
│   │   06-github-repository-structure.md
│   │   07-github-actions-logic.md
│   │   08-collection-import-flow.md
│   │   09-analytics-signal-definitions.md
│   │   10-readme-documentation-structure.md
│   │   11-local-environment-setup.md
│   │   future-cardmarket-expansions.md
│   │
│   └───stages
│           01-pokemon-tcg-sets-reference.md
│           02-cardmarket-product-catalog-foundation.md
│           plan_claude.md
│           README.md
│
├───logs
│   │   README.md
│   │
│   ├───collection_import
│   ├───ingestion
│   └───validation
├───scripts
│   └───reference
│           extract_expansions_seed.py
│           load_expansions.py
│           load_pokemon_tcg_sets.py
│           validate_expansions_reference.py
│
├───sql
│   ├───checks
│   │       .gitkeep
│   │       check_category_mismatch.sql
│   │       check_duplicate_price_snapshots.sql
│   │       check_empty_price_snapshot.sql
│   │       check_invalid_collection_items.sql
│   │       check_missing_products.sql
│   │       check_products_without_prices.sql
│   │       missing_expansions_check.sql
│   │       pokemon_tcg_sets_basic_check.sql
│   │       products_without_expansion_reference_check.sql
│   │
│   ├───import
│   │       import_pokemon_tcg_sets.sql
│   │
│   ├───schema
│   │       .gitkeep
│   │       001_create_products.sql
│   │       002_create_price_snapshots.sql
│   │       003_create_collection_items.sql
│   │       004_create_collection_import_staging.sql
│   │       005_create_watchlist.sql
│   │       006_create_analytics_signals.sql
│   │       00_pokemon_tcg_sets.sql
│   │       01_expansions.sql
│   │       01_expansions_sqlite.sql
│   │       reference_schema.sql
│   │
│   └───views
│           .gitkeep
│           vw_collection_current_value.sql
│           vw_collection_summary.sql
│           vw_latest_prices.sql
│           vw_products_enriched.sql
│           vw_products_enriched_sqlite.sql
│           vw_products_without_prices.sql
│           vw_product_price_history.sql
│
├───src
│   │   __init__.py
│   │
│   ├───analytics
│   │       signals.py
│   │       valuation.py
│   │       __init__.py
│   │
│   ├───collection
│   │       import_reader.py
│   │       matching.py
│   │       promote.py
│   │       review.py
│   │       __init__.py
│   │
│   ├───config
│   │       config.py
│   │       database.py
│   │       settings.py
│   │       timezone.py
│   │       __init__.py
│   │
│   ├───ingestion
│   │       archive.py
│   │       download.py
│   │       download_price_guide.py
│   │       run_daily_price_guide.py
│   │       run_product_catalog.py
│   │       __init__.py
│   │
│   ├───load
│   │       canonical_file.py
│   │       upsert.py
│   │       waiting_for_product.py
│   │       __init__.py
│   │
│   ├───transform
│   │       normalize.py
│   │       validate.py
│   │       __init__.py
│   │
│   └───utils
│           archive_filenames.py
│           dates.py
│           date_helpers.py
│           filenames.py
│           ftp.py
│           json_utils.py
│           logging_utils.py
│           __init__.py
│

│
└───tests
        conftest.py
        README.md
        test_archive_filenames.py
        test_date_helpers.py
        test_download_price_guide.py
        test_expansions_reference.py
        __init__.py