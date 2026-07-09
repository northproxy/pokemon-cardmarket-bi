"""
Extract unique Cardmarket Pokémon idExpansion values from product catalog JSON files.

Input:
    data/raw/cardmarket/pokemon/product_catalogs/products_singles_6_YYYY-MM-DD.json
    data/raw/cardmarket/pokemon/product_catalogs/products_nonsingles_6_YYYY-MM-DD.json

Output:
    data/reference/expansions_seed.csv

The script does not modify the curated reference table `expansions.csv`.
It only creates a seed/work file that can be manually enriched and reviewed.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INPUT_DIR = Path("data/raw/cardmarket/pokemon/product_catalogs")
DEFAULT_OUTPUT_FILE = Path("data/reference/expansions_seed.csv")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_product_list(data: Any) -> list[dict[str, Any]]:
    """
    Cardmarket JSON can be a list directly or a dictionary wrapping the list.
    This function keeps the script resilient to small source format variations.
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        candidate_keys = [
            "products",
            "product",
            "data",
            "productList",
            "product_list",
        ]

        for key in candidate_keys:
            value = data.get(key)
            if isinstance(value, list):
                return value

        # Last-resort fallback: first list of dictionaries in the object.
        for value in data.values():
            if isinstance(value, list) and all(isinstance(item, dict) for item in value[:10]):
                return value

    raise ValueError("Could not find a product list in the JSON structure.")


def get_field(product: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in product:
            return product[name]
    return None


def extract_from_files(input_files: list[Path]) -> tuple[Counter[int], dict[int, dict[str, Any]]]:
    expansion_counter: Counter[int] = Counter()
    samples: dict[int, dict[str, Any]] = {}

    for input_file in input_files:
        data = load_json(input_file)
        products = find_product_list(data)

        for product in products:
            raw_id_expansion = get_field(product, "idExpansion", "id_expansion", "expansionId", "Expansion ID")

            if raw_id_expansion in (None, ""):
                continue

            try:
                id_expansion = int(raw_id_expansion)
            except (TypeError, ValueError):
                continue

            expansion_counter[id_expansion] += 1

            if id_expansion not in samples:
                samples[id_expansion] = {
                    "sample_id_product": get_field(product, "idProduct", "id_product", "productId", "Product ID"),
                    "sample_product_name": get_field(product, "name", "Name", "productName", "product_name"),
                    "source_file": input_file.name,
                }

    return expansion_counter, samples


def write_seed(
    output_file: Path,
    expansion_counter: Counter[int],
    samples: dict[int, dict[str, Any]],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id_expansion",
        "detected_product_count",
        "sample_id_product",
        "sample_product_name",
        "source_file",
        "name_en",
        "name_de",
        "slug",
        "series_en",
        "series_de",
        "release_date",
        "card_count",
        "source_url_en",
        "source_url_de",
        "notes",
    ]

    with output_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for id_expansion in sorted(expansion_counter):
            sample = samples.get(id_expansion, {})

            writer.writerow(
                {
                    "id_expansion": id_expansion,
                    "detected_product_count": expansion_counter[id_expansion],
                    "sample_id_product": sample.get("sample_id_product", ""),
                    "sample_product_name": sample.get("sample_product_name", ""),
                    "source_file": sample.get("source_file", ""),
                    "name_en": "",
                    "name_de": "",
                    "slug": "",
                    "series_en": "",
                    "series_de": "",
                    "release_date": "",
                    "card_count": "",
                    "source_url_en": "",
                    "source_url_de": "",
                    "notes": "",
                }
            )


def discover_input_files(input_dir: Path) -> list[Path]:
    files = sorted(input_dir.glob("products_*_6_*.json"))
    if not files:
        raise FileNotFoundError(f"No product catalog files found in {input_dir}")
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract unique Cardmarket idExpansion values.")
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
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Seed CSV output path. Default: {DEFAULT_OUTPUT_FILE}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_files = args.input_file if args.input_file else discover_input_files(args.input_dir)
    expansion_counter, samples = extract_from_files(input_files)
    write_seed(args.output_file, expansion_counter, samples)

    print(f"Created: {args.output_file}")
    print(f"Input files: {len(input_files)}")
    print(f"Unique idExpansion values: {len(expansion_counter)}")


if __name__ == "__main__":
    main()
