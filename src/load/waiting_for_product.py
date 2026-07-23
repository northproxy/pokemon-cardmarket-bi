"""
Recheck collection_import_staging rows stuck in match_status =
'waiting_for_product', after a successful product catalog load.

Source of truth: docs/08-collection-import-flow.md ("waiting_for_product"),
docs/02-data-model.md, docs/04-etl-pipeline-design.md (catalog pipeline
step 14), docs/07-github-actions-logic.md (catalog pipeline step 10).

Scope kept deliberately narrow: a waiting_for_product row already has
matched_id_product set (from an earlier exact id_product or exact name
match in src/collection/ -- see docs/08 "Matching Logic"). The ONLY thing
that changed for these rows is that a product catalog run just happened,
so the only question this module answers is "does matched_id_product
exist in `products` now?" It does not re-run full field validation
(purchase_price, purchase_date, etc.) -- that already passed when the row
was first staged, and re-validating it here would duplicate logic that
belongs in src/collection/, not src/load/.
"""
from __future__ import annotations

import psycopg


def recheck_waiting_for_product(conn: "psycopg.Connection") -> int:
    """
    Move every collection_import_staging row with
    match_status = 'waiting_for_product' to match_status = 'ready_to_import'
    if matched_id_product now exists in `products`. Rows whose
    matched_id_product still doesn't exist are left untouched (still
    waiting).

    Call this AFTER a successful upsert_products() batch for this catalog
    run (docs/07 step 10: "Recheck ... against the refreshed products
    table"). Does not commit -- caller controls the transaction.

    Returns the number of rows moved to ready_to_import.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE collection_import_staging AS s
               SET match_status = 'ready_to_import',
                   error_message = NULL
              FROM products AS p
             WHERE s.match_status = 'waiting_for_product'
               AND s.matched_id_product = p.id_product
            """
        )
        return cur.rowcount
