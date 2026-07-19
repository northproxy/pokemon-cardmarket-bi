"""
Validation and normalization for the weekly Cardmarket product catalog
files (products_singles_6.json, products_nonsingles_6.json).

Scope, per docs/06-github-repository-structure.md (src/transform/):
    - validate JSON structure
    - check required fields
    - prepare product records (product_group / source_file enrichment)

Deliberately NOT handled here (belongs in src/load/ instead):
    - first_seen_at / last_seen_at / is_active_in_catalog -- these depend
      on whether the id_product already exists in the database, i.e.
      upsert logic (see docs/04 "Product Catalog Update Logic").
    - cross-file duplicate id_product detection -- requires combining
      both files' output (see docs/04 "Product Deduplication Rule").
      check_duplicate_id_products() below is defined here for proximity
      to the normalization logic it operates on, but is meant to be
      CALLED from src/load/ after both files are transformed.
"""
from __future__ import annotations

from typing import Any, Literal

from src.transform.errors import RecordValidationError, ValidationError

SourceFile = Literal["products_singles_6.json", "products_nonsingles_6.json"]

# docs/02 "Allowed Values", docs/03
SOURCE_FILE_TO_PRODUCT_GROUP = {
    "products_singles_6.json": "single",
    "products_nonsingles_6.json": "non_single",
}


def extract_records(raw_json: Any, source_file: str) -> list[dict]:
    """
    Same unconfirmed-root-shape caveat as
    src/transform/price_guide.py::extract_records -- see that docstring.
    The product catalog files' exact root shape is equally unconfirmed
    as of this writing.
    """
    if isinstance(raw_json, list):
        return raw_json

    if isinstance(raw_json, dict):
        for key in ("products", "data", "items"):
            candidate = raw_json.get(key)
            if isinstance(candidate, list):
                return candidate

    raise ValidationError(
        f"Could not locate a records list in {source_file}. Root was "
        f"{type(raw_json).__name__}. This mapping is UNCONFIRMED -- "
        "update extract_records() once the real file structure is known."
    )


def validate_product_catalog(raw_json: Any, source_file: SourceFile) -> list[dict]:
    """
    Minimum MVP validation, per docs/04 "Validation Rules" > "Product Files":
        - file is not empty (zero records)
        - id_product exists on every record
        - name exists on every record

    id_category / id_expansion / id_metacard / date_added are nullable
    per docs/02/03 and are not validated here.
    """
    if source_file not in SOURCE_FILE_TO_PRODUCT_GROUP:
        raise ValueError(
            f"Unknown source_file {source_file!r}. Expected one of "
            f"{list(SOURCE_FILE_TO_PRODUCT_GROUP)}."
        )

    records = extract_records(raw_json, source_file)

    if len(records) == 0:
        raise ValidationError(f"{source_file} contained zero records.")

    for i, record in enumerate(records):
        if "idProduct" not in record or record["idProduct"] in (None, ""):
            raise RecordValidationError(
                f"Record at index {i} in {source_file} is missing required field 'idProduct'.",
                record_index=i,
                raw_record=record,
            )
        if "name" not in record or record["name"] in (None, ""):
            raise RecordValidationError(
                f"Record at index {i} in {source_file} is missing required field 'name'.",
                record_index=i,
                raw_record=record,
            )

    return records


def normalize_product_record(record: dict, source_file: SourceFile) -> dict:
    """
    Convert one raw Cardmarket product record into a products-table-ready
    dict, enriched with product_group / source_file per docs/02/03/04.

    NOT set here (see module docstring): first_seen_at, last_seen_at,
    is_active_in_catalog -- those are upsert-time concerns in src/load/.
    """
    return {
        "id_product": int(record["idProduct"]),
        "name": record["name"],
        "id_category": (
            int(record["idCategory"])
            if record.get("idCategory") not in (None, "")
            else None
        ),
        "category_name": record.get("categoryName"),
        "id_expansion": (
            int(record["idExpansion"])
            if record.get("idExpansion") not in (None, "")
            else None
        ),
        "id_metacard": (
            int(record["idMetacard"])
            if record.get("idMetacard") not in (None, "")
            else None
        ),
        "date_added": record.get("dateAdded"),
        "product_group": SOURCE_FILE_TO_PRODUCT_GROUP[source_file],
        "source_file": source_file,
    }


def transform_product_catalog(raw_json: Any, source_file: SourceFile) -> list[dict]:
    """Validate + normalize an entire catalog file in one call."""
    records = validate_product_catalog(raw_json, source_file)
    return [normalize_product_record(r, source_file) for r in records]


def check_duplicate_id_products(
    singles_records: list[dict], nonsingles_records: list[dict]
) -> list[dict]:
    """
    Cross-file duplicate id_product detection, per docs/04 "Product
    Deduplication Rule". Call this from src/load/ AFTER both files have
    been transformed via transform_product_catalog(), since detecting
    duplicates requires the combined set.

    Returns one entry per id_product present in BOTH files:
        {"id_product": ..., "conflicting": bool, "records": [singles_row, nonsingles_row]}

    Per docs/04:
        same data       -> keep one row, log a warning (conflicting=False)
        conflicting data -> FAIL the catalog pipeline (conflicting=True)

    Callers should fail the whole catalog run if any entry has
    conflicting=True. An empty return list means no duplicates were
    found, which is the expected case.
    """
    by_id_singles = {r["id_product"]: r for r in singles_records}
    by_id_nonsingles = {r["id_product"]: r for r in nonsingles_records}

    shared_ids = set(by_id_singles) & set(by_id_nonsingles)
    duplicates = []

    for id_product in shared_ids:
        a = by_id_singles[id_product]
        b = by_id_nonsingles[id_product]
        # product_group / source_file are expected to differ by
        # definition (that's the whole reason each row exists in its
        # own file) -- exclude them from the equality comparison.
        comparable_a = {k: v for k, v in a.items() if k not in ("product_group", "source_file")}
        comparable_b = {k: v for k, v in b.items() if k not in ("product_group", "source_file")}
        duplicates.append({
            "id_product": id_product,
            "conflicting": comparable_a != comparable_b,
            "records": [a, b],
        })

    return duplicates
