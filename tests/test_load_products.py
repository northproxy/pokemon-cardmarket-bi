import datetime

from src.load.products import (
    get_new_product_ids_since,
    mark_missing_products_inactive,
    upsert_products,
)


def make_row(**overrides):
    base = {
        "id_product": 1,
        "name": "Pikachu",
        "id_category": 7,
        "category_name": "Singles",
        "id_expansion": 3,
        "id_metacard": 99,
        "date_added": None,
        "product_group": "single",
        "source_file": "products_singles_6.json",
    }
    base.update(overrides)
    return base


def fetch_product(conn, id_product):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id_product, name, is_active_in_catalog, first_seen_at, "
            "last_seen_at FROM products WHERE id_product = %s",
            (id_product,),
        )
        row = cur.fetchone()
    return row


class TestUpsertProductsInsert:
    def test_insert_sets_active_true(self, db_conn):
        upsert_products(db_conn, [make_row()])
        db_conn.commit()
        row = fetch_product(db_conn, 1)
        assert row[2] is True  # is_active_in_catalog

    def test_insert_sets_first_seen_and_last_seen_equal(self, db_conn):
        upsert_products(db_conn, [make_row()])
        db_conn.commit()
        row = fetch_product(db_conn, 1)
        first_seen, last_seen = row[3], row[4]
        assert first_seen == last_seen

    def test_returns_count(self, db_conn):
        n = upsert_products(db_conn, [make_row(id_product=1), make_row(id_product=2)])
        assert n == 2

    def test_empty_rows_is_a_noop(self, db_conn):
        n = upsert_products(db_conn, [])
        assert n == 0


class TestUpsertProductsConflict:
    def test_conflict_preserves_first_seen_at(self, db_conn):
        upsert_products(db_conn, [make_row()])
        db_conn.commit()
        first_row = fetch_product(db_conn, 1)
        original_first_seen = first_row[3]

        # Re-upsert with a changed name -- simulates a later catalog run.
        upsert_products(db_conn, [make_row(name="Pikachu (updated)")])
        db_conn.commit()
        second_row = fetch_product(db_conn, 1)

        assert second_row[3] == original_first_seen  # first_seen_at unchanged
        assert second_row[1] == "Pikachu (updated)"   # name did update

    def test_conflict_reactivates_inactive_product(self, db_conn):
        upsert_products(db_conn, [make_row()])
        db_conn.commit()
        mark_missing_products_inactive(db_conn, [])  # id 1 not "seen" -> inactive
        db_conn.commit()
        assert fetch_product(db_conn, 1)[2] is False

        # Product reappears in a later catalog run.
        upsert_products(db_conn, [make_row()])
        db_conn.commit()
        assert fetch_product(db_conn, 1)[2] is True

    def test_no_duplicate_rows_created(self, db_conn):
        upsert_products(db_conn, [make_row()])
        upsert_products(db_conn, [make_row(name="Renamed")])
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM products WHERE id_product = 1")
            (count,) = cur.fetchone()
        assert count == 1


class TestMarkMissingProductsInactive:
    def test_marks_unseen_products_inactive(self, db_conn):
        upsert_products(db_conn, [make_row(id_product=1), make_row(id_product=2)])
        db_conn.commit()

        # Only id_product=1 appears in the "latest" catalog run.
        changed = mark_missing_products_inactive(db_conn, [1])
        db_conn.commit()

        assert changed == 1
        assert fetch_product(db_conn, 1)[2] is True
        assert fetch_product(db_conn, 2)[2] is False

    def test_never_deletes_rows(self, db_conn):
        upsert_products(db_conn, [make_row(id_product=1)])
        db_conn.commit()
        mark_missing_products_inactive(db_conn, [])
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM products")
            (count,) = cur.fetchone()
        assert count == 1  # still there, just inactive

    def test_no_grace_period_first_miss_is_immediate(self, db_conn):
        upsert_products(db_conn, [make_row(id_product=1)])
        db_conn.commit()
        # First catalog run where product 1 is missing -- immediately inactive.
        mark_missing_products_inactive(db_conn, [999])
        db_conn.commit()
        assert fetch_product(db_conn, 1)[2] is False


class TestGetNewProductIdsSince:
    def test_detects_new_products(self, db_conn):
        upsert_products(db_conn, [make_row(id_product=1)])
        db_conn.commit()
        new_ids = get_new_product_ids_since(db_conn, [1, 2, 3])
        assert set(new_ids) == {2, 3}

    def test_empty_input_returns_empty(self, db_conn):
        assert get_new_product_ids_since(db_conn, []) == []
