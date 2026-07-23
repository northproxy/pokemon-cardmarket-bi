import uuid

from src.load.products import upsert_products
from src.load.waiting_for_product import recheck_waiting_for_product


def make_product_row(**overrides):
    base = {
        "id_product": 500,
        "name": "Charizard ex",
        "id_category": 7,
        "category_name": "Singles",
        "id_expansion": 3,
        "id_metacard": 1,
        "date_added": None,
        "product_group": "single",
        "source_file": "products_singles_6.json",
    }
    base.update(overrides)
    return base


def insert_staging_row(conn, matched_id_product, match_status="waiting_for_product"):
    row_id = uuid.uuid4()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO collection_import_staging (
                import_row_id, import_batch_id, matched_id_product,
                match_status, match_confidence, error_message
            ) VALUES (%s, %s, %s, %s, NULL, %s)
            """,
            (
                row_id,
                "test-batch-001",
                matched_id_product,
                match_status,
                "Product matched, but not yet present in the local catalog"
                if match_status == "waiting_for_product"
                else None,
            ),
        )
    return row_id


def fetch_status(conn, row_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT match_status, error_message FROM collection_import_staging WHERE import_row_id = %s",
            (row_id,),
        )
        return cur.fetchone()


class TestRecheckWaitingForProduct:
    def test_moves_to_ready_to_import_once_product_exists(self, db_conn):
        row_id = insert_staging_row(db_conn, matched_id_product=500)
        db_conn.commit()

        # Product doesn't exist yet -- recheck should do nothing.
        changed = recheck_waiting_for_product(db_conn)
        db_conn.commit()
        assert changed == 0
        assert fetch_status(db_conn, row_id)[0] == "waiting_for_product"

        # Now the catalog run happens and the product is upserted.
        upsert_products(db_conn, [make_product_row(id_product=500)])
        db_conn.commit()

        changed = recheck_waiting_for_product(db_conn)
        db_conn.commit()
        assert changed == 1
        status, error_message = fetch_status(db_conn, row_id)
        assert status == "ready_to_import"
        assert error_message is None

    def test_leaves_still_unmatched_rows_untouched(self, db_conn):
        row_id = insert_staging_row(db_conn, matched_id_product=999)
        db_conn.commit()
        # A different product gets catalogued, not this one.
        upsert_products(db_conn, [make_product_row(id_product=500)])
        db_conn.commit()

        changed = recheck_waiting_for_product(db_conn)
        db_conn.commit()

        assert changed == 0
        assert fetch_status(db_conn, row_id)[0] == "waiting_for_product"

    def test_does_not_touch_rows_in_other_statuses(self, db_conn):
        ready_row = insert_staging_row(db_conn, matched_id_product=500, match_status="ready_to_import")
        error_row = insert_staging_row(db_conn, matched_id_product=500, match_status="error")
        db_conn.commit()
        upsert_products(db_conn, [make_product_row(id_product=500)])
        db_conn.commit()

        recheck_waiting_for_product(db_conn)
        db_conn.commit()

        assert fetch_status(db_conn, ready_row)[0] == "ready_to_import"
        assert fetch_status(db_conn, error_row)[0] == "error"

    def test_multiple_rows_same_product_all_move(self, db_conn):
        row_a = insert_staging_row(db_conn, matched_id_product=500)
        row_b = insert_staging_row(db_conn, matched_id_product=500)
        db_conn.commit()
        upsert_products(db_conn, [make_product_row(id_product=500)])
        db_conn.commit()

        changed = recheck_waiting_for_product(db_conn)
        db_conn.commit()

        assert changed == 2
        assert fetch_status(db_conn, row_a)[0] == "ready_to_import"
        assert fetch_status(db_conn, row_b)[0] == "ready_to_import"
