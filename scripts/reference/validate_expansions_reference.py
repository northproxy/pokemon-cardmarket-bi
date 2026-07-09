"""
Validate that all idExpansion values used in Cardmarket product catalogs
exist in the curated expansions reference table.

This script is designed for local checks and CI checks.
It exits with code 1 when missing expansions are detected.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = Path("data/raw/cardmarket/pokemon/product_catalogs")
DEFAULT_REFERENCE_FILE = Path("data/reference/expansions.csv")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_product_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["products", "product", "data", "productList", "product_list"]:
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value[:10]):
                return value

    raise ValueError("Could not find product list in JSON file.")


def get_field(product: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in product:
            return product[name]
    return None


def discover_input_files(input_dir: Path) -> list[Path]:
    files = sorted(input_dir.glob("products_*_6_*.json"))
    if not files:
        raise FileNotFoundError(f"No product catalog files found in {input_dir}")
    return files


def load_catalog_expansion_ids(input_files: list[Path]) -> set[int]:
    ids: set[int] = set()

    for input_file in input_files:
        products = find_product_list(load_json(input_file))

        for product in products:
            raw_id = get_field(product, "idExpansion", "id_expansion", "expansionId", "Expansion ID")
            if raw_id in (None, ""):
                continue

            try:
                ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue

    return ids


def load_reference_expansion_ids(reference_file: Path) -> set[int]:
    ids: set[int] = set()

    with reference_file.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        if "id_expansion" not in (reader.fieldnames or []):
            raise ValueError("Reference file must contain column: id_expansion")

        for row in reader:
            raw_id = row.get("id_expansion")
            if raw_id in (None, ""):
                continue
            ids.add(int(raw_id))

    return ids


def validate_required_metadata(reference_file: Path) -> list[str]:
    errors: list[str] = []
    required_columns = ["id_expansion", "name_en", "name_de"]

    with reference_file.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []

        for column in required_columns:
            if column not in fieldnames:
                errors.append(f"Missing required column: {column}")

        for line_number, row in enumerate(reader, start=2):
            id_expansion = row.get("id_expansion", "").strip()
            name_en = row.get("name_en", "").strip()
            name_de = row.get("name_de", "").strip()

            if not id_expansion:
                errors.append(f"Line {line_number}: id_expansion is empty")
            if not name_en:
                errors.append(f"Line {line_number}: name_en is empty for id_expansion={id_expansion}")
            if not name_de:
                errors.append(f"Line {line_number}: name_de is empty for id_expansion={id_expansion}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate expansions reference coverage.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Folder with Cardmarket product catalog JSON files. Default: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        action="append",
        help="Specific product catalog JSON file. Can be passed multiple times.",
    )
    parser.add_argument(
        "--reference-file",
        type=Path,
        default=DEFAULT_REFERENCE_FILE,
        help=f"Curated expansions CSV path. Default: {DEFAULT_REFERENCE_FILE}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_files = args.input_file if args.input_file else discover_input_files(args.input_dir)

    catalog_ids = load_catalog_expansion_ids(input_files)
    reference_ids = load_reference_expansion_ids(args.reference_file)

    missing_ids = sorted(catalog_ids - reference_ids)
    unused_reference_ids = sorted(reference_ids - catalog_ids)
    metadata_errors = validate_required_metadata(args.reference_file)

    if missing_ids:
        print("Missing expansions in data/reference/expansions.csv:")
        for id_expansion in missing_ids:
            print(f"- {id_expansion}")

    if unused_reference_ids:
        print("Reference expansions not found in current product catalogs:")
        for id_expansion in unused_reference_ids:
            print(f"- {id_expansion}")

    if metadata_errors:
        print("Metadata validation errors:")
        for error in metadata_errors:
            print(f"- {error}")

    if missing_ids or metadata_errors:
        sys.exit(1)

    print("Expansion reference validation passed.")
    print(f"Catalog expansion IDs: {len(catalog_ids)}")
    print(f"Reference expansion IDs: {len(reference_ids)}")


if __name__ == "__main__":
    main()
