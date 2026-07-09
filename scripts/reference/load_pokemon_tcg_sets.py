"""
Load Pokémon TCG sets reference data.

Project:
    pokemon-cardmarket-bi

Purpose:
    Reads the Pokémon TCG sets JSON file and converts it into a clean CSV file
    for the local reference table: pokemon_tcg_sets.

Input:
    data/reference/pokemon_tcg/sets/en.json

Output:
    data/reference/pokemon_tcg/sets/pokemon_tcg_sets.csv

Notes:
    This script does not download data.
    This script does not load data directly into Supabase.
    It only transforms the local source JSON into a clean CSV file.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = PROJECT_ROOT / "data" / "reference" / "pokemon_tcg" / "sets" / "en.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "reference" / "pokemon_tcg" / "sets" / "pokemon_tcg_sets.csv"


CSV_FIELDS = [
    "pokemon_tcg_set_id",
    "name_en",
    "series_en",
    "ptcgo_code",
    "release_date",
    "printed_total",
    "total_cards",
    "secret_card_count",
    "legalities",
    "symbol_url",
    "logo_url",
    "source_updated_at",
    "is_active",
    "notes",
]


def parse_date(value: str | None) -> str | None:
    """
    Convert source date from YYYY/MM/DD to YYYY-MM-DD.

    Example:
        2022/09/09 -> 2022-09-09
    """
    if not value:
        return None

    return datetime.strptime(value, "%Y/%m/%d").date().isoformat()


def parse_timestamp(value: str | None) -> str | None:
    """
    Convert source timestamp from YYYY/MM/DD HH:MM:SS to ISO-like format.

    Example:
        2022/09/09 13:45:00 -> 2022-09-09 13:45:00
    """
    if not value:
        return None

    return datetime.strptime(value, "%Y/%m/%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")


def calculate_secret_card_count(
    printed_total: int | None,
    total_cards: int | None,
) -> int | None:
    """
    Calculate number of secret cards.

    Formula:
        secret_card_count = max(total_cards - printed_total, 0)

    Some promo or special sets in the source data may have total_cards lower
    than printed_total. In those cases, keep the analytical field non-negative
    and document the anomaly in the notes field.
    """
    if printed_total is None or total_cards is None:
        return None

    return max(total_cards - printed_total, 0)


def build_notes(
    printed_total: int | None,
    total_cards: int | None,
) -> str:
    """
    Build notes for source-data anomalies that should be preserved.
    """
    if printed_total is None or total_cards is None:
        return ""

    if total_cards < printed_total:
        return (
            "Source has total_cards lower than printed_total; "
            "secret_card_count was normalized to 0."
        )

    return ""


def normalize_set(source_row: dict[str, Any]) -> dict[str, Any]:
    """
    Convert one source JSON object into one clean CSV row.
    """
    printed_total = source_row.get("printedTotal")
    total_cards = source_row.get("total")

    images = source_row.get("images") or {}
    legalities = source_row.get("legalities") or {}
    notes = build_notes(
        printed_total=printed_total,
        total_cards=total_cards,
    )

    return {
        "pokemon_tcg_set_id": source_row.get("id"),
        "name_en": source_row.get("name"),
        "series_en": source_row.get("series"),
        "ptcgo_code": source_row.get("ptcgoCode"),
        "release_date": parse_date(source_row.get("releaseDate")),
        "printed_total": printed_total,
        "total_cards": total_cards,
        "secret_card_count": calculate_secret_card_count(
            printed_total=printed_total,
            total_cards=total_cards,
        ),
        "legalities": json.dumps(legalities, ensure_ascii=False),
        "symbol_url": images.get("symbol"),
        "logo_url": images.get("logo"),
        "source_updated_at": parse_timestamp(source_row.get("updatedAt")),
        "is_active": True,
        "notes": notes,
    }


def load_source_json(input_file: Path) -> list[dict[str, Any]]:
    """
    Load source JSON file.
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Expected source JSON to contain a list of sets.")

    return data


def write_csv(rows: list[dict[str, Any]], output_file: Path) -> None:
    """
    Write normalized rows to CSV.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    source_rows = load_source_json(INPUT_FILE)
    normalized_rows = [normalize_set(row) for row in source_rows]

    write_csv(normalized_rows, OUTPUT_FILE)

    print("Pokémon TCG sets CSV created successfully.")
    print(f"Input file:  {INPUT_FILE}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Rows:        {len(normalized_rows)}")


if __name__ == "__main__":
    main()