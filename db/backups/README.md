# db/backups/

Manual backups of the **prod** Supabase project. The free tier has no
automated backups — see docs/04-etl-pipeline-design.md, "Backing up the
prod project," for the full explanation and exact command.

This README is committed. The actual `.sql.gz` dump files are NOT —
they're gitignored, kept here locally, and should be synced somewhere
off-machine (a cloud-synced folder is enough at this project's scale).

Quick reference:

    pg_dump "$DATABASE_URL_BACKUP" \
      --clean --if-exists --no-owner --no-privileges \
      | gzip > db/backups/pokemon_cardmarket_bi_prod_$(date +%Y-%m-%d).sql.gz

DATABASE_URL_BACKUP must be the Session Pooler connection string (not the
transaction pooler used by DATABASE_URL for normal pipeline runs) for the
PROD project. Never commit this value or any file in this folder except
this README.

Restore (same project or, as a drill, the dev project):

    psql "$DATABASE_URL_BACKUP" < db/backups/pokemon_cardmarket_bi_prod_2026-07-05.sql.gz
    # (gunzip first if compressed)
