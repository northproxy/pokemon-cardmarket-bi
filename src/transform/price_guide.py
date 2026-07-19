"""
Validation and normalization for the daily Cardmarket price guide file
(price_guide_6.json).

Scope, per docs/06-github-repository-structure.md (src/transform/):
    - validate JSON structure
    - check required fields
    - normalize hyphenated field names
    - prepare price snapshot records

This module does NOT touch the database and does NOT compute
snapshot_date itself -- that's an Europe/Vienna calculation owned by
src/config / src/ingestion (see docs/04 "Price Snapshot Date Logic").
Callers pass snapshot_date in explicitly, so there is exactly one place
in the codebase that owns that timezone rule.

source_created_at IS derived here, from the price guide file's own
root-level "createdAt" field (confirmed present via a real sample file,
2026-07-19) -- see extract_source_created_at() below.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from src.transform.errors import RecordValidationError, ValidationError

# Cardmarket source field -> normalized snake_case DB column.
# docs/02-data-model.md, docs/03-data-dictionary.md, docs/04 "Field Normalization"
HOLO_FIELD_MAP = {
    "avg-holo": "avg_holo",
    "low-holo": "low_holo",
    "trend-holo": "trend_holo",
    "avg1-holo": "avg1_holo",
    "avg7-holo": "avg7_holo",
    "avg30-holo": "avg30_holo",
}

# Non-holo price fields: same name in source and DB, just carried through.
PLAIN_PRICE_FIELDS = ("avg", "low", "trend", "avg1", "avg7", "avg30")


def extract_records(raw_json: Any) -> list[dict]:
    """
    Return the list of price guide records from the parsed JSON root.

    CONFIRMED shape (see data/sample/price_guide_6_sample.json, checked
    2026-07-19):
        {"version": 1, "createdAt": "2026-06-29T02:55:18+0200",
         "priceGuides": [ {...}, {...}, ... ]}

    A bare list is still accepted as a defensive fallback in case the
    shape ever changes, but "priceGuides" is now the confirmed, expected
    key -- this is no longer a guess.
    """
    if isinstance(raw_json, dict):
        candidate = raw_json.get("priceGuides")
        if isinstance(candidate, list):
            return candidate

    if isinstance(raw_json, list):
        return raw_json

    raise ValidationError(
        "Could not locate a records list in price_guide_6.json. Root was "
        f"{type(raw_json).__name__}; expected a dict with a 'priceGuides' "
        "list (confirmed shape), or a bare list as a fallback."
    )


def extract_source_created_at(raw_json: Any) -> datetime.datetime | None:
    """
    Parse Cardmarket's own createdAt timestamp from the price guide root.

    CONFIRMED present as of a real sample file checked 2026-07-19
    (root-level "createdAt": "2026-06-29T02:55:18+0200") -- this corrects
    the earlier assumption (docs/03-data-dictionary.md v0.4) that
    Cardmarket source files carry no usable file-level timestamp. See
    docs/02 v0.6, docs/03 v0.6, docs/04 v0.7 for the corrected docs.

    One createdAt value applies to the whole file, so it is used as
    source_created_at for every record loaded from that file.

    Returns None (rather than raising) if the field is missing or
    unparseable -- source_created_at is a nullable column, and a
    malformed/absent timestamp on this one field shouldn't fail the
    whole daily pipeline.
    """
    if not isinstance(raw_json, dict):
        return None

    raw_value = raw_json.get("createdAt")
    if not raw_value:
        return None

    try:
        # Observed format: "2026-06-29T02:55:18+0200" (ISO 8601, no colon
        # in the UTC offset). %z accepts both "+0200" and "+02:00".
        return datetime.datetime.strptime(raw_value, "%Y-%m-%dT%H:%M:%S%z")
    except (ValueError, TypeError):
        return None


def validate_price_guide(raw_json: Any) -> list[dict]:
    """
    Minimum MVP validation, per docs/04 "Validation Rules" > "Price Guide File":
        - file is not empty (zero records)
        - id_product exists on every record

    Price fields (avg, low, trend, avg1, avg7, avg30, and the holo
    variants) are nullable per docs/02/03 and are NOT validated here --
    only checked/coerced during normalization below.

    Raises ValidationError / RecordValidationError on failure. Per docs/04
    thresholds, either should be treated by the caller as a pipeline
    FAILURE (no data loaded), not a warning.
    """
    records = extract_records(raw_json)

    if len(records) == 0:
        raise ValidationError("price_guide_6.json contained zero records.")

    for i, record in enumerate(records):
        if "idProduct" not in record or record["idProduct"] in (None, ""):
            raise RecordValidationError(
                f"Record at index {i} is missing required field 'idProduct'.",
                record_index=i,
                raw_record=record,
            )

    return records


def _to_decimal(value: Any) -> Decimal | None:
    """
    Coerce a raw price value to Decimal, treating missing/malformed
    values as null rather than failing the row. Price fields are
    documented as nullable (docs/02/03) and a single bad value shouldn't
    fail the whole daily pipeline (see docs/04 failure thresholds, which
    only fail on a MISSING id_product/name, not malformed optional
    fields). If per-field malformed-value tracking becomes useful later,
    it belongs in a data quality check, not here.
    """
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def normalize_price_guide_record(
    record: dict, snapshot_date, source_created_at=None
) -> dict:
    """
    Convert one raw Cardmarket price guide record into a price_snapshots-
    ready dict (snake_case columns matching docs/02/03 exactly).

    snapshot_date and source_created_at must be supplied by the caller.
    """
    out = {
        "snapshot_date": snapshot_date,
        "source_created_at": source_created_at,
        "id_product": int(record["idProduct"]),
        "id_category": (
            int(record["idCategory"])
            if record.get("idCategory") not in (None, "")
            else None
        ),
    }

    for field in PLAIN_PRICE_FIELDS:
        out[field] = _to_decimal(record.get(field))

    for source_field, db_field in HOLO_FIELD_MAP.items():
        out[db_field] = _to_decimal(record.get(source_field))

    return out


def transform_price_guide(
    raw_json: Any, snapshot_date, source_created_at=None
) -> list[dict]:
    """
    Validate + normalize an entire price guide file in one call.

    source_created_at defaults to Cardmarket's own root-level createdAt
    timestamp (see extract_source_created_at) -- pass an explicit value
    only to override that (e.g. in tests, or if createdAt is ever absent
    and a fallback is needed).
    """
    records = validate_price_guide(raw_json)
    if source_created_at is None:
        source_created_at = extract_source_created_at(raw_json)
    return [
        normalize_price_guide_record(r, snapshot_date, source_created_at)
        for r in records
    ]
