"""
Load curated expansions.csv into a local SQLite database.

Default input:
    data/reference/expansions.csv

Default database:
    db/local/pokemon_cardmarket_bi.db

For Supabase/PostgreSQL, use the SQL schema and load the CSV with your preferred
database client, Supabase table import, or a later PostgreSQL-specific loader.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


DEFAULT_REFERENCE_FILE = Path("data/reference/expansions.csv")
DEFAULT_DATABASE_FILE = Path("db/local/pokemon_cardmarket_bi.db")


CREATE_TABLE_SQL = """
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
"""


UPSERT_SQL = """
INSERT INTO expansions (
    id_expansion,
    name_en,
    name_de,
    slug,
    series_en,
    series_de,
    release_date,
    card_count,
    source_url_en,
    source_url_de,
    is_active,
    notes,
    updated_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(id_expansion) DO UPDATE SET
    name_en = excluded.name_en,
    name_de = excluded.name_de,
    slug = excluded.slug,
    series_en = excluded.series_en,
    series_de = excluded.series_de,
    release_date = excluded.release_date,
    card_count = excluded.card_count,
    source_url_en = excluded.source_url_en,
    source_url_de = excluded.source_url_de,
    is_active = excluded.is_active,
    notes = excluded.notes,
    updated_at = CURRENT_TIMESTAMP;
"""


def parse_bool(value: str | None) -> int:
    if value is None:
        return 1

    normalized = value.strip().lower()

    if normalized in {"true", "1", "yes", "y"}:
        return 1

    if normalized in {"false", "0", "no", "n"}:
        return 0

    return 1


def parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def normalize_row(row: dict[str, str]) -> tuple:
    return (
        int(row["id_expansion"]),
        row["name_en"].strip(),
        row.get("name_de", "").strip() or None,
        row.get("slug", "").strip() or None,
        row.get("series_en", "").strip() or None,
        row.get("series_de", "").strip() or None,
        row.get("release_date", "").strip() or None,
        parse_optional_int(row.get("card_count")),
        row.get("source_url_en", "").strip() or None,
        row.get("source_url_de", "").strip() or None,
        parse_bool(row.get("is_active")),
        row.get("notes", "").strip() or None,
    )


def load_expansions(reference_file: Path, database_file: Path) -> int:
    database_file.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(database_file) as connection:
        connection.execute(CREATE_TABLE_SQL)

        with reference_file.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            rows = [normalize_row(row) for row in reader]

        connection.executemany(UPSERT_SQL, rows)
        connection.commit()

    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load expansions.csv into local SQLite.")
    parser.add_argument(
        "--reference-file",
        type=Path,
        default=DEFAULT_REFERENCE_FILE,
        help=f"Curated expansions CSV path. Default: {DEFAULT_REFERENCE_FILE}",
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=DEFAULT_DATABASE_FILE,
        help=f"SQLite database path. Default: {DEFAULT_DATABASE_FILE}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loaded_count = load_expansions(args.reference_file, args.database_file)

    print(f"Loaded {loaded_count} expansion rows into {args.database_file}")


if __name__ == "__main__":
    main()
