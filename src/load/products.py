"""
Loading logic for the `products` table.

Source of truth: docs/02-data-model.md, docs/03-data-dictionary.md,
docs/04-etl-pipeline-design.md ("Product Catalog Update Logic",
"Product Deduplication Rule"), docs/07-github-actions-logic.md.

Responsibilities kept here, per docs/06 (src/load/):
    - upsert products by id_product
    - is_active_in_catalog transitions

Deliberately NOT here (already done upstream, in src/transform/):
    - product_group / source_file enrichment (transform-time)
    - cross-file duplicate id_product detection
      (src/transform/product_catalogs.py::check_duplicate_id_products --
      called by the orchestrator BEFORE upsert_products, since a
      conflicting duplicate must FAIL the whole catalog run per docs/04,
      not be silently upserted)
"""
from __future__ import annotations

from typing import Iterable

import psycopg

_UPSERT_SQL = """
INSERT INTO products (
    id_product, name, id_category, category_name, id_expansion,
    id_metacard, date_added, product_group, source_file,
    is_active_in_catalog, first_seen_at, last_seen_at
)
VALUES (
    %(id_product)s, %(name)s, %(id_category)s, %(category_name)s,
    %(id_expansion)s, %(id_metacard)s, %(date_added)s, %(product_group)s,
    %(source_file)s, TRUE, now(), now()
)
ON CONFLICT (id_product) DO UPDATE SET
    name                  = EXCLUDED.name,
    id_category            = EXCLUDED.id_category,
    category_name           = EXCLUDED.category_name,
    id_expansion             = EXCLUDED.id_expansion,
    id_metacard               = EXCLUDED.id_metacard,
    date_added                 = EXCLUDED.date_added,
    product_group                = EXCLUDED.product_group,
    source_file                    = EXCLUDED.source_file,
    is_active_in_catalog             = TRUE,
    last_seen_at                       = now()
    -- first_seen_at is intentionally NOT in the SET list: on conflict it
    -- must keep its original value (docs/02/03: "first time this project
    -- saw the product"). Leaving it out of DO UPDATE SET is what
    -- preserves the existing row's value instead of overwriting it.
"""


def upsert_products(conn: "psycopg.Connection", rows: Iterable[dict]) -> int:
    """
    Upsert a batch of already-transformed product rows (see
    src/transform/product_catalogs.py::normalize_product_record) into
    `products`.

    On INSERT: first_seen_at = last_seen_at = now(), is_active_in_catalog = true.
    On CONFLICT (id_product already exists): update the catalog-sourced
    fields, set is_active_in_catalog = true (it was seen again), bump
    last_seen_at = now(), and leave first_seen_at untouched.

    Does not commit -- caller controls the transaction (see
    src/load/db.py::get_connection). Returns the number of rows upserted.
    """
    rows = list(rows)
    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)

    return len(rows)


def mark_missing_products_inactive(
    conn: "psycopg.Connection", seen_id_products: Iterable[int]
) -> int:
    """
    Set is_active_in_catalog = false for every currently-active product
    NOT present in `seen_id_products` (the full combined set of
    id_product values from THIS catalog run's singles + non-singles
    files).

    Per docs/01/02/03/04: no grace period, no N-miss tolerance -- a
    product is marked inactive the FIRST time it's missing from a
    freshly downloaded catalog. Never deletes rows.

    Must be called with the full combined id_product set from a
    SUCCESSFUL run of both catalog files -- per docs/04's catalog
    failure rule, if singles or non-singles failed, the caller must not
    call this at all (products stays untouched, see docs/07 "Product
    Catalog Failure").
    """
    seen = list(seen_id_products)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE products
               SET is_active_in_catalog = FALSE
             WHERE is_active_in_catalog = TRUE
               AND id_product != ALL(%(seen)s)
            """,
            {"seen": seen},
        )
        return cur.rowcount


def get_new_product_ids_since(
    conn: "psycopg.Connection", seen_id_products: Iterable[int]
) -> list[int]:
    """
    Of the id_product values in this catalog run, return the ones that
    did NOT already exist in `products` before this run (i.e. brand new
    products). Intended to be called AFTER upsert_products() for the same
    batch would defeat the purpose (every id would already exist) -- call
    this BEFORE upsert_products() with the same id list, or track new IDs
    another way. Provided as a convenience for the catalog pipeline
    summary (docs/04 "How many new products were detected?").
    """
    seen = list(seen_id_products)
    if not seen:
        return []

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id_product FROM products WHERE id_product = ANY(%(seen)s)",
            {"seen": seen},
        )
        already_known = {row[0] for row in cur.fetchall()}

    return [pid for pid in seen if pid not in already_known]
